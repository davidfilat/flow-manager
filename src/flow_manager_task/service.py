from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Any

from .engine import EventType, FlowStateMachine, TaskRunner
from .models import FlowDefinition, RunStatus
from .schemas import RunStartedResponse, RunStatusResponse


@dataclass
class RunRecord:
    run_id: str
    flow_id: str
    status: RunStatus = RunStatus.RUNNING
    outputs: dict[str, Any] = field(default_factory=dict)


class FlowService:
    def __init__(self, task_runner: TaskRunner | None = None) -> None:
        self._flows: dict[str, FlowDefinition] = {}
        self._runs: dict[str, RunRecord] = {}
        self.task_runner = task_runner or TaskRunner()

    def register_flow(self, flow: FlowDefinition) -> None:
        self._flows[flow.id] = flow

    async def start_run(self, flow_id: str, flow_input: dict[str, Any]) -> RunStartedResponse:
        flow = self._flows.get(flow_id)
        if flow is None:
            raise ValueError(f"Flow '{flow_id}' not found")

        self.task_runner.validate_handlers(flow)

        run_id = str(uuid.uuid4())
        record = RunRecord(run_id=run_id, flow_id=flow_id)
        self._runs[run_id] = record

        asyncio.create_task(self._execute(record, flow, flow_input))

        return RunStartedResponse(run_id=run_id, flow_id=flow_id)

    def get_run(self, run_id: str) -> RunStatusResponse:
        record = self._runs.get(run_id)
        if record is None:
            raise KeyError(f"Run '{run_id}' not found")
        return RunStatusResponse(
            run_id=record.run_id,
            flow_id=record.flow_id,
            status=record.status,
            outputs=record.outputs,
        )

    async def _execute(
        self, record: RunRecord, flow: FlowDefinition, flow_input: dict[str, Any]
    ) -> None:
        machine = FlowStateMachine(flow)
        current = machine.initial_state()
        context: dict[str, Any] = {"outputs": {}, **flow_input}

        try:
            while True:
                state = machine.state(current)
                if state.is_terminal:
                    record.status = state.status_on_enter or RunStatus.END_SUCCESS
                    record.outputs = context["outputs"]
                    return
                if state.task is None:
                    record.status = RunStatus.END_FAILED
                    record.outputs = context["outputs"]
                    return
                result = await asyncio.get_event_loop().run_in_executor(
                    None, self.task_runner.execute, state.task, context
                )
                context["outputs"][state.task.name] = result.output
                event = EventType.TASK_SUCCEEDED if result.success else EventType.TASK_FAILED
                current = machine.transition(current, event)
        except Exception:
            record.status = RunStatus.END_FAILED
            record.outputs = context["outputs"]
