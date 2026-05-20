# Maestro AI — System Design

## Architecture Overview

Maestro AI implements a **distributed multi-agent orchestration model** where user queries are decomposed into subtasks, distributed across specialized AI agents via Redis queues, and results are streamed back in real time via WebSockets.

---

## Core Design Principles

1. **Stateless Agents** — Each agent is a pure function: input → output, no shared state
2. **Async-First** — Every operation is non-blocking (asyncio, Celery, WebSockets)
3. **Queue Decoupling** — Agents communicate through Redis queues, not direct calls
4. **Fault Isolation** — One agent failure does not cascade to others
5. **Horizontal Scalability** — Workers can be added without code changes

---

## Component Interactions

```
┌─────────────────────────────────────────────────────────────┐
│                     FRONTEND (React/Vite)                    │
│  QueryInput ──────────── HTTP POST /submit                   │
│  StreamLog  ──────────── WebSocket /stream/{id}              │
│  FinalReport ─────────── Rendered Markdown                   │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                  FASTAPI GATEWAY (main.py)                    │
│  /submit  → create_task() → background run_pipeline()        │
│  /status  → get_task() from SQLite                           │
│  /stream  → WebSocket + Redis pub/sub listener               │
│  /queues  → queue depth monitoring                           │
└──────────┬──────────────────────────┬────────────────────────┘
           │                          │
┌──────────▼──────────┐   ┌──────────▼──────────────────────┐
│   PLANNER AGENT     │   │      WEBSOCKET MANAGER           │
│   (Groq LLM)        │   │  ConnectionManager singleton     │
│   Stateless         │   │  broadcast() to all listeners    │
│   JSON output       │   └──────────────────────────────────┘
└──────────┬──────────┘
           │ plan[]
┌──────────▼──────────────────────────────────────────────────┐
│                    ORCHESTRATOR                               │
│  Phase 1: Dispatch retriever tasks (parallel)                │
│  Phase 2: Dispatch analyzer tasks (with retrieval context)   │
│  Phase 3: Dispatch writer tasks (with analysis context)      │
│  Phase 4: Dispatch validator task (with final report)        │
│  _wait_for_celery_jobs() — async polling, non-blocking       │
└──────┬───────────────────────────────────────────────────────┘
       │ apply_async()
┌──────▼──────────────────────────────────────────────────────┐
│                  REDIS (Message Broker)                       │
│  retriever_queue  analyzer_queue  writer_queue  failed_queue │
│  task:{id}:progress  (pub/sub channel per task)              │
└──────┬──────────────────────────────────────────────────────┘
       │ consume
┌──────▼──────────────────────────────────────────────────────┐
│                  CELERY WORKERS                               │
│  run_retriever()  run_analyzer()  run_writer()  run_validator│
│  max_retries=3  countdown=5*(2^attempt)                      │
│  publish_progress() → Redis pub/sub after each step         │
└──────────────────────────────────────────────────────────────┘
```

---

## Queue Design

| Queue | Producer | Consumer | Purpose |
|---|---|---|---|
| `retriever_queue` | Orchestrator | Retriever workers | Web/knowledge retrieval |
| `analyzer_queue` | Orchestrator | Analyzer workers | Data analysis |
| `writer_queue` | Orchestrator | Writer workers | Report generation |
| `validator_queue` | Orchestrator | Validator workers | QA check |
| `failed_queue` | Retry handler | Manual review | Dead-letter tasks |
| `task:{id}:progress` | All workers | WebSocket listener | Live streaming |

---

## Manual Batching System

The `BatchProcessor` class in `backend/batching/batch_processor.py` independently implements batching:

```python
BATCH_SIZE = 5
FLUSH_TIMEOUT = 2.0  # seconds

class BatchProcessor:
    async def add_task(task):
        batch.append(task)
        if len(batch) >= BATCH_SIZE:
            await flush()   # Size-based flush
        else:
            schedule timeout_flush()  # Timeout-based flush
```

**Benefits:**
- Reduces individual Celery task overhead by 5x
- Groups API calls to Groq (rate limit friendly)
- 2-second timeout ensures no task waits indefinitely

---

## Retry Strategy

```
Attempt 1 → fail → wait 5s
Attempt 2 → fail → wait 10s
Attempt 3 → fail → wait 20s
Attempt 4 → fail → dead_letter_queue + DB log
```

