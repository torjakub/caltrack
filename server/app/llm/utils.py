import json
import re


def extract_json(text: str) -> dict:
    """Some providers (Anthropic) have no forced-JSON mode — strip markdown
    code fences a model might still wrap its answer in before parsing."""
    stripped = text.strip()
    match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", stripped, re.DOTALL)
    if match:
        stripped = match.group(1)
    return json.loads(stripped)
