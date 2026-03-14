from __future__ import annotations

from collections.abc import AsyncGenerator
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from flow_manager_task import api
from flow_manager_task.application.service import FlowService
from flow_manager_task.domain.models import FlowDefinition


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


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


@pytest.fixture(autouse=True)
def mock_task1_sleep() -> AsyncGenerator[None, None]:
    with patch("flow_manager_task.tasks.task1.time.sleep"):
        yield


@pytest.fixture
async def api_client() -> AsyncGenerator[AsyncClient, None]:
    service = FlowService()
    api.app.dependency_overrides[api.get_service] = lambda: service
    async with AsyncClient(transport=ASGITransport(app=api.app), base_url="http://test") as client:
        yield client
    api.app.dependency_overrides.clear()
