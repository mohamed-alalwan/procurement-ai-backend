from langchain_openai import ChatOpenAI
from app.core.config import settings


def getChatModel() -> ChatOpenAI:
    # Important: temperature 0 for deterministic query + summaries.
    
    model = ChatOpenAI(
        model=settings.openaiModel,
        temperature=0,
        api_key=settings.openaiApiKey,  # exact name matters
        
    )

    return model
