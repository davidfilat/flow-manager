from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from ..domain.registry import TaskExecutionResult

if TYPE_CHECKING:
    from ..domain.models import TaskDefinition
    from ..domain.registry import Registry


def register(runner: Registry) -> None:
    @runner.handler("task2")
    def process_data(task: TaskDefinition, context: dict[str, Any]) -> TaskExecutionResult:
        logging.info(f"Executing task {task.name}")
        fetched = context.get("outputs", {}).get("task1", {}).get("data", {})
        records = fetched.get("records", [])
        processed = [value * 2 for value in records]
        return TaskExecutionResult(success=True, output={"task": task.name, "processed": processed})
