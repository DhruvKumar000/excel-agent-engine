"""
LAYER 3 — Step Executor.

A workflow handler is a small class whose methods are marked with @step("...").
The executor runs those steps IN ORDER, times each one, records a trace,
and converts exceptions into clean statuses:

    NeedsInput      -> status "needs_input"  (ask the user for more information)
    WorkflowError   -> status "error"        (business-rule failure)
    any Exception   -> status "error"        (unexpected failure, captured safely)

Every run is appended to logs/executions.csv — which WF010 later analyses.
"""
import csv
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from .models import NeedsInput, RunResult, StepResult, Workflow, WorkflowError
from . import tools

LOG_FILE = Path(__file__).resolve().parent.parent / "logs" / "executions.csv"


# ----------------------------------------------------------- @step decorator
_counter = [0]


def step(name: str):
    """Mark a handler method as an executable step (order = definition order)."""
    def deco(fn):
        _counter[0] += 1
        fn._step_name = name
        fn._step_order = _counter[0]
        return fn
    return deco


class BaseHandler:
    """Every workflow handler extends this. State flows between steps via self.state."""
    workflow_id: str = ""

    def __init__(self, workflow: Workflow, request: str, inputs: Dict[str, Any]):
        self.wf = workflow
        self.request = request
        self.inputs = inputs or {}
        self.state: Dict[str, Any] = {}
        self.tools_used: List[str] = []

    def use(self, tool_name: str):
        """Fetch a registered tool and remember that it was used (for the trace)."""
        if tool_name not in tools.TOOLS:
            raise WorkflowError(f"Tool '{tool_name}' is not registered")
        if tool_name not in self.tools_used:
            self.tools_used.append(tool_name)
        return tools.TOOLS[tool_name]

    def get_steps(self):
        methods = [getattr(self, n) for n in dir(self) if callable(getattr(self, n, None))]
        steps = [m for m in methods if hasattr(m, "_step_name")]
        return sorted(steps, key=lambda m: m._step_order)

    def output(self) -> Any:
        return self.state.get("output")


# ----------------------------------------------------------------- executor
def execute(handler: BaseHandler, selection_reason: str, confidence: float) -> RunResult:
    wf = handler.wf
    result = RunResult(request=handler.request, workflow_id=wf.id, workflow_name=wf.name,
                       selection_reason=selection_reason, confidence=confidence, status="success")
    t_total = time.perf_counter()
    failed_step, error_msg = "", ""

    for fn in handler.get_steps():
        t0 = time.perf_counter()
        try:
            detail = fn()
            ms = int((time.perf_counter() - t0) * 1000)
            result.steps.append(StepResult(fn._step_name, "ok", str(detail or ""), ms))
        except NeedsInput as e:
            ms = int((time.perf_counter() - t0) * 1000)
            result.steps.append(StepResult(fn._step_name, "needs_input", str(e), ms))
            result.status, result.message = "needs_input", str(e)
            failed_step, error_msg = fn._step_name, str(e)
            break
        except (WorkflowError, Exception) as e:
            ms = int((time.perf_counter() - t0) * 1000)
            result.steps.append(StepResult(fn._step_name, "error", f"{type(e).__name__}: {e}", ms))
            result.status, result.message = "error", f"Step '{fn._step_name}' failed: {e}"
            failed_step, error_msg = fn._step_name, f"{type(e).__name__}: {e}"
            break

    result.output = handler.output()
    result.total_ms = int((time.perf_counter() - t_total) * 1000)
    _log_run(result, handler.tools_used, failed_step, error_msg)
    return result


def _log_run(result: RunResult, tools_used: List[str], failed_step: str, error: str) -> None:
    LOG_FILE.parent.mkdir(exist_ok=True)
    new = not LOG_FILE.exists()
    with LOG_FILE.open("a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["timestamp", "workflow_id", "workflow_name", "status", "duration_ms",
                        "steps_run", "tools_used", "failed_step", "error"])
        w.writerow([datetime.now().isoformat(timespec="seconds"), result.workflow_id, result.workflow_name,
                    result.status, result.total_ms, len(result.steps), "|".join(tools_used),
                    failed_step, error])
