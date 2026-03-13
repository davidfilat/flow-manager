from __future__ import annotations

import asyncio

import pytest
from httpx import AsyncClient

from flow_manager_task.domain.models import FlowDefinition


async def _wait_for_terminal(client: AsyncClient, run_id: str, *, timeout: float = 5.0) -> dict:
    """Poll GET /flows/runs/{run_id} until the run leaves RUNNING state."""
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        resp = await client.get(f"/flows/runs/{run_id}")
        assert resp.status_code == 200
        data = resp.json()
        if data["status"] != "RUNNING":
            return data
        await asyncio.sleep(0.05)
    pytest.fail(f"Run {run_id} did not reach a terminal state within {timeout}s")


async def test_register_flow_and_run(api_client: AsyncClient, flow_payload: dict) -> None:
    register_response = await api_client.post("/flows", json={"flow": flow_payload})
    assert register_response.status_code == 201
    assert register_response.json()["flow_id"] == flow_payload["id"]

    run_response = await api_client.post(
        "/flows/run", json={"flow_id": flow_payload["id"], "input": {}}
    )
    assert run_response.status_code == 202
    body = run_response.json()
    assert body["flow_id"] == flow_payload["id"]
    assert body["status"] == "RUNNING"
    run_id = body["run_id"]

    result = await _wait_for_terminal(api_client, run_id)
    assert result["status"] == "END_SUCCESS"
    assert "task1" in result["outputs"]
    assert "task3" in result["outputs"]


async def test_run_returns_404_for_unknown_flow(api_client: AsyncClient) -> None:
    response = await api_client.post("/flows/run", json={"flow_id": "missing", "input": {}})

    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


async def test_run_returns_422_for_unregistered_task(
    api_client: AsyncClient, flow_payload: dict
) -> None:
    await api_client.post("/flows", json={"flow": flow_payload})

    from flow_manager_task import api

    service = api.app.dependency_overrides[api.get_service]()
    service.task_runner._registry.clear()

    response = await api_client.post(
        "/flows/run", json={"flow_id": flow_payload["id"], "input": {}}
    )

    assert response.status_code == 422
    assert "no handler registered" in response.json()["detail"]


async def test_run_stops_on_task_failure(
    api_client: AsyncClient, flow_payload: dict, flow_definition: FlowDefinition
) -> None:
    await api_client.post("/flows", json={"flow": flow_payload})

    from flow_manager_task import api
    from flow_manager_task.domain.registry import TaskExecutionResult

    service = api.app.dependency_overrides[api.get_service]()
    service.task_runner.register("task1", lambda t, ctx: TaskExecutionResult(success=False))

    run_response = await api_client.post(
        "/flows/run",
        json={"flow_id": flow_payload["id"], "input": {}},
    )
    assert run_response.status_code == 202
    run_id = run_response.json()["run_id"]

    result = await _wait_for_terminal(api_client, run_id)
    assert result["status"] == "END_FAILED"
    assert "task2" not in result["outputs"]


async def test_get_run_returns_404_for_unknown_run(api_client: AsyncClient) -> None:
    response = await api_client.get("/flows/runs/does-not-exist")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"]
