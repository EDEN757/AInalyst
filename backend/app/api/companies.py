from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..db.database import get_db
from ..db import crud
from ..models.database_models import Company

router = APIRouter()


@router.get("/companies", response_model=List[dict])
async def get_companies(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get a list of all companies in the database"""
    companies = crud.get_companies(db=db, skip=skip, limit=limit)
    return [
        {
            "symbol": company.symbol,
            "name": company.name,
            "sector": company.sector,
            "industry": company.industry
        }
        for company in companies
    ]


@router.get("/companies/{symbol}/filings")
async def get_company_filings(symbol: str, db: Session = Depends(get_db)):
    """Get all filings for a specific company"""
    company = crud.get_company_by_symbol(db=db, symbol=symbol)
    if not company:
        raise HTTPException(status_code=404, detail=f"Company with symbol {symbol} not found")
    
    return [
        {
            "id": filing.id,
            "filing_type": filing.filing_type,
            "filing_date": filing.filing_date,
            "fiscal_year": filing.fiscal_year,
            "fiscal_period": filing.fiscal_period,
            "accession_number": filing.accession_number
        }
        for filing in company.filings
    ]
