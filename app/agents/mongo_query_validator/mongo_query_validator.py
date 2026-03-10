from typing import List, Dict, Any
from pathlib import Path
import json

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

from .schemas import MongoQueryValidatorOutput
from app.core.llm import getChatModel
from app.utils.prompt_loader import loadPrompt
from app.utils.field_catalog import loadFieldCatalog
from app.utils.data_overview import loadDataOverview


PROMPTS_DIR = Path(__file__).parent


def runMongoQueryValidator(
    userMessage: str,
    normalizedQuery: str,
    pipeline: List[Dict[str, Any]],
    results: List[Dict[str, Any]],
    history: List[Dict[str, Any]],
) -> MongoQueryValidatorOutput:
    prompt = loadPrompt(PROMPTS_DIR, "prompt.txt")

    dataOverview = loadDataOverview()
    fieldCatalog = loadFieldCatalog()

    parser = PydanticOutputParser(pydantic_object=MongoQueryValidatorOutput)

    promptTemplate = ChatPromptTemplate.from_messages(
        [
            ("system", prompt + "\n\n{format_instructions}"),
        ]
    )

    model = getChatModel()

    chain = promptTemplate.partial(format_instructions=parser.get_format_instructions()) | model | parser

    # Limit results sent to LLM to avoid token overflow
    limitedResults = results[:50] if len(results) > 50 else results
    trimmedHistory = history[-5:] if history else []

    result = chain.invoke(
        {
            "userMessage": userMessage,
            "normalizedQuery": normalizedQuery,
            "history": trimmedHistory,
            "pipeline": json.dumps(pipeline, indent=2),
            "results": json.dumps(limitedResults, indent=2, default=str),
            "resultCount": len(results),
            "dataOverview": dataOverview,
            "fieldCatalog": fieldCatalog,
        }
    )

    return result
