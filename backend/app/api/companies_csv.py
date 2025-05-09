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
from data_updater.fetch_sec import lookup_company_cik_from_sec, get_company_submissions, extract_filings_by_type
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
    'end_date': ['end_date', 'enddate', 'end', 'to_date', 'to', 'date_to'],
    'year': ['year', 'fiscal_year', 'filing_year']
}

# SEC Filing types
VALID_FILING_TYPES = ['10-K', '10-Q', '8-K', '10-K/A', '10-Q/A', '8-K/A', 'S-1', 'S-1/A',
                    'DEF 14A', '424B2', '424B3', '424B4', '424B5']

def find_csv_file():
    """
    Find the CSV file in various possible locations.
    
    Returns:
        str or None: The path to the CSV file if found, None otherwise
    """
    logger.info("Searching for companies_to_import.csv file...")
    current_dir = os.getcwd()
    logger.info(f"Current working directory: {current_dir}")
    
    # Calculate project root from backend app location
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    logger.info(f"Project root directory: {project_root}")
    
    # Define all possible paths to look for the CSV
    possible_paths = [
        # Standard Docker mount locations
        "/data/companies_to_import.csv",  # Primary Docker volume mount
        "/companies_to_import.csv",       # Project root in Docker
        
        # Common project paths
        os.path.join(project_root, "companies_to_import.csv"),  # Project root (local development)
        "/app/companies_to_import.csv",                         # App directory in Docker
        "/project/companies_to_import.csv",                     # Project directory in Docker
        "/src/companies_to_import.csv",                         # Source directory in Docker
    ]
    
    # If current directory is not inside backend, check there too
    if "backend" not in current_dir:
        possible_paths.append(os.path.join(current_dir, "companies_to_import.csv"))
        
        # Check one level up as well (common for Docker)
        parent_dir = os.path.dirname(current_dir)
        if parent_dir:
            possible_paths.append(os.path.join(parent_dir, "companies_to_import.csv"))
    
    # Try each path
    csv_path = None
    for path in possible_paths:
        try:
            if os.path.exists(path):
                # Try to open the file to verify it's readable
                with open(path, 'r') as test_file:
                    first_line = test_file.readline()
                    if first_line:
                        logger.info(f"Found CSV file at: {path} (First line: {first_line.strip()})")
                        csv_path = path
                        break
                    else:
                        logger.warning(f"CSV file at {path} is empty")
            else:
                logger.debug(f"No CSV file at {path}")
        except Exception as e:
            logger.error(f"Error testing path {path}: {str(e)}")
    
    if not csv_path:
        # Last resort - try to find anywhere in the filesystem
        try:
            find_cmd = "find / -name 'companies_to_import.csv' 2>/dev/null || true"
            import subprocess
            result = subprocess.check_output(find_cmd, shell=True, text=True, timeout=10)
            found_paths = result.strip().split('\n')
            
            for found_path in found_paths:
                if found_path and os.path.exists(found_path) and os.access(found_path, os.R_OK):
                    csv_path = found_path
                    logger.info(f"Found CSV using system search at: {csv_path}")
                    break
        except Exception as e:
            logger.warning(f"Error during system-wide file search: {str(e)}")
    
    return csv_path


def create_emergency_csv():
    """
    Create an emergency CSV file when none can be found.
    
    Returns:
        str or None: The path to the created CSV file, None if failed
    """
    emergency_locations = [
        "/data/companies_to_import.csv",
        "/app/companies_to_import.csv",
        "/companies_to_import.csv",
        os.getcwd() + "/companies_to_import.csv"
    ]
    
    template_content = """ticker,cik,doc_type,start_date,end_date
AAPL,0000320193,10-K,2020-01-01,2023-12-31
MSFT,0000789019,10-K,2020-01-01,2023-12-31
GOOGL,0001652044,10-K,2020-01-01,2023-12-31
AMZN,0001018724,10-K,2020-01-01,2023-12-31
JPM,0000019617,10-K,2020-01-01,2023-12-31"""
    
    for path in emergency_locations:
        try:
            directory = os.path.dirname(path)
            if directory and not os.path.exists(directory):
                try:
                    os.makedirs(directory)
                    logger.info(f"Created directory: {directory}")
                except Exception as e:
                    logger.warning(f"Could not create directory {directory}: {str(e)}")
                    continue
                    
            # Try to create the file
            with open(path, 'w') as f:
                f.write(template_content)
            
            # Make readable/writable by all users
            try:
                os.chmod(path, 0o666)
            except Exception as e:
                logger.warning(f"Could not set permissions on {path}: {str(e)}")
            
            logger.info(f"Created emergency CSV file at {path}")
            return path
        except Exception as e:
            logger.warning(f"Failed to create emergency CSV at {path}: {str(e)}")
    
    return None


