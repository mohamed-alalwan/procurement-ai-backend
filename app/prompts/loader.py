"""Prompt loader utility."""

from pathlib import Path


def load_prompt(filename: str) -> str:
    """Load a prompt from a file."""
    prompt_dir = Path(__file__).parent
    prompt_path = prompt_dir / filename
    
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {filename}")
    
    return prompt_path.read_text(encoding="utf-8")
