"""
THE AGENT — glue for the three layers.

    user request
        ↓
    loader.load_workflows()          Excel → catalog
        ↓
    router.route()                   pick workflow (LLM + keyword fallback)
        ↓
    workflows.registry               find handler class (or GenericLLMHandler)
        ↓
    executor.execute()               run steps, trace, errors
        ↓
    RunResult                        selected workflow + steps + output
"""
from pathlib import Path
from typing import Any, Dict, Optional

from . import loader, router
from .executor import execute
from .generic_handler import GenericLLMHandler
from .models import RunResult
import workflows as workflow_pkg  # triggers auto-discovery of handlers


class Agent:
    def __init__(self, excel_path: Optional[Path] = None):
        self.excel_path = excel_path or loader.DEFAULT_EXCEL
        self.workflows = loader.load_workflows(self.excel_path)
        self.registry = workflow_pkg.REGISTRY  # {workflow_id: HandlerClass}

    def reload(self):
        """Re-read the Excel (useful after adding an 11th row)."""
        self.workflows = loader.load_workflows(self.excel_path)

    def handle(self, request: str, inputs: Optional[Dict[str, Any]] = None) -> RunResult:
        inputs = inputs or {}
        wf_id, confidence, reason = router.route(request, self.workflows)

        if not wf_id:
            return RunResult(request=request, workflow_id="NONE", workflow_name="No matching workflow",
                             selection_reason=reason, confidence=0.0, status="error",
                             message="I could not map this request to any known workflow. "
                                     "Try rephrasing or add the workflow to the Excel file.")

        wf = self.workflows[wf_id]
        handler_cls = self.registry.get(wf_id, GenericLLMHandler)
        handler = handler_cls(wf, request, inputs)
        return execute(handler, reason, confidence)

    def describe(self) -> str:
        lines = []
        for wf in self.workflows.values():
            kind = "custom handler" if wf.id in self.registry else "generic (LLM)"
            lines.append(f"{wf.id}  {wf.name:<32} {len(wf.steps)} steps   <{kind}>")
        return "\n".join(lines)
