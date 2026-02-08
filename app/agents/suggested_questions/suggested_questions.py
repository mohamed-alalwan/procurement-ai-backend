from pathlib import Path
from typing import Any, Dict, List

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

from .schemas import SuggestionsOutput
from app.core.llm import getChatModel
from app.utils.prompt_loader import loadPrompt
from app.utils.data_overview import loadDataOverview
from app.utils.field_catalog import loadFieldCatalog


PROMPTS_DIR = Path(__file__).parent


def runSuggestedQuestions(question: str, answer: str, history: List[Dict[str, Any]]) -> SuggestionsOutput:
    systemPrompt = loadPrompt(PROMPTS_DIR, "suggestions_system.txt")

    userPrompt = loadPrompt(PROMPTS_DIR, "suggestions_user.txt")

    dataOverview = loadDataOverview()
    fieldCatalog = loadFieldCatalog()

    parser = PydanticOutputParser(pydantic_object=SuggestionsOutput)

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", systemPrompt + "\n\n{format_instructions}"),
            ("human", userPrompt),
        ]
    )

    model = getChatModel()

    chain = prompt.partial(format_instructions=parser.get_format_instructions()) | model | parser

    # Important: keep history small.
    trimmedHistory = history[-5:] if history else []

    result = chain.invoke(
        {
            "question": question,
            "answer": answer,
            "history": trimmedHistory,
            "dataOverview": dataOverview,
            "fieldCatalog": fieldCatalog,
        }
    )

    # Important: enforce exactly 3 questions in case the model misbehaves.
    
    if len(result.suggestedQuestions) > 3:
        result.suggestedQuestions = result.suggestedQuestions[:3]

    if len(result.suggestedQuestions) < 3:
        # Pad safely with generic but relevant questions.
        
        while len(result.suggestedQuestions) < 3:
            result.suggestedQuestions.append("Which vendor had the highest total spend in this period?")

    return result
