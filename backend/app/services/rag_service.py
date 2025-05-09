from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional, Tuple
import hashlib
import logging

from .llm_clients import create_embedding, create_embedding_sync, generate_completion
from ..db import crud
from ..core.config import settings

# Configure logging
logger = logging.getLogger(__name__)

async def get_similar_documents(
    db: Session,
    query: str,
    ticker: Optional[str] = None,
    year: Optional[int] = None,
    document_type: Optional[str] = None,
    section_name: Optional[str] = None,
    k: int = 5,
    similarity_threshold: float = 0.5
) -> List[Dict[str, Any]]:
    """
    Get documents similar to the query.
    
    Parameters:
    - db: Database session
    - query: The query text
    - ticker: Optional filter by ticker
    - year: Optional filter by year
    - document_type: Optional filter by document type
    - section_name: Optional filter by section name
    - k: Number of results to return
    - similarity_threshold: Minimum similarity score threshold
    
    Returns:
    - List of similar documents with their metadata and text
    """
    try:
        # Create embedding for the query
        query_embedding = await create_embedding(query, settings.DEFAULT_EMBEDDING_MODEL)
        
        # Get similar documents from the database
        similar_docs = crud.get_similar_documents(
            db=db,
            query_embedding=query_embedding,
            k=k,
            ticker=ticker,
            year=year,
            document_type=document_type,
            section_name=section_name,
            similarity_threshold=similarity_threshold
        )
        
        # Log the results
        logger.info(f"Retrieved {len(similar_docs)} similar documents for query: '{query}'")
        if len(similar_docs) > 0:
            avg_similarity = sum(doc["similarity_score"] for doc in similar_docs) / len(similar_docs)
            logger.info(f"Average similarity score: {avg_similarity:.4f}")
        
        return similar_docs
    
    except Exception as e:
        logger.error(f"Error getting similar documents: {str(e)}")
        # Return empty list in case of error
        return []

def get_similar_documents_sync(
    db: Session,
    query: str,
    ticker: Optional[str] = None,
    year: Optional[int] = None,
    document_type: Optional[str] = None,
    section_name: Optional[str] = None,
    k: int = 5,
    similarity_threshold: float = 0.5
) -> List[Dict[str, Any]]:
    """
    Get documents similar to the query (synchronous version).
    
    Parameters:
    - db: Database session
    - query: The query text
    - ticker: Optional filter by ticker
    - year: Optional filter by year
    - document_type: Optional filter by document type
    - section_name: Optional filter by section name
    - k: Number of results to return
    - similarity_threshold: Minimum similarity score threshold
    
    Returns:
    - List of similar documents with their metadata and text
    """
    try:
        # Create embedding for the query
        query_embedding = create_embedding_sync(query, settings.DEFAULT_EMBEDDING_MODEL)
        
        # Get similar documents from the database
        similar_docs = crud.get_similar_documents(
            db=db,
            query_embedding=query_embedding,
            k=k,
            ticker=ticker,
            year=year,
            document_type=document_type,
            section_name=section_name,
            similarity_threshold=similarity_threshold
        )
        
        # Log the results
        logger.info(f"Retrieved {len(similar_docs)} similar documents for query: '{query}'")
        if len(similar_docs) > 0:
            avg_similarity = sum(doc["similarity_score"] for doc in similar_docs) / len(similar_docs)
            logger.info(f"Average similarity score: {avg_similarity:.4f}")
        
        return similar_docs
    
    except Exception as e:
        logger.error(f"Error getting similar documents: {str(e)}")
        # Return empty list in case of error
        return []

async def generate_chat_response(
    query: str,
    documents: List[Dict[str, Any]],
    model: Optional[str] = None
) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Generate a chat response based on the query and retrieved documents.
    
    Parameters:
    - query: The user's query
    - documents: The retrieved documents
    - model: Optional chat model to use
    
    Returns:
    - Tuple of (response_text, sources)
    """
    try:
        # Log request
        logger.info(f"Generating chat response for query: '{query}'")
        logger.info(f"Using {len(documents)} context documents")
        
        # Generate completion
        response = await generate_completion(
            prompt=query,
            context=documents,
            model=model or settings.DEFAULT_CHAT_MODEL
        )
        
        # Prepare sources for the response
        sources = []
        for doc in documents:
            sources.append({
                "ticker": doc["ticker"],
                "year": doc["year"],
                "document_type": doc["document_type"],
                "section": doc.get("section_name", ""),
                "similarity_score": doc["similarity_score"],
                "url": doc.get("source_url", "")
            })
        
        # Log response summary
        logger.info(f"Generated response of length {len(response)} characters")
        
        return response, sources
    
    except Exception as e:
        logger.error(f"Error generating chat response: {str(e)}")
        # Return error message
        error_message = "I'm sorry, but I encountered an error while generating a response. Please try again."
        return error_message, []

def create_text_hash(text: str) -> str:
    """
    Create a hash of the given text.
    
    Parameters:
    - text: The text to hash
    
    Returns:
    - MD5 hash of the text
    """
    return hashlib.md5(text.encode()).hexdigest()