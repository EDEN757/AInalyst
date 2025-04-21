import logging
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from typing import List, Dict, Any

from ..db.database import get_db
from ..db import crud
from ..models.database_models import Company

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/companies", response_model=List[dict])
async def get_companies(
    request: Request, 
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db)
):
    """Get a list of all companies in the database"""
    client_ip = request.client.host if request.client else "unknown"
    logger.info(f"GET /companies request from {client_ip} (skip={skip}, limit={limit})")
    
    try:
        # Get start_time if it exists, otherwise it's None
        start_time = getattr(request.state, "start_time", None)
        companies = crud.get_companies(db=db, skip=skip, limit=limit)
        
        if not companies:
            logger.warning(f"No companies found in database from request {client_ip}")
            return []
            
        logger.info(f"Retrieved {len(companies)} companies from database")
        return [
            {
                "symbol": company.symbol,
                "name": company.name,
                "sector": company.sector,
                "industry": company.industry
            }
            for company in companies
        ]
    except SQLAlchemyError as e:
        logger.error(f"Database error in get_companies: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Unexpected error in get_companies: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while fetching companies.",
        )


@router.get("/companies/{symbol}/filings", response_model=List[Dict[str, Any]])
async def get_company_filings(symbol: str, request: Request, db: Session = Depends(get_db)):
    """Get all filings for a specific company"""
    client_ip = request.client.host if request.client else "unknown"
    logger.info(f"GET /companies/{symbol}/filings request from {client_ip}")
    
    try:
        company = crud.get_company_by_symbol(db=db, symbol=symbol)
        if not company:
            logger.warning(f"Company with symbol {symbol} not found for request from {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail=f"Company with symbol {symbol} not found"
            )
        
        if not company.filings:
            logger.info(f"No filings found for company {symbol}")
            return []
            
        logger.info(f"Retrieved {len(company.filings)} filings for company {symbol}")
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
    except HTTPException:
        # Re-raise HTTP exceptions without wrapping
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error retrieving filings for {symbol}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Unexpected error retrieving filings for {symbol}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while fetching company filings.",
        )
