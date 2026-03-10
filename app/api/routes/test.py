from __future__ import annotations

from typing import Annotated, Any, Dict, List, Literal, Optional, Union

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.agents.user_query_validator.user_query_validator import runUserQueryValidator
from app.agents.mongo_query_builder.mongo_query_builder import runMongoQueryBuilder
from app.agents.mongo_query_validator.mongo_query_validator import runMongoQueryValidator
from app.agents.result_summarizer.result_summarizer import runResultSummarizer
from app.agents.suggested_questions.suggested_questions import runSuggestedQuestions
from app.core.config import settings
from app.db.mongo import runAggregation
from app.utils.serialization import convertObjectIds


router = APIRouter(prefix="/test", tags=["test"])


class HistoryMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., min_length=1)


# ── Per-agent request bodies ─────────────────────────────────────────────────

class UserQueryValidatorRequest(BaseModel):
    agent: Literal["user_query_validator"] = "user_query_validator"
    message: str = Field(..., min_length=1, description="The user's raw message")
    history: List[HistoryMessage] = Field(default_factory=list)


class MongoQueryBuilderRequest(BaseModel):
    agent: Literal["mongo_query_builder"] = "mongo_query_builder"
    normalizedQuery: str = Field(..., min_length=1, description="Normalized/rewritten user query")
    history: List[HistoryMessage] = Field(default_factory=list)
    collectionName: str = Field(default="", description="MongoDB collection name (defaults to configured collection)")
    refinement: Optional[str] = Field(default=None, description="Optional refinement guidance from the query validator")
    runPipeline: bool = Field(default=False, description="If true, execute the built pipeline and include results in the response")


class MongoQueryValidatorRequest(BaseModel):
    agent: Literal["mongo_query_validator"] = "mongo_query_validator"
    userMessage: str = Field(..., min_length=1, description="Original user message")
    normalizedQuery: str = Field(..., min_length=1, description="Normalized query")
    pipeline: List[Dict[str, Any]] = Field(..., description="MongoDB aggregation pipeline to execute")
    results: Optional[List[Dict[str, Any]]] = Field(default=None, description="Raw results — if omitted, the pipeline is run automatically")
    history: List[HistoryMessage] = Field(default_factory=list)


class ResultSummarizerRequest(BaseModel):
    agent: Literal["result_summarizer"] = "result_summarizer"
    question: str = Field(..., min_length=1, description="The user's question")
    pipeline: Optional[List[Dict[str, Any]]] = Field(default=None, description="MongoDB aggregation pipeline — if provided, results are fetched automatically")
    results: Optional[List[Dict[str, Any]]] = Field(default=None, description="Query results to summarize — required if pipeline is not provided")
    history: List[HistoryMessage] = Field(default_factory=list)


class SuggestedQuestionsRequest(BaseModel):
    agent: Literal["suggested_questions"] = "suggested_questions"
    question: str = Field(..., min_length=1, description="The user's original question")
    answer: str = Field(..., min_length=1, description="The assistant's answer to base suggestions on")
    history: List[HistoryMessage] = Field(default_factory=list)


# ── Discriminated union ──────────────────────────────────────────────────────

AgentRequest = Annotated[
    Union[
        UserQueryValidatorRequest,
        MongoQueryBuilderRequest,
        MongoQueryValidatorRequest,
        ResultSummarizerRequest,
        SuggestedQuestionsRequest,
    ],
    Field(discriminator="agent"),
]


# ── Endpoint ─────────────────────────────────────────────────────────────────

@router.post("/agent", summary="Run a single agent and return its raw output")
def testAgent(body: AgentRequest) -> Dict[str, Any]:
    """
    Test any agent in isolation. Set **agent** to one of:

    | Value | Agent |
    |---|---|
    | `user_query_validator` | Validates / normalizes the user's question |
    | `mongo_query_builder` | Builds a MongoDB aggregation pipeline |
    | `mongo_query_validator` | Validates query results and suggests refinements |
    | `result_summarizer` | Summarizes query results in plain language |
    | `suggested_questions` | Generates 3 follow-up questions |

    Supply only the fields that belong to the chosen agent.
    """
    history = [h.model_dump() for h in body.history]

    if isinstance(body, UserQueryValidatorRequest):
        result = runUserQueryValidator(
            message=body.message,
            history=history,
        )

    elif isinstance(body, MongoQueryBuilderRequest):
        collection = body.collectionName or settings.mongodbCollection
        result = runMongoQueryBuilder(
            normalizedQuery=body.normalizedQuery,
            history=history,
            collectionName=collection,
            refinement=body.refinement,
        )
        output = result.model_dump()
        if body.runPipeline and result.pipeline:
            try:
                raw = runAggregation(result.pipeline)
                output["fetchedResults"] = convertObjectIds(raw)
            except Exception as e:
                output["fetchedResults"] = []
                output["fetchedResultsError"] = str(e)
        return output

    elif isinstance(body, MongoQueryValidatorRequest):
        results = body.results if body.results is not None else runAggregation(body.pipeline)
        result = runMongoQueryValidator(
            userMessage=body.userMessage,
            normalizedQuery=body.normalizedQuery,
            pipeline=body.pipeline,
            results=results,
            history=history,
        )

    elif isinstance(body, ResultSummarizerRequest):
        if body.results is not None:
            results = body.results
        elif body.pipeline is not None:
            results = runAggregation(body.pipeline)
        else:
            raise HTTPException(status_code=422, detail="Either 'results' or 'pipeline' must be provided for result_summarizer")
        result = runResultSummarizer(
            question=body.question,
            results=results,
            history=history,
        )

    else:  # SuggestedQuestionsRequest
        result = runSuggestedQuestions(
            question=body.question,
            answer=body.answer,
            history=history,
        )

    return result.model_dump()

