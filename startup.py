#!/usr/bin/env python3
"""
Startup script for production deployment.
Downloads data and builds embeddings after app starts.
"""

import os
import sys
import subprocess
import logging
import threading
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def download_and_process_data():
    """Download filings and create embeddings in background"""
    try:
        logger.info("Starting data download...")
        
        # Get root directory path
        root_dir = Path(__file__).parent.parent if "api" in str(Path.cwd()) else Path(".")
        
        # Check if data already exists
        data_dir = root_dir / "data"
        if data_dir.exists() and any(data_dir.iterdir()):
            logger.info("Data directory exists, skipping download")
        else:
            logger.info("Downloading filings...")
            subprocess.run(["python", str(root_dir / "download_filings.py")], 
                         cwd=str(root_dir), check=True)
        
        # Check if embeddings exist  
        faiss_index = root_dir / "faiss_index.idx"
        if faiss_index.exists():
            logger.info("FAISS index exists, skipping embedding")
        else:
            logger.info("Creating embeddings...")
            subprocess.run(["python", str(root_dir / "incremental_chunk_embed.py")], 
                         cwd=str(root_dir), check=True)
            
        logger.info("Data processing complete!")
        
    except Exception as e:
        logger.error(f"Data processing failed: {e}")

def start_data_processing():
    """Start data processing in background thread"""
    thread = threading.Thread(target=download_and_process_data, daemon=True)
    thread.start()
    return thread

if __name__ == "__main__":
    start_data_processing()