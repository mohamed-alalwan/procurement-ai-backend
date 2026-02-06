"""JSON utility functions."""

import json
from typing import Any


def safe_json_loads(text: str, default: Any = None) -> Any:
    """Safely load JSON, returning default on error."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return default


def safe_json_dumps(obj: Any, default: str = "{}") -> str:
    """Safely dump JSON, returning default on error."""
    try:
        return json.dumps(obj, indent=2)
    except (TypeError, ValueError):
        return default
