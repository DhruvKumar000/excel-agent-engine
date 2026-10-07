"""
Run:  python -m pytest -q      (or simply: python tests/test_all_workflows.py)

Covers: Excel loading, routing of all 10 test questions, successful execution of all
10 workflows, needs_input / error handling, and the zero-code 11th workflow.
"""
import os
import sys
from pathlib import Path

os.environ["LLM_MOCK"] = "true"  # tests never need a real API key
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.agent import Agent  # noqa: E402

agent = Agent()

DEMO_INPUTS = {
    "WF004": {"product_name": "Linen Shirt Beige", "category": "apparel", "material": "linen", "color": "beige"},
    "WF007": {"campaign_goal": "Launch autumn collection", "dates": "15–30 Oct"},
    "WF009": {"skills": "python, sql", "priority": "high"},
}


def test_excel_loaded():
    assert len(agent.workflows) == 10
    assert all(wf.steps for wf in agent.workflows.values())


def test_routing_all_test_questions():
    for wf in agent.workflows.values():
        res = agent.handle(wf.test_request, DEMO_INPUTS.get(wf.id, {}))
        assert res.workflow_id == wf.id, f"{wf.test_request!r} routed to {res.workflow_id}"


def test_all_workflows_succeed():
    for wf in agent.workflows.values():
        res = agent.handle(wf.test_request, DEMO_INPUTS.get(wf.id, {}))
        assert res.status == "success", f"{wf.id}: {res.message}"
        assert res.output is not None
        assert len(res.steps) == len(wf.steps)


def test_wf001_threshold_logic():
    out = agent.handle("Which products need restocking?").output
    skus = {p["sku"] for p in out["products_requiring_restock"]}
    assert skus == {"SKU-001", "SKU-003", "SKU-005", "SKU-007"}  # strictly below minimum


def test_wf002_ten_percent_rule():
    out = agent.handle("Find products where vendor price differs by more than 10%.").output
    assert {e["sku"] for e in out["exceptions"]} == {"SKU-003", "SKU-005", "SKU-007"}


def test_wf003_invalid_rows():
    out = agent.handle("Process this vendor spreadsheet and show invalid rows.").output
    assert out["summary"]["invalid_rows"] == 3


def test_wf005_missing_order_asks_again():
    res = agent.handle("Where is order ORD-9999?")
    assert res.status == "needs_input" and "another" in res.message.lower()


def test_wf007_missing_inputs():
    res = agent.handle("Create a campaign brief for the new collection.")
    assert res.status == "needs_input" and "campaign_goal" in res.message


def test_wf006_definite_and_possible():
    out = agent.handle("Find likely duplicate products in the catalog.").output
    assert out["definite"] >= 1 and out["possible"] >= 1


def test_wf009_escalation():
    res = agent.handle("Assign this task", {"skills": "cobol"})
    assert res.status == "success" and res.output["escalation"] is True


def test_no_match():
    res = agent.handle("What is the weather today?")
    assert res.workflow_id == "NONE" and res.status == "error"


def test_eleventh_workflow_zero_code():
    a11 = Agent(ROOT / "examples" / "AI_Agent_Workflow_Assessment_11_workflows.xlsx")
    assert "WF011" in a11.workflows and "WF011" not in a11.registry
    res = a11.handle("Analyse the customer reviews and tell me which products get negative feedback.")
    assert res.workflow_id == "WF011" and res.status == "success"


if __name__ == "__main__":
    import inspect
    fails = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and inspect.isfunction(fn):
            try:
                fn(); print("PASS", name)
            except AssertionError as e:
                fails += 1; print("FAIL", name, e)
    print("\nALL PASSED" if not fails else f"\n{fails} failed")
