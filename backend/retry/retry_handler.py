"""
Retry Handler — wraps agent calls with exponential backoff retry logic.
Also handles timeouts and dead-letter routing on final failure.
"""

import asyncio
import functools
import logging
import os
from typing import Callable, Any, Coroutine, Optional
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
TASK_TIMEOUT = int(os.getenv("TASK_TIMEOUT", "60"))
BASE_BACKOFF = 5  # seconds


class RetryHandler:
    """
    Retry wrapper with:
    - Configurable max_retries
    - Exponential backoff (5s, 10s, 20s...)
    - asyncio.wait_for timeout
    - Dead-letter callback on final failure
    """

    def __init__(
        self,
        max_retries: int = MAX_RETRIES,
        timeout: int = TASK_TIMEOUT,
        backoff_base: int = BASE_BACKOFF,
        dead_letter_callback: Optional[Callable] = None,
    ):
        self.max_retries = max_retries
        self.timeout = timeout
        self.backoff_base = backoff_base
        self.dead_letter_callback = dead_letter_callback

    async def execute(
        self,
        func: Callable[..., Coroutine],
        *args,
        task_name: str = "task",
        dead_letter_payload: Optional[dict] = None,
        **kwargs,
    ) -> Any:
        """
        Execute an async callable with retry + timeout.
        
        Args:
            func: Async function to call
            task_name: Human-readable name for logging
            dead_letter_payload: Sent to dead-letter if all retries fail
        """
        last_error = None

        for attempt in range(1, self.max_retries + 2):  # +1 for initial attempt
            try:
                logger.info(f"[Retry] {task_name} — attempt {attempt}/{self.max_retries + 1}")

                # Wrap in asyncio.wait_for for timeout control
                result = await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=self.timeout
                )
                
                if attempt > 1:
                    logger.info(f"[Retry] {task_name} succeeded on attempt {attempt}")
                return result

            except asyncio.TimeoutError:
                last_error = f"Timeout after {self.timeout}s"
                logger.warning(f"[Retry] {task_name} timed out on attempt {attempt}")

            except Exception as e:
                last_error = str(e)
                logger.warning(f"[Retry] {task_name} failed on attempt {attempt}: {e}")

            if attempt <= self.max_retries:
                backoff = self.backoff_base * (2 ** (attempt - 1))
                logger.info(f"[Retry] Waiting {backoff}s before retry...")
                await asyncio.sleep(backoff)

        # All retries exhausted
        logger.error(f"[Retry] {task_name} permanently failed after {self.max_retries + 1} attempts: {last_error}")

        if self.dead_letter_callback and dead_letter_payload:
            try:
                await self.dead_letter_callback({
                    **dead_letter_payload,
                    "error": last_error,
                    "retries": self.max_retries,
                })
            except Exception as e:
                logger.error(f"[Retry] Dead-letter callback failed: {e}")

        raise RuntimeError(f"{task_name} failed after {self.max_retries + 1} attempts: {last_error}")


def with_retry(max_retries: int = MAX_RETRIES, timeout: int = TASK_TIMEOUT):
    """
    Decorator version of RetryHandler for simple use cases.
    
    Usage:
        @with_retry(max_retries=3, timeout=30)
        async def my_agent_call():
            ...
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            handler = RetryHandler(max_retries=max_retries, timeout=timeout)
            return await handler.execute(func, *args, task_name=func.__name__, **kwargs)
        return wrapper
    return decorator
