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
    import os

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
        # Create a default CSV file in /app directory
        default_csv_path = "/app/companies_to_import.csv"
        try:
            with open(default_csv_path, 'w') as f:
                f.write("ticker,doc_type,start_date,end_date\nAAPL,10-K,2020-01-01,2025-12-31\nMSFT,10-K,2020-01-01,2025-12-31\nGOOGL,10-K,2020-01-01,2025-12-31")
            logger.info(f"Created default CSV file at {default_csv_path}")
            csv_path = default_csv_path
        except Exception as e:
            logger.error(f"Failed to create default CSV file: {str(e)}")
            # Try a different location if /app is not writable
            alt_paths = [
                os.path.join(current_dir, "companies_to_import.csv"),
                "./companies_to_import.csv"
            ]
            
            created = False
            for path in alt_paths:
                try:
                    with open(path, 'w') as f:
                        f.write("ticker,doc_type,start_date,end_date\nAAPL,10-K,2020-01-01,2025-12-31\nMSFT,10-K,2020-01-01,2025-12-31\nGOOGL,10-K,2020-01-01,2025-12-31")
                    logger.info(f"Created default CSV file at alternate location: {path}")
                    csv_path = path
                    created = True
                    break
                except Exception as err:
                    logger.error(f"Failed to create CSV at {path}: {str(err)}")
            
            if not created:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Could not find or create CSV file. Tried multiple locations. Error: {str(e)}"
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
            for row in csv_reader:
                if len(row) < 4 or not row[0] or not row[1] or not row[2] or not row[3]:
                    logger.warning(f"Skipping row - insufficient data: {row}")
                    continue  # Skip empty or insufficient rows

                ticker = row[0].strip().upper()
                doc_type = row[1].strip()

                # Handle both formats:
                # 1. If date_range is a separate column with comma: "2020-01-01,2025-12-31"
                # 2. If start_date and end_date are separate columns: "2020-01-01" "2025-12-31"
                if len(row) >= 4:
                    # Assume separate columns format
                    start_date = row[2].strip()
                    end_date = row[3].strip()
                else:
                    # Try to split the third column by comma
                    date_range = row[2].strip().split(',')
                    if len(date_range) != 2:
                        logger.warning(f"Skipping {ticker} - invalid date range format: {row[2]}")
                        continue
                    start_date = date_range[0].strip()
                    end_date = date_range[1].strip()

                # Validate date format
                if not re.match(date_pattern, start_date) or not re.match(date_pattern, end_date):
                    logger.warning(f"Skipping {ticker} - invalid date format (should be YYYY-MM-DD): {start_date} or {end_date}")
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
    
    # Process companies directly instead of using a subprocess
    def process_companies_in_thread():
        # List to track processed companies
        processed_count = 0
        
        # Process each company individually with its own database session
        for company in companies_to_import:
            # Create a fresh database session for each company
            db = SessionLocal()
            
            try:
                symbol = company["symbol"]
                doc_type = company["doc_type"]
                start_date = company["start_date"]
                end_date = company["end_date"]
                
                # Create a query description for logging
                query_desc = f"{symbol}:{doc_type} ({start_date} to {end_date})"
                logger.info(f"Starting to process: {query_desc}")
                
                existing_company = crud.get_company_by_symbol(db=db, symbol=symbol)
                if existing_company:
                    logger.info(f"Company {symbol} already exists, will add filings if they don't exist")
                
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
                    
                    if company_data['companies'] and company_data['filings']:
                        logger.info(f"Processing {symbol} with {len(company_data['filings'])} {doc_type} filings from {start_date} to {end_date}")
                        
                        # Process this specific company's data
                        try:
                            result = process_company_data(db, company_data)
                            logger.info(f"Processed {symbol} successfully: {result}")
                            processed_count += 1
                        except Exception as e:
                            logger.error(f"Error processing {symbol}: {str(e)}", exc_info=True)
                    else:
                        logger.warning(f"No data found for {query_desc}")
                except Exception as e:
                    logger.error(f"Error fetching data for {query_desc}: {str(e)}")
            
            except Exception as e:
                logger.error(f"Error processing company {company.get('symbol', 'unknown')}: {str(e)}", exc_info=True)
            finally:
                # Close the database session for this company before moving to the next one
                db.close()
                
                # Give some time between processing companies to avoid rate limiting
                # or potential resource conflicts
                import time
                time.sleep(1)
        
        logger.info(f"Completed processing {processed_count} out of {len(companies_to_import)} companies")
                
    
    # Start processing in background
    thread = threading.Thread(target=process_companies_in_thread)
    thread.daemon = True
    thread.start()
    
    return {
        "status": "processing",
        "message": f"Importing {len(companies_to_import)} queries from CSV (processing in background)",
        "companies": [f"{company['symbol']} ({company['doc_type']})" for company in companies_to_import]
    }

@router.get("/companies/csv-template")
async def get_csv_template():
    """Return a CSV template for company import"""
    # Basic template content with the new format
    csv_content = "ticker,doc_type,start_date,end_date\nAAPL,10-K,2020-01-01,2025-12-31\nMSFT,10-Q,2022-01-01,2022-12-31\nGOOGL,8-K,2023-01-01,2023-12-31"
    
    return {
        "content": csv_content,
        "filename": "companies_to_import.csv",
        "instructions": "Place this file in the project root directory. CSV should have four columns:\n1. ticker: Company ticker symbol (e.g., AAPL)\n2. doc_type: SEC filing type (e.g., 10-K, 10-Q, 8-K)\n3. start_date: Start date in ISO format (YYYY-MM-DD)\n4. end_date: End date in ISO format (YYYY-MM-DD)"
    }