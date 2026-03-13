from __future__ import annotations

from flow_manager_task.domain.engine import EventType, FlowStateMachine, TaskRunner
from flow_manager_task.domain.models import FlowDefinition
from flow_manager_task.domain.registry import TaskExecutionResult


def test_state_machine_follows_success_edge(flow_definition: FlowDefinition) -> None:
    machine = FlowStateMachine(flow_definition)

    assert machine.transition("task1", EventType.TASK_SUCCEEDED) == "task2"
    assert machine.transition("task2", EventType.TASK_SUCCEEDED) == "task3"


def test_state_machine_follows_failure_edge(flow_definition: FlowDefinition) -> None:
    machine = FlowStateMachine(flow_definition)

    assert machine.transition("task1", EventType.TASK_FAILED) == "END_FAILED"
    assert machine.transition("task2", EventType.TASK_FAILED) == "END_FAILED"


def test_state_machine_falls_back_to_terminal_when_no_transition(
    flow_definition: FlowDefinition,
) -> None:
    machine = FlowStateMachine(flow_definition)

    assert machine.transition("task3", EventType.TASK_SUCCEEDED) == "END_SUCCESS"
    assert machine.transition("task3", EventType.TASK_FAILED) == "END_FAILED"


def test_task_runner_register_custom_handler() -> None:
    runner = TaskRunner()
    task = FlowDefinition.model_validate(
        {
            "id": "f",
            "name": "f",
            "start_task": "my-task",
            "tasks": [{"name": "my-task", "description": ""}],
            "conditions": [],
        }
    ).tasks[0]

    def failing_handler(t, ctx):  # type: ignore[no-untyped-def]
        return TaskExecutionResult(success=False, error="custom")

    runner.register("my-task", failing_handler)

    result = runner.execute(task, {})
    assert result.success is False
    assert result.error == "custom"
