"""Utility for loading prompt files."""

from pathlib import Path


def loadPrompt(promptsDir: Path, fileName: str) -> str:
    """
    Load a prompt file from the specified directory.
    
    Args:
        promptsDir: Directory containing the prompt file
        fileName: Name of the prompt file (including extension)
        
    Returns:
        Content of the prompt file
        
    Raises:
        FileNotFoundError: If the prompt file doesn't exist
    """
    promptPath = promptsDir / fileName
    
    if not promptPath.exists():
        raise FileNotFoundError(f"Prompt file not found: {promptPath}")
    
    return promptPath.read_text(encoding="utf-8")
