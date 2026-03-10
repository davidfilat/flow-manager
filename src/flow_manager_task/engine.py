from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from .models import FlowDefinition, RunStatus, TaskDefinition


class EventType:
    TASK_SUCCEEDED = "TASK_SUCCEEDED"
    TASK_FAILED = "TASK_FAILED"


@runtime_checkable
class TaskHandler(Protocol):
    def __call__(self, task: TaskDefinition, context: dict[str, Any]) -> TaskExecutionResult: ...


@dataclass(frozen=True)
class State:
    name: str
    is_terminal: bool = False
    status_on_enter: RunStatus | None = None
    task: TaskDefinition | None = None


@dataclass(frozen=True)
class TaskExecutionResult:
    success: bool
    output: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


class TaskRunner:
    def __init__(self) -> None:
        self._registry: dict[str, TaskHandler] = {
            "task1": self._task_fetch_data,
            "task2": self._task_process_data,
            "task3": self._task_store_data,
        }

    def register(self, task_name: str, handler: TaskHandler) -> None:
        self._registry[task_name] = handler

    def execute(self, task: TaskDefinition, context: dict[str, Any]) -> TaskExecutionResult:
        handler = self._registry.get(task.name, self._task_default)
        return handler(task, context)

    def _task_fetch_data(
        self, task: TaskDefinition, context: dict[str, Any]
    ) -> TaskExecutionResult:
        source = context.get("source", "sample-source")
        payload = {"records": [1, 2, 3], "source": source}
        return TaskExecutionResult(success=True, output={"task": task.name, "data": payload})

    def _task_process_data(
        self, task: TaskDefinition, context: dict[str, Any]
    ) -> TaskExecutionResult:
        fetched = context.get("outputs", {}).get("task1", {}).get("data", {})
        records = fetched.get("records", [])
        processed = [value * 2 for value in records]
        return TaskExecutionResult(success=True, output={"task": task.name, "processed": processed})

    def _task_store_data(
        self, task: TaskDefinition, context: dict[str, Any]
    ) -> TaskExecutionResult:
        processed = context.get("outputs", {}).get("task2", {}).get("processed", [])
        return TaskExecutionResult(
            success=True,
            output={"task": task.name, "stored_count": len(processed)},
        )

    def _task_default(self, task: TaskDefinition, context: dict[str, Any]) -> TaskExecutionResult:
        return TaskExecutionResult(success=True, output={"task": task.name})


class FlowStateMachine:
    def __init__(self, flow: FlowDefinition) -> None:
        self.flow = flow
        self.states = self._build_states(flow)
        self._by_source: dict[str, dict[str, str]] = {}
        for condition in flow.conditions:
            self._by_source.setdefault(condition.source_task, {})[EventType.TASK_SUCCEEDED] = (
                self._normalize(condition.target_task_success, failure_edge=False)
            )
            self._by_source.setdefault(condition.source_task, {})[EventType.TASK_FAILED] = (
                self._normalize(condition.target_task_failure, failure_edge=True)
            )

    @staticmethod
    def _normalize(target: str, failure_edge: bool = False) -> str:
        if target.strip() == "end":
            return "END_FAILED" if failure_edge else "END_SUCCESS"
        return target.strip()

    def _build_states(self, flow: FlowDefinition) -> dict[str, State]:
        states: dict[str, State] = {
            task.name: State(name=task.name, task=task) for task in flow.tasks
        }
        states["END_SUCCESS"] = State(
            name="END_SUCCESS", is_terminal=True, status_on_enter=RunStatus.END_SUCCESS
        )
        states["END_FAILED"] = State(
            name="END_FAILED", is_terminal=True, status_on_enter=RunStatus.END_FAILED
        )
        return states

    def initial_state(self) -> str:
        return self.flow.start_task

    def transition(self, state_name: str, event: str) -> str:
        target = self._by_source.get(state_name, {}).get(event)
        if target is not None:
            return target
        return "END_SUCCESS" if event == EventType.TASK_SUCCEEDED else "END_FAILED"

    def state(self, name: str) -> State:
        state = self.states.get(name)
        if state is None:
            raise KeyError(f"Unknown state '{name}'")
        return state
