import logging
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
import csv
import io
import threading
import subprocess
import json
from typing import List
import datetime
import re
import os
import time

from ..db.database import get_db, SessionLocal
from ..db import crud
from ..core.config import settings
from data_updater.fetch_sec import fetch_filings_by_query_params
from data_updater.update_job import process_company_data

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/companies/import-from-csv", status_code=status.HTTP_202_ACCEPTED)
async def import_companies_from_csv(db: Session = Depends(get_db)):
    """Import companies from the CSV file in the project root"""
    # Debug the current directory and environment
    current_dir = os.getcwd()
    logger.info(f"Current working directory: {current_dir}")
    
    # Debug the file lookup process in detail
    logger.info("========== CSV FILE LOOKUP PROCESS ==========")

    # Try specific locations for the CSV file, in priority order
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    logger.info(f"Project root directory: {project_root}")

    # Define all possible paths with clear priorities
    possible_paths = [
        # Primary location - Docker volume mount
        "/data/companies_to_import.csv",  # This is the most reliable location in Docker

        # Project root (when running locally)
        os.path.join(project_root, "companies_to_import.csv"),

        # Legacy Docker location (keeping for compatibility)
        "/app/companies_to_import.csv",

        # Absolute path to the expected CSV location
        "/Users/edoardoschiatti/Documents/GitHub/AInalyst/companies_to_import.csv"
    ]

    # If current directory is not inside backend, check there too
    if "backend" not in current_dir:
        logger.info(f"Adding current directory: {current_dir}")
        possible_paths.append(os.path.join(current_dir, "companies_to_import.csv"))

        # Check one level up as well
        parent_dir = os.path.dirname(current_dir)
        if parent_dir and "backend" not in parent_dir:
            logger.info(f"Adding parent directory: {parent_dir}")
            possible_paths.append(os.path.join(parent_dir, "companies_to_import.csv"))

    logger.info("========== END CSV FILE LOOKUP PROCESS ==========")
    
    
    # Log all paths we're checking
    for path in possible_paths:
        logger.info(f"Checking path: {path}, exists: {os.path.exists(path)}")
    
    csv_path = None
    for path in possible_paths:
        try:
            if os.path.exists(path):
                # Try to open the file to verify it's readable
                with open(path, 'r') as test_read:
                    first_line = test_read.readline()
                    logger.info(f"Found CSV file at: {path} (First line: {first_line.strip()})")
                csv_path = path
                break
            else:
                # Check if path is accessible
                parent_dir = os.path.dirname(path)
                if os.path.exists(parent_dir):
                    logger.info(f"Parent directory {parent_dir} exists, but file not found")
                else:
                    logger.warning(f"Parent directory {parent_dir} does not exist")
        except Exception as e:
            logger.error(f"Error testing path {path}: {str(e)}")

    if not csv_path:
        # Check if anyone can find the file ANYWHERE
        logger.error("Failed to find companies_to_import.csv - checking ANY location")

        try:
            # Last resort - use find to locate the file anywhere
            import subprocess
            find_cmd = "find / -name 'companies_to_import.csv' 2>/dev/null || true"
            logger.info(f"Running command: {find_cmd}")

            try:
                result = subprocess.check_output(find_cmd, shell=True, text=True, timeout=10)
                if result.strip():
                    found_paths = result.strip().split('\n')
                    logger.info(f"Find command found files at: {found_paths}")

                    # Try these paths
                    for found_path in found_paths:
                        if os.path.exists(found_path) and os.access(found_path, os.R_OK):
                            csv_path = found_path
                            logger.info(f"Using file found by find command: {csv_path}")
                            break
                else:
                    logger.error("Find command found no CSV files")
            except Exception as cmd_err:
                logger.error(f"Error running find command: {str(cmd_err)}")
        except Exception as e:
            logger.error(f"Error in last resort search: {str(e)}")

        if not csv_path:
            # If the CSV file doesn't exist, create one in /data if possible
            try:
                if os.path.exists("/data") and os.access("/data", os.W_OK):
                    emergency_path = "/data/companies_to_import.csv"
                    template_content = "ticker,doc_type,start_date,end_date\nAAPL,10-K,2020-01-01,2025-12-31\nMSFT,10-Q,2022-01-01,2022-12-31\nGOOGL,8-K,2023-01-01,2023-12-31\nTSLA,10-K,2020-01-01,2022-12-31"

                    logger.info(f"Creating emergency CSV at {emergency_path}")
                    with open(emergency_path, 'w') as em_file:
                        em_file.write(template_content)
                    csv_path = emergency_path
                    logger.info(f"✅ Created emergency CSV at {emergency_path}")

                    # Fix permissions if needed
                    try:
                        os.chmod(emergency_path, 0o666)  # Make readable/writable by everyone
                    except Exception as perm_err:
                        logger.warning(f"Couldn't adjust permissions: {str(perm_err)}")
                else:
                    # If the CSV file does not exist and we can't create one, return a helpful error
                    error_paths = [
                        os.path.join(project_root, "companies_to_import.csv"),
                        "/data/companies_to_import.csv",
                        "/app/companies_to_import.csv"
                    ]

                    error_message = "No companies_to_import.csv file found. Please create the file at one of these locations:\n"
                    for path in error_paths:
                        error_message += f"- {path}\n"
                    error_message += "\nDownload the template from the web interface, edit it, and place it in one of these locations."

                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=error_message
                    )
            except Exception as e:
                logger.error(f"Error creating emergency CSV: {str(e)}")
                # Return a detailed error message
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Could not find or create CSV file. Error: {str(e)}"
                )
    
    # Process CSV data
    companies_to_import = []
    try:
        # Read and parse CSV
        with open(csv_path, 'r') as file:
            # Try to determine if there's a BOM (Byte Order Mark) at the beginning of the file
            content = file.read()
            if content.startswith('\ufeff'):
                # Remove BOM if present
                content = content[1:]

            # Parse CSV from the content
            csv_reader = csv.reader(content.splitlines())
            rows = list(csv_reader)

            if not rows:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="CSV file is empty"
                )

            # Get the header (first row)
            header = [col.strip().lower() for col in rows[0]]
            logger.info(f"CSV header found: {header}")

            # Define expected headers and try to map them
            # Support various header formats and column names
            header_mappings = {
                'ticker': ['ticker', 'symbol', 'company', 'company_symbol'],
                'doc_type': ['doc_type', 'doctype', 'document_type', 'filing_type', 'form_type', 'form'],
                'start_date': ['start_date', 'startdate', 'start', 'from_date', 'from', 'date_from'],
                'end_date': ['end_date', 'enddate', 'end', 'to_date', 'to', 'date_to']
            }

            # Find actual column indices for each required field
            column_indices = {}
            for field, possible_names in header_mappings.items():
                found = False
                for i, col in enumerate(header):
                    if col.lower() in possible_names:
                        column_indices[field] = i
                        found = True
                        break

                if not found and field not in ['start_date', 'end_date']:  # These might be in a combined field
                    logger.warning(f"Could not find column for {field} in header: {header}")

            # Check if we have at least ticker and doc_type columns
            if 'ticker' not in column_indices or 'doc_type' not in column_indices:
                # Check if the CSV might have no header
                if len(rows) > 0 and len(rows[0]) >= 4:
                    # Assume it's a CSV without header and use standard column order
                    logger.info("CSV appears to have no header, using default column order")
                    has_header = False
                    column_indices = {
                        'ticker': 0,
                        'doc_type': 1,
                        'start_date': 2,
                        'end_date': 3
                    }
                    start_row = 0  # Start processing from the first row
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"CSV must have at least 'ticker' and 'doc_type' columns."
                    )
            else:
                has_header = True
                start_row = 1  # Skip the header row

            # Check for date columns or a combined date_range column
            date_range_format = False
            date_range_index = None

            # Check if we need to look for a combined date_range column
            if 'start_date' not in column_indices or 'end_date' not in column_indices:
                for i, col in enumerate(header):
                    if col.lower() in ['date_range', 'daterange', 'dates', 'period', 'range']:
                        date_range_format = True
                        date_range_index = i
                        logger.info(f"Found date_range column at index {i}")
                        break

                if date_range_format and date_range_index is None:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Could not find 'start_date' and 'end_date' columns or a 'date_range' column"
                    )

            # Regular expression to validate date format YYYY-MM-DD
            date_pattern = r'^\d{4}-\d{2}-\d{2}$'

            # Parse rows
            for row_index, row in enumerate(rows[start_row:], start=start_row+1):  # 1-based row index
                if len(row) < 2:
                    logger.warning(f"Skipping row {row_index} - insufficient data: {row}")
                    continue  # Skip empty or very short rows

                # Extract ticker using mapped column index
                ticker_index = column_indices.get('ticker', 0)
                ticker = row[ticker_index].strip().upper() if ticker_index < len(row) and row[ticker_index] else ''

                if not ticker:
                    logger.warning(f"Skipping row {row_index} - missing ticker")
                    continue

                # Extract doc_type using mapped column index
                doc_type_index = column_indices.get('doc_type', 1)
                doc_type = row[doc_type_index].strip() if doc_type_index < len(row) and row[doc_type_index] else ''

                if not doc_type:
                    logger.warning(f"Skipping row {row_index} - missing document type")
                    continue

                # Extract dates based on format
                if date_range_format:
                    # Process combined date_range format
                    if date_range_index >= len(row) or not row[date_range_index]:
                        logger.warning(f"Skipping row {row_index} for {ticker} - missing date range")
                        continue

                    date_parts = row[date_range_index].strip().split(',')
                    if len(date_parts) != 2:
                        logger.warning(f"Skipping row {row_index} for {ticker} - invalid date range format: {row[date_range_index]}")
                        continue

                    start_date = date_parts[0].strip()
                    end_date = date_parts[1].strip()
                    logger.info(f"Row {row_index}: Using date_range column: {start_date} to {end_date}")
                else:
                    # Process separate start_date and end_date columns
                    start_date_index = column_indices.get('start_date', 2)
                    end_date_index = column_indices.get('end_date', 3)

                    if start_date_index >= len(row) or not row[start_date_index]:
                        logger.warning(f"Skipping row {row_index} for {ticker} - missing start date")
                        continue

                    if end_date_index >= len(row) or not row[end_date_index]:
                        logger.warning(f"Skipping row {row_index} for {ticker} - missing end date")
                        continue

                    start_date = row[start_date_index].strip()
                    end_date = row[end_date_index].strip()
                    logger.info(f"Row {row_index}: Using separate date columns: {start_date} to {end_date}")

                # Validate date format
                if not re.match(date_pattern, start_date) or not re.match(date_pattern, end_date):
                    logger.warning(f"Skipping row {row_index} for {ticker} - invalid date format (should be YYYY-MM-DD): {start_date} or {end_date}")
                    continue

                # Validate doc_type (optional: add more validation if needed)
                valid_doc_types = ['10-K', '10-Q', '8-K', '10-K/A', '10-Q/A', '8-K/A']
                if doc_type not in valid_doc_types:
                    logger.warning(f"Warning: {ticker} - doc_type '{doc_type}' is not in standard types {valid_doc_types}, but proceeding anyway")

                companies_to_import.append({
                    "symbol": ticker,
                    "doc_type": doc_type,
                    "start_date": start_date,
                    "end_date": end_date,
                    "row_index": row_index  # Keep track of row index for better error reporting
                })
    
    except Exception as e:
        logger.error(f"Error parsing CSV: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error parsing CSV: {str(e)}"
        )
    
    if not companies_to_import:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid companies found in CSV"
        )
    
    # Log what we're about to process
    logger.info(f"Preparing to process {len(companies_to_import)} companies/filings:")
    for company in companies_to_import:
        logger.info(f"  - {company['symbol']}: {company['doc_type']} from {company['start_date']} to {company['end_date']} (CSV row {company['row_index']})")
    
    # Process companies directly instead of using a subprocess
    def process_companies_in_thread():
        total_companies = len(companies_to_import)
        processed_count = 0
        success_count = 0
        error_count = 0
        
        logger.info(f"Starting background thread to process {total_companies} companies/filings")
        
        # Process each company individually with its own database session
        for company_index, company in enumerate(companies_to_import, start=1):
            # Create a fresh database session for each company
            db = SessionLocal()
            
            try:
                symbol = company["symbol"]
                doc_type = company["doc_type"]
                start_date = company["start_date"]
                end_date = company["end_date"]
                row_index = company.get("row_index", "unknown")
                
                # Create a query description for logging
                query_desc = f"{symbol}:{doc_type} from {start_date} to {end_date} (row {row_index}, company {company_index}/{total_companies})"
                
                logger.info(f"======== STARTED PROCESSING: {query_desc} ========")
                processed_count += 1
                
                existing_company = crud.get_company_by_symbol(db=db, symbol=symbol)
                if existing_company:
                    logger.info(f"Company {symbol} already exists in database, will add any new filings")
                else:
                    logger.info(f"Company {symbol} is new and will be created")
                
                # Process this company immediately
                try:
                    logger.info(f"Fetching data for {query_desc}")
                    
                    # Use the query-based function to fetch filings for this specific company
                    company_data = fetch_filings_by_query_params(
                        ticker=symbol,
                        doc_type=doc_type,
                        start_date=start_date,
                        end_date=end_date,
                        limit=50  # Reasonable limit to avoid overwhelming the system
                    )
                    
                    if company_data.get('companies') and company_data.get('filings'):
                        company_count = len(company_data['companies'])
                        filing_count = len(company_data['filings'])
                        logger.info(f"Found data for {symbol}: {company_count} companies, {filing_count} {doc_type} filings")
                        
                        # Process this specific company's data
                        try:
                            # Process just this company's data
                            logger.info(f"Processing {symbol} data with {filing_count} filings")
                            result = process_company_data(db, company_data)
                            logger.info(f"SUCCESSFULLY processed {symbol}: {result}")
                            success_count += 1
                        except Exception as e:
                            error_count += 1
                            logger.error(f"ERROR processing {symbol}: {str(e)}", exc_info=True)
                    else:
                        # No data found - provide guidance
                        logger.warning(f"No data found for {query_desc}")
                        if not company_data.get('companies'):
                            logger.warning(f"No company data returned for {symbol}. Check if the ticker symbol is correct.")
                        if not company_data.get('filings'):
                            logger.warning(f"No filings data returned for {symbol}. This could be because:")
                            logger.warning(f"1. No {doc_type} filings exist for the specified date range")
                            logger.warning(f"2. SEC API limitations without an API key")
                            logger.warning(f"3. The date range ({start_date} to {end_date}) might not include filing dates")
                except Exception as e:
                    error_count += 1
                    logger.error(f"ERROR fetching data for {query_desc}: {str(e)}", exc_info=True)
            
            except Exception as e:
                error_count += 1
                logger.error(f"ERROR processing company {company.get('symbol', 'unknown')}: {str(e)}", exc_info=True)
            finally:
                # Close the database session for this company before moving to the next one
                db.close()
                
                # Log completion
                logger.info(f"======== FINISHED PROCESSING: {query_desc} ========")
                
                # Give some time between processing companies to avoid rate limiting
                # or potential resource conflicts - but only if we have more to process
                if company_index < total_companies:
                    logger.info(f"Sleeping for 2 seconds before processing next company ({company_index}/{total_companies} completed)")
                    time.sleep(2)
        
        logger.info(f"IMPORT SUMMARY: {processed_count} companies processed, {success_count} succeeded, {error_count} errors")
                
    
    # Start processing in background
    thread = threading.Thread(target=process_companies_in_thread)
    thread.daemon = True
    thread.start()
    
    return {
        "status": "processing",
        "message": f"Importing {len(companies_to_import)} queries from CSV (processing in background). Check logs for progress.",
        "companies": [f"{c['symbol']} ({c['doc_type']} from {c['start_date']} to {c['end_date']})" for c in companies_to_import]
    }

