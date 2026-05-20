# 🎭 Maestro AI

> **Agentic AI System for Multi-Step Task Execution using Multi-Agent Orchestration**

A production-inspired, scalable, asynchronous, fault-tolerant AI orchestration platform that accepts complex user requests, decomposes them into subtasks, routes them to specialized AI agents, and streams real-time progress updates.

---

## 🌟 Features

| Feature | Description |
|---|---|
| **Multi-Agent Orchestration** | Planner → Retriever → Analyzer → Writer → Validator pipeline |
| **Async Task Queues** | Redis-backed Celery workers for non-blocking execution |
| **Real-Time Streaming** | WebSocket live progress updates per agent |
| **Manual Batching** | Independent batch processor (BATCH_SIZE=5, 2s timeout flush) |
| **Retry Handling** | Exponential backoff (3 retries), timeout management, dead-letter queue |
| **Fault Tolerance** | Graceful degradation, error logging, dead task storage |
| **Scalable Architecture** | Stateless agents, horizontal worker scaling |
| **React Frontend** | Premium dark-mode UI with live agent pipeline visualization |
| **Docker Ready** | Full docker-compose.yml for one-command deployment |
| **Free to Run** | Groq API (free tier) + Redis + SQLite + Celery |

---

## 🏗️ Architecture

```
User (React Frontend)
      │  HTTP / WebSocket
      ▼
FastAPI API Gateway
      │
      ├─ POST /submit     → Planner Agent → Redis queues
      ├─ GET  /status/{id} → SQLite lookup
      └─ WS   /stream/{id} → WebSocket manager (live push)
            │
            ▼
      Orchestrator (Phase-based execution)
            │
   ┌────────┼────────┬────────┐
   ▼        ▼        ▼        ▼
Retriever  Analyzer  Writer  Validator
(Celery)  (Celery)  (Celery) (Celery)
   │        │        │        │
   └────────┴────────┴────────┘
            │
      Redis Pub/Sub → WebSocket → Frontend
            │
      SQLite → Final Results
```

### Agent Pipeline Flow

```
User Query
↓ FastAPI accepts request
↓ Planner Agent (Groq LLM) decomposes into subtasks
↓ Tasks pushed to Redis named queues
↓ [Phase 1] Retriever workers execute (parallel)
↓ [Phase 2] Analyzer workers execute (with retrieval context)
↓ [Phase 3] Writer worker generates Markdown report
↓ [Phase 4] Validator checks completeness & quality
↓ Streaming layer pushes live events via WebSocket
↓ Final aggregated response returned to frontend
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Backend API** | FastAPI 0.111 + Uvicorn |
| **AI Models** | Groq API (llama-3.3-70b-versatile) |
| **Queue Broker** | Redis 7 |
| **Async Workers** | Celery 5.4 |
| **Streaming** | WebSockets (native FastAPI) |
| **Frontend** | React + Vite |
| **Database** | SQLite + SQLAlchemy async |
| **Containerization** | Docker + Docker Compose |
| **Deployment** | Render / Railway |

---

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Groq API key (free at [console.groq.com](https://console.groq.com))

### 1. Clone & Configure

```bash
git clone https://github.com/your-username/maestro-ai
cd maestro-ai

# Set your Groq API key
echo "GROQ_API_KEY=your_key_here" > .env
```

### 2. Run with Docker Compose

```bash
docker-compose up --build
```

Services will start:
- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Redis**: localhost:6379

### 3. Without Docker (Development)

```bash
# Terminal 1 — Start Redis
docker run -p 6379:6379 redis:7-alpine

# Terminal 2 — Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Terminal 3 — Celery Workers
cd backend
celery -A workers.celery_worker.celery_app worker --loglevel=info \
  -Q retriever_queue,analyzer_queue,writer_queue,validator_queue

# Terminal 4 — Frontend
cd frontend
npm install && npm run dev
```

---

## 📡 API Documentation

### POST `/submit`
Submit a complex task for multi-agent processing.

```json
// Request
{ "query": "Research AI in healthcare and write a report" }

// Response
{
  "task_id": "abc-123-...",
  "status": "pending",
  "message": "Task accepted. Connect to /stream/{task_id} for live updates."
}
```

### GET `/status/{task_id}`
Poll current task status.

```json
{
  "id": "abc-123",
  "status": "running",
  "subtask_count": 4,
  "completed_subtasks": 2
}
```

### GET `/results/{task_id}`
Get all results including final report and validation.

### WebSocket `/stream/{task_id}`
Connect for real-time streaming. Events:

```json
{ "event": "started",   "agent": "retriever", "content": "🔍 Retrieving..." }
{ "event": "completed", "agent": "retriever", "content": "✅ Done" }
{ "event": "final",     "agent": "system",    "report": "# Report..." }
```

### GET `/queues`
Monitor queue depths for all agent queues.

---

## 🗂️ Directory Structure

```
maestro-ai/
├── backend/
│   ├── agents/
│   │   ├── planner.py       # Task decomposition via Groq
│   │   ├── retriever.py     # Information retrieval
│   │   ├── analyzer.py      # Data analysis
│   │   ├── writer.py        # Report generation
│   │   └── validator.py     # Quality assurance
│   ├── orchestrator/
│   │   └── orchestrator.py  # Pipeline coordinator
│   ├── queues/
│   │   └── redis_queue.py   # Redis queue manager
│   ├── workers/
│   │   └── celery_worker.py # Celery async tasks
│   ├── streaming/
│   │   └── websocket_manager.py
│   ├── batching/
│   │   └── batch_processor.py  # Manual batch system
│   ├── retry/
│   │   └── retry_handler.py    # Retry + dead-letter
│   ├── db/
│   │   └── database.py     # SQLite async ORM
│   ├── main.py             # FastAPI gateway
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── App.jsx          # Main React app
│       └── index.css        # Design system
├── docker-compose.yml
├── system_design.md
└── README.md
```

---

## 🔧 Configuration

| Variable | Default | Description |
|---|---|---|
| `GROQ_API_KEY` | required | Your Groq API key |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Groq model to use |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection URL |
| `BATCH_SIZE` | `5` | Tasks per batch |
| `MAX_RETRIES` | `3` | Max retry attempts |
| `TASK_TIMEOUT` | `60` | Per-task timeout (seconds) |

---

## 📈 Scalability

The system scales horizontally:

```bash
# Scale to 10 Celery workers
docker-compose up --scale worker=10
```

- **Stateless agents** — Any worker can process any task
- **Redis distributes** tasks automatically across workers
- **Independent execution** — No shared state between workers

---

## 🛡️ Fault Tolerance

| Problem | Solution |
|---|---|
| Worker crash | `task_acks_late=True` — task re-queued |
| API timeout | `asyncio.wait_for` with 60s limit |
| Queue overload | Manual batching reduces throughput pressure |
| Max retries exceeded | Dead letter queue + DB storage |
| Streaming disconnect | Pub/Sub reconnect on new WS connect |

---

## 🔮 Future Improvements

- Kafka instead of Redis for enterprise scale
- Kubernetes deployment with auto-scaling
- Vector databases for long-term agent memory
- Agent-to-agent negotiation protocols
- Monitoring dashboard (Prometheus + Grafana)
- Multi-modal agents (image/audio processing)
- Autonomous recursive planning

---

## 👨‍💻 Author

Built as a production-inspired demonstration of distributed AI orchestration, async programming, and scalable system design.

> *"The final system resembles a lightweight distributed AI operating system capable of orchestrating multiple intelligent agents collaboratively in real time."*
