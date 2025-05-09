#!/usr/bin/env python
"""
Scheduled update script for AInalyst.

This script is designed to be run as a cron job to periodically update
company data from SEC filings.

Example cron entry (daily at 03:00 UTC):
0 3 * * * /path/to/python /path/to/run_scheduled_update.py

You can also pass a custom CSV path:
0 3 * * * /path/to/python /path/to/run_scheduled_update.py --csv /path/to/companies.csv
"""

import os
import sys
import logging
import asyncio
import argparse
from dotenv import load_dotenv

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import SessionLocal
from app.core.config import settings
from app.data_updater.scheduler import run_scheduled_update

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

async def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Run scheduled update for AInalyst")
    parser.add_argument("--csv", type=str, help="Path to the companies CSV file")
    args = parser.parse_args()
    
    # Get CSV path
    csv_path = args.csv or settings.COMPANIES_CSV_PATH
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Run scheduled update
        logger.info(f"Starting scheduled update from {csv_path}")
        stats = await run_scheduled_update(db, csv_path)
        
        # Log results
        if "error" in stats:
            logger.error(f"Scheduled update failed: {stats['error']}")
            sys.exit(1)
        else:
            logger.info(f"Scheduled update completed successfully: {stats['total']}")
    
    except Exception as e:
        logger.error(f"Error in scheduled update: {str(e)}")
        sys.exit(1)
    
    finally:
        # Close database session
        db.close()

if __name__ == "__main__":
    asyncio.run(main())