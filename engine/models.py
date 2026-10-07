"""
Data models used across the engine.
Simple dataclasses — no heavy framework, easy to read.
"""
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional
import json


@dataclass
class Workflow:
    """One row of the Excel 'Workflows' sheet."""
    id: str
    name: str
    trigger: str
    inputs: str
    steps: List[str]          # split on "→"
    decision_logic: str
    tools_required: List[str]  # split on ";"
    expected_output: str
    test_request: str = ""     # from 'Test_Questions' sheet (used as router example)

    def summary(self) -> str:
        return f"{self.id} | {self.name} | trigger: {self.trigger}"


@dataclass
class StepResult:
    name: str
    status: str          # ok | error | skipped
    detail: str = ""
    duration_ms: int = 0


@dataclass
class RunResult:
    request: str
    workflow_id: str
    workflow_name: str
    selection_reason: str
    confidence: float
    status: str                       # success | needs_input | error
    steps: List[StepResult] = field(default_factory=list)
    output: Any = None
    message: str = ""
    total_ms: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, default=str)


class NeedsInput(Exception):
    """Raised by a step when required input is missing (e.g. WF005, WF007)."""


class WorkflowError(Exception):
    """Raised by a step for a business-rule failure."""
