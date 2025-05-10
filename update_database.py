#!/usr/bin/env python3
"""
AInalyst Database Update Workflow

This script orchestrates the entire process of:
1. Downloading SEC filings using the Data_import/download_filings.py script
2. Processing those JSON files and generating embeddings
3. Storing the embeddings in the database

Run this script manually whenever you want to update the database.
"""

import os
import sys
import argparse
import subprocess
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(f"update_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("AInalyst-Updater")

def run_command(cmd, desc=None, check=True, shell=False):
    """Run a command and log its output."""
    if desc:
        logger.info(f"STEP: {desc}")
    
    logger.info(f"Running: {' '.join(cmd) if not shell else cmd}")
    
    try:
        if shell:
            result = subprocess.run(cmd, shell=True, check=check, text=True, capture_output=True)
        else:
            result = subprocess.run(cmd, check=check, text=True, capture_output=True)
        
        logger.info(f"Command completed with return code: {result.returncode}")
        
        if result.stdout:
            logger.info(f"Output:\n{result.stdout}")
        
        return result
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed with return code: {e.returncode}")
        logger.error(f"Error: {e.stderr}")
        if not check:
            return e
        raise

def main():
    parser = argparse.ArgumentParser(description="Update AInalyst database with SEC filings")
    parser.add_argument("--user-agent", required=True, help="SEC API user agent (your email)")
    parser.add_argument("--csv-file", default="Data_import/companies.csv", 
                      help="CSV file with companies to process")
    parser.add_argument("--output-dir", default="Data_import/data", 
                      help="Directory to store downloaded filings")
    parser.add_argument("--batch-size", type=int, default=10, 
                      help="Batch size for embedding generation")
    parser.add_argument("--force", action="store_true", 
                      help="Force reprocessing of already processed files")
    args = parser.parse_args()
    
    # Get the project root directory
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    # Step 1: Download filings using Data_import/download_filings.py
    logger.info("=== STEP 1: Downloading SEC filings ===")
    download_cmd = [
        sys.executable,
        os.path.join(project_root, "Data_import", "download_filings.py"),
        args.csv_file,
        "--user-agent", args.user_agent,
        "--output-dir", args.output_dir
    ]
    
    if args.force:
        download_cmd.append("--force")
    
    run_command(download_cmd, desc="Downloading SEC filings")
    
    # Step 2: Process JSON files and create embeddings
    logger.info("=== STEP 2: Processing JSON files and creating embeddings ===")
    process_cmd = [
        sys.executable,
        os.path.join(project_root, "backend", "data_updater", "process_json_filings.py"),
        "--data-dir", args.output_dir,
        "--batch-size", str(args.batch_size)
    ]
    
    if args.force:
        process_cmd.append("--force")
    
    run_command(process_cmd, desc="Processing JSON files and creating embeddings")
    
    logger.info("=== COMPLETED: Database update process finished ===")

if __name__ == "__main__":
    main()