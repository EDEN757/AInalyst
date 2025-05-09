from sqlalchemy.orm import Session
from sqlalchemy.sql import text
from sqlalchemy.exc import IntegrityError
import uuid
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from ..models.database_models import FilingMetadata, DocumentVector, ChatHistory
from ..core.config import settings

def get_or_create_doc_id() -> str:
    """Generate a unique document ID."""
    return str(uuid.uuid4())

def check_text_hash_exists(db: Session, text_hash: str) -> bool:
    """
    Check if a document with the given text hash already exists.
    
    Parameters:
    - db: Database session
    - text_hash: Hash of the document text
    
    Returns:
    - True if a document with the given hash exists, False otherwise
    """
    return db.query(FilingMetadata).filter(FilingMetadata.text_hash == text_hash).first() is not None

def get_document_by_hash(db: Session, text_hash: str) -> Optional[FilingMetadata]:
    """
    Get a document by its text hash.
    
    Parameters:
    - db: Database session
    - text_hash: Hash of the document text
    
    Returns:
    - FilingMetadata object if found, None otherwise
    """
    return db.query(FilingMetadata).filter(FilingMetadata.text_hash == text_hash).first()

def create_filing_metadata(
    db: Session, 
    doc_id: str,
    ticker: str,
    year: int,
    document_type: str,
    filing_date: str,
    section_name: str,
    source_url: str,
    page_number: Optional[int],
    embedding_model: str,
    text_hash: str
) -> FilingMetadata:
    """
    Create a new filing metadata record.
    
    Parameters:
    - db: Database session
    - doc_id: Unique document ID
    - ticker: Company ticker symbol
    - year: Filing year
    - document_type: Type of filing (e.g., 10-K, 10-K/A)
    - filing_date: Date of filing
    - section_name: Name of the section
    - source_url: URL of the source document
    - page_number: Page number in the document
    - embedding_model: Name of the embedding model used
    - text_hash: Hash of the document text
    
    Returns:
    - Created FilingMetadata object
    """
    try:
        # Check if document already exists
        existing = get_document_by_hash(db, text_hash)
        if existing:
            # Return existing document
            return existing
        
        # Create new document
        db_metadata = FilingMetadata(
            doc_id=doc_id,
            ticker=ticker,
            year=year,
            document_type=document_type,
            filing_date=filing_date,
            section_name=section_name,
            source_url=source_url,
            page_number=page_number,
            embedding_model=embedding_model,
            text_hash=text_hash
        )
        db.add(db_metadata)
        db.flush()  # Flush but don't commit yet (for transaction support)
        
        return db_metadata
    
    except IntegrityError as e:
        db.rollback()
        # Handle unique constraint violation
        if "duplicate key value violates unique constraint" in str(e):
            # Try to get the existing document
            existing = get_document_by_hash(db, text_hash)
            if existing:
                return existing
        
        # Re-raise exception if it's not a duplicate key error or if we can't get the existing document
        raise

def create_document_vector(
    db: Session,
    doc_id: str,
    embedding: List[float]
) -> DocumentVector:
    """
    Create a new document vector record.
    
    Parameters:
    - db: Database session
    - doc_id: Unique document ID (must match a record in filings_metadata)
    - embedding: Vector embedding for the document
    
    Returns:
    - Created DocumentVector object
    """
    try:
        # Check if vector already exists
        existing = db.query(DocumentVector).filter(DocumentVector.doc_id == doc_id).first()
        if existing:
            # Return existing vector
            return existing
        
        # Create new vector
        db_vector = DocumentVector(
            doc_id=doc_id,
            embedding=embedding
        )
        db.add(db_vector)
        db.flush()  # Flush but don't commit yet (for transaction support)
        
        return db_vector
    
    except IntegrityError as e:
        db.rollback()
        # Handle unique constraint violation
        if "duplicate key value violates unique constraint" in str(e):
            # Try to get the existing vector
            existing = db.query(DocumentVector).filter(DocumentVector.doc_id == doc_id).first()
            if existing:
                return existing
        
        # Re-raise exception if it's not a duplicate key error or if we can't get the existing vector
        raise

def upsert_document_with_embedding(
    db: Session,
    doc_id: str,
    ticker: str,
    year: int,
    document_type: str,
    filing_date: str,
    section_name: str,
    source_url: str,
    text_hash: str,
    embedding: List[float],
    page_number: Optional[int] = None,
    embedding_model: Optional[str] = None,
    commit: bool = True
) -> Tuple[FilingMetadata, DocumentVector]:
    """
    Create or update a document with its embedding in a single transaction.
    
    Parameters:
    - db: Database session
    - doc_id: Unique document ID
    - ticker: Company ticker symbol
    - year: Filing year
    - document_type: Type of filing (e.g., 10-K, 10-K/A)
    - filing_date: Date of filing
    - section_name: Name of the section
    - source_url: URL of the source document
    - text_hash: Hash of the document text
    - embedding: Vector embedding for the document
    - page_number: Page number in the document
    - embedding_model: Name of the embedding model used
    - commit: Whether to commit the transaction
    
    Returns:
    - Tuple of (FilingMetadata, DocumentVector)
    """
    try:
        # Use the specified embedding model or default
        embedding_model = embedding_model or settings.DEFAULT_EMBEDDING_MODEL
        
        # Create or get metadata
        metadata = create_filing_metadata(
            db=db,
            doc_id=doc_id,
            ticker=ticker,
            year=year,
            document_type=document_type,
            filing_date=filing_date,
            section_name=section_name,
            source_url=source_url,
            page_number=page_number,
            embedding_model=embedding_model,
            text_hash=text_hash
        )
        
        # Create or get vector
        vector = create_document_vector(
            db=db,
            doc_id=doc_id,
            embedding=embedding
        )
        
        # Commit if requested
        if commit:
            db.commit()
        
        return metadata, vector
    
    except Exception as e:
        db.rollback()
        raise

