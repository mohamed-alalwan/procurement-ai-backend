"""Agent schemas and data models."""

from pydantic import BaseModel


class ValidationResult(BaseModel):
    """Result of query validation."""
    is_valid: bool
    message: str


class QueryResult(BaseModel):
    """Result of a database query."""
    data: list
    count: int
