"""
Maestro AI — FastAPI API Gateway
Central entry point for all requests.
Handles: task submission, status polling, WebSocket streaming.
"""

import asyncio
import json
import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import Optional

import redis as redis_sync
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Ensure backend root is in path
sys.path.insert(0, os.path.dirname(__file__))

load_dotenv()

from db.database import init_db, create_task, get_task, get_task_results
from streaming.websocket_manager import manager
from queues.redis_queue import subscribe_progress, get_all_queue_stats, REDIS_URL

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ─── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize DB on startup."""
    logger.info("Maestro AI starting up...")
    await init_db()
    logger.info("Database initialized")
    yield
    logger.info("Maestro AI shutting down")


# ─── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Maestro AI",
    description="Agentic AI System for Multi-Step Task Execution",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Request Models ───────────────────────────────────────────────────────────

class SubmitRequest(BaseModel):
    query: str
    priority: Optional[str] = "normal"


class SubmitResponse(BaseModel):
    task_id: str
    status: str
    message: str


# ─── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
async def root():
    return {
        "service": "Maestro AI",
        "status": "running",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
async def health():
    """Health check endpoint."""
    try:
        url = REDIS_URL
        if url.startswith("rediss://") and "ssl_cert_reqs" not in url:
            separator = "&" if "?" in url else "?"
            url = f"{url}{separator}ssl_cert_reqs=none"
        r = redis_sync.from_url(url, decode_responses=True)
        r.ping()
        redis_ok = True
    except Exception:
        redis_ok = False

    return {
        "status": "healthy" if redis_ok else "degraded",
        "redis": "connected" if redis_ok else "disconnected",
        "database": "sqlite",
    }


@app.post("/submit", response_model=SubmitResponse, tags=["Tasks"])
async def submit_task(request: SubmitRequest, background_tasks: BackgroundTasks):
    """
    Submit a complex user query for multi-agent processing.
    Returns a task_id for tracking.
    """
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    if len(request.query) > 2000:
        raise HTTPException(status_code=400, detail="Query too long (max 2000 chars)")

    # Create task in DB
    task_id = await create_task(request.query)
    logger.info(f"[API] New task created: {task_id} — '{request.query[:60]}...'")

    # Start orchestration pipeline in background
    background_tasks.add_task(run_pipeline, task_id, request.query)

    return SubmitResponse(
        task_id=task_id,
        status="pending",
        message="Task accepted. Connect to /stream/{task_id} for live updates.",
    )


@app.get("/status/{task_id}", tags=["Tasks"])
async def get_status(task_id: str):
    """
    Get current task status and metadata.
    """
    task = await get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    results = await get_task_results(task_id)

    return {
        **task,
        "results_count": len(results),
        "agents_completed": list({r["agent"] for r in results}),
    }


@app.get("/results/{task_id}", tags=["Tasks"])
async def get_results(task_id: str):
    """
    Get all agent results for a completed task.
    """
    task = await get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    results = await get_task_results(task_id)

    # Find final report (writer output)
    final_report = next((r["result"] for r in results if r["agent"] == "writer"), None)

    # Find validation
    import json as json_module
    validation = None
    val_result = next((r["result"] for r in results if r["agent"] == "validator"), None)
    if val_result:
        try:
            validation = json_module.loads(val_result)
        except Exception:
            validation = {"summary": val_result}

    return {
        "task": task,
        "results": results,
        "final_report": final_report,
        "validation": validation,
    }


@app.get("/queues", tags=["Monitoring"])
async def queue_stats():
    """Get current queue depths for all agent queues."""
    return get_all_queue_stats()


@app.websocket("/stream/{task_id}")
async def stream_task(websocket: WebSocket, task_id: str):
    """
    WebSocket endpoint for real-time task progress streaming.
    Subscribes to Redis pub/sub channel for the task.
    """
    await manager.connect(task_id, websocket)
    logger.info(f"[WS] Client connected for task {task_id}")

    # Send initial status
    task = await get_task(task_id)
    if task:
        await websocket.send_json({
            "event": "connected",
            "agent": "system",
            "content": f"Connected to task stream. Status: {task['status']}",
            "task_id": task_id,
            "task": task,
        })

    # If task is already completed, send results immediately
    if task and task["status"] == "completed":
        results = await get_task_results(task_id)
        final_report = next((r["result"] for r in results if r["agent"] == "writer"), "")
        await websocket.send_json({
            "event": "final",
            "agent": "system",
            "content": "Task already completed.",
            "task_id": task_id,
            "report": final_report,
        })
        manager.disconnect(task_id, websocket)
        return

    # Subscribe to Redis pub/sub for live events
    try:
        pubsub = subscribe_progress(task_id)
        
        loop = asyncio.get_event_loop()
        
        while True:
            try:
                # Poll Redis pubsub in a thread to avoid blocking
                message = await loop.run_in_executor(
                    None, lambda: pubsub.get_message(timeout=1.0)
                )

                if message and message["type"] == "message":
                    data = json.loads(message["data"])
                    await websocket.send_json(data)

                    # Close stream when task is done
                    if data.get("event") == "final":
                        break

                # Check if client disconnected
                await asyncio.sleep(0.1)

            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"[WS] Stream error: {e}")
                break

    except WebSocketDisconnect:
        logger.info(f"[WS] Client disconnected from task {task_id}")
    finally:
        manager.disconnect(task_id, websocket)
        try:
            pubsub.unsubscribe()
        except Exception:
            pass


# ─── Pipeline Runner ──────────────────────────────────────────────────────────

async def run_pipeline(task_id: str, user_query: str):
    """
    Background pipeline: plan → orchestrate.
    Runs in FastAPI background task.
    """
    from agents.planner import plan_tasks
    from orchestrator.orchestrator import orchestrate
    from db.database import update_task_status, write_log
    from queues.redis_queue import publish_progress

    try:
        logger.info(f"[Pipeline] Starting for task {task_id}")

        # Step 1: Plan
        publish_progress(task_id, {
            "event": "started",
            "agent": "planner",
            "content": "Planning task decomposition...",
            "task_id": task_id,
        })

        plan = plan_tasks(user_query)
        logger.info(f"[Pipeline] Plan generated: {len(plan)} subtasks")

        publish_progress(task_id, {
            "event": "completed",
            "agent": "planner",
            "content": f"Plan ready — {len(plan)} subtasks identified",
            "task_id": task_id,
            "plan": plan,
        })

        await write_log(task_id, "planner", f"Plan generated: {len(plan)} subtasks")

        # Step 2: Orchestrate
        await orchestrate(task_id, user_query, plan)

    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        logger.error(f"[Pipeline] Fatal error for task {task_id}: {type(e).__name__}: {e}\n{tb}")
        await update_task_status(task_id, "failed")
        publish_progress(task_id, {
            "event": "failed",
            "agent": "system",
            "content": f"FATAL — {type(e).__name__}: {str(e)[:200]}",
            "task_id": task_id,
        })
