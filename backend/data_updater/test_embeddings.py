import os
import sys
import logging
from dotenv import load_dotenv
import json
import argparse
import time
from sqlalchemy.orm import Session

# Add the parent directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Import the modules to test
from app.db.database import SessionLocal
from data_updater.csv_reader import get_companies_for_update
from data_updater.fetch_sec import fetch_filings_for_company, download_filing_contents
from data_updater.process_docs import process_filings, save_chunks_to_json
from data_updater.create_embeddings import process_and_store_chunks, load_embeddings_cache

def main():
    """Test embeddings and storage functionality"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Test embeddings and storage")
    parser.add_argument("--chunks-file", type=str, help="Path to the file with processed chunks")
    parser.add_argument("--cache-file", type=str, help="Path to the cache file with embeddings")
    parser.add_argument("--limit", type=int, default=10, help="Limit the number of chunks to process")
    parser.add_argument("--output", type=str, default="cache/embeddings_test.json", help="Output file for embeddings")
    parser.add_argument("--batch-size", type=int, default=8, help="Batch size for embedding creation")
    parser.add_argument("--store", action="store_true", help="Store embeddings in the database")
    args = parser.parse_args()
    
    try:
        chunks = []
        
        # Determine the source of chunks
        if args.cache_file:
            # Load embeddings from cache file
            logger.info(f"Loading embeddings from cache file: {args.cache_file}")
            chunks_with_embeddings = load_embeddings_cache(args.cache_file)
            
            # Limit if requested
            if args.limit and args.limit > 0 and len(chunks_with_embeddings) > args.limit:
                chunks_with_embeddings = chunks_with_embeddings[:args.limit]
            
            # Store in database if requested
            if args.store:
                db = SessionLocal()
                try:
                    logger.info(f"Storing {len(chunks_with_embeddings)} chunks in the database")
                    from data_updater.create_embeddings import store_embeddings
                    stored_count = store_embeddings(db, chunks_with_embeddings)
                    logger.info(f"Stored {stored_count} chunks in the database")
                finally:
                    db.close()
            
            # We already have embeddings, so we're done
            return 0
        
        elif args.chunks_file:
            # Load chunks from file
            logger.info(f"Loading chunks from file: {args.chunks_file}")
            with open(args.chunks_file, "r") as f:
                chunks = json.load(f)
            
            # Limit if requested
            if args.limit and args.limit > 0 and len(chunks) > args.limit:
                chunks = chunks[:args.limit]
        
        else:
            # We need to generate chunks from SEC filings
            # Check for minimum requirements in test_process_docs.py first
            logger.error("No source file provided. Please provide --chunks-file or --cache-file.")
            return 1
        
        # Process chunks and create embeddings
        if chunks:
            logger.info(f"Processing {len(chunks)} chunks and creating embeddings")
            
            # Create database session if storing
            if args.store:
                db = SessionLocal()
            else:
                db = None
            
            try:
                # Process and store chunks
                if db:
                    # Process and store in database
                    stored_count = process_and_store_chunks(
                        db=db,
                        chunks=chunks,
                        batch_size=args.batch_size,
                        use_cache=True
                    )
                    logger.info(f"Stored {stored_count} chunks in the database")
                else:
                    # Just create embeddings and cache them
                    from data_updater.create_embeddings import embed_document_chunks, save_embeddings_cache
                    chunks_with_embeddings = embed_document_chunks(chunks, args.batch_size)
                    
                    # Save to output file
                    if args.output:
                        cache_file = save_embeddings_cache(chunks_with_embeddings, os.path.dirname(args.output))
                        logger.info(f"Saved embeddings to cache file: {cache_file}")
            
            finally:
                # Close database session if it was created
                if db:
                    db.close()
        
        else:
            logger.warning("No chunks to process")
        
        # Return success
        return 0
    
    except Exception as e:
        # Log error
        logger.error(f"Error testing embeddings: {str(e)}")
        
        # Return failure
        return 1

if __name__ == "__main__":
    start_time = time.time()
    exit_code = main()
    elapsed_time = time.time() - start_time
    logger.info(f"Finished in {elapsed_time:.2f} seconds")
    sys.exit(exit_code)