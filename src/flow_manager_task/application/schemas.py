from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from ..domain.models import RunStatus


class RunStartedResponse(BaseModel):
    run_id: str
    flow_id: str
    status: RunStatus = RunStatus.RUNNING


class RunStatusResponse(BaseModel):
    run_id: str
    flow_id: str
    status: RunStatus
    outputs: dict[str, Any]
