from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class RunStatus(StrEnum):
    RUNNING = "RUNNING"
    END_SUCCESS = "END_SUCCESS"
    END_FAILED = "END_FAILED"


class TaskDefinition(BaseModel):
    name: str = Field(min_length=1)
    description: str = ""


class ConditionDefinition(BaseModel):
    name: str = Field(min_length=1)
    description: str = ""
    source_task: str = Field(min_length=1)
    target_task_success: str = Field(min_length=1)
    target_task_failure: str = Field(min_length=1)


class FlowDefinition(BaseModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    start_task: str = Field(min_length=1)
    tasks: list[TaskDefinition] = Field(min_length=1)
    conditions: list[ConditionDefinition] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_graph(self) -> FlowDefinition:
        task_names_list = [task.name for task in self.tasks]
        task_names = set(task_names_list)

        duplicates = {n for n in task_names_list if task_names_list.count(n) > 1}
        if duplicates:
            raise ValueError(f"duplicate task names: {', '.join(sorted(duplicates))}")

        if self.start_task not in task_names:
            raise ValueError(f"start_task '{self.start_task}' is not defined in tasks")

        valid_targets = task_names | {"end", "END_SUCCESS", "END_FAILED"}
        for condition in self.conditions:
            if condition.source_task not in task_names:
                raise ValueError(
                    f"condition '{condition.name}': source_task '{condition.source_task}'"
                    " is not a defined task"
                )
            if condition.target_task_success not in valid_targets:
                raise ValueError(
                    f"condition '{condition.name}': target_task_success"
                    f" '{condition.target_task_success}' is not a defined task or terminal"
                )
            if condition.target_task_failure not in valid_targets:
                raise ValueError(
                    f"condition '{condition.name}': target_task_failure"
                    f" '{condition.target_task_failure}' is not a defined task or terminal"
                )
        return self
