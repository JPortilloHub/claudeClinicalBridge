"""
Workflow execution utilities for the clinical pipeline.

Provides retry logic with exponential backoff and structured
step execution for agent pipeline phases.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from src.python.orchestration.state import PhaseResult
from src.python.utils.config import settings
from src.python.utils.logging import get_logger

logger = get_logger(__name__)


def run_with_retry(
    fn: Callable[..., dict[str, Any]],
    *args: Any,
    max_retries: int | None = None,
    base_delay: float = 1.0,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Execute a function with exponential backoff retry on failure.

    Only retries when the result contains an 'error' key (agent-level errors).
    Does not retry on exceptions — those propagate immediately.

    Args:
        fn: The callable to execute (typically agent.run or agent method)
        *args: Positional arguments for fn
        max_retries: Maximum retry attempts (defaults to settings.agent_max_retries)
        base_delay: Base delay in seconds between retries (doubles each attempt)
        **kwargs: Keyword arguments for fn

    Returns:
        The function result dict
    """
    if max_retries is None:
        max_retries = settings.agent_max_retries

    last_result: dict[str, Any] = {}

    for attempt in range(max_retries + 1):
        result = fn(*args, **kwargs)

        if "error" not in result:
            return result

        last_result = result

        if attempt < max_retries:
            delay = base_delay * (2**attempt)
            logger.warning(
                "agent_retry",
                agent=result.get("agent", "unknown"),
                attempt=attempt + 1,
                max_retries=max_retries,
                error=result.get("error"),
                delay_seconds=delay,
            )
            time.sleep(delay)

    logger.error(
        "agent_retries_exhausted",
        agent=last_result.get("agent", "unknown"),
        max_retries=max_retries,
        final_error=last_result.get("error"),
    )
    return last_result


def execute_phase(
    phase: PhaseResult,
    fn: Callable[..., dict[str, Any]],
    *args: Any,
    use_retry: bool = True,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Execute a pipeline phase with state tracking and optional retry.

    Updates the PhaseResult with timing and status information.

    Args:
        phase: The PhaseResult to update
        fn: The agent method to call
        *args: Positional arguments for fn
        use_retry: Whether to use retry logic
        **kwargs: Keyword arguments for fn

    Returns:
        The agent result dict
    """
    phase.mark_running()

    logger.info(
        "phase_started",
        phase=phase.phase_name,
        agent=phase.agent_name,
    )

    try:
        if use_retry:
            result = run_with_retry(fn, *args, **kwargs)
        else:
            result = fn(*args, **kwargs)
    except Exception as e:
        error_msg = f"Unexpected error: {e}"
        phase.mark_failed(error_msg)
        logger.error(
            "phase_exception",
            phase=phase.phase_name,
            agent=phase.agent_name,
            error=error_msg,
        )
        raise

    if "error" in result:
        phase.mark_failed(result["error"])
        logger.error(
            "phase_failed",
            phase=phase.phase_name,
            agent=phase.agent_name,
            error=result["error"],
        )
    else:
        phase.mark_completed(
            content=result.get("content", ""),
            usage=result.get("usage", {}),
        )
        logger.info(
            "phase_completed",
            phase=phase.phase_name,
            agent=phase.agent_name,
            duration_seconds=phase.duration_seconds,
        )

    return result
