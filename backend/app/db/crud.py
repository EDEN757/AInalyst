from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Dict, Any, Optional

from ..models.database_models import Company, Filing, TextChunk
from ..core.config import settings


# Company operations
def create_company(db: Session, symbol: str, name: str, sector: str = None, industry: str = None) -> Company:
    company = Company(symbol=symbol, name=name, sector=sector, industry=industry)
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


def get_company_by_symbol(db: Session, symbol: str) -> Optional[Company]:
    return db.query(Company).filter(Company.symbol == symbol).first()


def get_companies(db: Session, skip: int = 0, limit: int = 100) -> List[Company]:
    return db.query(Company).order_by(Company.symbol).offset(skip).limit(limit).all()


# Filing operations
def create_filing(
    db: Session,
    company_id: int,
    filing_type: str,
    filing_date: Any,
    filing_url: str,
    accession_number: str,
    fiscal_year: int,
    fiscal_period: str
) -> Filing:
    filing = Filing(
        company_id=company_id,
        filing_type=filing_type,
        filing_date=filing_date,
        filing_url=filing_url,
        accession_number=accession_number,
        fiscal_year=fiscal_year,
        fiscal_period=fiscal_period
    )
    db.add(filing)
    db.commit()
    db.refresh(filing)
    return filing


def get_filing_by_accession(db: Session, accession_number: str) -> Optional[Filing]:
    return db.query(Filing).filter(Filing.accession_number == accession_number).first()


def mark_filing_as_processed(db: Session, filing_id: int) -> Filing:
    filing = db.query(Filing).filter(Filing.id == filing_id).first()
    if filing:
        filing.processed = True
        db.commit()
        db.refresh(filing)
    return filing


# TextChunk operations
def create_text_chunk(
    db: Session, 
    filing_id: int, 
    chunk_index: int,
    text_content: str,
    section: str = None,
    page_number: int = None
) -> TextChunk:
    chunk = TextChunk(
        filing_id=filing_id,
        chunk_index=chunk_index,
        text_content=text_content,
        section=section,
        page_number=page_number
    )
    db.add(chunk)
    db.commit()
    db.refresh(chunk)
    return chunk


def get_unembedded_chunks(db: Session, limit: int = 100) -> List[TextChunk]:
    """Get chunks that haven't been embedded yet"""
    return db.query(TextChunk).filter(TextChunk.embedded == False).limit(limit).all()


def update_chunk_embedding(db: Session, chunk_id: int, embedding: List[float]) -> TextChunk:
    """Update a chunk with its embedding vector and mark it as embedded"""
    chunk = db.query(TextChunk).filter(TextChunk.id == chunk_id).first()
    if chunk:
        chunk.embedding = embedding
        chunk.embedded = True
        db.commit()
        db.refresh(chunk)
    return chunk


def search_chunks_by_embedding(
    db: Session, 
    query_embedding: List[float],
    company_symbols: Optional[List[str]] = None,
    filing_year: Optional[int] = None,
    limit: int = settings.RAG_TOP_K
) -> List[TextChunk]:
    """Search for chunks by embedding similarity, with optional filters"""
    query = db.query(
        TextChunk, 
        TextChunk.embedding.cosine_distance(query_embedding).label("distance")
    ).filter(TextChunk.embedded == True)
    
    # Track if we've already joined the tables
    tables_joined = False
    
    # Apply filters if provided
    if company_symbols and len(company_symbols) > 0:
        query = query.join(Filing, TextChunk.filing_id == Filing.id) \
                 .join(Company, Filing.company_id == Company.id) \
                 .filter(Company.symbol.in_(company_symbols))
        tables_joined = True
    
    if filing_year:
        if not tables_joined:  # Only need to join if we haven't already
            query = query.join(Filing, TextChunk.filing_id == Filing.id)
        query = query.filter(Filing.fiscal_year == filing_year)
    
    # Order by similarity (lower distance = more similar)
    query = query.order_by("distance")
    
    # Limit results
    chunks = query.limit(limit).all()
    
    # Return just the TextChunk objects (not the distance)
    return [chunk for chunk, distance in chunks]
