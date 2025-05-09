"""
Data update scheduler module.

This module provides functionality to schedule and run data updates
for companies and years that need to be updated.
"""

import asyncio
import logging
import time
from typing import List, Dict, Any, Optional, Set, Tuple
from sqlalchemy.orm import Session

import sys
import os

# Add app directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.core.config import settings
from data_updater.diff_checker import get_update_candidates, UpdateCandidate
from data_updater.update_job import update_company_data

# Configure logging
logger = logging.getLogger(__name__)


async def process_update_candidates(
    db: Session, 
    candidates: List[UpdateCandidate]
) -> Dict[str, Any]:
    """
    Process a list of update candidates.
    
    Parameters:
    - db: Database session
    - candidates: List of UpdateCandidate objects
    
    Returns:
    - Statistics about the update process
    """
    # Organize candidates by ticker
    ticker_years: Dict[str, Set[int]] = {}
    
    for candidate in candidates:
        if candidate.ticker not in ticker_years:
            ticker_years[candidate.ticker] = set()
        
        ticker_years[candidate.ticker].add(candidate.year)
    
    # Process each ticker
    company_stats = {}
    
    for ticker, years in ticker_years.items():
        # Sort years
        sorted_years = sorted(list(years))
        
        # Get start and end years
        if sorted_years:
            start_year = sorted_years[0]
            end_year = sorted_years[-1]
            
            # Update company data for the year range
            stats = await update_company_data(db, ticker, start_year, end_year)
            company_stats[ticker] = stats
    
    # Calculate total statistics
    if company_stats:
        total_stats = {
            "companies_processed": len(company_stats),
            "filings_processed": sum(stats["filings_processed"] for stats in company_stats.values()),
            "documents_processed": sum(stats["documents_processed"] for stats in company_stats.values()),
            "chunks_created": sum(stats["chunks_created"] for stats in company_stats.values()),
            "chunks_stored": sum(stats["chunks_stored"] for stats in company_stats.values()),
            "errors": sum(stats["errors"] for stats in company_stats.values())
        }
    else:
        total_stats = {
            "companies_processed": 0,
            "filings_processed": 0,
            "documents_processed": 0,
            "chunks_created": 0,
            "chunks_stored": 0,
            "errors": 0
        }
    
    return {
        "total": total_stats,
        "companies": company_stats
    }


async def on_launch_update(db: Session, csv_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Perform an update check and processing on application launch.
    
    Parameters:
    - db: Database session
    - csv_path: Path to the CSV file (defaults to config)
    
    Returns:
    - Statistics about the update process
    """
    logger.info("Performing on-launch update check")
    
    try:
        # Get update candidates
        candidates = get_update_candidates(db, csv_path)
        
        if not candidates:
            logger.info("No updates needed")
            return {
                "total": {
                    "companies_processed": 0,
                    "filings_processed": 0,
                    "documents_processed": 0,
                    "chunks_created": 0,
                    "chunks_stored": 0,
                    "errors": 0
                },
                "companies": {}
            }
        
        # Process update candidates
        return await process_update_candidates(db, candidates)
    
    except Exception as e:
        logger.error(f"Error in on-launch update: {str(e)}")
        return {
            "error": str(e)
        }


async def run_scheduled_update(db: Session, csv_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Run a scheduled update check and processing.
    
    Parameters:
    - db: Database session
    - csv_path: Path to the CSV file (defaults to config)
    
    Returns:
    - Statistics about the update process
    """
    logger.info("Running scheduled update")
    
    try:
        # Get update candidates
        candidates = get_update_candidates(db, csv_path)
        
        if not candidates:
            logger.info("No updates needed")
            return {
                "total": {
                    "companies_processed": 0,
                    "filings_processed": 0,
                    "documents_processed": 0,
                    "chunks_created": 0,
                    "chunks_stored": 0,
                    "errors": 0
                },
                "companies": {}
            }
        
        # Process update candidates
        return await process_update_candidates(db, candidates)
    
    except Exception as e:
        logger.error(f"Error in scheduled update: {str(e)}")
        return {
            "error": str(e)
        }