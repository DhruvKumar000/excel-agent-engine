# Example requests

Run any of these with `python main.py "<request>"` (add inputs with `-i key=value`) or in the Streamlit UI.

| Workflow | Request | Inputs (optional) |
|---|---|---|
| WF001 | Which products need restocking? | — |
| WF002 | Find products where vendor price differs by more than 10%. | — |
| WF003 | Process this vendor spreadsheet and show invalid rows. | `-i file=vendor_upload.csv` |
| WF004 | Generate SEO content for this product. | `-i product_name="Linen Shirt" -i color=beige` |
| WF005 | Where is order ORD-1001? | or `-i identifier=riya@example.com` |
| WF006 | Find likely duplicate products in the catalog. | — |
| WF007 | Create a campaign brief for the new collection. | `-i campaign_goal="Launch autumn collection" -i dates="15-30 Oct"` |
| WF008 | Classify these keywords and map them to pages. | — |
| WF009 | Assign this urgent task to the best available developer. | `-i skills="python, sql"` |
| WF010 | Which workflows are failing most often? | `-i source=live` to analyse this engine's own logs |

## Error / condition handling demos
| Case | Request | What happens |
|---|---|---|
| Order not found | Where is order ORD-9999? | `needs_input` → asks for another identifier (WF005 rule) |
| Missing goal/dates | Create a campaign brief | `needs_input` → asks for goal + dates before generating (WF007 rule) |
| Missing attributes | Generate SEO content -i product_name=Scarf | success, missing attributes explicitly flagged (WF004 rule) |
| Nobody suitable | Assign this task -i skills=cobol | success with `escalation: true` (WF009 rule) |
| Unknown request | What is the weather today? | `error` → no workflow matched |

## 11th workflow (zero code)
```
streamlit run app.py   →  upload examples/AI_Agent_Workflow_Assessment_11_workflows.xlsx
```
or
```python
from engine.agent import Agent
Agent("examples/AI_Agent_Workflow_Assessment_11_workflows.xlsx").handle("Analyse the customer reviews ...")
```
Outputs of every example are in `examples/outputs/`.
