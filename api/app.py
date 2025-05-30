#!/usr/bin/env python3
# api/app.py

import os
import json
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from dotenv import load_dotenv
import openai
import uvicorn

# ─── Load environment ─────────────────────────────────────────────────────────
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# Read desired chat model from .env (defaults to gpt-3.5-turbo)
CHAT_MODEL = os.getenv("CHAT_MODEL", "gpt-3.5-turbo")

# ─── Bring in your RAG retriever ──────────────────────────────────────────────
from query_rag import retrieve  # returns List[dict] with keys ticker, accession, chunk_index, filing_date, score, text, form, cik, url

# ─── FastAPI setup ──────────────────────────────────────────────────────────
app = FastAPI(
    title="10-K RAG Chatbot API",
    description="Retrieval-Augmented-Generation over SEC 10-K filings",
    version="0.1.0"
)
app.add_middleware(
  CORSMiddleware,
  allow_origins=["http://localhost:3000"],  # your Next.js dev URL
  allow_methods=["POST", "GET", "OPTIONS"],
  allow_headers=["*"],
)
# ─── Request/response schemas ─────────────────────────────────────────────────
class AskRequest(BaseModel):
    query: str
    k: int = 5

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

# ─── The /ask endpoint ───────────────────────────────────────────────────────
@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
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
        model=CHAT_MODEL,
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