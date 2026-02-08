from pydantic import BaseModel


class ValidatorOutput(BaseModel):
    isValid: bool

    clarifyingQuestion: str = ""

    normalizedQuery: str = ""
