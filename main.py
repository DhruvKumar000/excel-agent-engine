"""
CLI for the Excel Agent Engine.

  python main.py                                   # interactive chat
  python main.py "Which products need restocking?" # one request
  python main.py --list                            # show workflows loaded from Excel
  python main.py --demo                            # run all 10 Excel test questions
  python main.py "Where is order ORD-1001?" --input identifier=ORD-1001
"""
import argparse
import json
import sys

from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table

from engine.agent import Agent
from engine import llm

console = Console()


def parse_inputs(pairs):
    out = {}
    for p in pairs or []:
        if "=" in p:
            k, v = p.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def show(result):
    color = {"success": "green", "needs_input": "yellow", "error": "red"}[result.status]
    console.print(Panel(f"[bold]{result.workflow_id} — {result.workflow_name}[/bold]\n"
                        f"confidence: {result.confidence}   reason: {escape(result.selection_reason)}",
                        title="Selected Workflow", border_style="cyan"))
    t = Table(title="Steps Executed", show_lines=False)
    t.add_column("#", width=3); t.add_column("Step"); t.add_column("Status"); t.add_column("Detail"); t.add_column("ms", justify="right")
    for i, s in enumerate(result.steps, 1):
        sc = {"ok": "green", "needs_input": "yellow", "error": "red"}[s.status]
        t.add_row(str(i), s.name, f"[{sc}]{s.status}[/{sc}]", escape(s.detail[:90]), str(s.duration_ms))
    console.print(t)
    body = result.message if result.status != "success" else json.dumps(result.output, indent=2, default=str)
    console.print(Panel(escape(body[:4000]), title=f"Final Result — [{color}]{result.status}[/{color}] ({result.total_ms} ms)", border_style=color))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("request", nargs="?", help="natural-language request")
    ap.add_argument("--input", "-i", action="append", help="key=value input (repeatable)")
    ap.add_argument("--list", action="store_true", help="list workflows from Excel")
    ap.add_argument("--demo", action="store_true", help="run all Excel test questions")
    ap.add_argument("--json", action="store_true", help="print raw JSON result")
    args = ap.parse_args()

    agent = Agent()
    if not args.json:
        console.print(f"[dim]LLM mode: {'MOCK (no API key)' if llm.is_mock() else llm.MODEL}[/dim]")

    if args.list:
        console.print(escape(agent.describe())); return

    if args.demo:
        demo_inputs = {
            "WF004": {"product_name": "Linen Shirt Beige", "category": "apparel", "material": "linen", "color": "beige"},
            "WF007": {"campaign_goal": "Launch autumn collection", "dates": "15–30 Oct", "target_audience": "young professionals"},
            "WF009": {"skills": "python, sql", "priority": "high", "deadline": "Friday"},
        }
        for wf in agent.workflows.values():
            console.rule(f"[bold]{wf.id}: \"{wf.test_request}\"")
            show(agent.handle(wf.test_request, demo_inputs.get(wf.id, {})))
        return

    if args.request:
        res = agent.handle(args.request, parse_inputs(args.input))
        print(res.to_json()) if args.json else show(res); return

    console.print("[bold cyan]Excel Agent Engine[/bold cyan] — type a request (or 'quit'). "
                  "Add inputs like: key=value key2=value2 after '|'")
    while True:
        try:
            line = console.input("\n[bold]you>[/bold] ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if line.lower() in ("quit", "exit", "q"):
            break
        req, _, extra = line.partition("|")
        show(agent.handle(req.strip(), parse_inputs(extra.split())))


if __name__ == "__main__":
    main()
