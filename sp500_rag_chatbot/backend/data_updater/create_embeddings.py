import time
import logging
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from ..db import crud
from ..core.config import settings
from ..services import llm_clients

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Batch sizes for different providers
BATCH_SIZES = {
    "OPENAI": 20,  # OpenAI can handle larger batches
    "GEMINI": 5   # Gemini may have stricter limits
}


def process_embeddings_in_batches(db: Session, batch_size: int = None):
    """Process text chunks in batches to create embeddings.
    
    Args:
        db: Database session
        batch_size: Number of chunks to process in each batch (default: provider-specific)
        
    Returns:
        Tuple of (processed_count, error_count)
    """
    if batch_size is None:
        # Use provider-specific batch size
        batch_size = BATCH_SIZES.get(settings.EMBEDDING_PROVIDER, 10)
    
    processed_count = 0
    error_count = 0
    
    logger.info(f"Starting embedding generation using {settings.EMBEDDING_PROVIDER} - {settings.EMBEDDING_MODEL}")
    logger.info(f"Embedding dimension: {settings.EMBEDDING_DIMENSION}, Batch size: {batch_size}")
    
    # Get unembedded chunks
    while True:
        chunks = crud.get_unembedded_chunks(db, limit=batch_size)
        
        if not chunks:
            logger.info("No more unembedded chunks found. Processing complete.")
            break
        
        logger.info(f"Processing batch of {len(chunks)} chunks")
        
        # Process each chunk in the batch
        for chunk in chunks:
            try:
                # Generate embedding using the configured embedding provider
                embedding = llm_clients.get_embedding(chunk.text_content, settings)
                
                # Update the chunk with its embedding
                crud.update_chunk_embedding(db, chunk.id, embedding)
                
                processed_count += 1
                
                # Add a small delay to avoid rate limits
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error generating embedding for chunk {chunk.id}: {str(e)}")
                error_count += 1
        
        logger.info(f"Completed batch. Processed {processed_count} chunks, {error_count} errors.")
    
    return processed_count, error_count


def create_embeddings(db: Session):
    """Main function to create embeddings for all unembedded chunks.
    
    Args:
        db: Database session
        
    Returns:
        Summary of processing results
    """
    start_time = time.time()
    
    try:
        processed_count, error_count = process_embeddings_in_batches(db)
        duration = time.time() - start_time
        
        return {
            "status": "completed",
            "processed_count": processed_count,
            "error_count": error_count,
            "duration_seconds": round(duration, 2),
            "embedding_provider": settings.EMBEDDING_PROVIDER,
            "embedding_model": settings.EMBEDDING_MODEL
        }
        
    except Exception as e:
        logger.error(f"Error in embedding creation process: {str(e)}")
        
        return {
            "status": "error",
            "error": str(e),
            "duration_seconds": round(time.time() - start_time, 2)
        }
