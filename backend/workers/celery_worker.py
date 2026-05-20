"""
Celery Worker — async task execution engine.
Defines Celery tasks for each agent: retriever, analyzer, writer, validator.
Wired to Redis as broker and result backend.
"""

import os
import sys

# Ensure backend root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import asyncio
import logging

from celery import Celery
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# ─── Celery App ───────────────────────────────────────────────────────────────

celery_app = Celery(
    "maestro",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_acks_late=True,              # Ack only after successful execution
    task_reject_on_worker_lost=True,  # Requeue if worker crashes
    worker_prefetch_multiplier=1,     # Fair distribution across workers
    task_routes={
        "workers.celery_worker.run_retriever": {"queue": "retriever_queue"},
        "workers.celery_worker.run_analyzer": {"queue": "analyzer_queue"},
        "workers.celery_worker.run_writer": {"queue": "writer_queue"},
        "workers.celery_worker.run_validator": {"queue": "validator_queue"},
    },
    task_default_retry_delay=5,
)


def run_async(coro):
    """Helper to run async code inside sync Celery tasks."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


# ─── Celery Tasks ─────────────────────────────────────────────────────────────

@celery_app.task(bind=True, max_retries=3, name="workers.celery_worker.run_retriever")
def run_retriever(self, task_id: str, subtask_index: int, instruction: str):
    """Celery task: run the retriever agent."""
    from agents.retriever import retrieve
    from db.database import save_task_result, increment_completed_subtasks, write_log
    from queues.redis_queue import publish_progress

    try:
        logger.info(f"[Retriever] task={task_id} idx={subtask_index}")
        publish_progress(task_id, {
            "event": "started",
            "agent": "retriever",
            "content": f"Retrieving information...",
            "task_id": task_id,
        })

        result = retrieve(instruction)

        run_async(save_task_result(task_id, "retriever", subtask_index, result))
        run_async(increment_completed_subtasks(task_id))
        run_async(write_log(task_id, "retriever", f"Retrieval completed for subtask {subtask_index}"))

        publish_progress(task_id, {
            "event": "completed",
            "agent": "retriever",
            "content": f"Retrieval complete",
            "task_id": task_id,
            "result_preview": result[:200] + "..." if len(result) > 200 else result,
        })

        return {"status": "success", "result": result}

    except Exception as exc:
        logger.error(f"[Retriever] Failed: {exc}")
        publish_progress(task_id, {
            "event": "failed",
            "agent": "retriever",
            "content": f"Retriever error: {str(exc)[:100]}",
            "task_id": task_id,
        })
        raise self.retry(exc=exc, countdown=5 * (2 ** self.request.retries))


@celery_app.task(bind=True, max_retries=3, name="workers.celery_worker.run_analyzer")
def run_analyzer(self, task_id: str, subtask_index: int, instruction: str, context: str = ""):
    """Celery task: run the analyzer agent."""
    from agents.analyzer import analyze
    from db.database import save_task_result, increment_completed_subtasks, write_log
    from queues.redis_queue import publish_progress

    try:
        logger.info(f"[Analyzer] task={task_id} idx={subtask_index}")
        publish_progress(task_id, {
            "event": "started",
            "agent": "analyzer",
            "content": "Analyzing retrieved information...",
            "task_id": task_id,
        })

        result = analyze(instruction, context)

        run_async(save_task_result(task_id, "analyzer", subtask_index, result))
        run_async(increment_completed_subtasks(task_id))
        run_async(write_log(task_id, "analyzer", f"Analysis completed for subtask {subtask_index}"))

        publish_progress(task_id, {
            "event": "completed",
            "agent": "analyzer",
            "content": "Analysis complete",
            "task_id": task_id,
            "result_preview": result[:200] + "..." if len(result) > 200 else result,
        })

        return {"status": "success", "result": result}

    except Exception as exc:
        logger.error(f"[Analyzer] Failed: {exc}")
        publish_progress(task_id, {
            "event": "failed",
            "agent": "analyzer",
            "content": f"Analyzer error: {str(exc)[:100]}",
            "task_id": task_id,
        })
        raise self.retry(exc=exc, countdown=5 * (2 ** self.request.retries))


@celery_app.task(bind=True, max_retries=3, name="workers.celery_worker.run_writer")
def run_writer(self, task_id: str, subtask_index: int, instruction: str, analysis: str = "", retrieved_data: str = ""):
    """Celery task: run the writer agent."""
    from agents.writer import write_report
    from db.database import save_task_result, increment_completed_subtasks, write_log
    from queues.redis_queue import publish_progress

    try:
        logger.info(f"[Writer] task={task_id} idx={subtask_index}")
        publish_progress(task_id, {
            "event": "started",
            "agent": "writer",
            "content": "Generating report...",
            "task_id": task_id,
        })

        result = write_report(instruction, analysis, retrieved_data)

        run_async(save_task_result(task_id, "writer", subtask_index, result))
        run_async(increment_completed_subtasks(task_id))
        run_async(write_log(task_id, "writer", f"Report generation completed for subtask {subtask_index}"))

        publish_progress(task_id, {
            "event": "completed",
            "agent": "writer",
            "content": "Report generated",
            "task_id": task_id,
            "result_preview": result[:200] + "..." if len(result) > 200 else result,
        })

        return {"status": "success", "result": result}

    except Exception as exc:
        logger.error(f"[Writer] Failed: {exc}")
        publish_progress(task_id, {
            "event": "failed",
            "agent": "writer",
            "content": f"Writer error: {str(exc)[:100]}",
            "task_id": task_id,
        })
        raise self.retry(exc=exc, countdown=5 * (2 ** self.request.retries))


@celery_app.task(bind=True, max_retries=3, name="workers.celery_worker.run_validator")
def run_validator(self, task_id: str, subtask_index: int, original_query: str, report: str):
    """Celery task: run the validator agent."""
    from agents.validator import validate
    from db.database import save_task_result, increment_completed_subtasks, update_task_status, write_log
    from queues.redis_queue import publish_progress
    import json

    try:
        logger.info(f"[Validator] task={task_id} idx={subtask_index}")
        publish_progress(task_id, {
            "event": "started",
            "agent": "validator",
            "content": "Validating report quality...",
            "task_id": task_id,
        })

        validation = validate(original_query, report)
        result_str = json.dumps(validation)

        run_async(save_task_result(task_id, "validator", subtask_index, result_str))
        run_async(increment_completed_subtasks(task_id))
        run_async(update_task_status(task_id, "completed"))
        run_async(write_log(task_id, "validator", f"Validation completed. Score: {validation.get('score', 'N/A')}"))

        score = validation.get("score", 0)
        valid = validation.get("valid", True)

        publish_progress(task_id, {
            "event": "completed",
            "agent": "validator",
            "content": f"Validation complete — Score: {score}/100",
            "task_id": task_id,
            "validation": validation,
        })

        publish_progress(task_id, {
            "event": "final",
            "agent": "system",
            "content": "Task complete. Final report is ready.",
            "task_id": task_id,
            "report": report,
            "validation": validation,
        })

        return {"status": "success", "validation": validation, "report": report}

    except Exception as exc:
        logger.error(f"[Validator] Failed: {exc}")
        publish_progress(task_id, {
            "event": "failed",
            "agent": "validator",
            "content": f"Validator error: {str(exc)[:100]}",
            "task_id": task_id,
        })
        raise self.retry(exc=exc, countdown=5 * (2 ** self.request.retries))
