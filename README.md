# 🧩 Excel Agent Engine

> **One agent. Ten workflows. Zero hard-coded chatbots.**
> The Excel file *is* the workflow catalog. Python tools do the work. An LLM decides which workflow to run.

Built for the *AI Agent Workflow Automation* technical assignment. The agent reads
`data/AI_Agent_Workflow_Assessment.xlsx`, understands a natural-language request, selects the
right workflow, executes its steps with reusable tools, handles conditions/errors, and returns
**which workflow was selected, what steps ran, and the final output** — exactly as the brief asks.

---

## 1. The idea in one picture

```
                 ┌──────────────────────────────────────────────┐
  User request   │  LAYER 1  loader.py    Excel  →  Workflow catalog│
 "Which products │                        (name, trigger, steps,   │
  need restock?" │                         decision rule, tools)   │
       │         └──────────────────────┬───────────────────────┘
       ▼                                ▼
  ┌─────────────────────────────────────────────────────────┐
  │  LAYER 2  router.py   LLM picks the workflow (JSON)      │
  │                       ↳ keyword fallback if LLM unsure  │
  └──────────────────────────┬──────────────────────────────┘
                             ▼  WF001 · confidence 0.9 · reason
  ┌─────────────────────────────────────────────────────────┐
  │  LAYER 3  executor.py  runs the handler's @step methods │
  │     workflows/wf001_*.py   ──uses──►  tools.py          │
  │     (one small file per      csv_reader · calculator    │
  │      workflow, or the        text_similarity · llm      │
  │      GenericLLMHandler)      order_database · shipment  │
  └──────────────────────────┬──────────────────────────────┘
                             ▼
        RunResult { selected workflow, steps[], output, status }
                             │
                             └──► logs/executions.csv  (WF010 reads this!)
```

**Three layers, three files you need to understand.** Everything else is a plug-in.

---

## 2. Why this architecture (technical decisions)

| Decision | Why |
|---|---|
| **Excel is the single source of truth** | The assignment says "Excel as the workflow source". Steps, decision rules and tools are read from the sheet at runtime — nothing about a workflow is duplicated in code. |
| **Plain Python, no agent framework** | 10 deterministic business workflows don't need LangGraph's state machine. Plain Python is easier to read, test, explain in a 10-minute video and debug. The LLM is used where it adds value: *routing* and *content generation*. |
| **Two-stage router (LLM → keyword fallback)** | LLM gives real understanding of paraphrased requests; keyword scoring guarantees the system still works offline / when the API fails. The Excel `Test_Questions` sheet is injected as few-shot examples, so the router improves just by editing Excel. |
| **One handler file per workflow with `@step`** | Each Excel step maps to one small method. The executor runs them in order, times them, and records a trace — this *is* the "steps executed" output. |
| **Shared tool registry** | `csv_reader`, `calculator`, `text_similarity`, `llm`, `order_database`, `shipment_lookup` are registered once and reused by every workflow. Real APIs are simulated with CSVs (allowed by the brief). |
| **Typed exceptions → statuses** | `NeedsInput` → `needs_input` (WF005 "ask for another identifier", WF007 "request goal/dates"). Any other exception → `error` with the failing step. No crashes, always a clean answer. |
| **GenericLLMHandler** | A workflow that exists in Excel but has no Python file still runs — the LLM executes the Excel steps. That is how an **11th workflow needs zero code**. |
| **Provider-agnostic LLM** | One `openai` client + `LLM_BASE_URL`. Works with OpenAI, Groq, Gemini or local Ollama. `LLM_MOCK` mode runs everything with no key — tests and demos never depend on the network. |
| **Self-monitoring** | Every run is appended to `logs/executions.csv`. WF010 (Performance Report) can analyse the engine's *own* history (`-i source=live`). |

---

## 3. Quick start

```bash
git clone <this repo> && cd excel-agent-engine
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # add an API key, or leave empty for MOCK mode

python main.py --list                                  # workflows loaded from Excel
python main.py --demo                                  # run all 10 Excel test questions
python main.py "Which products need restocking?"       # one request
python main.py "Where is order ORD-1001?"
python main.py "Generate SEO content" -i product_name="Linen Shirt" -i color=beige
python main.py                                         # interactive chat mode

streamlit run app.py                                   # web UI (used in the Loom video)
python -m pytest -q                                    # 12 tests
```

Works out of the box with **no API key** (rule-based mock). Add a key for real LLM routing and
content generation — see `.env.example` for OpenAI / Groq / Gemini / Ollama.

---

## 4. What a result looks like

```
$ python main.py "Which products need restocking?"

╭──────────── Selected Workflow ─────────────╮
│ WF001 — Inventory Restock Check             │
│ confidence: 0.9  reason: LLM: user asks     │
│ which items are low on stock                │
╰─────────────────────────────────────────────╯
  #  Step                                      Status  Detail                          ms
  1  Load inventory                            ok      8 products loaded                2
  2  Compare current stock with minimum        ok      4 below threshold                1
  3  Identify low-stock products               ok      Cotton T-Shirt White, Leather…   0
  4  Calculate reorder quantity                ok      reorder qty = (2 × minimum) − …  0
  5  Generate restock list                     ok      4 items in restock list          0
╭──────────── Final Result — success ────────╮
│ { "products_requiring_restock": [            │
│     {"sku": "SKU-001", "product_name": …,    │
│      "current_stock": 12, "minimum_stock": 50,│
│      "suggested_reorder_qty": 88}, … ],       │
│   "count": 4 }                                │
╰─────────────────────────────────────────────╯
```

