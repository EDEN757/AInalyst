import logging
import os
import csv
import io
import threading
import datetime
import re
import time
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..db.database import get_db, SessionLocal
from ..db import crud
from ..core.config import settings
from data_updater.fetch_sec import lookup_company_cik_from_sec, fetch_company_10k_filings
from data_updater.update_job import process_company_data

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter()

# CSV column definitions with support for various naming conventions
COLUMN_MAPPINGS = {
    'ticker': ['ticker', 'symbol', 'company', 'company_symbol', 'ticker_symbol'],
    'cik': ['cik', 'cik_number', 'sec_cik', 'company_cik'],
    'doc_type': ['doc_type', 'doctype', 'document_type', 'filing_type', 'form_type', 'form'],
    'start_date': ['start_date', 'startdate', 'start', 'from_date', 'from', 'date_from'],
    'end_date': ['end_date', 'enddate', 'end', 'to_date', 'to', 'date_to']
}

def find_csv_file() -> Optional[str]:
    """
    Find the CSV file in the project root.
    
    Returns:
        str or None: The path to the CSV file if found, None otherwise
    """
    logger.info("Searching for companies_to_import.csv file...")
    
    # Calculate project root
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    logger.info(f"Project root directory: {project_root}")
    
    # Standard path in project root
    csv_path = os.path.join(project_root, "companies_to_import.csv")
    
    if os.path.exists(csv_path):
        logger.info(f"Found CSV file at: {csv_path}")
        return csv_path
    
    # Check Docker paths if standard path not found
    docker_paths = [
        "/data/companies_to_import.csv",
        "/companies_to_import.csv",
        "/app/companies_to_import.csv"
    ]
    
    for path in docker_paths:
        if os.path.exists(path):
            logger.info(f"Found CSV file at: {path}")
            return path
    
    logger.error("Could not find companies_to_import.csv file")
    return None

def create_default_csv() -> Optional[str]:
    """
    Create a default CSV file if none exists.
    
    Returns:
        str or None: The path to the created CSV file, None if failed
    """
    locations = [
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 
                     "companies_to_import.csv"),
        "/data/companies_to_import.csv",
        "/companies_to_import.csv"
    ]
    
    template_content = """ticker,cik,doc_type,start_date,end_date
AAPL,0000320193,10-K,2020-01-01,2023-12-31
MSFT,0000789019,10-K,2020-01-01,2023-12-31
GOOGL,0001652044,10-K,2020-01-01,2023-12-31
AMZN,0001018724,10-K,2020-01-01,2023-12-31"""
    
    for path in locations:
        try:
            # Ensure directory exists
            directory = os.path.dirname(path)
            if directory and not os.path.exists(directory):
                try:
                    os.makedirs(directory)
                except Exception as e:
                    logger.warning(f"Could not create directory {directory}: {str(e)}")
                    continue
            
            # Create the file
            with open(path, 'w') as f:
                f.write(template_content)
            
            logger.info(f"Created default CSV file at {path}")
            return path
        except Exception as e:
            logger.warning(f"Failed to create default CSV at {path}: {str(e)}")
    
    return None

