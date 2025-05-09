import pandas as pd
import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session

from ..core.config import settings
from .fetch_sec import get_sec_filings, get_filing_document_url, download_filing_document
from .process_docs import process_filing
from .create_embeddings import create_embeddings_batch, store_embeddings

# Configure logging
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(settings.LOG_LEVEL)

async def update_company_data(db: Session, ticker: str, start_year: int, end_year: int) -> Dict[str, int]:
    """
    Update data for a specific company.
    
    Parameters:
    - db: Database session
    - ticker: Company ticker symbol
    - start_year: Start year for data retrieval
    - end_year: End year for data retrieval
    
    Returns:
    - Statistics about the update process
    """
    logger.info(f"Updating data for {ticker} from {start_year} to {end_year}")
    
    stats = {
        "filings_processed": 0,
        "documents_processed": 0,
        "chunks_created": 0,
        "chunks_stored": 0,
        "errors": 0
    }
    
    # Process each year
    for year in range(start_year, end_year + 1):
        try:
            # Get 10-K filings
            filings = get_sec_filings(ticker, year, "10-K")
            stats["filings_processed"] += len(filings)
            
            # Process each filing
            for filing in filings:
                try:
                    # Get filing document URL
                    document_url = get_filing_document_url(filing["filing_details_url"])
                    if not document_url:
                        logger.warning(f"Could not find document URL for {ticker} {year} 10-K")
                        continue
                    
                    # Download document
                    document_content = download_filing_document(document_url)
                    if not document_content:
                        logger.warning(f"Could not download document for {ticker} {year} 10-K")
                        continue
                    
                    stats["documents_processed"] += 1
                    
                    # Process filing
                    chunks = process_filing(
                        ticker=ticker,
                        year=year,
                        document_type=filing["filing_type"],
                        filing_date=filing["filing_date"],
                        document_content=document_content,
                        source_url=document_url
                    )
                    
                    stats["chunks_created"] += len(chunks)
                    
                    # Create embeddings for chunks
                    chunks_with_embeddings = await create_embeddings_batch(chunks)
                    
                    # Store embeddings in database
                    stored_count = store_embeddings(db, chunks_with_embeddings)
                    stats["chunks_stored"] += stored_count
                    
                except Exception as e:
                    logger.error(f"Error processing filing for {ticker} {year}: {str(e)}")
                    stats["errors"] += 1
        
        except Exception as e:
            logger.error(f"Error processing year {year} for {ticker}: {str(e)}")
            stats["errors"] += 1
    
    logger.info(f"Completed update for {ticker}: {stats}")
    return stats

async def update_from_csv(db: Session, csv_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Update data for companies specified in a CSV file.
    
    Parameters:
    - db: Database session
    - csv_path: Path to the CSV file (defaults to config)
    
    Returns:
    - Statistics about the update process
    """
    # Use default path if not specified
    csv_path = csv_path or settings.COMPANIES_CSV_PATH
    
    logger.info(f"Updating from CSV: {csv_path}")
    
    try:
        # Read CSV file
        df = pd.read_csv(csv_path)
        
        # Validate columns
        required_columns = ["ticker", "start_year", "end_year"]
        for column in required_columns:
            if column not in df.columns:
                raise ValueError(f"CSV file must contain column: {column}")
        
        # Process each company
        company_stats = {}
        for _, row in df.iterrows():
            ticker = row["ticker"]
            start_year = int(row["start_year"])
            end_year = int(row["end_year"])
            
            # Update company data
            stats = await update_company_data(db, ticker, start_year, end_year)
            company_stats[ticker] = stats
        
        # Calculate total statistics
        total_stats = {
            "companies_processed": len(company_stats),
            "filings_processed": sum(stats["filings_processed"] for stats in company_stats.values()),
            "documents_processed": sum(stats["documents_processed"] for stats in company_stats.values()),
            "chunks_created": sum(stats["chunks_created"] for stats in company_stats.values()),
            "chunks_stored": sum(stats["chunks_stored"] for stats in company_stats.values()),
            "errors": sum(stats["errors"] for stats in company_stats.values())
        }
        
        return {
            "total": total_stats,
            "companies": company_stats
        }
    
    except Exception as e:
        logger.error(f"Error updating from CSV: {str(e)}")
        return {
            "error": str(e)
        }