from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from .models import FlowDefinition, RunStatus, TaskDefinition
from .registry import Registry, TaskExecutionResult, TaskHandler


class UnregisteredTaskError(ValueError):
    pass


class EventType(StrEnum):
    TASK_SUCCEEDED = "TASK_SUCCEEDED"
    TASK_FAILED = "TASK_FAILED"


@dataclass(frozen=True)
class State:
    name: str
    is_terminal: bool = False
    status_on_enter: RunStatus | None = None
    task: TaskDefinition | None = None


class TaskRunner:
    def __init__(self) -> None:
        self._registry = Registry()
        self._register_defaults()

    def handler(self, task_name: str) -> Callable[[TaskHandler], TaskHandler]:
        return self._registry.handler(task_name)

    def register(self, task_name: str, fn: TaskHandler) -> None:
        self._registry.register(task_name, fn)

    def validate_handlers(self, flow: FlowDefinition) -> None:
        missing = [task.name for task in flow.tasks if task.name not in self._registry]
        if missing:
            raise UnregisteredTaskError(f"no handler registered for tasks: {', '.join(missing)}")

    def execute(self, task: TaskDefinition, context: dict[str, Any]) -> TaskExecutionResult:
        return self._registry.get(task.name)(task, context)

    def _register_defaults(self) -> None:
        from ..tasks import register_all

        register_all(self._registry)


class FlowStateMachine:
    def __init__(self, flow: FlowDefinition) -> None:
        self.flow = flow
        self.states = self._build_states(flow)
        self._transitions = self._build_transitions(flow)

    def _build_states(self, flow: FlowDefinition) -> dict[str, State]:
        states: dict[str, State] = {
            task.name: State(name=task.name, task=task) for task in flow.tasks
        }
        states[RunStatus.END_SUCCESS] = State(
            name=RunStatus.END_SUCCESS, is_terminal=True, status_on_enter=RunStatus.END_SUCCESS
        )
        states[RunStatus.END_FAILED] = State(
            name=RunStatus.END_FAILED, is_terminal=True, status_on_enter=RunStatus.END_FAILED
        )
        return states

    def _build_transitions(self, flow: FlowDefinition) -> dict[str, dict[EventType, str]]:
        transitions: dict[str, dict[EventType, str]] = {}
        for condition in flow.conditions:
            transitions[condition.source_task] = {
                EventType.TASK_SUCCEEDED: self._resolve_target(
                    condition.target_task_success, event=EventType.TASK_SUCCEEDED
                ),
                EventType.TASK_FAILED: self._resolve_target(
                    condition.target_task_failure, event=EventType.TASK_FAILED
                ),
            }
        return transitions

    def _resolve_target(self, target: str, event: EventType) -> str:
        if target.strip() != "end":
            return target.strip()
        return RunStatus.END_SUCCESS if event is EventType.TASK_SUCCEEDED else RunStatus.END_FAILED

    def initial_state(self) -> str:
        return self.flow.start_task

    def transition(self, state_name: str, event: EventType) -> str:
        target = self._transitions.get(state_name, {}).get(event)
        if target is not None:
            return target
        return RunStatus.END_SUCCESS if event is EventType.TASK_SUCCEEDED else RunStatus.END_FAILED

    def state(self, name: str) -> State:
        state = self.states.get(name)
        if state is None:
            raise KeyError(f"Unknown state '{name}'")
        return state
