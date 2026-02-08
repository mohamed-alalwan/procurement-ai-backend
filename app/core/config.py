from pydantic import BaseModel
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings(BaseModel):
    # OpenAI
    
    openaiApiKey: str = os.getenv("OPENAI_API_KEY", "")
    
    openaiModel: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # MongoDB
    
    mongodbUri: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    
    mongodbDb: str = os.getenv("MONGODB_DB", "procurement")
    
    mongodbCollection: str = os.getenv("MONGODB_COLLECTION", "purchases")

    # App
    
    appEnv: str = os.getenv("APP_ENV", "local")


settings = Settings()