def parse_csv_data(csv_path: str) -> List[Dict[str, Any]]:
    """
    Parse the CSV file into a structured format.
    
    Args:
        csv_path: Path to the CSV file
        
    Returns:
        List of dictionaries with company information
    """
    logger.info(f"Parsing CSV file: {csv_path}")
    companies_data = []
    
    try:
        with open(csv_path, 'r') as file:
            # Read the CSV content
            content = file.read()
            if content.startswith('\ufeff'):
                content = content[1:]  # Remove BOM if present
            
            # Parse CSV
            csv_reader = csv.reader(content.splitlines())
            rows = list(csv_reader)
            
            if not rows or len(rows) < 2:
                logger.error("CSV file is empty or has only headers")
                return []
            
            # Get header and map columns
            header = [col.strip().lower() for col in rows[0]]
            logger.info(f"CSV header: {header}")
            
            # Map columns to their standardized names
            column_indices = {}
            for field, possible_names in COLUMN_MAPPINGS.items():
                for i, col in enumerate(header):
                    if col in possible_names:
                        column_indices[field] = i
                        break
            
            # Check for required columns: ticker is mandatory
            if 'ticker' not in column_indices:
                logger.error("CSV must have a ticker column")
                return []
            
            # Set default indices for doc_type (always 10-K for this implementation)
            if 'doc_type' not in column_indices:
                logger.info("No doc_type column found, defaulting to 10-K for all companies")
            
            # Process rows (skip header)
            for row_index, row in enumerate(rows[1:], start=2):
                if len(row) <= column_indices['ticker']:
                    logger.warning(f"Row {row_index} has insufficient columns")
                    continue
                
                # Extract ticker (required)
                ticker = row[column_indices['ticker']].strip().upper()
                if not ticker:
                    logger.warning(f"Skipping row {row_index}: missing ticker")
                    continue
                
                # Extract CIK if available
                cik = None
                if 'cik' in column_indices and column_indices['cik'] < len(row):
                    cik_raw = row[column_indices['cik']].strip()
                    if cik_raw:
                        # Format CIK with leading zeros
                        cik = cik_raw.lstrip('0').zfill(10)
                
                # Always use 10-K as doc_type
                doc_type = "10-K"
                if 'doc_type' in column_indices and column_indices['doc_type'] < len(row):
                    doc_type_raw = row[column_indices['doc_type']].strip()
                    if doc_type_raw and doc_type_raw.upper() == "10-K":
                        doc_type = "10-K"
                    else:
                        logger.warning(f"Row {row_index}: Only 10-K filings are supported. Using 10-K.")
                
                # Extract start_date and end_date
                start_date = None
                if 'start_date' in column_indices and column_indices['start_date'] < len(row):
                    start_date = row[column_indices['start_date']].strip()
                    # Validate date format
                    if not start_date or not re.match(r'^\d{4}-\d{2}-\d{2}$', start_date):
                        logger.warning(f"Row {row_index}: Invalid start_date format: {start_date}")
                        start_date = None
                
                end_date = None
                if 'end_date' in column_indices and column_indices['end_date'] < len(row):
                    end_date = row[column_indices['end_date']].strip()
                    # Validate date format
                    if not end_date or not re.match(r'^\d{4}-\d{2}-\d{2}$', end_date):
                        logger.warning(f"Row {row_index}: Invalid end_date format: {end_date}")
                        end_date = None
                
                # Use default dates if not specified
                if not start_date:
                    start_date = f"{datetime.datetime.now().year - 3}-01-01"
                    logger.info(f"Row {row_index}: Using default start_date: {start_date}")
                
                if not end_date:
                    end_date = f"{datetime.datetime.now().year}-12-31"
                    logger.info(f"Row {row_index}: Using default end_date: {end_date}")
                
                # Add company to the list
                companies_data.append({
                    "symbol": ticker,
                    "cik": cik,
                    "doc_type": doc_type,
                    "start_date": start_date,
                    "end_date": end_date
                })
                
                logger.info(f"Added company: {ticker} (10-K from {start_date} to {end_date})")
    
    except Exception as e:
        logger.error(f"Error parsing CSV: {str(e)}")
        raise ValueError(f"Error parsing CSV: {str(e)}")
    
    return companies_data