Full JSON outputs for all 10 workflows + error cases: [`examples/outputs/`](examples/outputs).
All example requests: [`examples/requests.md`](examples/requests.md).

---

## 5. The 10 workflows

| ID | Workflow | Decision rule implemented | Tools |
|---|---|---|---|
| WF001 | Inventory Restock Check | `current_stock < minimum_stock` → restock, qty = 2×min − current | csv_reader, calculator |
| WF002 | Product Price Validation | flag when \|% diff\| > 10 % | csv_reader, calculator |
| WF003 | Vendor File Processing | normalise column aliases; rows missing SKU/name are invalid; writes cleaned CSV | csv_reader (csv/xlsx) |
| WF004 | Product Description Generator | never invents attributes — marks `[missing: …]` | llm |
| WF005 | Customer Order Status | order id *or* email; not found → `needs_input` ask again | order_database, shipment_lookup |
| WF006 | Duplicate Product Detection | same normalised SKU = definite (1.0); name similarity ≥ 0.85 + same category = possible | csv_reader, text_similarity |
| WF007 | Marketing Campaign Brief | goal or dates missing → `needs_input` before generating | llm, csv_reader |
| WF008 | SEO Keyword Classification | informational / commercial / transactional / navigational → page mapping, priority | csv_reader, rules |
| WF009 | Employee Task Assignment | skills × workload score; nobody with capacity → **escalate** | csv_reader, ranking |
| WF010 | Workflow Performance Report | flag failure > 10 % or avg time > 1500 ms; recommendations | csv_reader, calculator |

---

## 6. Adding an 11th workflow

**Step 1 — add one row to the Excel.** That's it. The engine routes to it and the
`GenericLLMHandler` executes the Excel steps with the LLM.

```
examples/AI_Agent_Workflow_Assessment_11_workflows.xlsx   ← WF011 "Customer Review Sentiment" already added
```

```python
Agent("examples/AI_Agent_Workflow_Assessment_11_workflows.xlsx") \
    .handle("Analyse the customer reviews and tell me which products get negative feedback.")
# → WF011 selected · 5 steps executed · status success   (no Python written)
```

**Step 2 (optional) — add precise logic.** Drop `workflows/wf011_review_sentiment.py`:

```python
from engine.executor import BaseHandler, step

class ReviewSentiment(BaseHandler):
    workflow_id = "WF011"

    @step("Load reviews")
    def load(self):
        self.state["df"] = self.use("csv_reader")("reviews.csv")
        return f"{len(self.state['df'])} reviews"

    @step("Classify sentiment")
    def classify(self):
        ...
        self.state["output"] = {...}
```

Auto-discovery registers it. **No other file changes.** Nothing to import, no `if/elif` chain to extend.

---

## 7. Project structure

```
excel-agent-engine/
├── main.py                 CLI (chat / single request / --demo / --list)
├── app.py                  Streamlit UI
├── engine/
│   ├── loader.py           Excel → Workflow objects            (Layer 1)
│   ├── router.py           LLM routing + keyword fallback       (Layer 2)
│   ├── executor.py         @step runner, trace, error handling  (Layer 3)
│   ├── agent.py            glue: request → route → handler → result
│   ├── tools.py            shared tool registry (@tool)
│   ├── generic_handler.py  zero-code LLM handler for new Excel rows
│   ├── llm.py              provider-agnostic client + mock mode
│   └── models.py           Workflow / StepResult / RunResult / NeedsInput
├── workflows/              one small file per workflow, auto-discovered
│   ├── wf001_inventory_restock.py … wf010_performance_report.py
├── data/
│   ├── AI_Agent_Workflow_Assessment.xlsx   ← the provided workflow source
│   └── samples/            CSVs simulating inventory, orders, vendors, logs…
├── examples/
│   ├── requests.md         every example request + expected behaviour
│   ├── outputs/            JSON result of each workflow and error case
│   └── AI_Agent_Workflow_Assessment_11_workflows.xlsx
├── tests/test_all_workflows.py   12 tests (routing, all workflows, errors, 11th)
├── logs/executions.csv     created at runtime; analysed by WF010
├── requirements.txt · .env.example · README.md
```

---

## 8. How the evaluation criteria are met

| Criterion | Where |
|---|---|
| Reusability | `engine/` never changes per workflow; tools shared via `@tool` registry |
| Scalability | New Excel row → works via GenericLLMHandler; optional one-file handler |
| Maintainability | 3-layer design, ~100 lines per workflow, typed results, 12 tests |
| Workflow selection | `router.py` — LLM JSON decision with reason + confidence, keyword fallback |
| Agent reasoning | selection reason + per-step detail printed for every run |
| Tool execution | `handler.use("tool_name")` — tracked and logged per run |
| Error / condition handling | `NeedsInput`, `WorkflowError`, per-step try/except → clean statuses |

---

*AI assistants were used during development; every line was reviewed, run and tested against all 10 workflows.*