def parse_csv_data(csv_path):
    """
    Parse the CSV file into a structured format.
    
    Args:
        csv_path: Path to the CSV file
        
    Returns:
        List of dictionaries with company information
    """
    logger.info(f"Parsing CSV file: {csv_path}")
    companies_to_import = []
    
    try:
        with open(csv_path, 'r') as file:
            # Read entire file content to handle potential BOM characters
            content = file.read()
            if content.startswith('\ufeff'):
                content = content[1:]  # Remove BOM if present
            
            # Parse CSV
            csv_reader = csv.reader(content.splitlines())
            rows = list(csv_reader)
            
            if not rows:
                logger.error("CSV file is empty")
                return []
            
            # Get header and map columns
            header = [col.strip().lower() for col in rows[0]]
            logger.info(f"CSV header: {header}")
            
            # Map columns to their standardized names
            column_indices = {}
            for field, possible_names in COLUMN_MAPPINGS.items():
                found = False
                for i, col in enumerate(header):
                    if col.lower() in possible_names:
                        column_indices[field] = i
                        found = True
                        break
            
            logger.info(f"Mapped columns: {column_indices}")
            
            # Check for minimum required columns: ticker and doc_type
            if 'ticker' not in column_indices or 'doc_type' not in column_indices:
                # Check if no header (first row has data)
                if len(rows) > 0 and len(rows[0]) >= 3:
                    logger.info("CSV may have no header, using default column order")
                    column_indices = {
                        'ticker': 0,
                        'doc_type': 1,
                        'start_date': 2,
                        'end_date': 3
                    }
                    if len(rows[0]) >= 5:
                        column_indices['cik'] = 4
                    start_row = 0  # Start from first row
                else:
                    raise ValueError("CSV must have ticker and doc_type columns")
            else:
                start_row = 1  # Skip header row
            
            # Regular expression for validating dates
            date_pattern = r'^\d{4}-\d{2}-\d{2}$'
            
            # CIK pattern - 10 digits with optional leading zeros
            cik_pattern = r'^0*(\d{1,10})$'  
            
            # Process rows
            for row_index, row in enumerate(rows[start_row:], start=start_row+1):
                if len(row) < 2:
                    logger.warning(f"Skipping row {row_index}: insufficient columns")
                    continue
                
                # Extract ticker
                ticker_idx = column_indices.get('ticker', 0)
                ticker = row[ticker_idx].strip().upper() if ticker_idx < len(row) else ''
                
                if not ticker:
                    logger.warning(f"Skipping row {row_index}: missing ticker")
                    continue
                
                # Extract doc_type
                doc_type_idx = column_indices.get('doc_type', 1)
                doc_type = row[doc_type_idx].strip() if doc_type_idx < len(row) else ''
                
                if not doc_type:
                    logger.warning(f"Skipping row {row_index}: missing doc_type")
                    continue
                
                # Extract CIK if available
                cik = None
                if 'cik' in column_indices and column_indices['cik'] < len(row):
                    cik_raw = row[column_indices['cik']].strip()
                    if cik_raw and re.match(cik_pattern, cik_raw):
                        # Format CIK as 10 digits with leading zeros
                        cik = cik_raw.lstrip('0').zfill(10)
                        logger.info(f"Found CIK {cik} for {ticker}")
                
                # Extract start_date and end_date
                start_date = None
                end_date = None
                year = None
                
                # Check for year-only specification
                if 'year' in column_indices and column_indices['year'] < len(row):
                    year_str = row[column_indices['year']].strip()
                    if year_str and year_str.isdigit():
                        year = int(year_str)
                        start_date = f"{year}-01-01"
                        end_date = f"{year}-12-31"
                        logger.info(f"Using year {year} for date range")
                
                # Extract start_date if not set by year
                if not start_date and 'start_date' in column_indices and column_indices['start_date'] < len(row):
                    start_date = row[column_indices['start_date']].strip()
                    if not start_date or not re.match(date_pattern, start_date):
                        logger.warning(f"Row {row_index}: Invalid start_date format: {start_date}")
                        start_date = None
                
                # Extract end_date if not set by year
                if not end_date and 'end_date' in column_indices and column_indices['end_date'] < len(row):
                    end_date = row[column_indices['end_date']].strip()
                    if not end_date or not re.match(date_pattern, end_date):
                        logger.warning(f"Row {row_index}: Invalid end_date format: {end_date}")
                        end_date = None
                
                # Default dates if not specified
                if not start_date:
                    start_date = f"{datetime.datetime.now().year - 3}-01-01"
                    logger.info(f"Row {row_index}: Using default start_date: {start_date}")
                
                if not end_date:
                    end_date = f"{datetime.datetime.now().year}-12-31"
                    logger.info(f"Row {row_index}: Using default end_date: {end_date}")
                
                # Validate doc_type
                if doc_type not in VALID_FILING_TYPES:
                    logger.warning(f"Row {row_index}: doc_type '{doc_type}' is not a standard SEC filing type")
                
                # Create entry
                companies_to_import.append({
                    "symbol": ticker,
                    "cik": cik,  # May be None
                    "doc_type": doc_type,
                    "start_date": start_date,
                    "end_date": end_date,
                    "year": year,
                    "row_index": row_index
                })
                
                logger.info(f"Added company: {ticker} ({doc_type} from {start_date} to {end_date})")
    
    except Exception as e:
        logger.error(f"Error parsing CSV: {str(e)}")
        raise ValueError(f"Error parsing CSV: {str(e)}")
    
    return companies_to_import


