from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

from ..domain.registry import TaskExecutionResult

if TYPE_CHECKING:
    from ..domain.models import TaskDefinition
    from ..domain.registry import Registry


def register(runner: Registry) -> None:
    @runner.handler("task1")
    def fetch_data(task: TaskDefinition, context: dict[str, Any]) -> TaskExecutionResult:
        logging.info(f"Executing task {task.name}")

        source = context.get("source", "sample-source")
        payload = {"records": [1, 2, 3], "source": source}
        time.sleep(30)  # simulate long-running I/O
        return TaskExecutionResult(
            success=True,
            output={"task": task.name, "data": payload},
        )
