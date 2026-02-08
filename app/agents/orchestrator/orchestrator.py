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
    print(f"[ORCHESTRATOR] Starting query validation for message: {message[:100]}...")
    validatorResult = runUserQueryValidator(message=message, history=history)
    print(f"[ORCHESTRATOR] Validator result - isValid: {validatorResult.isValid}")

    if not validatorResult.isValid:
        # Add validator output to history for context
        historyWithValidator = history + [
            {"role": "assistant", "content": validatorResult.clarifyingQuestion}
        ]
        
        # Generate suggested questions even during clarification
        suggestionsOutput = runSuggestedQuestions(
            question=message, 
            answer=validatorResult.clarifyingQuestion,
            history=historyWithValidator
        )
        print(f"[ORCHESTRATOR] Generated {len(suggestionsOutput.suggestedQuestions)} suggested questions during clarification")
        
        return {
            "status": "needs_clarification",
            "clarifyingQuestion": validatorResult.clarifyingQuestion,
            "suggestedQuestions": suggestionsOutput.suggestedQuestions,
        }

    normalizedQuery = validatorResult.normalizedQuery or message
    print(f"[ORCHESTRATOR] Normalized query: {normalizedQuery}")

    # Add normalized query to history for context
    historyWithNormalized = history + [
        {"role": "assistant", "content": f"Normalized query: {normalizedQuery}"}
    ]

    # Query refinement loop (max 2 iterations to avoid infinite loops)
    maxRefinements = 1
    refinementCount = 0
    refinementGuidance = None
    queryContext = None

    while refinementCount <= maxRefinements:
        # 2) Build Mongo pipeline
        print(f"[ORCHESTRATOR] Building MongoDB aggregation pipeline (attempt {refinementCount + 1})")
        try:
            queryOutput = runMongoQueryBuilder(
                normalizedQuery=normalizedQuery,
                history=historyWithNormalized,
                collectionName=collectionName,
                refinement=refinementGuidance,
            )
            pipeline = queryOutput.pipeline
            print(f"[ORCHESTRATOR] Generated pipeline with {len(pipeline)} stages: {queryOutput.explanation}")
        except ValueError as e:
            # Pipeline validation failed
            print(f"[ORCHESTRATOR ERROR] Pipeline validation failed: {str(e)}")
            return {
                "status": "error",
                "answer": f"Unable to generate a valid query: {str(e)}. Please try rephrasing your question.",
                "suggestedQuestions": [],
            }
        except Exception as e:
            # Other errors during query building
            print(f"[ORCHESTRATOR ERROR] Query builder error: {str(e)}")
            return {
                "status": "error",
                "answer": f"An error occurred while processing your query: {str(e)}",
                "suggestedQuestions": [],
            }

        # 3) Execute
        print("[ORCHESTRATOR] Executing MongoDB aggregation")
        try:
            results = runAggregation(pipeline)
            print(f"[ORCHESTRATOR] Query returned {len(results)} results")
        except Exception as e:
            # MongoDB execution error
            print(f"[ORCHESTRATOR ERROR] MongoDB execution error: {str(e)}")
            return {
                "status": "error",
                "answer": f"Database query failed: {str(e)}. The query may be malformed.",
                "suggestedQuestions": [],
            }

        # 4) Validate query results
        print("[ORCHESTRATOR] Validating query results")
        try:
            queryValidation = runMongoQueryValidator(
                userMessage=message,
                normalizedQuery=normalizedQuery,
                pipeline=pipeline,
                results=results,
                history=history,
            )
            print(f"[ORCHESTRATOR] Query validation - isValid: {queryValidation.isValid}")

            if queryValidation.isValid:
                # Results are good, proceed to summarization
                queryContext = queryValidation.context
                break
            else:
                # Refinement needed
                print(f"[ORCHESTRATOR] Refinement needed: {queryValidation.refinement}")
                
                if refinementCount >= maxRefinements:
                    # Max refinements reached, proceed anyway
                    print("[ORCHESTRATOR] Max refinements reached, proceeding with current results")
                    queryContext = queryValidation.context
                    break
                
                # Use refinement guidance for next iteration
                refinementGuidance = queryValidation.refinement
                queryContext = queryValidation.context
                refinementCount += 1
                print(f"[ORCHESTRATOR] Applying refinement guidance (attempt {refinementCount + 1})")
                
        except Exception as e:
            # Validation error, proceed with current results
            print(f"[ORCHESTRATOR WARNING] Query validation error: {str(e)}, proceeding anyway")
            break

    # Add query builder context to history
    historyWithQuery = historyWithNormalized + [
        {"role": "assistant", "content": f"Generated MongoDB pipeline with {len(pipeline)} stages"}
    ]

    # Add query validation context if available
    if queryContext:
        historyWithQuery.append({"role": "assistant", "content": f"Query context: {queryContext}"})

    # 5) Summarize
    print("[ORCHESTRATOR] Generating summary")
    summarizerOutput = runResultSummarizer(question=normalizedQuery, results=results, history=historyWithQuery)
    print(f"[ORCHESTRATOR] Summary generated: {summarizerOutput.answer[:100]}...")

    # Add summarizer output to history for context
    historyWithSummarizer = historyWithQuery + [
        {"role": "assistant", "content": summarizerOutput.answer}
    ]

    # 6) Suggested questions
    print("[ORCHESTRATOR] Generating suggested questions")
    suggestionsOutput = runSuggestedQuestions(question=normalizedQuery, answer=summarizerOutput.answer, history=historyWithSummarizer)
    print(f"[ORCHESTRATOR] Generated {len(suggestionsOutput.suggestedQuestions)} suggested questions")

    # Convert ObjectIds to strings for JSON serialization
    serializedResults = convertObjectIds(results)

    # Convert column metadata to dict format
    columns = [col.model_dump() for col in queryOutput.columns]

    return {
        "status": "ok",
        "answer": summarizerOutput.answer,
        "suggestedQuestions": suggestionsOutput.suggestedQuestions,
        # Useful for debugging/demo. You can hide later if you want.
        
        "pipeline": pipeline,
        "data": serializedResults,
        "columns": columns,
    }
