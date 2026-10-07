"""
Streamlit UI — run with:  streamlit run app.py

Shows the three things the assignment asks for, visually:
  1. which workflow was selected (and why)
  2. which steps were executed (with status + timing)
  3. the final output
"""
import json
import tempfile
from pathlib import Path

import streamlit as st

from engine.agent import Agent
from engine import llm

st.set_page_config(page_title="Excel Agent Engine", page_icon="🧩", layout="wide")
st.title("🧩 Excel Agent Engine")
st.caption("Excel defines the workflows · an LLM routes the request · Python tools execute the steps")

# ------------------------------------------------------------------ sidebar
with st.sidebar:
    st.header("Workflow source")
    uploaded = st.file_uploader("Upload a workflow Excel (optional)", type=["xlsx"])
    if uploaded:
        tmp = Path(tempfile.gettempdir()) / uploaded.name
        tmp.write_bytes(uploaded.getvalue())
        agent = Agent(tmp)
    else:
        agent = Agent()
    st.success(f"{len(agent.workflows)} workflows loaded")
    st.write(f"LLM: `{'MOCK (no API key)' if llm.is_mock() else llm.MODEL}`")
    st.divider()
    st.header("Workflows in Excel")
    for wf in agent.workflows.values():
        kind = "🐍 custom" if wf.id in agent.registry else "🤖 generic (LLM)"
        with st.expander(f"{wf.id} · {wf.name}"):
            st.write(f"**Trigger:** {wf.trigger}")
            st.write(f"**Steps:** " + " → ".join(wf.steps))
            st.write(f"**Decision:** {wf.decision_logic}")
            st.write(f"**Handler:** {kind}")

# --------------------------------------------------------------- main panel
examples = [wf.test_request for wf in agent.workflows.values() if wf.test_request]
col1, col2 = st.columns([3, 2])
with col1:
    request = st.text_input("Your request", value=st.session_state.get("req", examples[0] if examples else ""))
    picked = st.selectbox("…or pick an Excel test question", [""] + examples)
    if picked:
        request = picked
with col2:
    st.write("Optional inputs (JSON)")
    inputs_text = st.text_area("inputs", value='{}', height=120, label_visibility="collapsed",
                               help='e.g. {"product_name": "Linen Shirt", "color": "beige"} or {"identifier": "ORD-1001"}')

if st.button("▶ Run agent", type="primary", use_container_width=True):
    try:
        inputs = json.loads(inputs_text or "{}")
    except json.JSONDecodeError:
        st.error("Inputs must be valid JSON"); st.stop()

    with st.spinner("Routing & executing…"):
        res = agent.handle(request, inputs)

    # 1. selected workflow
    st.subheader("1️⃣ Selected workflow")
    c1, c2, c3 = st.columns(3)
    c1.metric("Workflow", f"{res.workflow_id}")
    c2.metric("Confidence", f"{res.confidence:.0%}")
    c3.metric("Total time", f"{res.total_ms} ms")
    st.info(f"**{res.workflow_name}** — {res.selection_reason}")

    # 2. steps
    st.subheader("2️⃣ Steps executed")
    icon = {"ok": "✅", "needs_input": "🟡", "error": "❌"}
    for i, s in enumerate(res.steps, 1):
        st.write(f"{icon[s.status]} **Step {i}: {s.name}** — {s.detail}  `{s.duration_ms} ms`")

    # 3. output
    st.subheader("3️⃣ Final result")
    if res.status == "success":
        st.success("Success")
        st.json(res.output)
    elif res.status == "needs_input":
        st.warning(f"Needs more input: {res.message}")
    else:
        st.error(res.message)
    with st.expander("Raw JSON result"):
        st.code(res.to_json(), language="json")
