from sqlalchemy import Column, String, Integer, Date, Text, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import JSONB, ARRAY, FLOAT
from sqlalchemy.sql import func
from ..db.database import Base

class FilingMetadata(Base):
    """SQLAlchemy model for filings_metadata table."""
    __tablename__ = "filings_metadata"
    
    doc_id = Column(String(255), primary_key=True, index=True)
    ticker = Column(String(10), nullable=False, index=True)
    year = Column(Integer, nullable=False, index=True)
    document_type = Column(String(10), default="10-K", index=True)
    filing_date = Column(Date, index=True)
    section_name = Column(Text, index=True)
    source_url = Column(Text)
    page_number = Column(Integer)
    embedding_model = Column(String(50))
    text_hash = Column(String(32), nullable=False, index=True)
    ingested_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        UniqueConstraint('ticker', 'year', 'document_type', 'section_name', 'text_hash', name='unique_filing_chunk'),
        Index('idx_filings_metadata_ticker_year', 'ticker', 'year'),
        Index('idx_filings_metadata_ticker_year_type', 'ticker', 'year', 'document_type'),
    )

class DocumentVector(Base):
    """SQLAlchemy model for document_vectors table."""
    __tablename__ = "document_vectors"
    
    doc_id = Column(String(255), ForeignKey("filings_metadata.doc_id", ondelete="CASCADE"), primary_key=True)
    # Note: We're using ARRAY(FLOAT) here as a placeholder
    # The actual pgvector type is handled by the database
    embedding = Column(ARRAY(FLOAT(precision=53)), nullable=False)
    
    # Define table arguments for pgvector index
    # This is commented out here because the index is created in the SQL migration script
    # __table_args__ = (
    #     Index('idx_hnsw_embedding', 'embedding', postgresql_using='hnsw', postgresql_with={'m': 16, 'ef_construction': 64}),
    # )

class DocumentChunk(Base):
    """SQLAlchemy model for document_chunks table to store the actual text content."""
    __tablename__ = "document_chunks"
    
    doc_id = Column(String(255), ForeignKey("filings_metadata.doc_id", ondelete="CASCADE"), primary_key=True)
    chunk_text = Column(Text, nullable=False)
    chunk_number = Column(Integer)
    total_chunks = Column(Integer)
    
    __table_args__ = (
        Index('idx_document_chunks_doc_id', 'doc_id'),
    )

class ChatHistory(Base):
    """SQLAlchemy model for chat_history table."""
    __tablename__ = "chat_history"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), nullable=False, index=True)
    user_message = Column(Text, nullable=False)
    assistant_message = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    metadata = Column(JSONB)
    
    __table_args__ = (
        Index('idx_chat_history_session_id_created_at', 'session_id', 'created_at'),
    )