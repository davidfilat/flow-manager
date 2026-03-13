from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class TaskHandler(Protocol):
    def __call__(self, task: Any, context: dict[str, Any]) -> TaskExecutionResult: ...


@dataclass(frozen=True)
class TaskExecutionResult:
    success: bool
    output: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


def _default_handler(task: Any, context: dict[str, Any]) -> TaskExecutionResult:
    return TaskExecutionResult(
        success=False,
        error=f"no handler registered for task '{task.name}'",
    )


class Registry:
    def __init__(self) -> None:
        self._handlers: dict[str, TaskHandler] = {}

    def handler(self, task_name: str) -> Callable[[TaskHandler], TaskHandler]:
        def decorator(fn: TaskHandler) -> TaskHandler:
            self._handlers[task_name] = fn
            return fn

        return decorator

    def register(self, task_name: str, fn: TaskHandler) -> None:
        self._handlers[task_name] = fn

    def get(self, task_name: str) -> TaskHandler:
        return self._handlers.get(task_name, _default_handler)

    def __contains__(self, task_name: str) -> bool:
        return task_name in self._handlers

    def clear(self) -> None:
        self._handlers.clear()
