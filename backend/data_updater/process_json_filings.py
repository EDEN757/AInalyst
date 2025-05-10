"""
Process JSON filings downloaded by download_filings.py and create embeddings

This script:
1. Scans the data directory for JSON filings created by download_filings.py
2. Chunks the text into manageable segments for embeddings
3. Creates embeddings using OpenAI's API
4. Stores the embeddings in a pgvector-enabled PostgreSQL database
"""
import os
import sys
import json
import logging
import argparse
import uuid
import glob
import tiktoken
import hashlib
from datetime import datetime
from tqdm import tqdm
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional, Tuple

# Add app directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.core.config import settings
from app.db.database import SessionLocal
from app.services.llm_clients import create_embedding_sync, create_embeddings_batch
from app.db.crud import upsert_document_with_embedding, store_chunk_text

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Initialize tokenizer for splitting text
tokenizer = tiktoken.get_encoding("cl100k_base")  # OpenAI's encoding used by models like text-embedding-ada-002

def create_text_hash(text: str) -> str:
    """Create a hash of the given text."""
    return hashlib.md5(text.encode()).hexdigest()

def clean_text(text: str) -> str:
    """Clean text for embedding."""
    # Remove excessive whitespace and normalize
    cleaned = ' '.join(text.split())
    return cleaned

def split_text(text: str, max_tokens: int = 1000, overlap: int = 100) -> List[str]:
    """Split text into chunks of specified token size with overlap."""
    # Skip empty text
    if not text or len(text.strip()) == 0:
        return []
    
    # Handle very short text
    if len(text) < 100:
        return [text]
    
    # Tokenize the text
    tokens = tokenizer.encode(text)
    
    # Handle case where the text is shorter than max_tokens
    if len(tokens) <= max_tokens:
        return [text]
    
    # Split into chunks
    chunks = []
    i = 0
    while i < len(tokens):
        # Get chunk of tokens
        chunk_end = min(i + max_tokens, len(tokens))
        chunk = tokens[i:chunk_end]
        
        # Decode chunk back to text
        chunk_text = tokenizer.decode(chunk)
        
        # Add to chunks list
        chunks.append(chunk_text)
        
        # Advance position (with overlap)
        i += max_tokens - overlap
        
        # Ensure we're making progress
        if max_tokens <= overlap:
            i += 1  # Avoid infinite loop
    
    # Ensure we have at least one chunk
    if not chunks:
        chunks = [text]
    
    return chunks

def process_filing_json(json_path: str, max_tokens: int = 1000, overlap: int = 100) -> List[Dict[str, Any]]:
    """Process a single filing JSON and return chunks for embedding."""
    try:
        # Load the JSON file
        with open(json_path, 'r') as f:
            filing = json.load(f)
            
        # Extract key fields
        ticker = filing.get('ticker')
        filing_date_str = filing.get('filing_date')
        form = filing.get('form')
        text = filing.get('text')
        doc_url = filing.get('document_url')
        
        if not ticker or not filing_date_str or not form or not text:
            logger.warning(f"Missing required fields in {json_path}, skipping")
            return []
            
        # Parse filing year from date
        try:
            filing_year = int(filing_date_str.split('-')[0])
        except (ValueError, IndexError):
            logger.warning(f"Invalid filing date {filing_date_str} in {json_path}, skipping")
            return []
            
        # Clean text
        cleaned_text = clean_text(text)
        
        # Split into chunks
        chunks = split_text(cleaned_text, max_tokens=max_tokens, overlap=overlap)
        
        # Create document chunks
        doc_chunks = []
        for i, chunk_text in enumerate(chunks):
            # Skip if chunk is too short
            if len(chunk_text) < 100:
                continue
                
            # Generate a unique document ID
            doc_id = str(uuid.uuid4())
            
            # Create text hash
            text_hash = create_text_hash(chunk_text)
            
            # Add to chunks list
            doc_chunks.append({
                "id": doc_id,
                "ticker": ticker,
                "year": filing_year,
                "document_type": form,
                "filing_date": filing_date_str,
                "section_name": "Full Document",  # Not breaking into sections with this approach
                "source_url": doc_url,
                "chunk_number": i + 1,
                "total_chunks": len(chunks),
                "chunk_text": chunk_text,
                "text_hash": text_hash
            })
            
        logger.info(f"Created {len(doc_chunks)} chunks for {ticker} {filing_year} {form}")
        return doc_chunks
        
    except Exception as e:
        logger.error(f"Error processing {json_path}: {str(e)}")
        return []

