from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException

from .engine import UnregisteredTaskError
from .schemas import (
    RegisterFlowRequest,
    RegisterFlowResponse,
    RunFlowRequest,
    RunStartedResponse,
    RunStatusResponse,
)
from .service import FlowService

app = FastAPI(title="Flow Manager", version="0.1.0")

_service = FlowService()


def get_service() -> FlowService:
    return _service


@app.post("/flows", status_code=201, response_model=RegisterFlowResponse)
def register_flow(
    request: RegisterFlowRequest,
    service: FlowService = Depends(get_service),
) -> RegisterFlowResponse:
    service.register_flow(request.flow)
    return RegisterFlowResponse(flow_id=request.flow.id, name=request.flow.name)


@app.post("/flows/run", status_code=202, response_model=RunStartedResponse)
async def run_flow(
    request: RunFlowRequest,
    service: FlowService = Depends(get_service),
) -> RunStartedResponse:
    try:
        return await service.start_run(request.flow_id, request.input)
    except UnregisteredTaskError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/flows/runs/{run_id}", response_model=RunStatusResponse)
def get_run_status(
    run_id: str,
    service: FlowService = Depends(get_service),
) -> RunStatusResponse:
    try:
        return service.get_run(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
