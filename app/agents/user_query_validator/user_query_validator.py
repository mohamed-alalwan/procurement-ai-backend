from typing import List, Dict, Any
from pathlib import Path

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

from .schemas import ValidatorOutput
from app.core.llm import getChatModel
from app.utils.prompt_loader import loadPrompt
from app.utils.data_overview import loadDataOverview
from app.utils.field_catalog import loadFieldCatalog


PROMPTS_DIR = Path(__file__).parent


def runUserQueryValidator(message: str, history: List[Dict[str, Any]]) -> ValidatorOutput:
    systemPrompt = loadPrompt(PROMPTS_DIR, "validator_system.txt")

    userPrompt = loadPrompt(PROMPTS_DIR, "validator_user.txt")

    dataOverview = loadDataOverview()
    fieldCatalog = loadFieldCatalog()

    parser = PydanticOutputParser(pydantic_object=ValidatorOutput)

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", systemPrompt + "\n\n{format_instructions}"),
            ("human", userPrompt),
        ]
    )

    model = getChatModel()

    chain = prompt.partial(format_instructions=parser.get_format_instructions()) | model | parser

    # Important: keep history small, don't send huge context.
    
    trimmedHistory = history[-5:] if history else []

    result = chain.invoke(
        {
            "message": message,
            "history": trimmedHistory,
            "dataOverview": dataOverview,
            "fieldCatalog": fieldCatalog,
        }
    )

    return result