def process_companies(companies_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Process the companies data for import.
    
    Args:
        companies_data: List of dictionaries with company information
        
    Returns:
        Results of the import process
    """
    total_companies = len(companies_data)
    logger.info(f"Processing {total_companies} companies from CSV")
    
    processed_count = 0
    success_count = 0
    error_count = 0
    results = []
    
    for i, company in enumerate(companies_data, start=1):
        # Create a fresh database session for each company
        db = SessionLocal()
        
        try:
            symbol = company["symbol"]
            start_date = company["start_date"]
            end_date = company["end_date"]
            cik = company.get("cik")
            
            logger.info(f"Processing company {symbol} ({i}/{total_companies})")
            processed_count += 1
            
            # Check if company exists
            existing_company = crud.get_company_by_symbol(db=db, symbol=symbol)
            if existing_company:
                logger.info(f"Company {symbol} already exists in database")
            
            # If CIK not provided, look it up
            if not cik:
                logger.info(f"No CIK provided for {symbol}, looking it up from SEC...")
                cik = lookup_company_cik_from_sec(symbol)
                if cik:
                    logger.info(f"Found CIK {cik} for {symbol}")
                else:
                    logger.warning(f"Could not find CIK for {symbol}, will try proceeding without it")
            
            # Fetch 10-K filings for this company
            logger.info(f"Fetching 10-K filings for {symbol} from {start_date} to {end_date}")
            company_data = fetch_company_10k_filings(
                symbol=symbol,
                cik=cik,
                start_date=start_date,
                end_date=end_date
            )
            
            # Process data if any filings were found
            if company_data['companies'] and company_data['filings']:
                logger.info(f"Found {len(company_data['filings'])} 10-K filing(s) for {symbol}")
                result = process_company_data(db, company_data)
                success_count += 1
                
                results.append({
                    'symbol': symbol,
                    'status': 'success',
                    'filings': len(company_data['filings']),
                    'details': result
                })
            else:
                logger.warning(f"No 10-K filings found for {symbol} in date range {start_date} to {end_date}")
                error_count += 1
                
                results.append({
                    'symbol': symbol,
                    'status': 'no_data',
                    'message': f"No 10-K filings found in date range {start_date} to {end_date}"
                })
        
        except Exception as e:
            error_count += 1
            logger.error(f"Error processing {company.get('symbol', 'unknown')}: {str(e)}")
            
            results.append({
                'symbol': company.get('symbol', 'unknown'),
                'status': 'error',
                'message': f"Error: {str(e)}"
            })
        
        finally:
            # Close the database session
            db.close()
            
            # Pause briefly between companies to avoid rate limiting
            if i < total_companies:
                time.sleep(1)
    
    logger.info(f"Completed processing {processed_count} companies: {success_count} succeeded, {error_count} failed")
    
    return {
        'processed': processed_count,
        'successful': success_count,
        'failed': error_count,
        'results': results
    }

@router.post("/companies/import-from-csv", status_code=status.HTTP_202_ACCEPTED)
async def import_companies_from_csv(db: Session = Depends(get_db)):
    """
    Import companies from the CSV file.
    
    This endpoint finds and processes the companies_to_import.csv file
    to import companies and their 10-K filings into the database.
    """
    # Find the CSV file
    csv_path = find_csv_file()
    
    # If not found, try to create a default one
    if not csv_path:
        logger.warning("CSV file not found, attempting to create a default one")
        csv_path = create_default_csv()
    
    # If still not found, return error
    if not csv_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Could not find or create companies_to_import.csv. Please place this file in the project root."
        )
    
    # Parse the CSV
    try:
        companies_data = parse_csv_data(csv_path)
        if not companies_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid companies found in the CSV file"
            )
        
        logger.info(f"Found {len(companies_data)} valid companies in CSV")
        
        # Process in background thread
        def process_in_background():
            process_companies(companies_data)
        
        thread = threading.Thread(target=process_in_background)
        thread.daemon = True
        thread.start()
        
        return {
            "status": "processing",
            "message": f"Importing {len(companies_data)} companies from CSV (processing in background)",
            "companies": [c['symbol'] for c in companies_data]
        }
    
    except Exception as e:
        logger.error(f"Error during CSV import: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error during CSV import: {str(e)}"
        )

@router.get("/companies/csv-template")
async def get_csv_template():
    """
    Get a CSV template for importing companies.
    
    Returns a template CSV file with example data and instructions.
    """
    # Create CSV content
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)
    
    # Write header
    writer.writerow(["ticker", "cik", "start_date", "end_date"])
    
    # Example companies with real CIKs
    examples = [
        ["AAPL", "0000320193", "2020-01-01", "2023-12-31"],
        ["MSFT", "0000789019", "2020-01-01", "2023-12-31"],
        ["GOOGL", "0001652044", "2020-01-01", "2023-12-31"],
        ["AMZN", "0001018724", "2020-01-01", "2023-12-31"],
        ["META", "0001326801", "2020-01-01", "2023-12-31"]
    ]
    
    for example in examples:
        writer.writerow(example)
    
    csv_content = output.getvalue()
    
    # Instructions
    instructions = """CSV Format for SEC 10-K Filings Import

The CSV file should have the following columns:
1. ticker: Company ticker symbol (e.g., AAPL) - REQUIRED
2. cik: SEC Central Index Key (e.g., 0000320193) - OPTIONAL but recommended for faster processing
3. start_date: Start date in ISO format (YYYY-MM-DD) - OPTIONAL (defaults to 3 years ago)
4. end_date: End date in ISO format (YYYY-MM-DD) - OPTIONAL (defaults to current year)

Notes:
- This application only supports 10-K filings
- CIK will be automatically looked up if not provided
- Place this file in the project root directory as 'companies_to_import.csv'
- Dates must be in YYYY-MM-DD format
- The system will fetch all 10-K filings within the specified date range
"""
    
    return {
        "content": csv_content,
        "filename": "companies_to_import.csv",
        "instructions": instructions
    }

@router.get("/companies/import-status")
async def get_import_status(db: Session = Depends(get_db)):
    """
    Get the status of the last import operation.
    
    Returns information about processed and unprocessed filings.
    """
    try:
        # Get counts of processed and unprocessed filings
        from ..models.database_models import Filing, Company, TextChunk
        
        total_filings = db.query(Filing).count()
        processed_filings = db.query(Filing).filter(Filing.processed == True).count()
        unprocessed_filings = db.query(Filing).filter(Filing.processed == False).count()
        
        # Get company count
        total_companies = db.query(Company).count()
        
        # Get chunk count
        total_chunks = db.query(TextChunk).count()
        embedded_chunks = db.query(TextChunk).filter(TextChunk.embedded == True).count()
        
        return {
            "status": "success",
            "companies": total_companies,
            "filings": {
                "total": total_filings,
                "processed": processed_filings,
                "unprocessed": unprocessed_filings,
                "processing_progress": f"{processed_filings}/{total_filings}" if total_filings > 0 else "0/0"
            },
            "chunks": {
                "total": total_chunks,
                "embedded": embedded_chunks,
                "embedding_progress": f"{embedded_chunks}/{total_chunks}" if total_chunks > 0 else "0/0"
            }
        }
    
    except Exception as e:
        logger.error(f"Error getting import status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting import status: {str(e)}"
        )