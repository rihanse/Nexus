"""
Prompts loader — reads all agent prompts from .txt files in this directory.

To update any prompt, just edit the corresponding .txt file.
No Python changes needed.
"""
from pathlib import Path

_PROMPTS_DIR = Path(__file__).parent


def _load(filename: str) -> str:
    """Read and return the content of a prompt text file."""
    return (_PROMPTS_DIR / filename).read_text(encoding="utf-8").strip()


# Loaded once at import time; restart the app to pick up changes.
HR_SYSTEM_PROMPT = _load("hr.txt")
IT_SYSTEM_PROMPT = _load("it.txt")
FINANCE_SYSTEM_PROMPT = _load("finance.txt")
INTENT_DETECTION_PROMPT_TEMPLATE = _load("router.txt")

__all__ = [
    "HR_SYSTEM_PROMPT",
    "IT_SYSTEM_PROMPT",
    "FINANCE_SYSTEM_PROMPT",
    "INTENT_DETECTION_PROMPT_TEMPLATE",
]
