from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct
from typing import List, Dict, Any

from ..db.database import get_db
from ..models.database_models import FilingMetadata

router = APIRouter()

@router.get("/companies")
async def get_companies(db: Session = Depends(get_db)):
    """
    Get a list of all companies in the database.
    
    Returns:
    - List of unique tickers with their respective years and document counts
    """
    # Query for unique tickers and their metadata
    results = db.query(
        FilingMetadata.ticker,
        FilingMetadata.year,
        func.count().label('document_count')
    ).group_by(
        FilingMetadata.ticker,
        FilingMetadata.year
    ).all()
    
    # Organize results by ticker
    companies = {}
    for ticker, year, doc_count in results:
        if ticker not in companies:
            companies[ticker] = {
                "ticker": ticker,
                "years": [],
                "total_documents": 0
            }
        
        companies[ticker]["years"].append(year)
        companies[ticker]["total_documents"] += doc_count
    
    # Convert to list and sort by ticker
    company_list = list(companies.values())
    for company in company_list:
        company["years"].sort()
    
    company_list.sort(key=lambda x: x["ticker"])
    
    return company_list

@router.get("/companies/{ticker}")
async def get_company_data(ticker: str, db: Session = Depends(get_db)):
    """
    Get detailed data for a specific company.
    
    Parameters:
    - ticker: The company ticker symbol
    
    Returns:
    - Detailed information about the company's filings
    """
    # Check if company exists
    company = db.query(FilingMetadata).filter(FilingMetadata.ticker == ticker).first()
    if not company:
        raise HTTPException(status_code=404, detail=f"Company with ticker {ticker} not found")
    
    # Get years available
    years = db.query(
        distinct(FilingMetadata.year)
    ).filter(
        FilingMetadata.ticker == ticker
    ).order_by(
        FilingMetadata.year
    ).all()
    years = [y[0] for y in years]
    
    # Get document types
    doc_types = db.query(
        distinct(FilingMetadata.document_type)
    ).filter(
        FilingMetadata.ticker == ticker
    ).all()
    doc_types = [dt[0] for dt in doc_types]
    
    # Get section counts
    section_counts = db.query(
        FilingMetadata.section_name,
        func.count().label('count')
    ).filter(
        FilingMetadata.ticker == ticker
    ).group_by(
        FilingMetadata.section_name
    ).all()
    section_counts = {sc[0]: sc[1] for sc in section_counts}
    
    return {
        "ticker": ticker,
        "years": years,
        "document_types": doc_types,
        "section_counts": section_counts,
        "total_documents": sum(section_counts.values())
    }