def get_document_text(db: Session, doc_id: str) -> Optional[str]:
    """
    Get the text of a document by its ID.
    
    Parameters:
    - db: Database session
    - doc_id: Unique document ID
    
    Returns:
    - Document text if found, None otherwise
    """
    # Execute raw SQL query to fetch text
    query = """
    SELECT chunk_text FROM document_chunks
    WHERE doc_id = :doc_id
    """
    result = db.execute(text(query), {"doc_id": doc_id}).first()
    
    return result[0] if result else None

def get_similar_documents(
    db: Session,
    query_embedding: List[float],
    k: int = 5,
    ticker: Optional[str] = None,
    year: Optional[int] = None,
    document_type: Optional[str] = None,
    section_name: Optional[str] = None,
    similarity_threshold: float = 0.5
) -> List[Dict[str, Any]]:
    """
    Get documents similar to the query embedding.
    
    Uses pgvector's cosine similarity search to find the most similar documents.
    Additional filters can be applied based on ticker, year, document type, and section.
    
    Parameters:
    - db: Database session
    - query_embedding: Vector embedding for the query
    - k: Number of similar documents to return
    - ticker: Filter by ticker symbol
    - year: Filter by filing year
    - document_type: Filter by document type
    - section_name: Filter by section name
    - similarity_threshold: Minimum similarity score threshold
    
    Returns:
    - List of similar documents with metadata
    """
    # Start building the query
    query = """
    SELECT 
        fm.doc_id,
        fm.ticker,
        fm.year,
        fm.document_type,
        fm.filing_date,
        fm.section_name,
        fm.source_url,
        fm.page_number,
        dc.chunk_text,
        1 - (dv.embedding <=> :query_embedding) as similarity_score
    FROM 
        document_vectors dv
    JOIN 
        filings_metadata fm ON dv.doc_id = fm.doc_id
    LEFT JOIN
        document_chunks dc ON fm.doc_id = dc.doc_id
    WHERE (1 - (dv.embedding <=> :query_embedding)) > :similarity_threshold
    """
    
    # Add filters if provided
    params = {
        "query_embedding": query_embedding, 
        "k": k,
        "similarity_threshold": similarity_threshold
    }
    
    if ticker:
        query += " AND fm.ticker = :ticker"
        params["ticker"] = ticker
    
    if year:
        query += " AND fm.year = :year"
        params["year"] = year
    
    if document_type:
        query += " AND fm.document_type = :document_type"
        params["document_type"] = document_type
    
    if section_name:
        query += " AND fm.section_name = :section_name"
        params["section_name"] = section_name
    
    # Add order by and limit
    query += """
    ORDER BY similarity_score DESC
    LIMIT :k
    """
    
    # Execute the query
    result = db.execute(text(query), params)
    
    # Convert to list of dictionaries
    similar_docs = []
    for row in result:
        similar_docs.append({
            "doc_id": row.doc_id,
            "ticker": row.ticker,
            "year": row.year,
            "document_type": row.document_type,
            "filing_date": str(row.filing_date) if row.filing_date else None,
            "section_name": row.section_name,
            "source_url": row.source_url,
            "page_number": row.page_number,
            "chunk_text": row.chunk_text,
            "similarity_score": float(row.similarity_score)
        })
    
    return similar_docs

def save_chat_history(
    db: Session,
    session_id: str,
    user_message: str,
    assistant_message: str,
    metadata: Optional[Dict[str, Any]] = None
) -> ChatHistory:
    """
    Save a chat message pair to the history.
    
    Parameters:
    - db: Database session
    - session_id: Chat session ID
    - user_message: Message from the user
    - assistant_message: Response from the assistant
    - metadata: Additional metadata (e.g., sources used)
    
    Returns:
    - Created ChatHistory object
    """
    chat_entry = ChatHistory(
        session_id=session_id,
        user_message=user_message,
        assistant_message=assistant_message,
        metadata=metadata
    )
    db.add(chat_entry)
    db.commit()
    db.refresh(chat_entry)
    return chat_entry

def get_chat_history(
    db: Session,
    session_id: str,
    limit: int = 10
) -> List[ChatHistory]:
    """
    Get the chat history for a session.
    
    Parameters:
    - db: Database session
    - session_id: Chat session ID
    - limit: Maximum number of history entries to return
    
    Returns:
    - List of ChatHistory objects
    """
    return db.query(ChatHistory)\
        .filter(ChatHistory.session_id == session_id)\
        .order_by(ChatHistory.created_at.desc())\
        .limit(limit)\
        .all()