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
    tasks: list[TaskDefinition]
    conditions: list[ConditionDefinition]

    @model_validator(mode="after")
    def validate_graph(self) -> FlowDefinition:
        task_names = {task.name for task in self.tasks}
        if self.start_task not in task_names:
            raise ValueError("start_task must be present in tasks")
        for condition in self.conditions:
            if condition.source_task not in task_names:
                raise ValueError(
                    f"condition source_task '{condition.source_task}' is not a known task"
                )
            valid_targets = task_names | {"end", "END_SUCCESS", "END_FAILED"}
            if condition.target_task_success not in valid_targets:
                raise ValueError(
                    f"target_task_success '{condition.target_task_success}' is invalid"
                )
            if condition.target_task_failure not in valid_targets:
                raise ValueError(
                    f"target_task_failure '{condition.target_task_failure}' is invalid"
                )
        return self
