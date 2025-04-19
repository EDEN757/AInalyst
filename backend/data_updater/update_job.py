import time
import logging
import argparse
import sys
import os
from typing import Dict, List, Any

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import SessionLocal, Base, engine
from app.core.config import settings
from app.db import crud
from app.models.database_models import Company, Filing, TextChunk

from data_updater.fetch_sec import fetch_companies_and_filings, fetch_filing_document
from data_updater.process_docs import process_filing_text
from data_updater.create_embeddings import create_embeddings

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def setup_database():
    """Create database tables if they don't exist"""
    logger.info("Setting up database...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database setup complete")


def store_companies_and_filings(db, data):
    """Store companies and filings data in the database.
    
    Args:
        db: Database session
        data: Dictionary with 'companies' and 'filings' lists
    
    Returns:
        Dictionary with counts of created items
    """
    companies_created = 0
    filings_created = 0
    
    # Store companies
    for company_data in data['companies']:
        existing_company = crud.get_company_by_symbol(db, company_data['symbol'])
        
        if not existing_company:
            company = crud.create_company(
                db=db,
                symbol=company_data['symbol'],
                name=company_data['name'],
                sector=company_data.get('sector'),
                industry=company_data.get('industry')
            )
            companies_created += 1
            logger.info(f"Created company: {company.symbol} - {company.name}")
        else:
            logger.info(f"Company already exists: {existing_company.symbol}")
    
    # Store filings
    for filing_data in data['filings']:
        existing_filing = crud.get_filing_by_accession(db, filing_data['accession_number'])
        
        if not existing_filing:
            # Get company
            company = crud.get_company_by_symbol(db, filing_data['company_symbol'])
            if not company:
                logger.error(f"Company not found for filing: {filing_data['company_symbol']}")
                continue
            
            filing = crud.create_filing(
                db=db,
                company_id=company.id,
                filing_type=filing_data['filing_type'],
                filing_date=filing_data['filing_date'],
                filing_url=filing_data['filing_url'],
                accession_number=filing_data['accession_number'],
                fiscal_year=filing_data['fiscal_year'],
                fiscal_period=filing_data['fiscal_period']
            )
            filings_created += 1
            logger.info(f"Created filing: {filing.accession_number} for {company.symbol}")
        else:
            logger.info(f"Filing already exists: {existing_filing.accession_number}")
    
    return {
        "companies_created": companies_created,
        "filings_created": filings_created
    }


def process_filings(db):
    """Fetch and process unprocessed filings.
    
    Args:
        db: Database session
    
    Returns:
        Summary of processing results
    """
    # Get all unprocessed filings
    filings = db.query(Filing).filter(Filing.processed == False).all()
    
    if not filings:
        logger.info("No unprocessed filings found")
        return {"filings_processed": 0, "chunks_created": 0}
    
    filings_processed = 0
    chunks_created = 0
    
    for filing in filings:
        logger.info(f"Processing filing: {filing.accession_number}")
        
        # Fetch the filing document
        document_text = fetch_filing_document(filing.filing_url)
        
        if not document_text:
            logger.error(f"Failed to fetch document for {filing.accession_number}")
            continue
        
        # Get company for metadata
        company = filing.company
        
        # Process the document into chunks
        metadata = {
            "filing_id": filing.id,
            "company_symbol": company.symbol,
            "filing_type": filing.filing_type,
            "filing_date": filing.filing_date,
            "fiscal_year": filing.fiscal_year
        }
        
        chunks = process_filing_text(document_text, metadata)
        
        # Store the chunks
        for i, chunk_data in enumerate(chunks):
            crud.create_text_chunk(
                db=db,
                filing_id=filing.id,
                chunk_index=i,
                text_content=chunk_data['text_content'],
                section=chunk_data['section']
            )
            chunks_created += 1
        
        # Mark the filing as processed
        crud.mark_filing_as_processed(db, filing.id)
        filings_processed += 1
        
        logger.info(f"Created {len(chunks)} chunks for filing {filing.accession_number}")
    
    return {
        "filings_processed": filings_processed,
        "chunks_created": chunks_created
    }


def run_update_job(mode='DEMO', skip_fetch=False, skip_process=False, skip_embeddings=False):
    """Run the complete data update job.
    
    Args:
        mode: 'DEMO' or 'FULL'
        skip_fetch: Skip fetching new data
        skip_process: Skip processing filings
        skip_embeddings: Skip creating embeddings
    
    Returns:
        Summary of the update job
    """
    start_time = time.time()
    summary = {}
    
    # Setup database
    setup_database()
    
    # Create a database session
    db = SessionLocal()
    
    try:
        # 1. Fetch companies and filings
        if not skip_fetch:
            logger.info(f"Fetching companies and filings in {mode} mode...")
            data = fetch_companies_and_filings(mode=mode)
            summary["fetch"] = store_companies_and_filings(db, data)
        
        # 2. Process filings into chunks
        if not skip_process:
            logger.info("Processing filings...")
            summary["process"] = process_filings(db)
        
        # 3. Create embeddings for chunks
        if not skip_embeddings:
            logger.info("Creating embeddings...")
            summary["embeddings"] = create_embeddings(db)
        
        duration = time.time() - start_time
        summary["duration_seconds"] = round(duration, 2)
        summary["status"] = "completed"
        
        return summary
        
    except Exception as e:
        logger.error(f"Error in update job: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "duration_seconds": round(time.time() - start_time, 2)
        }
    
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the 10-K filings update job")
    parser.add_argument('--mode', choices=['DEMO', 'FULL'], default=settings.APP_MODE,
                        help='Mode to run the job in: DEMO for a subset, FULL for all S&P 500')
    parser.add_argument('--skip-fetch', action='store_true', help='Skip fetching new data')
    parser.add_argument('--skip-process', action='store_true', help='Skip processing filings')
    parser.add_argument('--skip-embeddings', action='store_true', help='Skip creating embeddings')
    
    args = parser.parse_args()
    
    result = run_update_job(
        mode=args.mode,
        skip_fetch=args.skip_fetch,
        skip_process=args.skip_process,
        skip_embeddings=args.skip_embeddings
    )
    
    logger.info(f"Update job completed with result: {result}")
