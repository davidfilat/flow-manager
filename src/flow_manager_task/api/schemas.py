from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from ..application.schemas import RunStartedResponse, RunStatusResponse  # noqa: F401
from ..domain.models import FlowDefinition


class RegisterFlowRequest(BaseModel):
    flow: FlowDefinition


class RunFlowRequest(BaseModel):
    flow_id: str = Field(min_length=1)
    input: dict[str, Any] = Field(default_factory=dict)


class RegisterFlowResponse(BaseModel):
    flow_id: str
    name: str
