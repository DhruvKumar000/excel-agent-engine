"""
LAYER 2 — Router Agent: "Which workflow does the user want?"

Strategy (two layers, so it is both smart and reliable):
  1. LLM routing  — the LLM sees every workflow's name, trigger, inputs and the
                    Excel test question (used as a few-shot example) and returns JSON.
  2. Keyword fallback — if the LLM is unavailable (mock mode) or returns something
                    invalid, score each workflow by keyword overlap.

Because the catalog comes straight from Excel, an 11th row is routable with zero code.
"""
import re
from typing import Dict, Tuple

from . import llm
from .models import Workflow

STOP = {"the", "a", "an", "this", "that", "for", "to", "of", "in", "and", "or", "is", "are",
        "which", "what", "where", "show", "me", "please", "my", "our", "with", "find", "all"}

# Extra hints per workflow for the keyword fallback (names/triggers already count)
SYNONYMS = {
    "WF001": "restock restocking stock inventory low reorder",
    "WF002": "price prices vendor validate validation differ difference 10%",
    "WF003": "process vendor file spreadsheet upload invalid rows clean csv xlsx",
    "WF004": "seo content description generate product write meta title",
    "WF005": "order status where ord tracking shipment delivery",
    "WF006": "duplicate duplicates catalog similar same",
    "WF007": "campaign brief marketing collection launch promotion",
    "WF008": "keyword keywords classify intent map pages",
    "WF009": "assign task employee developer urgent team",
    "WF010": "performance report failing failures logs slow workflows",
}


def _tokens(text: str):
    return {t for t in re.findall(r"[a-z0-9%\-]+", text.lower()) if t not in STOP}


def keyword_route(request: str, workflows: Dict[str, Workflow]) -> Tuple[str, float, str]:
    req = _tokens(request)
    best_id, best_score = None, 0.0
    for wf in workflows.values():
        corpus = " ".join([wf.name, wf.trigger, wf.inputs, wf.test_request, SYNONYMS.get(wf.id, "")])
        hits = req & _tokens(corpus)
        score = len(hits) / max(len(req), 1)
        # name words are strong signals
        score += 0.5 * len(req & _tokens(wf.name))
        if score > best_score:
            best_id, best_score = wf.id, score
    if best_id is None or best_score == 0:
        return "", 0.0, "No workflow matched the request keywords."
    conf = min(0.95, 0.4 + best_score * 0.3)
    return best_id, round(conf, 2), f"Keyword match on '{workflows[best_id].name}'."


def llm_route(request: str, workflows: Dict[str, Workflow]) -> Tuple[str, float, str]:
    catalog = "\n".join(
        f"- {wf.id}: {wf.name}\n    trigger: {wf.trigger}\n    inputs: {wf.inputs}\n"
        f"    example request: \"{wf.test_request}\""
        for wf in workflows.values()
    )
    prompt = f"""You are a workflow router. Pick the single best workflow for the user's request.

Available workflows:
{catalog}

User request: "{request}"

Respond ONLY with JSON: {{"workflow_id": "...", "confidence": 0.0-1.0, "reason": "one sentence"}}
If nothing fits, use workflow_id "NONE"."""
    data = llm.complete_json(prompt)
    wf_id = str(data.get("workflow_id", "")).strip().upper()
    if wf_id in workflows:
        return wf_id, float(data.get("confidence", 0.8)), str(data.get("reason", "LLM selection"))
    return "", 0.0, str(data.get("reason", "LLM found no match"))


def route(request: str, workflows: Dict[str, Workflow]) -> Tuple[str, float, str]:
    """Return (workflow_id, confidence, reason). Empty id = no match."""
    if not llm.is_mock():
        try:
            wf_id, conf, reason = llm_route(request, workflows)
            if wf_id:
                return wf_id, conf, "LLM: " + reason
        except Exception as e:  # network / parse error → fall back
            reason_prefix = f"LLM failed ({type(e).__name__}); "
        else:
            reason_prefix = "LLM unsure; "
    else:
        reason_prefix = ""
    wf_id, conf, reason = keyword_route(request, workflows)
    return wf_id, conf, reason_prefix + reason
