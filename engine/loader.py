"""
LAYER 1 — Excel is the source of truth.

Reads the 'Workflows' sheet (and 'Test_Questions') and returns Workflow objects.
Adding a new row to the Excel = the engine knows a new workflow. No code here changes.
"""
from pathlib import Path
from typing import Dict, List
import pandas as pd

from .models import Workflow

DEFAULT_EXCEL = Path(__file__).resolve().parent.parent / "data" / "AI_Agent_Workflow_Assessment.xlsx"


def _split(text: str, sep: str) -> List[str]:
    if not isinstance(text, str):
        return []
    return [p.strip() for p in text.split(sep) if p.strip()]


def load_workflows(path: Path = DEFAULT_EXCEL) -> Dict[str, Workflow]:
    wf_df = pd.read_excel(path, sheet_name="Workflows").fillna("")
    try:
        tq_df = pd.read_excel(path, sheet_name="Test_Questions").fillna("")
        tests = dict(zip(tq_df["Workflow_ID"], tq_df["Test_Request"]))
    except Exception:
        tests = {}

    workflows: Dict[str, Workflow] = {}
    for _, row in wf_df.iterrows():
        wf = Workflow(
            id=str(row["Workflow_ID"]).strip(),
            name=str(row["Workflow_Name"]).strip(),
            trigger=str(row["Trigger"]).strip(),
            inputs=str(row["Inputs"]).strip(),
            steps=_split(row["Steps"], "→"),
            decision_logic=str(row["Decision_Logic"]).strip(),
            tools_required=_split(row["Tools_Required"], ";"),
            expected_output=str(row["Expected_Output"]).strip(),
            test_request=str(tests.get(row["Workflow_ID"], "")).strip(),
        )
        workflows[wf.id] = wf
    return workflows


if __name__ == "__main__":
    for wf in load_workflows().values():
        print(wf.summary())
        print("   steps:", " → ".join(wf.steps))
