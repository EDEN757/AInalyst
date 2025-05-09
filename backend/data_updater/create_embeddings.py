import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
import asyncio
import time
import json
import os
import sys
from tqdm import tqdm
from sqlalchemy.exc import IntegrityError

# Add app directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.services.llm_clients import create_embedding_sync, create_embeddings_batch as llm_create_embeddings_batch
from app.db.crud import (
    check_text_hash_exists,
    create_filing_metadata,
    create_document_vector,
    upsert_document_with_embedding
)
from app.models.database_models import DocumentChunk
from app.core.config import settings

# Configure logging
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(settings.LOG_LEVEL)

async def create_embedding_for_chunk(chunk: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create an embedding for a document chunk.

    Parameters:
    - chunk: The document chunk to embed

    Returns:
    - The document chunk with embedding
    """
    try:
        # Create embedding
        embedding = await create_embedding_sync(chunk["chunk_text"], settings.DEFAULT_EMBEDDING_MODEL)

        # Add embedding to chunk
        chunk["embedding"] = embedding

        return chunk
    except Exception as e:
        logger.error(f"Error creating embedding for chunk {chunk.get('id')}: {str(e)}")
        # Add an empty embedding
        chunk["embedding"] = [0.0] * settings.EMBEDDING_DIMENSION
        return chunk

async def create_embeddings_batch_async(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Create embeddings for a batch of document chunks asynchronously.

    Parameters:
    - chunks: List of document chunks to embed

    Returns:
    - List of document chunks with embeddings
    """
    # Create embeddings for all chunks in parallel
    tasks = [create_embedding_for_chunk(chunk) for chunk in chunks]
    chunks_with_embeddings = await asyncio.gather(*tasks)

    return chunks_with_embeddings

async def create_embeddings_batch(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Create embeddings for a batch of document chunks.
    This is the function called from update_job.py.

    Parameters:
    - chunks: List of document chunks to embed

    Returns:
    - List of document chunks with embeddings
    """
    # Extract texts for batched embedding
    texts = [chunk["chunk_text"] for chunk in chunks]

    # Create embeddings in batch (using synchronous function without await)
    embeddings = llm_create_embeddings_batch(
        texts=texts,
        model=settings.DEFAULT_EMBEDDING_MODEL
    )

    # Add embeddings to chunks
    chunks_with_embeddings = []
    for i, chunk in enumerate(chunks):
        try:
            chunk_copy = chunk.copy()
            chunk_copy["embedding"] = embeddings[i]
            chunk_copy["embedding_model"] = settings.DEFAULT_EMBEDDING_MODEL
            chunks_with_embeddings.append(chunk_copy)
        except Exception as e:
            logger.error(f"Error adding embedding to chunk {i}: {str(e)}")

    return chunks_with_embeddings

def embed_document_chunks(chunks: List[Dict[str, Any]], batch_size: int = 32) -> List[Dict[str, Any]]:
    """
    Create embeddings for document chunks using batching.
    
    Parameters:
    - chunks: List of document chunks to embed
    - batch_size: Number of chunks to embed in each batch
    
    Returns:
    - List of document chunks with embeddings
    """
    if not chunks:
        logger.warning("No chunks to embed")
        return []
    
    # Extract texts for batched embedding
    texts = [chunk["chunk_text"] for chunk in chunks]
    
    # Log embedding process start
    logger.info(f"Creating embeddings for {len(texts)} chunks using {settings.DEFAULT_EMBEDDING_MODEL}")
    
    # Use batched embedding creation
    embeddings = llm_create_embeddings_batch(
        texts=texts,
        model=settings.DEFAULT_EMBEDDING_MODEL,
        batch_size=batch_size
    )
    
    # Add embeddings to chunks
    chunks_with_embeddings = []
    for i, chunk in enumerate(chunks):
        try:
            chunk_copy = chunk.copy()
            chunk_copy["embedding"] = embeddings[i]
            chunk_copy["embedding_model"] = settings.DEFAULT_EMBEDDING_MODEL
            chunks_with_embeddings.append(chunk_copy)
        except Exception as e:
            logger.error(f"Error adding embedding to chunk {i}: {str(e)}")
    
    logger.info(f"Created embeddings for {len(chunks_with_embeddings)} chunks")
    
    return chunks_with_embeddings

def store_chunk_text(db: Session, doc_id: str, chunk_text: str, chunk_number: Optional[int] = None, total_chunks: Optional[int] = None) -> DocumentChunk:
    """
    Store the text content of a document chunk.
    
    Parameters:
    - db: Database session
    - doc_id: Unique document ID
    - chunk_text: Text content of the chunk
    - chunk_number: Number of this chunk in the document
    - total_chunks: Total number of chunks in the document
    
    Returns:
    - Created DocumentChunk object
    """
    try:
        # Check if chunk already exists
        existing = db.query(DocumentChunk).filter(DocumentChunk.doc_id == doc_id).first()
        if existing:
            return existing
        
        # Create new chunk
        doc_chunk = DocumentChunk(
            doc_id=doc_id,
            chunk_text=chunk_text,
            chunk_number=chunk_number,
            total_chunks=total_chunks
        )
        db.add(doc_chunk)
        db.flush()  # Flush but don't commit yet (for transaction support)
        
        return doc_chunk
    
    except IntegrityError as e:
        db.rollback()
        # Handle unique constraint violation
        if "duplicate key value violates unique constraint" in str(e):
            # Try to get the existing chunk
            existing = db.query(DocumentChunk).filter(DocumentChunk.doc_id == doc_id).first()
            if existing:
                return existing
        
        # Re-raise exception if it's not a duplicate key error or if we can't get the existing chunk
        raise

def store_embeddings(db: Session, chunks_with_embeddings: List[Dict[str, Any]]) -> int:
    """
    Store document chunks and their embeddings in the database.
    
    Parameters:
    - db: Database session
    - chunks_with_embeddings: List of document chunks with embeddings
    
    Returns:
    - Number of chunks stored
    """
    stored_count = 0
    skipped_count = 0
    error_count = 0
    
    # Process each chunk with progress bar
    for chunk in tqdm(chunks_with_embeddings, desc="Storing embeddings", unit="chunk"):
        try:
            # Check if the chunk already exists
            if check_text_hash_exists(db, chunk["text_hash"]):
                skipped_count += 1
                continue
            
            # Begin transaction
            doc_id = chunk["id"]
            
            # Store metadata and vector in a single transaction
            upsert_document_with_embedding(
                db=db,
                doc_id=doc_id,
                ticker=chunk["ticker"],
                year=chunk["year"],
                document_type=chunk["document_type"],
                filing_date=chunk["filing_date"],
                section_name=chunk["section_name"],
                source_url=chunk["source_url"],
                text_hash=chunk["text_hash"],
                embedding=chunk["embedding"],
                page_number=chunk.get("page_number"),
                embedding_model=chunk.get("embedding_model", settings.DEFAULT_EMBEDDING_MODEL),
                commit=False  # Don't commit yet
            )
            
            # Store chunk text
            store_chunk_text(
                db=db,
                doc_id=doc_id,
                chunk_text=chunk["chunk_text"],
                chunk_number=chunk.get("chunk_number", 1),
                total_chunks=chunk.get("total_chunks", 1)
            )
            
            # Commit the transaction
            db.commit()
            
            stored_count += 1
        
        except Exception as e:
            db.rollback()
            error_count += 1
            logger.error(f"Error storing chunk {chunk.get('id')}: {str(e)}")
    
    logger.info(f"Stored {stored_count} chunks, skipped {skipped_count} existing chunks, {error_count} errors")
    
    return stored_count

def save_embeddings_cache(chunks_with_embeddings: List[Dict[str, Any]], cache_dir: str = "cache") -> str:
    """
    Save chunks with embeddings to a cache file.
    
    Parameters:
    - chunks_with_embeddings: List of document chunks with embeddings
    - cache_dir: Directory to save cache files
    
    Returns:
    - Path to the cache file
    """
    # Create cache directory if it doesn't exist
    os.makedirs(cache_dir, exist_ok=True)
    
    # Create cache file path with timestamp
    timestamp = int(time.time())
    cache_file = os.path.join(cache_dir, f"embeddings_cache_{timestamp}.json")
    
    # Save to cache file
    with open(cache_file, "w") as f:
        json.dump(chunks_with_embeddings, f)
    
    logger.info(f"Saved {len(chunks_with_embeddings)} chunks with embeddings to cache file: {cache_file}")
    
    return cache_file

def load_embeddings_cache(cache_file: str) -> List[Dict[str, Any]]:
    """
    Load chunks with embeddings from a cache file.
    
    Parameters:
    - cache_file: Path to the cache file
    
    Returns:
    - List of document chunks with embeddings
    """
    if not os.path.exists(cache_file):
        logger.error(f"Cache file not found: {cache_file}")
        return []
    
    # Load from cache file
    with open(cache_file, "r") as f:
        chunks_with_embeddings = json.load(f)
    
    logger.info(f"Loaded {len(chunks_with_embeddings)} chunks with embeddings from cache file: {cache_file}")
    
    return chunks_with_embeddings

def process_and_store_chunks(db: Session, chunks: List[Dict[str, Any]], batch_size: int = 32, use_cache: bool = True) -> int:
    """
    Process and store document chunks with embeddings.
    
    Parameters:
    - db: Database session
    - chunks: List of document chunks to process
    - batch_size: Number of chunks to embed in each batch
    - use_cache: Whether to use cache files
    
    Returns:
    - Number of chunks stored
    """
    if not chunks:
        logger.warning("No chunks to process")
        return 0
    
    # Create embeddings
    chunks_with_embeddings = embed_document_chunks(chunks, batch_size)
    
    # Save to cache if enabled
    if use_cache:
        save_embeddings_cache(chunks_with_embeddings)
    
    # Store in database
    stored_count = store_embeddings(db, chunks_with_embeddings)
    
    return stored_count