Implemented in both:
1. **Celery level**: `max_retries=3, countdown=5 * 2^retries`
2. **Application level**: `RetryHandler` class with `asyncio.wait_for` timeout

---

## Database Schema

```sql
-- Task lifecycle tracking
CREATE TABLE tasks (
    id TEXT PRIMARY KEY,
    user_query TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    subtask_count INTEGER DEFAULT 0,
    completed_subtasks INTEGER DEFAULT 0,
    created_at DATETIME,
    updated_at DATETIME
);

-- Per-agent outputs
CREATE TABLE task_results (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    agent TEXT NOT NULL,         -- retriever|analyzer|writer|validator
    subtask_index INTEGER,
    result TEXT,
    success BOOLEAN DEFAULT TRUE,
    created_at DATETIME
);

-- Dead-letter storage
CREATE TABLE failed_tasks (
    id TEXT PRIMARY KEY,
    task_id TEXT,
    agent TEXT,
    instruction TEXT,
    error TEXT,
    retries INTEGER,
    created_at DATETIME
);

-- Audit trail
CREATE TABLE logs (
    id TEXT PRIMARY KEY,
    task_id TEXT,
    level TEXT DEFAULT 'INFO',
    component TEXT,
    message TEXT,
    created_at DATETIME
);
```

---

## Streaming Protocol

WebSocket events follow this schema:

```typescript
interface StreamEvent {
  event: 'connected' | 'started' | 'completed' | 'failed' | 'phase' | 'final'
  agent: 'planner' | 'retriever' | 'analyzer' | 'writer' | 'validator' | 'orchestrator' | 'system'
  content: string          // Human-readable message
  task_id: string
  result_preview?: string  // First 200 chars of result
  plan?: SubTask[]         // Present on planner completion
  validation?: object      // Present on final event
  report?: string          // Full Markdown report on final event
}
```

---

## Scaling Strategy

### Horizontal Worker Scaling

```bash
# Add more workers for high load
docker-compose up --scale worker=10

# Redis automatically distributes tasks
# No code changes required
```

### Queue-Based Load Balancing

Redis LPOP/RPUSH provides FIFO ordering with automatic distribution across N workers consuming the same queue.

### Bottleneck Analysis (from SOP)

> As concurrent user requests increased, Redis queues became saturated, leading to delayed task execution.
>
> **Resolution:** Manual batching reduces queue saturation by grouping 5 tasks before processing, and concurrent worker pools (concurrency=4 per worker) maximize throughput.


---

## UI/UX & Layout Stability Strategy

To deliver an elite, zero-movement console interface, the client architecture enforces strict structural layout anchors:
- **Zero-Shift Controls:** Control inputs such as the `.run-btn` are bound to strictly fixed structural dimensions (`width: 290px`, `min-height: 62px`). This ensures that swapping states (e.g. from "RUN" to "PROCESSING" and displaying the loading spinner) never dynamically resizes elements, preventing layout flow wrap shifts on utility elements next to it.
- **Scroll Containment:** Replaced general page-level view jumps (like `.scrollIntoView()`) with bounded element-level scroll capping (`bodyRef.current.scrollTop = bodyRef.current.scrollHeight`). This isolates scrolling exclusively to the terminal logger, guaranteeing zero window viewport shifts.
- **Focus & Chasing Protection:** Implemented propagation halts (`e.stopPropagation()`) and focus resets (`document.activeElement.blur()`) on form submissions. This prevents the browser from automatically scroll-chasing inputs when they transition into disabled processing states.
- **Visual Stability:** Disabled smooth viewport behaviors and vertical translation animations (`translateY`) to ensure the dashboard layout coordinates remain perfectly constant.

---

## Trade-offs Made

| Decision | Alternative | Reason |
|---|---|---|
| Redis | Kafka | Simpler deployment, sufficient for demo scale |
| SQLite | PostgreSQL | Zero-config, free, no external DB needed |
| Celery | Kubernetes Jobs | Lower overhead, faster setup |
| Groq | OpenAI | Free tier, faster inference |

---

## Security Considerations

- API keys stored in `.env` (never committed)
- CORS configured for development (restrict in production)
- Input validation on all endpoints (max 2000 char queries)
- Sanitized outputs via Pydantic models
- Rate limiting recommended for production (via nginx/traefik)
