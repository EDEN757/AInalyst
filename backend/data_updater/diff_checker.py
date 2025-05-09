"""
Data diff checker module.

This module compares the companies in a CSV file against the records in the database
to determine which companies and years need to be updated.
"""

import pandas as pd
import logging
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text

import sys
import os

# Add app directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.core.config import settings

# Configure logging
logger = logging.getLogger(__name__)

class UpdateCandidate:
    """Class representing a company-year that needs to be updated."""
    
    def __init__(self, ticker: str, year: int, reason: str):
        """
        Initialize an update candidate.
        
        Parameters:
        - ticker: Company ticker symbol
        - year: Filing year
        - reason: Reason for the update
        """
        self.ticker = ticker
        self.year = year
        self.reason = reason
    
    def __repr__(self):
        return f"UpdateCandidate(ticker={self.ticker}, year={self.year}, reason={self.reason})"


def get_companies_from_csv(csv_path: str = None) -> List[Dict[str, Any]]:
    """
    Read companies from CSV file.
    
    Parameters:
    - csv_path: Path to the CSV file (defaults to config)
    
    Returns:
    - List of company dictionaries
    """
    # Use default path if not specified
    csv_path = csv_path or settings.COMPANIES_CSV_PATH
    
    try:
        # Read CSV file
        df = pd.read_csv(csv_path)
        
        # Validate columns
        required_columns = ["ticker", "start_year", "end_year"]
        for column in required_columns:
            if column not in df.columns:
                raise ValueError(f"CSV file must contain column: {column}")
        
        # Convert to list of dictionaries
        companies = df.to_dict(orient="records")
        
        logger.info(f"Read {len(companies)} companies from CSV: {csv_path}")
        return companies
    
    except Exception as e:
        logger.error(f"Error reading companies from CSV: {str(e)}")
        raise


def get_db_companies(db: Session) -> Dict[str, Dict[int, Dict[str, Any]]]:
    """
    Get companies and their filings from the database.
    
    Parameters:
    - db: Database session
    
    Returns:
    - Nested dictionary: {ticker: {year: {'10-K': True, '10-K/A': True}}}
    """
    try:
        # Query database for existing filings
        query = text("""
        SELECT 
            ticker, 
            year, 
            document_type, 
            COUNT(*) as document_count
        FROM 
            filings_metadata
        GROUP BY 
            ticker, year, document_type
        ORDER BY 
            ticker, year, document_type
        """)
        
        result = db.execute(query)
        
        # Create nested dictionary of existing filings
        db_companies = {}
        
        for row in result:
            ticker = row.ticker
            year = row.year
            doc_type = row.document_type
            
            # Initialize ticker if not exists
            if ticker not in db_companies:
                db_companies[ticker] = {}
            
            # Initialize year if not exists
            if year not in db_companies[ticker]:
                db_companies[ticker][year] = {}
            
            # Record document type presence
            db_companies[ticker][year][doc_type] = row.document_count > 0
        
        logger.info(f"Found {len(db_companies)} companies in database")
        return db_companies
    
    except Exception as e:
        logger.error(f"Error getting companies from database: {str(e)}")
        raise


def find_missing_filings(
    csv_companies: List[Dict[str, Any]], 
    db_companies: Dict[str, Dict[int, Dict[str, Any]]]
) -> List[UpdateCandidate]:
    """
    Find filings that are in the CSV but missing from the database.
    
    Parameters:
    - csv_companies: List of companies from CSV
    - db_companies: Nested dictionary of companies from database
    
    Returns:
    - List of UpdateCandidate objects
    """
    update_candidates = []
    
    for company in csv_companies:
        ticker = company["ticker"]
        start_year = int(company["start_year"])
        end_year = int(company["end_year"])
        
        # Process each year in the range
        for year in range(start_year, end_year + 1):
            # Check if ticker exists in db
            if ticker not in db_companies:
                update_candidates.append(
                    UpdateCandidate(ticker, year, "New company")
                )
                continue
            
            # Check if year exists for ticker
            if year not in db_companies[ticker]:
                update_candidates.append(
                    UpdateCandidate(ticker, year, "New year for existing company")
                )
                continue
            
            # Check if documents exist for year
            year_docs = db_companies[ticker][year]
            
            # Check for 10-K
            if "10-K" not in year_docs or not year_docs["10-K"]:
                update_candidates.append(
                    UpdateCandidate(ticker, year, "Missing 10-K")
                )
            
            # Check for 10-K/A (amended filing)
            if "10-K/A" not in year_docs or not year_docs["10-K/A"]:
                update_candidates.append(
                    UpdateCandidate(ticker, year, "Missing 10-K/A")
                )
    
    logger.info(f"Found {len(update_candidates)} candidates for update")
    return update_candidates


def get_update_candidates(db: Session, csv_path: str = None) -> List[UpdateCandidate]:
    """
    Get list of companies and years that need to be updated.
    
    Parameters:
    - db: Database session
    - csv_path: Path to the CSV file (defaults to config)
    
    Returns:
    - List of UpdateCandidate objects
    """
    # Get companies from CSV
    csv_companies = get_companies_from_csv(csv_path)
    
    # Get companies from database
    db_companies = get_db_companies(db)
    
    # Find missing filings
    update_candidates = find_missing_filings(csv_companies, db_companies)
    
    return update_candidates