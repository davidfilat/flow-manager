# Flow Manager

This project implements a generic flow manager microservice in Python.

It uses:
- explicit workflow states (each task is a state),
- explicit transitions for success/failure,
- event-driven execution (`TASK_SUCCEEDED` and `TASK_FAILED`),
- async execution with immediate 202 response and polling for status.

## Architecture

The codebase is organized into three layers:

```
src/flow_manager_task/
├── domain/          # Core logic: models, state machine, task runner, validator
├── application/     # Orchestration: FlowService, run schemas
├── api/             # HTTP layer: FastAPI routes, request schemas
└── tasks/           # Built-in task implementations (auto-registered)
```

Key components:
- `domain.models` — `FlowDefinition`, `TaskDefinition`, `ConditionDefinition`, `RunStatus`
- `domain.validator` — `FlowValidator` with pluggable `Rule` implementations
- `domain.engine` — `FlowStateMachine` for transition resolution, `TaskRunner` for dispatch
- `domain.registry` — `Registry` for handler registration, `TaskExecutionResult`
- `application.service` — `FlowService` orchestrates async execution and run state
- `api.routes` — FastAPI app with register/run/poll endpoints

### Task dependency model

- Tasks are executed sequentially by following transition edges.
- A condition defines two outgoing edges from a source task:
  - success edge (`TASK_SUCCEEDED`)
  - failure edge (`TASK_FAILED`)
- A run starts at `flow.start_task` and stops at terminal states:
  - `END_SUCCESS`
  - `END_FAILED`

### Async execution

- `POST /flows/run` returns `202` immediately with a `run_id`.
- The flow executes in the background; tasks run in a thread pool executor.
- Poll `GET /flows/runs/{run_id}` until `status` is no longer `RUNNING`.

### Adding task handlers

Task handlers live in `tasks/` and are auto-registered at startup. Each module exposes a `register(runner)` function:

```python
def register(runner: Registry) -> None:
    @runner.handler("my_task")
    def my_task(task: TaskDefinition, context: dict[str, Any]) -> TaskExecutionResult:
        ...
        return TaskExecutionResult(success=True, output={"result": ...})
```

## API

- `POST /flows` — register a flow definition
- `POST /flows/run` — start an async run, returns `run_id`
- `GET /flows/runs/{run_id}` — poll run status and outputs

## Setup and run (using uv)

```bash
uv sync
uv run flow-manager-task
```

Service listens on `http://localhost:8000`.
Interactive docs: `http://localhost:8000/docs`.

## Linting and hooks

Install dev tooling and hooks:

```bash
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
# Register the flow
curl -X POST http://localhost:8000/flows \
  -H 'Content-Type: application/json' \
  -d '{ "flow": { ... } }'

# Start a run
curl -X POST http://localhost:8000/flows/run \
  -H 'Content-Type: application/json' \
  -d '{ "flow_id": "flow123", "input": { "source": "demo-api" } }'

# Poll for completion
curl http://localhost:8000/flows/runs/{run_id}
```
