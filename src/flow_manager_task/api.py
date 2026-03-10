from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException

from .schemas import RegisterFlowRequest, RegisterFlowResponse, RunFlowRequest, RunFlowResponse
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


@app.post("/flows/run", response_model=RunFlowResponse)
def run_flow(
    request: RunFlowRequest,
    service: FlowService = Depends(get_service),
) -> RunFlowResponse:
    try:
        return service.run(request.flow_id, request.input)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
