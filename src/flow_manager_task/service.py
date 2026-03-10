from __future__ import annotations

from typing import Any

from .engine import EventType, FlowStateMachine, TaskRunner
from .models import FlowDefinition, RunStatus
from .schemas import RunFlowResponse


class FlowService:
    def __init__(self, task_runner: TaskRunner | None = None) -> None:
        self._flows: dict[str, FlowDefinition] = {}
        self.task_runner = task_runner or TaskRunner()

    def register_flow(self, flow: FlowDefinition) -> None:
        self._flows[flow.id] = flow

    def run(self, flow_id: str, flow_input: dict[str, Any]) -> RunFlowResponse:
        flow = self._flows.get(flow_id)
        if flow is None:
            raise ValueError(f"Flow '{flow_id}' not found")

        machine = FlowStateMachine(flow)
        current = machine.initial_state()
        context: dict[str, Any] = {"outputs": {}, **flow_input}

        while True:
            state = machine.state(current)
            if state.is_terminal:
                return RunFlowResponse(
                    flow_id=flow_id,
                    status=state.status_on_enter or RunStatus.END_SUCCESS,
                    outputs=context["outputs"],
                )
            if state.task is None:
                return RunFlowResponse(
                    flow_id=flow_id,
                    status=RunStatus.END_FAILED,
                    outputs=context["outputs"],
                )
            result = self.task_runner.execute(state.task, context)
            context["outputs"][state.task.name] = result.output
            event = EventType.TASK_SUCCEEDED if result.success else EventType.TASK_FAILED
            current = machine.transition(current, event)
