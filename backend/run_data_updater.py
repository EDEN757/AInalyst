#!/usr/bin/env python3
"""
Script to run the data updater from the Docker container
"""
import os
import sys
import argparse
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
    parser = argparse.ArgumentParser(description="Run the SEC filings update job")
    parser.add_argument('--mode', choices=['CSV_ONLY'], default='CSV_ONLY',
                        help='Mode to run the job in: only CSV_ONLY is supported now')
    parser.add_argument('--skip-fetch', action='store_true', help='Skip fetching new data')
    parser.add_argument('--skip-process', action='store_true', help='Skip processing filings')
    parser.add_argument('--skip-embeddings', action='store_true', help='Skip creating embeddings')

    args = parser.parse_args()

    logger.info("Starting update job with CSV import only")
    
    try:
        result = run_update_job(
            mode=args.mode,
            skip_fetch=args.skip_fetch,
            skip_process=args.skip_process,
            skip_embeddings=args.skip_embeddings
        )
        
        logger.info(f"Update job completed with result: {result}")
    except Exception as e:
        logger.error(f"Error running update job: {e}")
        sys.exit(1)