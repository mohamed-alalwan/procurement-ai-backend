import json
from typing import Any, Dict, List
from pathlib import Path

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

from .schemas import SummarizerOutput
from app.core.llm import getChatModel
from app.utils.prompt_loader import loadPrompt
from app.utils.data_overview import loadDataOverview
from app.utils.field_catalog import loadFieldCatalog


PROMPTS_DIR = Path(__file__).parent


def runResultSummarizer(question: str, results: List[Dict[str, Any]], history: List[Dict[str, Any]]) -> SummarizerOutput:
    systemPrompt = loadPrompt(PROMPTS_DIR, "summarizer_system.txt")

    userPrompt = loadPrompt(PROMPTS_DIR, "summarizer_user.txt")

    dataOverview = loadDataOverview()
    fieldCatalog = loadFieldCatalog()

    parser = PydanticOutputParser(pydantic_object=SummarizerOutput)

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", systemPrompt + "\n\n{format_instructions}"),
            ("human", userPrompt),
        ]
    )

    model = getChatModel()

    chain = prompt.partial(format_instructions=parser.get_format_instructions()) | model | parser

    # Important: stringify results to keep prompt stable.
    
    resultsJson = json.dumps(results, default=str, ensure_ascii=False)

    # Important: keep history small.
    trimmedHistory = history[-5:] if history else []

    result = chain.invoke(
        {
            "question": question,
            "results": resultsJson,
            "dataOverview": dataOverview,
            "fieldCatalog": fieldCatalog,
            "history": trimmedHistory,
        }
    )

    return result
