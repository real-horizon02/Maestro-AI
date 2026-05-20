"""
Manual Batch Processor — groups tasks before execution to reduce overhead.
Implements BATCH_SIZE-based flushing with a timeout fallback.
Independently implemented as required by the SOP.
"""

import asyncio
import logging
import os
from typing import List, Callable, Any, Coroutine
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

BATCH_SIZE = int(os.getenv("BATCH_SIZE", "5"))
FLUSH_TIMEOUT = 2.0  # seconds — auto-flush even if batch not full


class BatchProcessor:
    """
    Accumulates tasks and processes them in batches.
    Flushes when BATCH_SIZE is reached OR after FLUSH_TIMEOUT seconds.
    
    Usage:
        processor = BatchProcessor(handler=my_async_handler)
        await processor.add_task(task_payload)
    """

    def __init__(self, handler: Callable[[List[Any]], Coroutine], batch_size: int = BATCH_SIZE):
        self._batch: List[Any] = []
        self._lock = asyncio.Lock()
        self._handler = handler
        self._batch_size = batch_size
        self._flush_task: asyncio.Task | None = None
        self._processed_count = 0

    async def add_task(self, task: Any):
        """Add a task to the batch. Auto-flushes when batch is full."""
        async with self._lock:
            self._batch.append(task)
            logger.debug(f"[Batch] Added task. Batch size: {len(self._batch)}/{self._batch_size}")

            if len(self._batch) >= self._batch_size:
                # Cancel any pending timeout flush
                if self._flush_task and not self._flush_task.done():
                    self._flush_task.cancel()
                await self._flush()
            else:
                # Schedule timeout-based flush
                if self._flush_task is None or self._flush_task.done():
                    self._flush_task = asyncio.create_task(self._timeout_flush())

    async def _timeout_flush(self):
        """Flush after timeout if batch hasn't filled."""
        await asyncio.sleep(FLUSH_TIMEOUT)
        async with self._lock:
            if self._batch:
                logger.info(f"[Batch] Timeout flush triggered with {len(self._batch)} tasks")
                await self._flush()

    async def _flush(self):
        """Process current batch and reset. Must be called under lock."""
        if not self._batch:
            return

        batch_to_process = self._batch.copy()
        self._batch.clear()
        self._processed_count += len(batch_to_process)

        logger.info(f"[Batch] Processing batch of {len(batch_to_process)} tasks (total processed: {self._processed_count})")

        try:
            await self._handler(batch_to_process)
        except Exception as e:
            logger.error(f"[Batch] Error processing batch: {e}")
            raise

    async def flush_all(self):
        """Force flush all remaining tasks immediately."""
        async with self._lock:
            if self._batch:
                await self._flush()

    @property
    def pending_count(self) -> int:
        return len(self._batch)

    @property
    def total_processed(self) -> int:
        return self._processed_count


# ─── Example batch handler used by orchestrator ───────────────────────────────

async def default_subtask_batch_handler(tasks: List[dict]):
    """
    Default handler: logs batch info.
    In production, this dispatches to Celery workers.
    """
    logger.info(f"[Batch] Dispatching {len(tasks)} subtasks to workers")
    for task in tasks:
        logger.info(f"  → [{task.get('agent', '?')}] {task.get('instruction', '')[:60]}")
