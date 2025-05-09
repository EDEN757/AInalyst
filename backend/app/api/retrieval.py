from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

from ..db.database import get_db
from ..db import crud
from ..models.chat_models import RetrieveQuery, RetrieveResponse, RetrieveResult
from ..services.rag_service import get_similar_documents
from ..core.config import settings

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/retrieve", response_model=RetrieveResponse)
async def retrieve(
    q: str = Query(..., description="The query to search for"),
    k: int = Query(5, description="Number of results to return", ge=1, le=50),
    ticker: Optional[str] = Query(None, description="Filter by ticker"),
    year: Optional[int] = Query(None, description="Filter by year"),
    document_type: Optional[str] = Query(None, description="Filter by document type"),
    section_name: Optional[str] = Query(None, description="Filter by section name"),
    similarity_threshold: float = Query(0.5, description="Minimum similarity score threshold", ge=0.0, le=1.0),
    db: Session = Depends(get_db)
):
    """
    Retrieve documents similar to the query.
    
    This endpoint:
    1. Takes a query and optional filters
    2. Converts the query to an embedding vector
    3. Performs vector similarity search in the database
    4. Returns the most similar documents
    
    Parameters:
    - q: The query text
    - k: Number of results to return (default: 5)
    - ticker: Filter by company ticker
    - year: Filter by filing year
    - document_type: Filter by document type (e.g., "10-K", "10-K/A")
    - section_name: Filter by section name
    - similarity_threshold: Minimum similarity score threshold (default: 0.5)
    
    Returns:
    - List of similar documents with metadata and text
    """
    try:
        # Log request
        logger.info(f"Retrieval request: query='{q}', ticker={ticker}, year={year}, document_type={document_type}")
        
        # Convert query to RetrieveQuery model
        query = RetrieveQuery(
            query=q,
            k=k,
            ticker=ticker,
            year=year,
            document_type=document_type
        )
        
        # Get similar documents
        similar_docs = await get_similar_documents(
            db=db,
            query=query.query,
            ticker=query.ticker,
            year=query.year,
            document_type=query.document_type,
            section_name=section_name,
            k=query.k,
            similarity_threshold=similarity_threshold
        )
        
        # Convert to RetrieveResult models
        results = []
        for doc in similar_docs:
            result = RetrieveResult(
                doc_id=doc["doc_id"],
                ticker=doc["ticker"],
                year=doc["year"],
                document_type=doc["document_type"],
                filing_date=doc["filing_date"],
                section_name=doc["section_name"],
                source_url=doc["source_url"],
                page_number=doc["page_number"],
                similarity_score=doc["similarity_score"],
                chunk_text=doc.get("chunk_text", "")
            )
            results.append(result)
        
        # Log response summary
        logger.info(f"Retrieval response: found {len(results)} documents")
        
        # Return response
        return RetrieveResponse(results=results)
    
    except Exception as e:
        # Log error
        logger.error(f"Error in retrieve endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving documents: {str(e)}")

@router.post("/retrieve", response_model=RetrieveResponse)
async def retrieve_post(query: RetrieveQuery, db: Session = Depends(get_db)):
    """
    Retrieve documents similar to the query (POST method).
    
    This endpoint works the same as the GET method but accepts a JSON body.
    """
    try:
        # Log request
        logger.info(f"Retrieval request (POST): query='{query.query}', ticker={query.ticker}, year={query.year}")
        
        # Get similar documents
        similar_docs = await get_similar_documents(
            db=db,
            query=query.query,
            ticker=query.ticker,
            year=query.year,
            document_type=query.document_type,
            k=query.k
        )
        
        # Convert to RetrieveResult models
        results = []
        for doc in similar_docs:
            result = RetrieveResult(
                doc_id=doc["doc_id"],
                ticker=doc["ticker"],
                year=doc["year"],
                document_type=doc["document_type"],
                filing_date=doc["filing_date"],
                section_name=doc["section_name"],
                source_url=doc["source_url"],
                page_number=doc["page_number"],
                similarity_score=doc["similarity_score"],
                chunk_text=doc.get("chunk_text", "")
            )
            results.append(result)
        
        # Log response summary
        logger.info(f"Retrieval response: found {len(results)} documents")
        
        # Return response
        return RetrieveResponse(results=results)
    
    except Exception as e:
        # Log error
        logger.error(f"Error in retrieve endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving documents: {str(e)}")