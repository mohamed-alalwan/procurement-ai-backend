"""Data overview context loader."""

from pathlib import Path


DATA_OVERVIEW_PATH = Path(__file__).parent.parent / "core" / "data_overview.txt"


def loadDataOverview() -> str:
    """
    Load the data overview context text.
    
    This provides high-level context about the dataset being queried,
    which helps agents better understand the domain and make informed decisions.
    
    Returns:
        String containing the data overview description
    """
    if not DATA_OVERVIEW_PATH.exists():
        return ""
    return DATA_OVERVIEW_PATH.read_text(encoding="utf-8").strip()
