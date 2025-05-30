#!/usr/bin/env python3
"""
query_rag.py

Given a user query, embed it, search the FAISS index, and print
the top-k most relevant chunks (along with their metadata).
Works over any SEC filing type you’ve indexed (10-K, 10-Q, etc).
"""

import os
import json
import logging
import argparse
from dotenv import load_dotenv
import openai
import tiktoken
import faiss
import numpy as np

# ─── Load & validate API Key ────────────────────────────────────────────────────
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    raise RuntimeError(
        "OPENAI_API_KEY not set. Please define it in your environment or .env file."
    )

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

def retrieve(query: str, k: int = DEFAULT_K) -> list[dict]:
    """
    Embed the query, search FAISS for top-k, then load chunk texts.
    Returns a list of dicts: metadata + 'text' + 'score' + form/url/cik.
    """
    # 1) Load index & metadata
    if not os.path.exists(METADATA_FILE) or not os.path.exists(INDEX_FILE):
        raise RuntimeError("Index or metadata file not found. Run your embed step first.")
    with open(METADATA_FILE, "r", encoding="utf-8") as f:
        metadata = json.load(f)
    index = faiss.read_index(INDEX_FILE)

    # 2) Embed query
    qresp = openai.embeddings.create(model=EMBED_MODEL, input=[query])
    q_emb = qresp.data[0].embedding
    arr = np.array([q_emb], dtype="float32")
    faiss.normalize_L2(arr)

    # 3) Search
    distances, ids = index.search(arr, k)
    hits = []
    for rank, vid in enumerate(ids[0]):
        if vid < 0 or vid >= len(metadata):
            continue

        # Copy basic metadata
        entry = metadata[vid].copy()
        entry["score"] = float(distances[0][rank])

        # Load the original JSON to pull form, url, cik, and chunk text
        path = os.path.join(DATA_DIR, entry["ticker"], f"{entry['accession']}.json")
        try:
            with open(path, "r", encoding="utf-8") as f:
                record = json.load(f)

            # Extract the correct chunk
            chunks = chunk_text(record.get("text", ""))
            entry["text"] = chunks[entry["chunk_index"]]

            # Include the real form, url, and cik
            entry["form"] = record.get("form")
            entry["url"]  = record.get("url")
            entry["cik"]  = record.get("cik")

        except FileNotFoundError:
            logging.warning(
                f"Missing file for {entry['ticker']}/{entry['accession']}.json – skipping this hit."
            )
            continue

        hits.append(entry)

    return hits

def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s"
    )
    parser = argparse.ArgumentParser(
        description="RAG retrieval over SEC filing chunks"
    )
    parser.add_argument(
        "--query", "-q", required=True,
        help="Your natural-language question"
    )
    parser.add_argument(
        "--k", "-k", type=int, default=DEFAULT_K,
        help=f"Number of chunks to retrieve (default: {DEFAULT_K})"
    )
    args = parser.parse_args()

    results = retrieve(args.query, args.k)
    if not results:
        print("⚠️  No relevant chunks found.")
        return

    for i, entry in enumerate(results, start=1):
        print(f"\n=== Hit {i} (score {entry['score']:.4f}) ===")
        print(f"Ticker     : {entry['ticker']}")
        print(f"Accession  : {entry['accession']}")
        print(f"Chunk index: {entry['chunk_index']}")
        print(f"Filing date: {entry.get('filing_date', '')}")
        print(f"Form       : {entry.get('form', '')}")
        print(f"CIK        : {entry.get('cik', '')}")
        print(f"URL        : {entry.get('url', '')}\n")
        print(entry["text"])
        print("-" * 80)

if __name__ == "__main__":
    main()