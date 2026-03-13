from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from ..domain.registry import TaskExecutionResult

if TYPE_CHECKING:
    from ..domain.models import TaskDefinition
    from ..domain.registry import Registry


def register(runner: Registry) -> None:
    @runner.handler("task3")
    def store_data(task: TaskDefinition, context: dict[str, Any]) -> TaskExecutionResult:
        logging.info(f"Executing task {task.name}")
        processed = context.get("outputs", {}).get("task2", {}).get("processed", [])
        return TaskExecutionResult(
            success=True,
            output={"task": task.name, "stored_count": len(processed)},
        )
