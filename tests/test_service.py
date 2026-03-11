from __future__ import annotations

import pytest

from flow_manager_task.engine import TaskExecutionResult
from flow_manager_task.models import FlowDefinition, RunStatus
from flow_manager_task.service import FlowService


def test_run_completes_successfully(flow_definition: FlowDefinition) -> None:
    service = FlowService()
    service.register_flow(flow_definition)

    result = service.run(flow_definition.id, {})

    assert result.status == RunStatus.END_SUCCESS
    assert "task1" in result.outputs
    assert "task2" in result.outputs
    assert "task3" in result.outputs


def test_run_stops_on_task_failure(flow_definition: FlowDefinition) -> None:
    service = FlowService()
    service.register_flow(flow_definition)
    service.task_runner.register("task2", lambda t, ctx: TaskExecutionResult(success=False))

    result = service.run(flow_definition.id, {})

    assert result.status == RunStatus.END_FAILED
    assert "task3" not in result.outputs


def test_run_raises_for_unknown_flow() -> None:
    service = FlowService()

    with pytest.raises(ValueError, match="not found"):
        service.run("missing", {})
