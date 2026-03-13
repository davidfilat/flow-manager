from __future__ import annotations

import asyncio

import pytest

from flow_manager_task.application.service import FlowService
from flow_manager_task.domain.engine import UnregisteredTaskError
from flow_manager_task.domain.models import FlowDefinition, RunStatus
from flow_manager_task.domain.registry import TaskExecutionResult


async def test_run_completes_successfully(flow_definition: FlowDefinition) -> None:
    service = FlowService()
    service.register_flow(flow_definition)

    started = await service.start_run(flow_definition.id, {})
    assert started.status == RunStatus.RUNNING

    # Yield to allow the background task to complete
    await asyncio.sleep(0.1)

    result = service.get_run(started.run_id)
    assert result.status == RunStatus.END_SUCCESS
    assert "task1" in result.outputs
    assert "task2" in result.outputs
    assert "task3" in result.outputs


async def test_run_stops_on_task_failure(flow_definition: FlowDefinition) -> None:
    service = FlowService()
    service.register_flow(flow_definition)
    service.task_runner.register("task2", lambda t, ctx: TaskExecutionResult(success=False))

    started = await service.start_run(flow_definition.id, {})
    await asyncio.sleep(0.1)

    result = service.get_run(started.run_id)
    assert result.status == RunStatus.END_FAILED
    assert "task3" not in result.outputs


async def test_run_raises_for_unknown_flow() -> None:
    service = FlowService()

    with pytest.raises(ValueError, match="not found"):
        await service.start_run("missing", {})


async def test_run_raises_for_unregistered_task(flow_definition: FlowDefinition) -> None:
    service = FlowService()
    service.register_flow(flow_definition)
    service.task_runner._registry.clear()

    with pytest.raises(UnregisteredTaskError, match="no handler registered for tasks"):
        await service.start_run(flow_definition.id, {})


def test_get_run_raises_for_unknown_run() -> None:
    service = FlowService()

    with pytest.raises(KeyError, match="not found"):
        service.get_run("nonexistent-run-id")
