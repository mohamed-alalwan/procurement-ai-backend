from pydantic import BaseModel


class SummarizerOutput(BaseModel):
    answer: str
