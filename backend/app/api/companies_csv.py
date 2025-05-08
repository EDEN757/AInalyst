import logging
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
import csv
import io
import threading
import subprocess
import json
from typing import List

from ..db.database import get_db, SessionLocal
from ..db import crud
from data_updater.fetch_sec import fetch_companies_and_filings_by_symbol, fetch_companies_and_filings
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
                f.write("ticker,num_10ks\nAAPL,2\nMSFT,1\nGOOGL,2")
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
                        f.write("ticker,num_10ks\nAAPL,2\nMSFT,1\nGOOGL,2")
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
            expected_header = ["ticker", "num_10ks"]
            
            # Validate header
            if not all(column in header for column in expected_header):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"CSV must have the following columns: {', '.join(expected_header)}"
                )
            
            # Parse rows
            for row in csv_reader:
                if len(row) < 2 or not row[0] or not row[1]:
                    continue  # Skip empty rows
                
                ticker = row[0].strip().upper()
                try:
                    num_10ks = int(row[1].strip())
                    if num_10ks <= 0:
                        logger.warning(f"Skipping {ticker} - invalid num_10ks value: {num_10ks}")
                        continue
                except ValueError:
                    logger.warning(f"Skipping {ticker} - invalid num_10ks value: {row[1]}")
                    continue
                
                companies_to_import.append({
                    "symbol": ticker,
                    "filing_limit": num_10ks
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
        
        # Check which companies already exist and create a list of new ones to process
        db = SessionLocal()
        try:
            for company in companies_to_import:
                symbol = company["symbol"]
                filing_limit = company["filing_limit"]
                
                existing_company = crud.get_company_by_symbol(db=db, symbol=symbol)
                if existing_company:
                    logger.info(f"Company {symbol} already exists, skipping")
                else:
                    logger.info(f"Adding {symbol} to batch processing list with filing_limit={filing_limit}")
                    symbols_to_process.append(symbol)
                    
                    # Fetch this company's data and add to our combined batch
                    try:
                        logger.info(f"Fetching data for {symbol}")
                        company_data = fetch_companies_and_filings_by_symbol(symbol, filing_limit=filing_limit)
                        
                        if company_data['companies']:
                            # Add this company's data to our combined batch
                            combined_data['companies'].extend(company_data['companies'])
                            combined_data['filings'].extend(company_data['filings'])
                            logger.info(f"Added {symbol} data with {len(company_data['filings'])} filings to batch")
                        else:
                            logger.warning(f"No data found for {symbol}")
                    except Exception as e:
                        logger.error(f"Error fetching data for {symbol}: {str(e)}")
            
            if not symbols_to_process:
                logger.info("No new companies to process, all already exist in database")
                return
                
            logger.info(f"About to process {len(symbols_to_process)} companies in a single batch: {', '.join(symbols_to_process)}")
            
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
        "message": f"Importing {len(companies_to_import)} companies from CSV (processing in background)",
        "companies": [company["symbol"] for company in companies_to_import]
    }

@router.get("/companies/csv-template")
async def get_csv_template():
    """Return a CSV template for company import"""
    # Basic template content
    csv_content = "ticker,num_10ks\nAAPL,2\nMSFT,1\nGOOGL,2"
    
    return {
        "content": csv_content,
        "filename": "companies_to_import.csv",
        "instructions": "Place this file in the project root directory. CSV should have two columns:\n1. ticker: Company ticker symbol (e.g., AAPL)\n2. num_10ks: Number of 10-K filings to download (1-5)"
    }