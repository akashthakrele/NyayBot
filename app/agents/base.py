"""
base.py — Shared LLM client and safe parsing utilities.

Single OpenAI client instance used across all agents.
"""

import os
from typing import TypedDict
from dotenv import load_dotenv
from openai import OpenAI

# ── Load environment ───────────────────────────────────────────────────────
load_dotenv()

# ── Single OpenAI client instance ─────────────────────────────────────────
client = OpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=os.environ.get("GITHUB_TOKEN", ""),
)


# ── StepResult TypedDict ──────────────────────────────────────────────────
class StepResult(TypedDict):
    step: str
    title: str
    content: str
    confidence: int  # 0 if not applicable


# ── LLM invocation helper ─────────────────────────────────────────────────
def invoke_llm(system: str, user: str) -> str:
    """
    Call the LLM with a system and user prompt.
    Returns the assistant's response text.
    On any failure returns an empty string — never raises.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        content = response.choices[0].message.content
        return content if content is not None else ""
    except Exception:
        return ""


# ── Safe key-value parser ─────────────────────────────────────────────────
def parse_kv(text: str, keys: list[str], defaults: dict) -> dict:
    """
    Parse structured LLM output into a dict.

    Splits each line on the FIRST colon, strips whitespace from both
    the key and the value.  Only keys present in *keys* are captured.
    Any key missing from the parsed output falls back to *defaults*.

    This function NEVER raises — malformed input simply returns defaults.

    Parameters
    ----------
    text : str
        Raw LLM response text.
    keys : list[str]
        Allowlist of keys to capture (case-sensitive match on uppercase).
    defaults : dict
        Fallback values for every key.

    Returns
    -------
    dict
        Parsed key-value mapping with guaranteed presence of every key
        listed in *defaults*.
    """
    result: dict = dict(defaults)  # start from a copy of defaults

    try:
        for line in text.strip().splitlines():
            if ":" not in line:
                continue
            raw_key, raw_value = line.split(":", 1)
            key = raw_key.strip()
            value = raw_value.strip()
            if key in keys:
                result[key] = value
    except Exception:
        # Any unexpected error → return defaults untouched
        pass

    return result
