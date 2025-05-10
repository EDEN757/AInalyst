#!/usr/bin/env python3
"""
query_rag.py

Given a user query, embed it, search the FAISS index, and print
the top-k most relevant 10-K text chunks (along with their metadata).
"""

import os
import json
from dotenv import load_dotenv
import openai
import tiktoken
import faiss
import numpy as np
import argparse

# ─── Load API Key ───────────────────────────────────────────────────────────────
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# ─── Configuration ─────────────────────────────────────────────────────────────
EMBED_MODEL   = "text-embedding-3-small"
DATA_DIR      = "data"
INDEX_FILE    = "faiss_index.idx"
METADATA_FILE = "faiss_metadata.json"
DEFAULT_K     = 5
CHUNK_SIZE    = 1000    # must match your embedder’s config
CHUNK_OVERLAP = 200     # must match your embedder’s config

# ─── Tokenizer ─────────────────────────────────────────────────────────────────
tokenizer = tiktoken.get_encoding("cl100k_base")

def chunk_text(text: str,
               chunk_size: int = CHUNK_SIZE,
               overlap:   int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks (must match your indexer!)."""
    tokens = tokenizer.encode(text)
    chunks = []
    start = 0
    while start < len(tokens):
        end = min(start + chunk_size, len(tokens))
        chunks.append(tokenizer.decode(tokens[start:end]))
        if end == len(tokens):
            break
        start += chunk_size - overlap
    return chunks

def load_chunk_text(entry: dict) -> str:
    """
    Given one metadata entry, re-load its JSON and return the exact chunk text.
    """
    path = os.path.join(DATA_DIR, entry["ticker"], f"{entry['accession']}.json")
    record = json.load(open(path, "r"))
    chunks = chunk_text(record["text"])
    return chunks[entry["chunk_index"]]

def retrieve(query: str, k: int = DEFAULT_K) -> list[dict]:
    """
    Embed the query, search FAISS for top-k, then load chunk texts.
    Returns a list of dicts: metadata + 'text' + 'score'.
    """
    # 1) Load index & metadata
    metadata = json.load(open(METADATA_FILE, "r"))
    index    = faiss.read_index(INDEX_FILE)

    # 2) Embed query (v1+ API)
    qresp = openai.embeddings.create(model=EMBED_MODEL, input=[query])
    q_emb = qresp.data[0].embedding
    arr   = np.array([q_emb], dtype="float32")
    faiss.normalize_L2(arr)

    # 3) Search
    distances, ids = index.search(arr, k)
    hits = []
    for rank, vid in enumerate(ids[0]):
        if vid < 0 or vid >= len(metadata):
            continue
        entry = metadata[vid].copy()
        entry["score"] = float(distances[0][rank])
        entry["text"]  = load_chunk_text(entry)
        hits.append(entry)
    return hits

def main():
    p = argparse.ArgumentParser(description="RAG retrieval over SEC 10-K chunks")
    p.add_argument("--query", "-q", required=True, help="Your natural-language question")
    p.add_argument("--k",      "-k", type=int, default=DEFAULT_K,
                   help="Number of chunks to retrieve (default: 5)")
    args = p.parse_args()

    results = retrieve(args.query, args.k)
    if not results:
        print("⚠️  No relevant chunks found.")
        return

    for i, entry in enumerate(results, start=1):
        print(f"\n=== Hit {i} (score {entry['score']:.4f}) ===")
        print(f"Ticker     : {entry['ticker']}")
        print(f"Accession  : {entry['accession']}")
        print(f"Chunk index: {entry['chunk_index']}")
        print(f"Filing date: {entry['filing_date']}\n")
        print(entry["text"])
        print("-" * 80)

if __name__ == "__main__":
    main()