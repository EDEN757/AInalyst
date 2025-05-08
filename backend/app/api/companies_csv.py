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
from data_updater.fetch_sec import fetch_companies_and_filings_by_symbol

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
        logger.error(f"Could not find companies_to_import.csv. Searched in: {', '.join(possible_paths)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CSV file not found. Please create 'companies_to_import.csv' in the project root or Docker volume"
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
    
    # Start background processing
    def process_companies_in_thread():
        for company in companies_to_import:
            symbol = company["symbol"]
            filing_limit = company["filing_limit"]
            
            try:
                logger.info(f"Processing company {symbol} with filing_limit={filing_limit}")
                
                # Check if company already exists
                local_db = SessionLocal()
                existing_company = crud.get_company_by_symbol(db=local_db, symbol=symbol)
                if existing_company:
                    logger.info(f"Company {symbol} already exists, skipping")
                    local_db.close()
                    continue
                local_db.close()
                
                # Execute a custom script to add the company
                cmd = ["python", "-c", f'''
import sys
sys.path.append("/app")
from data_updater.fetch_sec import fetch_companies_and_filings_by_symbol
from data_updater.update_job import process_company_data 
from app.db.database import SessionLocal

symbol = "{symbol}"
filing_limit = {filing_limit}

# Create DB session
db = SessionLocal()

try:
    # Fetch the company data
    print(f"Fetching data for company {{symbol}}")
    company_data = fetch_companies_and_filings_by_symbol(symbol, filing_limit=filing_limit)
    
    if not company_data["companies"]:
        print(f"No data found for company {{symbol}}")
        sys.exit(1)
        
    # Process the company data
    print(f"Processing data for company {{symbol}}")
    result = process_company_data(db, company_data)
    print(f"Company {{symbol}} processed: {{result}}")
except Exception as e:
    print(f"Error processing company {{symbol}}: {{str(e)}}")
    sys.exit(1)
finally:
    db.close()
''']
                
                # Run the script in a subprocess
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                    logger.info(f"Company {symbol} loading completed successfully: {result.stdout}")
                else:
                    logger.error(f"Company {symbol} loading failed: {result.stderr}")
                    
            except Exception as e:
                logger.error(f"Error processing company {symbol}: {str(e)}", exc_info=True)
    
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