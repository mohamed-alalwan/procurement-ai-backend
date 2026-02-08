from pydantic import BaseModel, Field
from typing import Any, Dict, List
from enum import Enum


class FieldType(str, Enum):
    MONEY = "MONEY"
    PERCENTAGE = "PERCENTAGE"
    YEAR = "YEAR"
    QUARTER = "QUARTER"
    MONTH = "MONTH"
    DATE = "DATE"
    NUMERIC = "NUMERIC"
    TEXT = "TEXT"


class ColumnMetadata(BaseModel):
    name: str = Field(..., description="Column name as it appears in the result")
    type: FieldType = Field(..., description="Type of the column data")


class MongoQueryOutput(BaseModel):
    pipeline: List[Dict[str, Any]] = Field(default_factory=list)

    explanation: str = ""

    columns: List[ColumnMetadata] = Field(
        default_factory=list,
        description="List of columns that will be returned in the query results with their types"
    )
