import logging
from fastapi import APIRouter, Depends, HTTPException, Request, status, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from ..db.database import get_db
from ..db import crud
from ..models.database_models import Company
from data_updater.fetch_sec import fetch_companies_and_filings_by_symbol, DEMO_COMPANIES
from data_updater.update_job import process_company_data

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter()


class AddCompanyRequest(BaseModel):
    symbol: str
    filing_years: Optional[List[int]] = None
    filing_limit: Optional[int] = 2


class AddDemoCompaniesRequest(BaseModel):
    enabled: bool = True


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
                "industry": company.industry,
                "filings_count": len(company.filings)
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
                "accession_number": filing.accession_number,
                "processed": filing.processed,
                "chunks_count": len(filing.chunks)
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


@router.post("/companies/add", status_code=status.HTTP_202_ACCEPTED)
async def add_company(
    data: AddCompanyRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    db: Session = Depends(get_db)
):
    """Add a new company and its filings to the database"""
    client_ip = request.client.host if request.client else "unknown"
    logger.info(f"POST /companies/add request from {client_ip} for symbol {data.symbol}")
    
    try:
        # Check if company already exists
        existing_company = crud.get_company_by_symbol(db=db, symbol=data.symbol)
        if existing_company:
            return {
                "status": "success", 
                "message": f"Company {data.symbol} already exists in the database",
                "company": {
                    "symbol": existing_company.symbol,
                    "name": existing_company.name,
                    "filings_count": len(existing_company.filings)
                }
            }
            
        # Schedule the background task
        background_tasks.add_task(
            fetch_and_process_company, 
            symbol=data.symbol,
            filing_years=data.filing_years,
            filing_limit=data.filing_limit
        )
        
        return {
            "status": "processing",
            "message": f"Adding company {data.symbol} to database (processing in background)"
        }
        
    except Exception as e:
        logger.error(f"Error in add_company for {data.symbol}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error adding company: {str(e)}"
        )


@router.post("/companies/add-demo", status_code=status.HTTP_202_ACCEPTED)
async def add_demo_companies(
    data: AddDemoCompaniesRequest,
    background_tasks: BackgroundTasks,
    request: Request
):
    """Add demo companies (AAPL, MSFT, GOOGL) to the database"""
    client_ip = request.client.host if request.client else "unknown"
    logger.info(f"POST /companies/add-demo request from {client_ip}")
    
    if data.enabled:
        # Schedule the background task to add demo companies
        background_tasks.add_task(add_demo_companies_task)
        
        demo_symbols = [company["symbol"] for company in DEMO_COMPANIES[:3]]
        return {
            "status": "processing",
            "message": f"Adding demo companies {', '.join(demo_symbols)} to database (processing in background)"
        }
    else:
        return {
            "status": "skipped",
            "message": "Demo companies flag set to false, no action taken"
        }


@router.delete("/companies/{symbol}", status_code=status.HTTP_200_OK)
async def delete_company(symbol: str, request: Request, db: Session = Depends(get_db)):
    """Delete a company and all its associated data"""
    client_ip = request.client.host if request.client else "unknown"
    logger.info(f"DELETE /companies/{symbol} request from {client_ip}")
    
    try:
        # Check if company exists
        company = crud.get_company_by_symbol(db=db, symbol=symbol)
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Company with symbol {symbol} not found"
            )
        
        # Delete the company and all associated filings/chunks
        crud.delete_company(db=db, company_id=company.id)
        
        return {
            "status": "success",
            "message": f"Company {symbol} and all its data successfully deleted"
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error deleting company {symbol}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting company: {str(e)}"
        )


async def fetch_and_process_company(symbol: str, filing_years=None, filing_limit=2):
    """Fetch and process a company and its filings in the background"""
    logger.info(f"Starting background task to add company {symbol}")
    try:
        # Create a new database session for the background task
        db = SessionLocal()
        
        # Fetch company data from SEC
        company_data = fetch_companies_and_filings_by_symbol(symbol, filing_limit=filing_limit, filing_years=filing_years)
        
        # Process the company data
        results = process_company_data(db, company_data)
        
        logger.info(f"Finished processing company {symbol}: {results}")
        db.close()
        return results
    except Exception as e:
        logger.error(f"Error in background task for company {symbol}: {str(e)}")
        if 'db' in locals():
            db.close()
        raise


async def add_demo_companies_task():
    """Add the demo companies (AAPL, MSFT, GOOGL) in the background"""
    logger.info("Starting background task to add demo companies")
    try:
        # Create a new database session for the background task
        db = SessionLocal()
        
        # Fetch only the first 3 demo companies (Apple, Microsoft, Google)
        company_data = fetch_companies_and_filings(mode='DEMO', filing_limit=2)
        
        # Process the company data
        results = process_company_data(db, company_data)
        
        logger.info(f"Finished processing demo companies: {results}")
        db.close()
        return results
    except Exception as e:
        logger.error(f"Error in background task for demo companies: {str(e)}")
        if 'db' in locals():
            db.close()
        raise
