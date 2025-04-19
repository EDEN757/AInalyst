from sqlalchemy import Column, Integer, String, ForeignKey, Text, Float, Boolean, DateTime, func
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from ..db.database import Base
from ..core.config import settings


class Company(Base):
    __tablename__ = "companies"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, unique=True, index=True)
    name = Column(String)
    sector = Column(String)
    industry = Column(String)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    filings = relationship("Filing", back_populates="company")


class Filing(Base):
    __tablename__ = "filings"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"))
    filing_type = Column(String)  # 10-K, 10-Q, etc.
    filing_date = Column(DateTime)
    filing_url = Column(String)
    accession_number = Column(String, unique=True, index=True)
    fiscal_year = Column(Integer)
    fiscal_period = Column(String)  # Q1, Q2, Q3, Q4, FY
    processed = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    company = relationship("Company", back_populates="filings")
    chunks = relationship("TextChunk", back_populates="filing")


class TextChunk(Base):
    __tablename__ = "text_chunks"
    
    id = Column(Integer, primary_key=True, index=True)
    filing_id = Column(Integer, ForeignKey("filings.id"))
    chunk_index = Column(Integer)  # To maintain order
    text_content = Column(Text)
    section = Column(String)  # e.g., "Item 1. Business", "Item 1A. Risk Factors", etc.
    page_number = Column(Integer, nullable=True)
    embedded = Column(Boolean, default=False)  # Flag to track if this chunk has an embedding
    embedding = Column(Vector(settings.EMBEDDING_DIMENSION), nullable=True)  # Vector embedding of chunk
    created_at = Column(DateTime, server_default=func.now())
    
    filing = relationship("Filing", back_populates="chunks")