def process_companies(companies_data):
    """
    Process the companies data for import.
    
    Args:
        companies_data: List of dictionaries with company information
        
    Returns:
        Results of the import process
    """
    total_companies = len(companies_data)
    logger.info(f"Processing {total_companies} companies/filings from CSV")
    
    processed_count = 0
    success_count = 0
    error_count = 0
    results = []
    
    for company_index, company in enumerate(companies_data, start=1):
        # Create a fresh database session for each company to avoid transaction issues
        db = SessionLocal()
        
        try:
            symbol = company["symbol"]
            doc_type = company["doc_type"]
            start_date = company["start_date"]
            end_date = company["end_date"]
            cik = company.get("cik")
            row_index = company.get("row_index", "unknown")
            
            query_desc = f"{symbol}:{doc_type} from {start_date} to {end_date} (row {row_index}, {company_index}/{total_companies})"
            logger.info(f"======== PROCESSING: {query_desc} ========")
            processed_count += 1
            
            # Check if company exists
            existing_company = crud.get_company_by_symbol(db=db, symbol=symbol)
            if existing_company:
                logger.info(f"Company {symbol} already exists in database")
            else:
                logger.info(f"Company {symbol} is new and will be created")
            
            # If CIK not provided, look it up
            if not cik:
                logger.info(f"No CIK provided for {symbol}, looking it up from SEC...")
                cik = lookup_company_cik_from_sec(symbol)
                if cik:
                    logger.info(f"Found CIK {cik} for {symbol}")
                else:
                    logger.warning(f"Could not find CIK for {symbol}, continuing without it")
            
            # Get company submission data from SEC API
            company_data = {
                'companies': [],
                'filings': []
            }
            
            try:
                company_name = symbol  # Default name is ticker
                if cik:
                    # Try to get company information from SEC
                    submissions = get_company_submissions(cik)
                    if submissions and 'name' in submissions:
                        company_name = submissions['name']
                        logger.info(f"Got company name from SEC: {company_name}")
                    
                    # Extract filings
                    filings = extract_filings_by_type(submissions, doc_type, limit=50)
                    
                    # If no filings found and this isn't 10-K, try 10-K as fallback
                    if not filings and doc_type != "10-K":
                        logger.warning(f"No {doc_type} filings found for {symbol}. Trying 10-K as fallback.")
                        filings = extract_filings_by_type(submissions, "10-K", limit=50)
                    
                    # Filter by date range
                    if filings:
                        start_dt = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
                        end_dt = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()
                        
                        filtered_filings = []
                        for filing in filings:
                            filing_date = filing['filing_date'].date()
                            if start_dt <= filing_date <= end_dt:
                                filtered_filings.append(filing)
                        
                        logger.info(f"Filtered filings by date range: {len(filings)} -> {len(filtered_filings)}")
                        filings = filtered_filings
                    
                    # Add company to data
                    company_data['companies'].append({
                        'symbol': symbol,
                        'name': company_name,
                        'cik': cik
                    })
                    
                    # Add filings to data
                    for filing in filings:
                        company_data['filings'].append({
                            'company_symbol': symbol,
                            'company_name': company_name,
                            'company_cik': cik,
                            'accession_number': filing['accession_number'],
                            'filing_type': filing['filing_type'],
                            'filing_date': filing['filing_date'],
                            'filing_url': filing['filing_url'],
                            'fiscal_year': filing['fiscal_year'],
                            'fiscal_period': filing['fiscal_period']
                        })
                    
                    logger.info(f"Found {len(filings)} filings for {symbol}")
                
                # Process data if any filings were found
                if company_data['companies'] and company_data['filings']:
                    result = process_company_data(db, company_data)
                    success_count += 1
                    logger.info(f"Successfully processed {symbol}: {result}")
                    results.append({
                        'symbol': symbol,
                        'status': 'success',
                        'filings': len(company_data['filings']),
                        'details': result
                    })
                else:
                    error_count += 1
                    logger.warning(f"No filings found for {symbol}")
                    results.append({
                        'symbol': symbol,
                        'status': 'no_data',
                        'message': f"No {doc_type} filings found in date range {start_date} to {end_date}"
                    })
            
            except Exception as e:
                error_count += 1
                logger.error(f"Error processing {symbol}: {str(e)}")
                results.append({
                    'symbol': symbol,
                    'status': 'error',
                    'message': f"Processing error: {str(e)}"
                })
        
        except Exception as e:
            error_count += 1
            logger.error(f"General error for {company.get('symbol', 'unknown')}: {str(e)}")
            results.append({
                'symbol': company.get('symbol', 'unknown'),
                'status': 'error',
                'message': f"General error: {str(e)}"
            })
        
        finally:
            # Close the database session
            db.close()
            
            # Log completion
            logger.info(f"======== COMPLETED: {query_desc} ========")
            
            # Pause briefly between companies to avoid rate limiting
            if company_index < total_companies:
                logger.info(f"Waiting before next company ({company_index}/{total_companies})...")
                time.sleep(1)
    
    logger.info(f"IMPORT SUMMARY: {processed_count} companies processed, {success_count} succeeded, {error_count} errors")
    
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
    to import companies and their filings into the database.
    """
    # Find the CSV file
    csv_path = find_csv_file()
    
    # If not found, try to create an emergency one
    if not csv_path:
        logger.warning("CSV file not found, attempting to create an emergency one")
        csv_path = create_emergency_csv()
    
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
            "companies": [f"{c['symbol']} ({c['doc_type']} from {c['start_date']} to {c['end_date']})" for c in companies_data]
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
    writer.writerow(["ticker", "cik", "doc_type", "start_date", "end_date"])
    
    # Example companies with real CIKs
    examples = [
        ["AAPL", "0000320193", "10-K", "2020-01-01", "2023-12-31"],
        ["MSFT", "0000789019", "10-Q", "2022-01-01", "2022-12-31"],
        ["GOOGL", "0001652044", "8-K", "2023-01-01", "2023-12-31"],
        ["AMZN", "0001018724", "10-K", "2020-01-01", "2023-12-31"],
        ["JPM", "0000019617", "10-K", "2019-01-01", "2023-12-31"]
    ]
    
    for example in examples:
        writer.writerow(example)
    
    csv_content = output.getvalue()
    
    # Check SEC API key availability
    has_sec_api_key = bool(settings.SEC_API_KEY)
    
    # Build instructions with appropriate notes
    api_key_note = ""
    if not has_sec_api_key:
        api_key_note = "\n\nNOTE: Without an SEC API key, only 10-K filings can be reliably imported. Other document types may work with limitations. Consider adding an SEC API key for full functionality."
    
    # Instructions
    instructions = """CSV Format for SEC Filings Import

The CSV file should have the following columns:
1. ticker: Company ticker symbol (e.g., AAPL) - REQUIRED
2. cik: SEC Central Index Key (e.g., 0000320193) - OPTIONAL but recommended
3. doc_type: SEC filing type (e.g., 10-K, 10-Q, 8-K) - REQUIRED
4. start_date: Start date in ISO format (YYYY-MM-DD) - OPTIONAL (defaults to 3 years ago)
5. end_date: End date in ISO format (YYYY-MM-DD) - OPTIONAL (defaults to current year)

Notes:
- If CIK is provided, it will speed up the import process
- The system will attempt to find the CIK if not provided
- Date ranges without year boundaries might miss some filings
- Place this file in the project root directory as 'companies_to_import.csv'"""
    
    instructions += api_key_note
    
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
        from ..models.database_models import Filing
        
        total_filings = db.query(Filing).count()
        processed_filings = db.query(Filing).filter(Filing.processed == True).count()
        unprocessed_filings = db.query(Filing).filter(Filing.processed == False).count()
        
        # Get company count
        from ..models.database_models import Company
        total_companies = db.query(Company).count()
        
        # Get chunk count
        from ..models.database_models import TextChunk
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