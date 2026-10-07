"""
LLM client — ONE small wrapper, ANY provider.

Uses the OpenAI SDK with a configurable BASE_URL, so the same code works with:
  - OpenAI          (default)
  - Groq            LLM_BASE_URL=https://api.groq.com/openai/v1
  - Google Gemini   LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
  - Ollama (local)  LLM_BASE_URL=http://localhost:11434/v1

If no API key is set (or LLM_MOCK=true) the engine runs in MOCK mode:
rule-based answers so the whole project still works offline for demos/tests.
"""
import json
import os
import re
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("LLM_API_KEY", "")
BASE_URL = os.getenv("LLM_BASE_URL") or None
MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
MOCK = os.getenv("LLM_MOCK", "").lower() == "true" or not API_KEY

_client = None
if not MOCK:
    from openai import OpenAI
    _client = OpenAI(api_key=API_KEY, base_url=BASE_URL)


def is_mock() -> bool:
    return MOCK


def complete(prompt: str, system: str = "You are a precise business assistant.", json_mode: bool = False) -> str:
    """Return the model's text. In mock mode return a deterministic placeholder."""
    if MOCK:
        return _mock_complete(prompt, json_mode)
    kwargs = {"model": MODEL, "temperature": 0.2,
              "messages": [{"role": "system", "content": system},
                           {"role": "user", "content": prompt}]}
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    resp = _client.chat.completions.create(**kwargs)
    return resp.choices[0].message.content.strip()


def complete_json(prompt: str, system: str = "Respond with valid JSON only.") -> dict:
    text = complete(prompt, system=system, json_mode=True)
    text = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.M).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.S)
        return json.loads(m.group(0)) if m else {}


# ---------------------------------------------------------------- mock mode
def _mock_complete(prompt: str, json_mode: bool) -> str:
    """Very small rule-based stand-in so demos work without a key."""
    if json_mode:
        return "{}"
    low = prompt.lower()
    name = re.search(r"product_name:\s*(.+)", prompt)
    name = name.group(1).strip() if name else "this product"
    missing = re.search(r"Attributes NOT provided:\s*(.+?)\.", prompt)
    missing = missing.group(1).strip() if missing else "none"
    if "write a short description" in low:
        return f"[MOCK LLM] {name} — simple, well-made and ready for everyday use."
    if "write a seo title" in low:
        return f"[MOCK LLM] {name} | Buy Online"
    if "write a meta description" in low:
        return f"[MOCK LLM] Shop {name}. Quality you can trust, delivered to your door."
    if "write a product description" in low:
        return (f"[MOCK LLM] {name} is designed for everyday comfort and durability. "
                f"Made with care using the details provided. [missing: {missing}]")
    if "campaign brief" in low:
        return ("[MOCK LLM] Messaging: Fresh styles, limited time.\n"
                "Channels: Instagram, Email, Google Ads.\n"
                "Checklist: creatives, landing page, tracking, launch, review.")
    if "recommend" in low or "improve" in low:
        return "[MOCK LLM] Add retries to failing steps, cache file reads, and monitor slow steps."
    return "[MOCK LLM] " + prompt[:120]
