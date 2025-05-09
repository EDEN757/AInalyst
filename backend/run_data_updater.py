#!/usr/bin/env python3
"""
Script to run the data updater from the Docker container
"""
import os
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Make sure we're in the right directory
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

# Import the updater
try:
    from data_updater.update_job import run_update_job
    from app.core.config import settings
    
    logger.info("Successfully imported update_job and settings")
except ImportError as e:
    logger.error(f"Import error: {e}")
    sys.exit(1)

if __name__ == "__main__":
    logger.info("Starting data updater job")
    
    try:
        # Run the update job
        result = run_update_job()
        
        if result["status"] == "completed":
            logger.info(f"Job completed successfully in {result['duration_seconds']} seconds")
            
            # Log processing summary
            if "process" in result:
                process_result = result["process"]
                logger.info(f"Processed {process_result.get('filings_processed', 0)} filings with {process_result.get('chunks_created', 0)} chunks")
            
            # Log embedding summary
            if "embeddings" in result:
                embed_result = result["embeddings"]
                logger.info(f"Created {embed_result.get('processed_count', 0)} embeddings with {embed_result.get('error_count', 0)} errors")
        else:
            logger.error(f"Job failed: {result.get('error', 'Unknown error')}")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Error running update job: {e}")
        sys.exit(1)