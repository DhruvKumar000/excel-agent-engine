"""
TOOLS — the "hands" of the agent. Shared by every workflow.

Each tool is a plain Python function registered with @tool("name").
The names match the 'Tools_Required' column in the Excel
(csv reader, calculator, text similarity, llm, order database/api, ...).

Real APIs are simulated with local CSV files (allowed by the assignment).
"""
from difflib import SequenceMatcher
from pathlib import Path
from typing import Callable, Dict, Optional
import pandas as pd

from . import llm

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "samples"

TOOLS: Dict[str, Callable] = {}


def tool(name: str):
    """Register a function as a tool the agent can call."""
    def deco(fn):
        TOOLS[name] = fn
        fn.tool_name = name
        return fn
    return deco


# ------------------------------------------------------------------ data tools
@tool("csv_reader")
def read_table(filename: str, path: Optional[str] = None) -> pd.DataFrame:
    """Read a CSV or XLSX file from data/samples (or a given path)."""
    p = Path(path) if path else DATA_DIR / filename
    if not p.exists():
        raise FileNotFoundError(f"Data file not found: {p}")
    if p.suffix.lower() in (".xlsx", ".xls"):
        return pd.read_excel(p)
    return pd.read_csv(p)


@tool("calculator")
def percent_diff(a: float, b: float) -> float:
    """Percentage difference of b relative to a."""
    if a == 0:
        return float("inf")
    return round((b - a) / a * 100, 2)


@tool("text_similarity")
def similarity(a: str, b: str) -> float:
    """0..1 similarity between two strings (normalised)."""
    a, b = str(a).lower().strip(), str(b).lower().strip()
    return round(SequenceMatcher(None, a, b).ratio(), 2)


# ------------------------------------------------------------ simulated APIs
@tool("order_database")
def lookup_order(identifier: str) -> Optional[dict]:
    """Simulated Order API: search by order id OR customer email."""
    df = read_table("orders.csv")
    ident = str(identifier).strip().lower()
    hit = df[(df["order_id"].str.lower() == ident) | (df["customer_email"].str.lower() == ident)]
    return None if hit.empty else hit.iloc[0].to_dict()


@tool("shipment_lookup")
def lookup_shipment(order_id: str) -> Optional[dict]:
    """Simulated Shipment API."""
    df = read_table("shipments.csv")
    hit = df[df["order_id"] == order_id]
    return None if hit.empty else hit.iloc[0].to_dict()


# ------------------------------------------------------------------- LLM tool
@tool("llm")
def generate(prompt: str, system: str = "You are a precise business assistant.") -> str:
    """Call the LLM (or mock) for text generation."""
    return llm.complete(prompt, system=system)


def list_tools() -> Dict[str, str]:
    return {name: (fn.__doc__ or "").strip() for name, fn in TOOLS.items()}
