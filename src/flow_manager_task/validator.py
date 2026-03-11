from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from .models import FlowDefinition


@runtime_checkable
class Rule(Protocol):
    description: str

    def check(self, flow: FlowDefinition) -> list[str]: ...


class UniqueTaskNamesRule:
    description = "Task names must be unique"

    def check(self, flow: FlowDefinition) -> list[str]:
        seen: set[str] = set()
        duplicates: set[str] = set()
        for task in flow.tasks:
            if task.name in seen:
                duplicates.add(task.name)
            seen.add(task.name)
        if duplicates:
            return [f"duplicate task names: {', '.join(sorted(duplicates))}"]
        return []


class StartTaskDefinedRule:
    description = "start_task must reference a defined task"

    def check(self, flow: FlowDefinition) -> list[str]:
        task_names = {task.name for task in flow.tasks}
        if flow.start_task not in task_names:
            return [f"start_task '{flow.start_task}' is not defined in tasks"]
        return []


class ConditionReferencesDefinedTasksRule:
    description = "All tasks referenced in conditions must be defined"

    def check(self, flow: FlowDefinition) -> list[str]:
        task_names = {task.name for task in flow.tasks}
        valid_targets = task_names | {"end", "END_SUCCESS", "END_FAILED"}
        errors: list[str] = []
        for condition in flow.conditions:
            if condition.source_task not in task_names:
                errors.append(
                    f"condition '{condition.name}': source_task"
                    f" '{condition.source_task}' is not a defined task"
                )
            if condition.target_task_success not in valid_targets:
                errors.append(
                    f"condition '{condition.name}': target_task_success"
                    f" '{condition.target_task_success}' is not a defined task or terminal"
                )
            if condition.target_task_failure not in valid_targets:
                errors.append(
                    f"condition '{condition.name}': target_task_failure"
                    f" '{condition.target_task_failure}' is not a defined task or terminal"
                )
        return errors


class FlowValidator:
    def __init__(self, rules: list[Rule] | None = None) -> None:
        self.rules: list[Rule] = rules or [
            UniqueTaskNamesRule(),
            StartTaskDefinedRule(),
            ConditionReferencesDefinedTasksRule(),
        ]

    def validate(self, flow: FlowDefinition) -> None:
        errors: list[str] = []
        for rule in self.rules:
            errors.extend(rule.check(flow))
        if errors:
            raise ValueError("\n".join(errors))


default_validator = FlowValidator()
