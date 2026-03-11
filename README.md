# Flow Manager (State Machine Pattern)

This project implements a generic flow manager microservice in Python.

It uses:
- explicit workflow states (each task is a state),
- explicit transitions for success/failure,
- event-driven execution (`TASK_SUCCEEDED` and `TASK_FAILED`),
- persisted run state/history for resume/retry behavior.

## Architecture

Core components:
- `State` and `Transition` in [engine.py](/Users/davidfilat/projects/flow-manager-task/src/flow_manager_task/engine.py)
- `FlowStateMachine`: graph and transition resolution
- `TransitionGuard`: hook for rule-based transitions (e.g., retries/timeouts)
- `TaskRunner`: executes task implementations
- `RunStore`: SQLite persistence for flows and runs
- `FlowService`: orchestration layer
- FastAPI app endpoints in [api.py](/Users/davidfilat/projects/flow-manager-task/src/flow_manager_task/api.py)

### Task dependency model

- Tasks are executed sequentially by following transition edges.
- A condition defines two outgoing edges from a source task:
  - success edge (`TASK_SUCCEEDED`)
  - failure edge (`TASK_FAILED`)
- A run starts at `flow.start_task` and stops in terminal states:
  - `END_SUCCESS`
  - `END_FAILED`

### Success/failure evaluation

- `TaskRunner.execute(...)` returns `TaskExecutionResult(success: bool, output, error)`.
- `success=True` emits `TASK_SUCCEEDED`; `success=False` emits `TASK_FAILED`.
- The state machine resolves the next state from explicit transitions.
- Every step is appended to run `history` with timestamp, event, source and target state.

### Behavior on task outcomes

- If a task succeeds, execution follows the success transition.
- If a task fails, execution follows the failure transition (usually to `END_FAILED`).
- If `max_steps` is provided when starting/resuming a run, execution pauses with `PAUSED` status once the step budget is reached.
- Runs can be resumed via `POST /runs/{id}/resume`.

## API

- `POST /flows` create flow graph
- `POST /runs` start execution
- `POST /runs/{id}/resume` continue a paused/in-progress run
- `GET /runs/{id}` inspect current state and audit history

## Setup and run (using uv)

```bash
cd /Users/davidfilat/projects/flow-manager-task
uv sync
uv run flow-manager-task
```

Service listens on `http://localhost:8000`.
Interactive docs: `http://localhost:8000/docs`.

## Linting and hooks

Install dev tooling and hooks:

```bash
cd /Users/davidfilat/projects/flow-manager-task
uv sync --dev
uv run pre-commit install
```

Run checks manually:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
uv run pre-commit run --all-files
```

## Example flow payload

Use this JSON body for `POST /flows`:

```json
{
  "flow": {
    "id": "flow123",
    "name": "Data processing flow",
    "start_task": "task1",
    "tasks": [
      { "name": "task1", "description": "Fetch data" },
      { "name": "task2", "description": "Process data" },
      { "name": "task3", "description": "Store data" }
    ],
    "conditions": [
      {
        "name": "condition_task1_result",
        "description": "If task1 succeeds go to task2, else end",
        "source_task": "task1",
        "target_task_success": "task2",
        "target_task_failure": "end"
      },
      {
        "name": "condition_task2_result",
        "description": "If task2 succeeds go to task3, else end",
        "source_task": "task2",
        "target_task_success": "task3",
        "target_task_failure": "end"
      },
      {
        "name": "condition_task3_result",
        "description": "If task3 succeeds flow succeeds, else fails",
        "source_task": "task3",
        "target_task_success": "END_SUCCESS",
        "target_task_failure": "END_FAILED"
      }
    ]
  }
}
```

## Start a run

```bash
curl -X POST http://localhost:8000/runs \
  -H 'Content-Type: application/json' \
  -d '{
    "flow_id": "flow123",
    "input": {
      "source": "demo-api"
    }
  }'
```

To force a task failure for testing:

```json
{
  "flow_id": "flow123",
  "input": {
    "task_outcomes": {
      "task2": false
    }
  }
}
```
