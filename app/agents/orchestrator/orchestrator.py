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
    # 1) Validate user query
    validatorResult = runUserQueryValidator(message=message, history=history)
    
    if not validatorResult.isValid:
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

    # 2) Build and execute query with retry logic
    maxRefinements = 1
    refinementCount = 0
    refinementGuidance = None
    queryContext = None
    executionErrorRetry = False

    while refinementCount <= maxRefinements:
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

        # 3) Validate results
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

    # 4) Summarize and suggest questions
    historyWithQuery = historyWithNormalized + [
        {"role": "assistant", "content": f"Pipeline: {len(pipeline)} stages"}
    ]
    if queryContext:
        historyWithQuery.append({"role": "assistant", "content": queryContext})

    summarizerOutput = runResultSummarizer(
        question=normalizedQuery, 
        results=results, 
        history=historyWithQuery
    )
    
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
