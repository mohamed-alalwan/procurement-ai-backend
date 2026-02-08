from typing import List, Dict, Any
from pathlib import Path

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

from .schemas import MongoQueryOutput
from app.core.llm import getChatModel
from app.utils.prompt_loader import loadPrompt
from app.utils.field_catalog import loadFieldCatalog
from app.utils.data_overview import loadDataOverview


PROMPTS_DIR = Path(__file__).parent


def validatePipeline(pipeline: List[Dict[str, Any]]) -> None:
    """
    Validate MongoDB aggregation pipeline for common errors.
    Raises ValueError if validation fails.
    """
    for idx, stage in enumerate(pipeline):
        for operator, spec in stage.items():
            # Check $project, $group, $addFields for empty field names
            if operator in ["$project", "$group", "$addFields", "$set"]:
                if isinstance(spec, dict):
                    for field_name in spec.keys():
                        if not field_name or field_name.strip() == "":
                            raise ValueError(
                                f"Stage {idx} ({operator}): Empty field name detected. "
                                f"All field names must be non-empty strings."
                            )
                    
                    # Validate specific operators
                    _validateOperators(spec, idx, operator)


def _validateOperators(spec: Dict[str, Any], stageIdx: int, stageName: str) -> None:
    """Recursively validate MongoDB operator usage."""
    if not isinstance(spec, dict):
        return
    
    for key, value in spec.items():
        if key == "$arrayElemAt":
            if not isinstance(value, list) or len(value) != 2:
                raise ValueError(
                    f"Stage {stageIdx} ({stageName}): $arrayElemAt requires exactly 2 arguments [array, index], "
                    f"got {len(value) if isinstance(value, list) else 'non-array'}"
                )
        
        # Recursively check nested structures
        if isinstance(value, dict):
            _validateOperators(value, stageIdx, stageName)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    _validateOperators(item, stageIdx, stageName)


def runMongoQueryBuilder(
    normalizedQuery: str,
    history: List[Dict[str, Any]],
    collectionName: str,
    refinement: str = None,
) -> MongoQueryOutput:
    systemPrompt = loadPrompt(PROMPTS_DIR, "query_builder_system.txt")

    userPrompt = loadPrompt(PROMPTS_DIR, "query_builder_user.txt")

    dataOverview = loadDataOverview()
    fieldCatalog = loadFieldCatalog()

    parser = PydanticOutputParser(pydantic_object=MongoQueryOutput)

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", systemPrompt + "\n\n{format_instructions}"),
            ("human", userPrompt),
        ]
    )

    model = getChatModel()

    chain = prompt.partial(format_instructions=parser.get_format_instructions()) | model | parser

    trimmedHistory = history[-5:] if history else []

    result = chain.invoke(
        {
            "normalizedQuery": normalizedQuery,
            "history": trimmedHistory,
            "collectionName": collectionName,
            "dataOverview": dataOverview,
            "fieldCatalog": fieldCatalog,
            "refinement": refinement or "None"
        }
    )

    # Validate pipeline before returning
    validatePipeline(result.pipeline)

    return result
