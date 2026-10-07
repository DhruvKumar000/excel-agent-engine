"""
GENERIC HANDLER — makes an 11th workflow work with ZERO code.

If a workflow exists in Excel but has no Python handler in /workflows,
the engine builds one on the fly:
  * each "Steps" item in the Excel row becomes a step,
  * the LLM performs the step using the request, the inputs,
    the Decision_Logic rule and the result of previous steps,
  * the final step produces the Expected_Output.

Later, if precision matters, a developer adds a real handler file and the
engine automatically prefers it. Nothing else changes.
"""
from typing import Any, Dict

from .executor import BaseHandler, StepResult
from .models import Workflow
from . import llm


class GenericLLMHandler(BaseHandler):
    workflow_id = "GENERIC"

    def __init__(self, workflow: Workflow, request: str, inputs: Dict[str, Any]):
        super().__init__(workflow, request, inputs)
        self._dynamic_steps = []
        for i, name in enumerate(workflow.steps, start=1):
            fn = self._make_step(i, name)
            self._dynamic_steps.append(fn)
        self.state["trace"] = []

    def _make_step(self, index: int, name: str):
        def run_step():
            previous = "\n".join(self.state["trace"]) or "(none)"
            prompt = f"""You are executing step {index} of workflow "{self.wf.name}".
User request: {self.request}
Provided inputs: {self.inputs or 'none'}
Decision rule for this workflow: {self.wf.decision_logic}
Tools available (simulated): {', '.join(self.wf.tools_required)}
Results so far:
{previous}

Step to perform now: "{name}"
Perform this step and reply with a concise result (2-4 lines). If information is missing, say exactly what is missing."""
            text = llm.complete(prompt)
            self.use("llm")
            self.state["trace"].append(f"[{index}] {name}: {text}")
            if index == len(self.wf.steps):
                self.state["output"] = {
                    "expected_output_format": self.wf.expected_output,
                    "result": text,
                    "step_trace": self.state["trace"],
                    "note": "Executed by GenericLLMHandler (no custom code) — add a handler file for exact logic.",
                }
            return text[:120]
        run_step._step_name = name
        run_step._step_order = index
        return run_step

    def get_steps(self):
        return self._dynamic_steps
