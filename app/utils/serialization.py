"""Serialization utilities for handling MongoDB and other data types."""

from typing import Any
from bson import ObjectId


def convertObjectIds(data: Any) -> Any:
    """
    Recursively convert ObjectId instances to strings for JSON serialization.
    
    This function handles:
    - Individual ObjectId instances
    - Dictionaries containing ObjectIds (recursively)
    - Lists containing ObjectIds (recursively)
    - Other data types (returned as-is)
    
    Args:
        data: Data that may contain ObjectId instances
        
    Returns:
        Data with all ObjectIds converted to strings
    """
    if isinstance(data, ObjectId):
        return str(data)
    elif isinstance(data, dict):
        return {k: convertObjectIds(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [convertObjectIds(item) for item in data]
    return data
