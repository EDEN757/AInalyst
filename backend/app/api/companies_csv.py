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
    
    # Start background processing
    def process_companies_in_thread():
        # Filter out companies that already exist to avoid redundant processing
        companies_to_process = []
        symbols_to_process = []
        
        # First, check which companies already exist
        local_db = SessionLocal()
        try:
            for company in companies_to_import:
                symbol = company["symbol"]
                filing_limit = company["filing_limit"]
                
                existing_company = crud.get_company_by_symbol(db=local_db, symbol=symbol)
                if existing_company:
                    logger.info(f"Company {symbol} already exists, skipping")
                else:
                    companies_to_process.append(company)
                    symbols_to_process.append(symbol)
        finally:
            local_db.close()
        
        if not companies_to_process:
            logger.info("No new companies to process, all already exist in database")
            return
            
        logger.info(f"Processing {len(companies_to_process)} companies: {', '.join(symbols_to_process)}")
        
        # Create a Python script that will process all companies at once
        script_content = f'''
import sys
import json
sys.path.append("/app")
from data_updater.fetch_sec import fetch_companies_and_filings_by_symbol
from data_updater.update_job import process_company_data 
from app.db.database import SessionLocal

# Companies to process - this is a list of dictionaries with symbol and filing_limit
companies = {json.dumps(companies_to_process)}

for company in companies:
    symbol = company["symbol"]
    filing_limit = company["filing_limit"]
    
    # Create a new DB session for each company
    db = SessionLocal()
    
    try:
        print(f"Fetching data for company {{symbol}}")
        company_data = fetch_companies_and_filings_by_symbol(symbol, filing_limit=filing_limit)
        
        if not company_data["companies"]:
            print(f"No data found for company {{symbol}}")
            continue
            
        print(f"Processing data for company {{symbol}}")
        result = process_company_data(db, company_data)
        print(f"Company {{symbol}} processed: {{result}}")
    except Exception as e:
        print(f"Error processing company {{symbol}}: {{str(e)}}")
    finally:
        db.close()

print(f"Finished processing {{len(companies)}} companies")
'''
        
        # Write the script to a temporary file
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.py', delete=False, mode='w') as temp_file:
            temp_file.write(script_content)
            script_path = temp_file.name
        
        try:
            # Execute the script that processes all companies
            cmd = ["python", script_path]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"Companies processed successfully: {result.stdout}")
            else:
                logger.error(f"Error processing companies: {result.stderr}")
                
        except Exception as e:
            logger.error(f"Error executing script to process companies: {str(e)}", exc_info=True)
        finally:
            # Clean up the temporary file
            import os
            try:
                os.unlink(script_path)
            except Exception as e:
                logger.error(f"Error removing temporary script: {str(e)}")
                
    
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