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
    
    # Try multiple possible locations for the CSV file
    possible_paths = [
        # Standard project root (when running locally)
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "companies_to_import.csv"),
        # Docker container root
        "/app/companies_to_import.csv",
        # Docker volume mount (if configured in docker-compose)
        "/data/companies_to_import.csv",
        # Current working directory
        os.path.join(current_dir, "companies_to_import.csv"),
        # One level up from current directory
        os.path.join(os.path.dirname(current_dir), "companies_to_import.csv")
    ]
    
    # Log all paths we're checking
    for path in possible_paths:
        logger.info(f"Checking path: {path}, exists: {os.path.exists(path)}")
    
    csv_path = None
    for path in possible_paths:
        if os.path.exists(path):
            csv_path = path
            logger.info(f"Found CSV file at: {csv_path}")
            break
    
    if not csv_path:
        # If the CSV file does not exist, just return an error
        # No longer creating a default CSV automatically
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No companies_to_import.csv file found. Please create one in the project root directory and try again."
        )
    
    # Process CSV data
    companies_to_import = []
    try:
        # Read and parse CSV
        with open(csv_path, 'r') as file:
            csv_reader = csv.reader(file)
            
            # Skip header row
            header = next(csv_reader)
            expected_header_old = ["ticker", "doc_type", "date_range"]
            expected_header_new = ["ticker", "doc_type", "start_date", "end_date"]
            
            # Validate header for either format
            if not (all(column in header for column in expected_header_old) or 
                    all(column in header for column in expected_header_new)):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"CSV must have either columns {', '.join(expected_header_old)} or {', '.join(expected_header_new)}"
                )

            # Regular expression to validate date format YYYY-MM-DD
            date_pattern = r'^\d{4}-\d{2}-\d{2}$'
            
            # Parse rows
            for row_index, row in enumerate(csv_reader, start=2):  # Start at 2 for 1-based row index (after header)
                if len(row) < 3:
                    logger.warning(f"Skipping row {row_index} - insufficient data: {row}")
                    continue  # Skip empty rows

                ticker = row[0].strip().upper() if row[0] else ''
                
                if not ticker:
                    logger.warning(f"Skipping row {row_index} - missing ticker")
                    continue
                    
                doc_type = row[1].strip() if len(row) > 1 and row[1] else ''
                
                if not doc_type:
                    logger.warning(f"Skipping row {row_index} - missing document type")
                    continue

                # Handle both formats:
                # 1. If date_range is a separate column with comma: "2020-01-01,2025-12-31"
                # 2. If start_date and end_date are separate columns: "2020-01-01" "2025-12-31"
                if len(row) >= 4 and row[2] and row[3]:
                    # Assume separate columns format
                    start_date = row[2].strip()
                    end_date = row[3].strip()
                    logger.info(f"Row {row_index}: Using separate date columns: {start_date} to {end_date}")
                elif len(row) >= 3 and row[2] and "," in row[2]:
                    # Try to split the third column by comma
                    date_range = row[2].strip().split(',')
                    if len(date_range) == 2:
                        start_date = date_range[0].strip()
                        end_date = date_range[1].strip()
                        logger.info(f"Row {row_index}: Using date_range column with comma: {start_date} to {end_date}")
                    else:
                        logger.warning(f"Skipping row {row_index} for {ticker} - invalid date range format: {row[2]}")
                        continue
                else:
                    logger.warning(f"Skipping row {row_index} for {ticker} - missing or invalid date information")
                    continue

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
                        logger.warning(f"No data found for {query_desc}")
                        if not company_data.get('companies'):
                            logger.warning(f"No company data returned for {symbol}")
                        if not company_data.get('filings'):
                            logger.warning(f"No filings data returned for {symbol}")
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
    # Basic template content with the new format - with more diverse examples
    csv_content = "ticker,doc_type,start_date,end_date\nAAPL,10-K,2020-01-01,2022-12-31\nMSFT,10-Q,2022-01-01,2022-12-31\nGOOGL,8-K,2023-01-01,2023-12-31\nJPM,10-K,2019-01-01,2021-12-31\nGS,10-K,2015-01-01,2016-12-31"
    
    return {
        "content": csv_content,
        "filename": "companies_to_import.csv",
        "instructions": "Place this file in the project root directory. CSV should have four columns:\n1. ticker: Company ticker symbol (e.g., AAPL)\n2. doc_type: SEC filing type (e.g., 10-K, 10-Q, 8-K)\n3. start_date: Start date in ISO format (YYYY-MM-DD)\n4. end_date: End date in ISO format (YYYY-MM-DD)\n\nNOTE: Without an SEC API key, only 10-K filings can be imported. Other document types require an SEC API key."
    }