"""
Orchestrator — coordinates agent execution pipeline.
Receives planner output, dispatches Celery tasks in dependency order,
monitors completion, and aggregates final response.
"""

import asyncio
import logging
from typing import List, Dict
from db.database import update_task_status, get_task_results, save_failed_task, write_log
from queues.redis_queue import publish_progress, push_to_dead_letter

logger = logging.getLogger(__name__)


async def orchestrate(task_id: str, user_query: str, plan: List[Dict]):
    """
    Main orchestration function.
    
    Args:
        task_id: Unique task identifier
        user_query: Original user query (for validator context)
        plan: List of subtask dicts from planner [{task_id, agent, instruction, depends_on}]
    """
    from workers.celery_worker import run_retriever, run_analyzer, run_writer, run_validator

    logger.info(f"[Orchestrator] Starting orchestration for task {task_id} with {len(plan)} subtasks")

    await update_task_status(task_id, "running", subtask_count=len(plan))
    await write_log(task_id, "orchestrator", f"Orchestration started with {len(plan)} subtasks")

    publish_progress(task_id, {
        "event": "started",
        "agent": "orchestrator",
        "content": f"Orchestration started — {len(plan)} subtasks planned",
        "task_id": task_id,
        "plan": plan,
    })

    # ── Separate tasks by agent type ──────────────────────────────────────────
    retriever_tasks = [t for t in plan if t["agent"] == "retriever"]
    analyzer_tasks = [t for t in plan if t["agent"] == "analyzer"]
    writer_tasks = [t for t in plan if t["agent"] == "writer"]
    validator_tasks = [t for t in plan if t["agent"] == "validator"]

    # ── Phase 1: Retrieval (parallel) ─────────────────────────────────────────
    publish_progress(task_id, {
        "event": "phase",
        "agent": "orchestrator",
        "content": f"Phase 1: Retrieving information ({len(retriever_tasks)} tasks)",
        "task_id": task_id,
    })

    retriever_jobs = []
    for t in retriever_tasks:
        job = run_retriever.apply_async(
            args=[task_id, t["task_id"], t["instruction"]],
            queue="retriever_queue",
        )
        retriever_jobs.append(job)

    # Wait for all retriever tasks to complete
    retrieval_results = await _wait_for_celery_jobs(retriever_jobs, timeout=120)
    retrieved_context = "\n\n".join(
        r.get("result", "") for r in retrieval_results if isinstance(r, dict) and r.get("status") == "success"
    )

    # ── Phase 2: Analysis (parallel, with retrieval context) ──────────────────
    publish_progress(task_id, {
        "event": "phase",
        "agent": "orchestrator",
        "content": f"Phase 2: Analyzing data ({len(analyzer_tasks)} tasks)",
        "task_id": task_id,
    })

    analyzer_jobs = []
    for t in analyzer_tasks:
        job = run_analyzer.apply_async(
            args=[task_id, t["task_id"], t["instruction"], retrieved_context],
            queue="analyzer_queue",
        )
        analyzer_jobs.append(job)

    analysis_results = await _wait_for_celery_jobs(analyzer_jobs, timeout=120)
    analysis_context = "\n\n".join(
        r.get("result", "") for r in analysis_results if isinstance(r, dict) and r.get("status") == "success"
    )

    # ── Phase 3: Writing (sequential, uses retrieval + analysis) ──────────────
    publish_progress(task_id, {
        "event": "phase",
        "agent": "orchestrator",
        "content": f"Phase 3: Generating report ({len(writer_tasks)} tasks)",
        "task_id": task_id,
    })

    final_report = ""
    writer_jobs = []
    for t in writer_tasks:
        job = run_writer.apply_async(
            args=[task_id, t["task_id"], t["instruction"], analysis_context, retrieved_context],
            queue="writer_queue",
        )
        writer_jobs.append(job)

    writer_results = await _wait_for_celery_jobs(writer_jobs, timeout=120)
    if writer_results:
        last = writer_results[-1]
        final_report = last.get("result", "") if isinstance(last, dict) else ""

    # ── Phase 4: Validation ───────────────────────────────────────────────────
    if not validator_tasks:
        # Auto-add a validation step even if planner forgot
        validator_tasks = [{"task_id": len(plan) + 1, "agent": "validator", "instruction": "Validate the report"}]

    publish_progress(task_id, {
        "event": "phase",
        "agent": "orchestrator",
        "content": "Phase 4: Validating output",
        "task_id": task_id,
    })

    for t in validator_tasks:
        job = run_validator.apply_async(
            args=[task_id, t["task_id"], user_query, final_report],
            queue="validator_queue",
        )
        await _wait_for_celery_jobs([job], timeout=60)

    logger.info(f"[Orchestrator] Task {task_id} pipeline complete")


async def _wait_for_celery_jobs(jobs: list, timeout: int = 120) -> list:
    """
    Async-friendly polling for Celery AsyncResult completion.
    Returns list of results (or empty dicts on failure).
    """
    if not jobs:
        return []

    deadline = asyncio.get_event_loop().time() + timeout
    results = []

    pending = list(jobs)
    completed_results = {}

    while pending and asyncio.get_event_loop().time() < deadline:
        still_pending = []
        for job in pending:
            if job.ready():
                try:
                    if job.failed():
                        # job.result is the exception object — store empty dict
                        completed_results[job.id] = {}
                    else:
                        result = job.result
                        # Guard: result must be a dict (never let exceptions leak through)
                        if isinstance(result, dict):
                            completed_results[job.id] = result
                        else:
                            completed_results[job.id] = {}
                except Exception:
                    completed_results[job.id] = {}
            else:
                still_pending.append(job)
        pending = still_pending

        if pending:
            await asyncio.sleep(0.5)

    # Collect in original order
    for job in jobs:
        results.append(completed_results.get(job.id, {}))

    return results
