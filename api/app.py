#!/usr/bin/env python3
# api/app.py

import os
import json
import logging
import re
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
# Custom CORS origin checker that handles Vercel deployment URLs
def is_origin_allowed(origin: str) -> bool:
    if not origin:
        return False
    
    # Always allow localhost for development
    if origin.startswith("http://localhost") or origin.startswith("http://127.0.0.1"):
        return True
    
    # Get configured origins
    configured_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    configured_origins = [o.strip().rstrip('/') for o in configured_origins if o.strip()]
    
    # Check exact matches (with and without trailing slash)
    origin_clean = origin.rstrip('/')
    for configured in configured_origins:
        if origin_clean == configured or origin_clean == configured + '/':
            return True
    
    # Check Vercel patterns: allow any deployment URL for allowed Vercel apps
    for configured in configured_origins:
        if "vercel.app" in configured:
            # Extract app name from configured origin like "https://a-inalyst.vercel.app"
            app_name = configured.split('.')[0].split('//')[-1]
            # Check if origin matches pattern: https://a-inalyst-*.vercel.app
            vercel_pattern = f"https://{app_name}.*\.vercel\.app"
            if re.match(vercel_pattern, origin):
                return True
    
    return False

# Use wildcard for CORS middleware but implement custom checking
all_origins = ["*"]
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
    origin_allowed = is_origin_allowed(origin) if origin != "No origin" else False
    logger.info(f"Request: {request.method} {request.url.path} from origin: {origin}")
    logger.info(f"Origin allowed: {origin_allowed}")
    
    # Block requests from disallowed origins
    if request.method == "OPTIONS" and origin != "No origin" and not origin_allowed:
        logger.warning(f"Blocked CORS request from disallowed origin: {origin}")
        return Response(status_code=403, content="CORS: Origin not allowed")
    
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
async def ask_options(request: Request):
    origin = request.headers.get("origin", "")
    
    if is_origin_allowed(origin):
        return Response(
            status_code=200,
            headers={
                "Access-Control-Allow-Origin": origin,
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization, Origin, Accept",
            }
        )
    else:
        logger.warning(f"OPTIONS request denied for origin: {origin}")
        return Response(status_code=403, content="CORS: Origin not allowed")

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