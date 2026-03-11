from __future__ import annotations

from fastapi.testclient import TestClient

from flow_manager_task.models import FlowDefinition


def test_register_flow_and_run(api_client: TestClient, flow_payload: dict) -> None:
    register_response = api_client.post("/flows", json={"flow": flow_payload})
    assert register_response.status_code == 201
    assert register_response.json()["flow_id"] == flow_payload["id"]

    run_response = api_client.post("/flows/run", json={"flow_id": flow_payload["id"], "input": {}})
    assert run_response.status_code == 200
    result = run_response.json()
    assert result["status"] == "END_SUCCESS"
    assert "task1" in result["outputs"]
    assert "task3" in result["outputs"]


def test_run_returns_404_for_unknown_flow(api_client: TestClient) -> None:
    response = api_client.post("/flows/run", json={"flow_id": "missing", "input": {}})

    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_run_stops_on_task_failure(
    api_client: TestClient, flow_payload: dict, flow_definition: FlowDefinition
) -> None:
    api_client.post("/flows", json={"flow": flow_payload})

    from flow_manager_task import api
    from flow_manager_task.engine import TaskExecutionResult

    service = api.app.dependency_overrides[api.get_service]()
    service.task_runner.register("task1", lambda t, ctx: TaskExecutionResult(success=False))

    run_response = api_client.post(
        "/flows/run",
        json={"flow_id": flow_payload["id"], "input": {}},
    )
    assert run_response.status_code == 200
    result = run_response.json()
    assert result["status"] == "END_FAILED"
    assert "task2" not in result["outputs"]
