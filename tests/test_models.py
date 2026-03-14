from __future__ import annotations

import pytest
from pydantic import ValidationError

from flow_manager_task.domain.models import FlowDefinition
from flow_manager_task.domain.validator import (
    ConditionReferencesDefinedTasksRule,
    FlowValidationError,
    FlowValidator,
    Rule,
    StartTaskDefinedRule,
    UniqueTaskNamesRule,
)


def _unwrap_flow_validation_error(exc: ValidationError) -> FlowValidationError:
    """Extract FlowValidationError from pydantic's ValidationError wrapper."""
    for error in exc.errors():
        cause = error.get("ctx", {}).get("error")
        if isinstance(cause, FlowValidationError):
            return cause
    raise AssertionError(f"No FlowValidationError found in {exc}")


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


def test_all_rules_implement_rule_protocol() -> None:
    rules = [UniqueTaskNamesRule(), StartTaskDefinedRule(), ConditionReferencesDefinedTasksRule()]
    for rule in rules:
        assert isinstance(rule, Rule)
        assert isinstance(rule.description, str)


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
    with pytest.raises(FlowValidationError) as exc_info:
        FlowValidator().validate(flow)

    assert any("nowhere" in e for e in exc_info.value.errors)
    assert any("also_nowhere" in e for e in exc_info.value.errors)


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


def test_start_task_not_in_tasks_is_rejected() -> None:
    with pytest.raises(ValidationError) as exc_info:
        FlowDefinition.model_validate(_base_payload(start_task="missing"))
    errors = _unwrap_flow_validation_error(exc_info.value).errors
    assert any("start_task 'missing' is not defined in tasks" in e for e in errors)


def test_duplicate_task_names_are_rejected() -> None:
    with pytest.raises(ValidationError) as exc_info:
        FlowDefinition.model_validate(
            _base_payload(
                tasks=[{"name": "t1", "description": ""}, {"name": "t1", "description": ""}]
            )
        )
    errors = _unwrap_flow_validation_error(exc_info.value).errors
    assert any("duplicate task names: t1" in e for e in errors)


def test_condition_with_unknown_source_task_is_rejected() -> None:
    with pytest.raises(ValidationError) as exc_info:
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
    errors = _unwrap_flow_validation_error(exc_info.value).errors
    assert any("source_task 'ghost'" in e for e in errors)


def test_condition_with_unknown_success_target_is_rejected() -> None:
    with pytest.raises(ValidationError) as exc_info:
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
    errors = _unwrap_flow_validation_error(exc_info.value).errors
    assert any("target_task_success 'nowhere'" in e for e in errors)


def test_condition_with_unknown_failure_target_is_rejected() -> None:
    with pytest.raises(ValidationError) as exc_info:
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
    errors = _unwrap_flow_validation_error(exc_info.value).errors
    assert any("target_task_failure 'nowhere'" in e for e in errors)


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