@router.get("/companies/csv-template")
async def get_csv_template():
    """Return a CSV template for company import"""
    # Create CSV content in memory using the csv module for proper formatting
    import io

    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

    # Write header row
    writer.writerow(["ticker", "doc_type", "start_date", "end_date"])

    # Write example rows with diverse companies and document types
    example_data = [
        ["AAPL", "10-K", "2020-01-01", "2022-12-31"],
        ["MSFT", "10-Q", "2022-01-01", "2022-12-31"],
        ["GOOGL", "8-K", "2023-01-01", "2023-12-31"],
        ["TSLA", "10-K", "2020-01-01", "2022-12-31"],
        ["JPM", "10-K", "2019-01-01", "2021-12-31"],
        ["GS", "10-K", "2015-01-01", "2016-12-31"]
    ]

    for row in example_data:
        writer.writerow(row)

    csv_content = output.getvalue()

    # Check if the SEC API key is available to provide accurate guidance
    has_sec_api_key = bool(settings.SEC_API_KEY)
    api_key_note = ""
    if not has_sec_api_key:
        api_key_note = "\n\nNOTE: Without an SEC API key, only 10-K filings can be reliably imported. Other document types may work with limitations. Consider adding an SEC API key for full functionality."

    return {
        "content": csv_content,
        "filename": "companies_to_import.csv",
        "instructions": "Place this file in the project root directory. CSV should have four columns:\n"
                       "1. ticker: Company ticker symbol (e.g., AAPL)\n"
                       "2. doc_type: SEC filing type (e.g., 10-K, 10-Q, 8-K)\n"
                       "3. start_date: Start date in ISO format (YYYY-MM-DD)\n"
                       "4. end_date: End date in ISO format (YYYY-MM-DD)" + api_key_note
    }