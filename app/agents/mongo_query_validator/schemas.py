from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


class MongoQueryValidatorOutput(BaseModel):
    isValid: bool = Field(
        ...,
        description="Whether the query results are valid and ready for summarization"
    )
    
    refinement: Optional[str] = Field(
        default=None,
        description="Guidance on what needs to be refined in the query (only if isValid=False). E.g., 'Use exact match for Health Care Services, Department of instead of regex matching'"
    )
    
    context: Optional[str] = Field(
        default=None,
        description="Additional context about matched entities or refinements to pass to summarizer"
    )
