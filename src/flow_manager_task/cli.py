from __future__ import annotations

import uvicorn


def main() -> None:
    uvicorn.run("flow_manager_task.api:app", host="0.0.0.0", port=8000, reload=False)
