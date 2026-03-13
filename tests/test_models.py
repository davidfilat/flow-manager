from __future__ import annotations

import pytest

from flow_manager_task.domain.models import FlowDefinition
from flow_manager_task.domain.validator import (
    ConditionReferencesDefinedTasksRule,
    FlowValidator,
    Rule,
    StartTaskDefinedRule,
    UniqueTaskNamesRule,
)


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


# ---------------------------------------------------------------------------
# FlowDefinition field-level validation (Pydantic)
# ---------------------------------------------------------------------------


def test_valid_flow_is_accepted() -> None:
    flow = FlowDefinition.model_validate(_base_payload())
    assert flow.id == "flow1"
    assert len(flow.tasks) == 1


def test_empty_tasks_list_is_rejected() -> None:
    with pytest.raises(Exception, match="at least 1 item"):
        FlowDefinition.model_validate(_base_payload(tasks=[]))


# ---------------------------------------------------------------------------
# Rule protocol conformance
# ---------------------------------------------------------------------------


def test_all_rules_implement_rule_protocol() -> None:
    rules = [UniqueTaskNamesRule(), StartTaskDefinedRule(), ConditionReferencesDefinedTasksRule()]
    for rule in rules:
        assert isinstance(rule, Rule)
        assert isinstance(rule.description, str)


# ---------------------------------------------------------------------------
# Individual rules — unit tests
# ---------------------------------------------------------------------------


def test_unique_task_names_rule_passes_for_distinct_names() -> None:
    flow = FlowDefinition.model_validate(_base_payload(tasks=[{"name": "t1"}, {"name": "t2"}]))
    assert UniqueTaskNamesRule().check(flow) == []


def test_unique_task_names_rule_reports_duplicates() -> None:
    from flow_manager_task.domain.models import TaskDefinition

    # Bypass model_validator to build a flow with duplicates for direct rule testing
    flow = FlowDefinition.model_construct(
        id="f",
        name="f",
        start_task="t1",
        tasks=[TaskDefinition(name="t1"), TaskDefinition(name="t1")],
        conditions=[],
    )
    errors = UniqueTaskNamesRule().check(flow)
    assert len(errors) == 1
    assert "t1" in errors[0]


def test_start_task_defined_rule_passes() -> None:
    flow = FlowDefinition.model_validate(_base_payload())
    assert StartTaskDefinedRule().check(flow) == []


def test_start_task_defined_rule_reports_missing() -> None:
    from flow_manager_task.domain.models import TaskDefinition

    flow = FlowDefinition.model_construct(
        id="f",
        name="f",
        start_task="ghost",
        tasks=[TaskDefinition(name="t1", description="")],
        conditions=[],
    )
    errors = StartTaskDefinedRule().check(flow)
    assert len(errors) == 1
    assert "ghost" in errors[0]


def test_condition_rule_passes_for_valid_flow() -> None:
    flow = FlowDefinition.model_validate(
        _base_payload(
            tasks=[{"name": "t1"}, {"name": "t2"}],
            conditions=[
                {
                    "name": "c1",
                    "source_task": "t1",
                    "target_task_success": "t2",
                    "target_task_failure": "end",
                }
            ],
        )
    )
    assert ConditionReferencesDefinedTasksRule().check(flow) == []


# ---------------------------------------------------------------------------
# FlowValidator — collects ALL errors before raising
# ---------------------------------------------------------------------------


def test_validator_raises_with_all_errors_combined() -> None:
    # Build without validation so we can test the validator in isolation
    from flow_manager_task.domain.models import ConditionDefinition, TaskDefinition

    flow = FlowDefinition.model_construct(
        id="f",
        name="f",
        start_task="t1",
        tasks=[TaskDefinition(name="t1"), TaskDefinition(name="t2")],
        conditions=[
            ConditionDefinition(
                name="c1",
                source_task="t1",
                target_task_success="nowhere",  # bad
                target_task_failure="end",
            ),
            ConditionDefinition(
                name="c2",
                source_task="t2",
                target_task_success="t1",
                target_task_failure="also_nowhere",  # bad
            ),
        ],
    )
    with pytest.raises(ValueError) as exc_info:
        FlowValidator().validate(flow)

    message = str(exc_info.value)
    assert "nowhere" in message
    assert "also_nowhere" in message


def test_validator_accepts_custom_rule_list() -> None:
    class AlwaysOkRule:
        description = "always passes"

        def check(self, flow: FlowDefinition) -> list[str]:
            return []

    flow = FlowDefinition.model_validate(_base_payload())
    FlowValidator(rules=[AlwaysOkRule()]).validate(flow)  # must not raise


def test_validator_is_silent_for_valid_flow() -> None:
    flow = FlowDefinition.model_validate(_base_payload())
    FlowValidator().validate(flow)  # must not raise


# ---------------------------------------------------------------------------
# Integration — FlowDefinition.model_validate triggers validator
# ---------------------------------------------------------------------------


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
