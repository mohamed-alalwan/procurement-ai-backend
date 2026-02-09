from typing import Any, Dict, List

from app.agents.user_query_validator import runUserQueryValidator
from app.agents.mongo_query_builder import runMongoQueryBuilder
from app.agents.mongo_query_validator import runMongoQueryValidator
from app.agents.result_summarizer import runResultSummarizer
from app.agents.suggested_questions import runSuggestedQuestions

from app.db.mongo import runAggregation
from app.utils.serialization import convertObjectIds


def runProcurementAssistant(
    message: str,
    history: List[Dict[str, Any]],
    collectionName: str,
) -> Dict[str, Any]:
    # Agent 1: User Query Validator
    validatorResult = runUserQueryValidator(message=message, history=history)
    
    if not validatorResult.isValid:
        # Agent 5: Suggested Questions (clarification)
        suggestionsOutput = runSuggestedQuestions(
            question=message, 
            answer=validatorResult.clarifyingQuestion,
            history=history + [{"role": "assistant", "content": validatorResult.clarifyingQuestion}]
        )
        return {
            "status": "needs_clarification",
            "clarifyingQuestion": validatorResult.clarifyingQuestion,
            "suggestedQuestions": suggestionsOutput.suggestedQuestions,
        }

    normalizedQuery = validatorResult.normalizedQuery or message
    historyWithNormalized = history + [{"role": "assistant", "content": f"Normalized: {normalizedQuery}"}]

    maxRefinements = 1
    refinementCount = 0
    refinementGuidance = None
    queryContext = None
    executionErrorRetry = False

    while refinementCount <= maxRefinements:
        # Agent 2: Mongo Query Builder
        try:
            queryOutput = runMongoQueryBuilder(
                normalizedQuery=normalizedQuery,
                history=historyWithNormalized,
                collectionName=collectionName,
                refinement=refinementGuidance,
            )
            pipeline = queryOutput.pipeline
        except (ValueError, Exception) as e:
            return {
                "status": "error",
                "error": f"Unable to generate query: {str(e)}",
                "suggestedQuestions": [],
            }

        try:
            results = runAggregation(pipeline)
        except Exception as e:
            if not executionErrorRetry:
                executionErrorRetry = True
                refinementGuidance = f"Previous query failed: {str(e)}. Fix the query."
                continue
            return {
                "status": "error",
                "error": f"Database query failed: {str(e)}",
                "suggestedQuestions": [],
            }

        # Agent 3: Mongo Query Validator
        try:
            queryValidation = runMongoQueryValidator(
                userMessage=message,
                normalizedQuery=normalizedQuery,
                pipeline=pipeline,
                results=results,
                history=history,
            )
            
            if queryValidation.isValid:
                queryContext = queryValidation.context
                break
            
            if refinementCount >= maxRefinements:
                queryContext = queryValidation.context
                break
            
            refinementGuidance = queryValidation.refinement
            queryContext = queryValidation.context
            refinementCount += 1
        except Exception:
            break

    historyWithQuery = historyWithNormalized + [
        {"role": "assistant", "content": f"Pipeline: {len(pipeline)} stages"}
    ]
    if queryContext:
        historyWithQuery.append({"role": "assistant", "content": queryContext})

    # Agent 4: Result Summarizer
    summarizerOutput = runResultSummarizer(
        question=normalizedQuery, 
        results=results, 
        history=historyWithQuery
    )
    
    # Agent 5: Suggested Questions
    suggestionsOutput = runSuggestedQuestions(
        question=normalizedQuery,
        answer=summarizerOutput.answer,
        history=historyWithQuery + [{"role": "assistant", "content": summarizerOutput.answer}]
    )

    return {
        "status": "ok",
        "answer": summarizerOutput.answer,
        "suggestedQuestions": suggestionsOutput.suggestedQuestions,
        "pipeline": pipeline,
        "data": convertObjectIds(results),
        "columns": [col.model_dump() for col in queryOutput.columns],
    }
