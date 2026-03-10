from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes.chat import router as chatRouter
from app.api.routes.test import router as testRouter


def createApp() -> FastAPI:
    app = FastAPI(title="Procurement AI Assistant API")

    # Enable CORS for local development (HTML file -> API)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, specify exact origins
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(chatRouter, prefix="/api")
    app.include_router(testRouter, prefix="/api")

    return app


app = createApp()
