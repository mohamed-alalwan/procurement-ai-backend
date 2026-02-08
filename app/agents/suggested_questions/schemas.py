from pydantic import BaseModel, Field
from typing import List


class SuggestionsOutput(BaseModel):
    suggestedQuestions: List[str] = Field(default_factory=list)
