"""Field catalog utilities."""

import json
from pathlib import Path
from typing import Dict, Any


FIELD_CATALOG_PATH = Path(__file__).parent.parent / "core" / "field_catalog.json"


def loadFieldCatalog() -> Dict[str, Any]:
    """
    Load the field catalog JSON directly.
    
    Returns:
        Dictionary containing field definitions and metadata
    """
    if not FIELD_CATALOG_PATH.exists():
        return {}
    return json.loads(FIELD_CATALOG_PATH.read_text(encoding="utf-8"))
