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
        from .validator import default_validator

        default_validator.validate(self)
        return self
