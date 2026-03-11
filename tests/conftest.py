from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from flow_manager_task import api
from flow_manager_task.models import FlowDefinition
from flow_manager_task.service import FlowService


@pytest.fixture
def flow_payload() -> dict:
    return {
        "id": "flow123",
        "name": "Data processing flow",
        "start_task": "task1",
        "tasks": [
            {"name": "task1", "description": "Fetch data"},
            {"name": "task2", "description": "Process data"},
            {"name": "task3", "description": "Store data"},
        ],
        "conditions": [
            {
                "name": "condition_task1_result",
                "description": "",
                "source_task": "task1",
                "target_task_success": "task2",
                "target_task_failure": "end",
            },
            {
                "name": "condition_task2_result",
                "description": "",
                "source_task": "task2",
                "target_task_success": "task3",
                "target_task_failure": "end",
            },
            {
                "name": "condition_task3_result",
                "description": "",
                "source_task": "task3",
                "target_task_success": "END_SUCCESS",
                "target_task_failure": "END_FAILED",
            },
        ],
    }


@pytest.fixture
def flow_definition(flow_payload: dict) -> FlowDefinition:
    return FlowDefinition.model_validate(flow_payload)


@pytest.fixture
def api_client(flow_definition: FlowDefinition) -> Generator[TestClient, None, None]:
    service = FlowService()
    api.app.dependency_overrides[api.get_service] = lambda: service
    yield TestClient(api.app)
    api.app.dependency_overrides.clear()
