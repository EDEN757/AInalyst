#!/usr/bin/env python3
"""
Incremental SEC EDGAR 10-K Chunk, FAISS Embedder & Retriever

- One-time or incremental embed build.
- Append-only: skips already-indexed chunks.
- Provides functions to retrieve and assemble context for RAG queries.
"""
import os
import json
import logging
from dotenv import load_dotenv
import openai
import tiktoken
import faiss
import numpy as np

# Load API key
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# Configuration
EMBED_MODEL    = "text-embedding-3-small"
CHUNK_SIZE     = 1000
CHUNK_OVERLAP  = 200
DATA_DIR       = "data"
INDEX_FILE     = "faiss_index.idx"
METADATA_FILE  = "faiss_metadata.json"
BATCH_SIZE     = 100
K_RETRIEVE     = 5

# Tokenizer
tokenizer = tiktoken.get_encoding("cl100k_base")


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP):
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


def embed_texts(texts: list[str], model: str = EMBED_MODEL) -> list[list[float]]:
    resp = openai.embeddings.create(input=texts, model=model)
    return [d.embedding for d in resp.data]


def build_empty_faiss(dims: int) -> faiss.IndexIDMap:
    return faiss.IndexIDMap(faiss.IndexFlatIP(dims))


def initialize_index():
    """Load or create FAISS index and metadata."""
    if os.path.exists(METADATA_FILE) and os.path.exists(INDEX_FILE):
        logging.info("Loading existing metadata and index...")
        metadata = json.load(open(METADATA_FILE))
        existing_keys = {(m['ticker'], m['accession'], m['chunk_index']) for m in metadata}
        next_id = max(m['id'] for m in metadata) + 1
        index = faiss.read_index(INDEX_FILE)
    else:
        logging.info("No existing index found. Creating fresh.")
        metadata = []
        existing_keys = set()
        next_id = 0
        index = None
    return index, metadata, existing_keys, next_id


def save_index_metadata(index, metadata):
    faiss.write_index(index, INDEX_FILE)
    logging.info(f"FAISS index saved to {INDEX_FILE}.")
    with open(METADATA_FILE, 'w') as f:
        json.dump(metadata, f, indent=2)
    logging.info(f"Metadata saved to {METADATA_FILE}.")


def update_embeddings():
    """Main driver: find new chunks, embed, and append to FAISS."""
    index, metadata, existing_keys, next_id = initialize_index()

    new_chunks = []
    new_entries = []

    for ticker in os.listdir(DATA_DIR):
        tdir = os.path.join(DATA_DIR, ticker)
        if not os.path.isdir(tdir):
            continue
        for fname in os.listdir(tdir):
            if not fname.endswith('.json'):
                continue
            record = json.load(open(os.path.join(tdir, fname)))
            accession = record['accession']
            filing_date = record.get('filing_date', '')
            full_text = record.get('text', '')

            chunks = chunk_text(full_text)
            for idx, chunk in enumerate(chunks):
                key = (ticker, accession, idx)
                if key in existing_keys:
                    continue
                new_chunks.append(chunk)
                new_entries.append({
                    'id': next_id,
                    'ticker': ticker,
                    'accession': accession,
                    'chunk_index': idx,
                    'filing_date': filing_date
                })
                next_id += 1

    if not new_chunks:
        logging.info("No new chunks to embed. Exiting.")
        return

    logging.info(f"Embedding {len(new_chunks)} new chunks...")
    new_embeddings = []
    for i in range(0, len(new_chunks), BATCH_SIZE):
        batch = new_chunks[i:i+BATCH_SIZE]
        logging.info(f"  Batch {i//BATCH_SIZE + 1}: {len(batch)} chunks")
        new_embeddings.extend(embed_texts(batch))

    # Build or extend index
    dims = len(new_embeddings[0])
    if index is None:
        index = build_empty_faiss(dims)
    arr = np.array(new_embeddings, dtype='float32')
    faiss.normalize_L2(arr)
    ids = np.array([e['id'] for e in new_entries], dtype='int64')
    index.add_with_ids(arr, ids)
    logging.info(f"Appended {len(new_entries)} vectors to index.")

    metadata.extend(new_entries)
    save_index_metadata(index, metadata)


def load_chunk_text(entry: dict) -> str:
    """Given a metadata entry, re-load and return the exact chunk text."""
    path = os.path.join(DATA_DIR, entry['ticker'], f"{entry['accession']}.json")
    record = json.load(open(path))
    chunks = chunk_text(record['text'])
    return chunks[entry['chunk_index']]


def retrieve(query: str, k: int = K_RETRIEVE) -> list[dict]:
    """Return top-k metadata entries for a query."""
    # Ensure index & metadata are loaded
    metadata = json.load(open(METADATA_FILE))
    index = faiss.read_index(INDEX_FILE)

    # Embed query
    qe_resp = openai.embeddings.create(input=[query], model=EMBED_MODEL)
    q_emb = qe_resp.data[0].embedding
    arr = np.array([q_emb], dtype='float32')
    faiss.normalize_L2(arr)

    # Search
    distances, ids = index.search(arr, k)
    hits = []
    for vid in ids[0]:
        if vid < 0 or vid >= len(metadata):
            continue
        hits.append(metadata[vid])
    return hits


def answer_rag(query: str, k: int = K_RETRIEVE) -> str:
    """Fetch top-k chunks, assemble context, and call the chat model."""
    hits = retrieve(query, k)
    contexts = [load_chunk_text(h) for h in hits]
    context_blob = "\n\n---\n\n".join(contexts)
    messages = [
        {"role": "system", "content": "You are a financial assistant."},
        {"role": "user",   "content": f"Context:\n{context_blob}\n\nQ: {query}"}
    ]
    resp = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=messages)
    return resp.choices[0].message.content


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    update_embeddings()