def embed_document_chunks(chunks: List[Dict[str, Any]], batch_size: int = 10) -> List[Dict[str, Any]]:
    """Create embeddings for document chunks using batching."""
    if not chunks:
        logger.warning("No chunks to embed")
        return []
    
    # Extract texts for batched embedding
    texts = [chunk["chunk_text"] for chunk in chunks]
    
    logger.info(f"Creating embeddings for {len(texts)} chunks")
    
    # Use batched embedding creation
    embeddings = create_embeddings_batch(
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

def store_embeddings(db: Session, chunks_with_embeddings: List[Dict[str, Any]]) -> int:
    """Store document chunks and their embeddings in the database."""
    stored_count = 0
    skipped_count = 0
    error_count = 0
    
    # Process each chunk with progress bar
    for chunk in tqdm(chunks_with_embeddings, desc="Storing embeddings", unit="chunk"):
        try:
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
    
    logger.info(f"Stored {stored_count} chunks, {error_count} errors")
    
    return stored_count

def process_data_directory(data_dir: str, batch_size: int = 10, force: bool = False) -> int:
    """
    Process all JSON files in the data directory.
    
    Args:
        data_dir: Path to the directory containing company folders with JSON filings
        batch_size: Number of embeddings to create at once
        force: Whether to reprocess JSONs that already have a processed marker file
        
    Returns:
        Total number of chunks processed
    """
    # Get all company directories
    company_dirs = [d for d in os.listdir(data_dir) if os.path.isdir(os.path.join(data_dir, d))]
    
    if not company_dirs:
        logger.warning(f"No company directories found in {data_dir}")
        return 0
    
    logger.info(f"Found {len(company_dirs)} companies in {data_dir}")
    
    total_processed = 0
    
    # Process each company directory
    for company in company_dirs:
        company_dir = os.path.join(data_dir, company)
        json_files = glob.glob(os.path.join(company_dir, "*.json"))
        
        if not json_files:
            logger.info(f"No JSON files found for {company}")
            continue
        
        logger.info(f"Processing {len(json_files)} filings for {company}")
        
        # Process each JSON file
        for json_path in json_files:
            # Check if already processed (unless force is True)
            marker_file = f"{json_path}.processed"
            if os.path.exists(marker_file) and not force:
                logger.info(f"Skipping already processed {json_path}")
                continue
            
            # Process the filing
            chunks = process_filing_json(json_path)
            
            if not chunks:
                logger.warning(f"No chunks created for {json_path}")
                continue
            
            # Create embeddings
            chunks_with_embeddings = embed_document_chunks(chunks, batch_size=batch_size)
            
            if not chunks_with_embeddings:
                logger.warning(f"No embeddings created for {json_path}")
                continue
            
            # Store in database
            db = SessionLocal()
            try:
                num_stored = store_embeddings(db, chunks_with_embeddings)
                
                # Create marker file to indicate this JSON has been processed
                with open(marker_file, 'w') as f:
                    f.write(f"Processed on {datetime.now().isoformat()}, created {num_stored} chunks")
                
                total_processed += num_stored
                
            finally:
                db.close()
    
    return total_processed

def main():
    parser = argparse.ArgumentParser(description="Process JSON filings and create embeddings")
    parser.add_argument("--data-dir", default="../Data_import/data", help="Directory with JSON filings")
    parser.add_argument("--batch-size", type=int, default=10, help="Batch size for embeddings")
    parser.add_argument("--force", action="store_true", help="Reprocess already processed files")
    args = parser.parse_args()
    
    # Process all JSON files in the data directory
    total_processed = process_data_directory(
        data_dir=args.data_dir,
        batch_size=args.batch_size,
        force=args.force
    )
    
    logger.info(f"Total processed chunks: {total_processed}")

if __name__ == "__main__":
    main()