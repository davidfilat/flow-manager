from __future__ import annotations

import pytest

from flow_manager_task.models import FlowDefinition


def _base_payload(**overrides: object) -> dict:
    payload: dict = {
        "id": "flow1",
        "name": "Test flow",
        "start_task": "t1",
        "tasks": [{"name": "t1", "description": ""}],
        "conditions": [],
    }
    payload.update(overrides)
    return payload


def test_valid_flow_is_accepted() -> None:
    flow = FlowDefinition.model_validate(_base_payload())
    assert flow.id == "flow1"
    assert len(flow.tasks) == 1


def test_empty_tasks_list_is_rejected() -> None:
    with pytest.raises(Exception, match="at least 1 item"):
        FlowDefinition.model_validate(_base_payload(tasks=[]))


def test_start_task_not_in_tasks_is_rejected() -> None:
    with pytest.raises(ValueError, match="start_task 'missing' is not defined in tasks"):
        FlowDefinition.model_validate(_base_payload(start_task="missing"))


def test_duplicate_task_names_are_rejected() -> None:
    with pytest.raises(ValueError, match="duplicate task names: t1"):
        FlowDefinition.model_validate(
            _base_payload(
                tasks=[{"name": "t1", "description": ""}, {"name": "t1", "description": ""}]
            )
        )


def test_condition_with_unknown_source_task_is_rejected() -> None:
    with pytest.raises(ValueError, match="source_task 'ghost'"):
        FlowDefinition.model_validate(
            _base_payload(
                tasks=[{"name": "t1"}, {"name": "t2"}],
                conditions=[
                    {
                        "name": "c1",
                        "source_task": "ghost",
                        "target_task_success": "t2",
                        "target_task_failure": "end",
                    }
                ],
            )
        )


def test_condition_with_unknown_success_target_is_rejected() -> None:
    with pytest.raises(ValueError, match="target_task_success 'nowhere'"):
        FlowDefinition.model_validate(
            _base_payload(
                tasks=[{"name": "t1"}, {"name": "t2"}],
                conditions=[
                    {
                        "name": "c1",
                        "source_task": "t1",
                        "target_task_success": "nowhere",
                        "target_task_failure": "end",
                    }
                ],
            )
        )


def test_condition_with_unknown_failure_target_is_rejected() -> None:
    with pytest.raises(ValueError, match="target_task_failure 'nowhere'"):
        FlowDefinition.model_validate(
            _base_payload(
                tasks=[{"name": "t1"}, {"name": "t2"}],
                conditions=[
                    {
                        "name": "c1",
                        "source_task": "t1",
                        "target_task_success": "end",
                        "target_task_failure": "nowhere",
                    }
                ],
            )
        )


def test_condition_can_target_terminal_keywords() -> None:
    flow = FlowDefinition.model_validate(
        _base_payload(
            tasks=[{"name": "t1"}, {"name": "t2"}],
            conditions=[
                {
                    "name": "c1",
                    "source_task": "t1",
                    "target_task_success": "t2",
                    "target_task_failure": "end",
                },
                {
                    "name": "c2",
                    "source_task": "t2",
                    "target_task_success": "END_SUCCESS",
                    "target_task_failure": "END_FAILED",
                },
            ],
        )
    )
    assert len(flow.conditions) == 2
