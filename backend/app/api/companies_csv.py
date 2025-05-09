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
                f.write("ticker,doc_type,date_range\nAAPL,10-K,2020-01-01,2025-12-31\nMSFT,10-K,2020-01-01,2025-12-31\nGOOGL,10-K,2020-01-01,2025-12-31")
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
                        f.write("ticker,doc_type,date_range\nAAPL,10-K,2020-01-01,2025-12-31\nMSFT,10-K,2020-01-01,2025-12-31\nGOOGL,10-K,2020-01-01,2025-12-31")
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
            expected_header = ["ticker", "doc_type", "date_range"]
            
            # Validate header
            if not all(column in header for column in expected_header):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"CSV must have the following columns: {', '.join(expected_header)}"
                )

            # Regular expression to validate date format YYYY-MM-DD
            date_pattern = r'^\d{4}-\d{2}-\d{2}$'
            
            # Parse rows
            for row in csv_reader:
                if len(row) < 3 or not row[0] or not row[1] or not row[2]:
                    continue  # Skip empty rows

                ticker = row[0].strip().upper()
                doc_type = row[1].strip()
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
        # Create a custom company data structure matching what the process_company_data function expects
        combined_data = {
            'companies': [],
            'filings': []
        }
        
        # List to track which companies we're going to process
        symbols_to_process = []
        queries_to_process = []
        
        # Check which companies already exist and create a list of new ones to process
        db = SessionLocal()
        try:
            for company in companies_to_import:
                symbol = company["symbol"]
                doc_type = company["doc_type"]
                start_date = company["start_date"]
                end_date = company["end_date"]
                
                # Create a query description for logging
                query_desc = f"{symbol}:{doc_type} ({start_date} to {end_date})"
                
                existing_company = crud.get_company_by_symbol(db=db, symbol=symbol)
                if existing_company:
                    logger.info(f"Company {symbol} already exists, will add filings if they don't exist")
                    
                # Add this to our processing list regardless if company exists or not
                # since we might be adding new filings to an existing company
                symbols_to_process.append(symbol)
                queries_to_process.append(query_desc)
                
                # Fetch this company's data and add to our combined batch
                try:
                    logger.info(f"Fetching data for {query_desc}")
                    
                    # Use the new query-based function to fetch filings
                    company_data = fetch_filings_by_query_params(
                        ticker=symbol,
                        doc_type=doc_type,
                        start_date=start_date,
                        end_date=end_date,
                        limit=50  # Reasonable limit to avoid overwhelming the system
                    )
                    
                    if company_data['companies']:
                        # Add this company's data to our combined batch
                        combined_data['companies'].extend(company_data['companies'])
                        combined_data['filings'].extend(company_data['filings'])
                        logger.info(f"Added {symbol} data with {len(company_data['filings'])} filings to batch")
                    else:
                        logger.warning(f"No data found for {query_desc}")
                except Exception as e:
                    logger.error(f"Error fetching data for {query_desc}: {str(e)}")
            
            if not symbols_to_process:
                logger.info("No companies to process")
                return
                
            logger.info(f"About to process {len(symbols_to_process)} queries in a single batch: {', '.join(queries_to_process)}")
            
            # Now process all the data in a single operation
            if combined_data['companies'] and combined_data['filings']:
                logger.info(f"Processing batch with {len(combined_data['companies'])} companies and {len(combined_data['filings'])} filings")
                try:
                    # Use the existing process_company_data function to handle all companies at once
                    result = process_company_data(db, combined_data)
                    logger.info(f"Batch processing completed successfully: {result}")
                except Exception as e:
                    logger.error(f"Error in batch processing: {str(e)}", exc_info=True)
            else:
                logger.warning("No data to process after fetching")
                
        except Exception as e:
            logger.error(f"Error in company processing thread: {str(e)}", exc_info=True)
        finally:
            db.close()
                
    
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
    csv_content = "ticker,doc_type,date_range\nAAPL,10-K,2020-01-01,2025-12-31\nMSFT,10-Q,2022-01-01,2022-12-31\nGOOGL,8-K,2023-01-01,2023-12-31"
    
    return {
        "content": csv_content,
        "filename": "companies_to_import.csv",
        "instructions": "Place this file in the project root directory. CSV should have three columns:\n1. ticker: Company ticker symbol (e.g., AAPL)\n2. doc_type: SEC filing type (e.g., 10-K, 10-Q, 8-K)\n3. date_range: Start and end dates in ISO format (YYYY-MM-DD) separated by comma"
    }