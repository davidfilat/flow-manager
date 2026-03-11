from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .models import FlowDefinition, RunStatus


class RegisterFlowRequest(BaseModel):
    flow: FlowDefinition


class RunFlowRequest(BaseModel):
    flow_id: str = Field(min_length=1)
    input: dict[str, Any] = Field(default_factory=dict)


class RegisterFlowResponse(BaseModel):
    flow_id: str
    name: str


class RunStartedResponse(BaseModel):
    run_id: str
    flow_id: str
    status: RunStatus = RunStatus.RUNNING


class RunStatusResponse(BaseModel):
    run_id: str
    flow_id: str
    status: RunStatus
    outputs: dict[str, Any]
