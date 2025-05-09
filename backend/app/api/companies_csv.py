from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import pandas as pd
import os

from ..db.database import get_db
from ..core.config import settings
from ..models.database_models import FilingMetadata

router = APIRouter()

@router.get("/companies-csv")
async def get_companies_csv():
    """
    Get the contents of the companies.csv file.
    
    Returns:
    - The contents of the companies CSV file as a list of dictionaries
    """
    try:
        # Check if file exists
        if not os.path.exists(settings.COMPANIES_CSV_PATH):
            raise HTTPException(status_code=404, detail=f"Companies CSV file not found at {settings.COMPANIES_CSV_PATH}")
        
        # Read CSV file
        df = pd.read_csv(settings.COMPANIES_CSV_PATH)
        
        # Convert to list of dictionaries
        companies = df.to_dict(orient="records")
        
        return companies
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading companies CSV: {str(e)}")

@router.get("/companies-status")
async def get_companies_status(db: Session = Depends(get_db)):
    """
    Get the status of companies listed in the CSV file.
    
    This endpoint:
    1. Reads the companies.csv file
    2. For each company and year range, checks if documents exist in the database
    3. Returns the status of each company/year combination
    
    Returns:
    - List of companies with their ingestion status
    """
    try:
        # Check if file exists
        if not os.path.exists(settings.COMPANIES_CSV_PATH):
            raise HTTPException(status_code=404, detail=f"Companies CSV file not found at {settings.COMPANIES_CSV_PATH}")
        
        # Read CSV file
        df = pd.read_csv(settings.COMPANIES_CSV_PATH)
        
        # Get all companies from the database
        db_companies = db.query(
            FilingMetadata.ticker,
            FilingMetadata.year,
            FilingMetadata.document_type
        ).distinct().all()
        
        # Create a set of (ticker, year, document_type) tuples for faster lookup
        db_set = set((t, y, dt) for t, y, dt in db_companies)
        
        # Process each company in the CSV
        result = []
        for _, row in df.iterrows():
            ticker = row["ticker"]
            start_year = int(row["start_year"])
            end_year = int(row["end_year"])
            
            company_status = {
                "ticker": ticker,
                "company_name": row.get("company_name", ""),
                "start_year": start_year,
                "end_year": end_year,
                "years": []
            }
            
            # Check status for each year in the range
            for year in range(start_year, end_year + 1):
                year_status = {
                    "year": year,
                    "documents": []
                }
                
                # Check for 10-K
                has_10k = (ticker, year, "10-K") in db_set
                year_status["documents"].append({
                    "type": "10-K",
                    "exists": has_10k
                })
                
                # Check for 10-K/A
                has_10ka = (ticker, year, "10-K/A") in db_set
                year_status["documents"].append({
                    "type": "10-K/A",
                    "exists": has_10ka
                })
                
                company_status["years"].append(year_status)
            
            result.append(company_status)
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting companies status: {str(e)}")