from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import chat, companies
from .core.config import settings

app = FastAPI(
    title="S&P 500 10-K RAG Chatbot API",
    description="A RAG-based chatbot for querying S&P 500 companies' 10-K filings",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat.router, prefix="/api/v1", tags=["chat"])
app.include_router(companies.router, prefix="/api/v1", tags=["companies"])


@app.get("/")
async def root():
    return {
        "message": "S&P 500 10-K RAG Chatbot API",
        "mode": settings.APP_MODE,
        "embedding_provider": settings.EMBEDDING_PROVIDER,
        "embedding_model": settings.EMBEDDING_MODEL,
        "chat_provider": settings.CHAT_PROVIDER,
        "chat_model": settings.CHAT_MODEL
    }


@app.get("/health")
async def health_check():
    return {"status": "ok"}
