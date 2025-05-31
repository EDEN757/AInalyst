#!/usr/bin/env python3
# api/app.py

import os
import json
import logging
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, HttpUrl
from dotenv import load_dotenv
load_dotenv()
import openai
import uvicorn

# ─── Bring in your RAG retriever ──────────────────────────────────────────────
from query_rag import retrieve  # returns List[dict] with keys ticker, accession, chunk_index, filing_date, score, text, form, cik, url
# Read CORS origins from CORS_ORIGINS (comma-separated), default to localhost
# In production, set CORS_ORIGINS="http://localhost:3000,https://your-vercel-app.vercel.app"
origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
# Clean up whitespace and trailing slashes from origins
origins = [origin.strip().rstrip('/') for origin in origins if origin.strip()]
# Also add versions with trailing slashes to be safe
origins_with_slashes = [origin + '/' for origin in origins]
all_origins = origins + origins_with_slashes
# ─── FastAPI setup ──────────────────────────────────────────────────────────
app = FastAPI(
    title="10-K RAG Chatbot API",
    description="Retrieval-Augmented-Generation over SEC 10-K filings",
    version="0.1.0"
)

# Log CORS configuration for debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info(f"CORS allowed origins: {all_origins}")
app.add_middleware(
  CORSMiddleware,
  allow_origins=all_origins,  # Allow both with and without trailing slashes
  allow_methods=["POST", "GET", "OPTIONS"],
  allow_headers=["Content-Type", "Authorization", "Origin", "Accept"],
  allow_credentials=False,
)

# Add request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    origin = request.headers.get("origin", "No origin")
    logger.info(f"Request: {request.method} {request.url.path} from origin: {origin}")
    logger.info(f"Headers: {dict(request.headers)}")
    response = await call_next(request)
    logger.info(f"Response status: {response.status_code}")
    return response
# ─── Request/response schemas ─────────────────────────────────────────────────
class AskRequest(BaseModel):
    query: str
    k: int = 5
    api_key: str
    chat_model: str

class ContextItem(BaseModel):
    ticker: str
    accession: str
    chunk_index: int
    filing_date: str
    score: float
    text: str
    form: str
    cik: str
    url: HttpUrl

class AskResponse(BaseModel):
    answer: str
    context: list[ContextItem]

# ─── Explicit OPTIONS handler for /ask endpoint ─────────────────────────────
@app.options("/ask")
async def ask_options():
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, Origin, Accept",
        }
    )

# ─── The /ask endpoint ───────────────────────────────────────────────────────
@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    openai.api_key = req.api_key
    # 1) Retrieve top-k chunks
    hits = retrieve(req.query, k=req.k)
    if not hits:
        raise HTTPException(status_code=404, detail="No relevant chunks found.")

    # 2) Build the prompt
    context_blob = "\n\n---\n\n".join(h["text"] for h in hits)
    messages = [
        {"role": "system", "content": "You are a helpful financial assistant, you only answer question regarding finance, your name is AInalyst."},
        {"role": "user",   "content": f"Context:\n{context_blob}\n\nQuestion: {req.query}"}
    ]

    # 3) Call the OpenAI Chat Completion (v1 library)
    chat_resp = openai.chat.completions.create(
        model=req.chat_model,
        messages=messages
    )
    answer = chat_resp.choices[0].message.content

    # 4) Return the answer + context
    return AskResponse(
        answer=answer,
        context=[ContextItem(**h) for h in hits]
    )

# ─── Run with Uvicorn ───────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)