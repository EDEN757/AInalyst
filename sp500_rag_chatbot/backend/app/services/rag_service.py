from typing import List, Dict, Optional
from sqlalchemy.orm import Session

from ..core.config import settings
from ..db import crud
from ..models.chat_models import UserQuery, ChatResponse
from . import llm_clients


def generate_answer(db: Session, user_query: UserQuery) -> ChatResponse:
    """Generate an answer to a user query using RAG (Retrieval-Augmented Generation).
    
    Args:
        db: Database session
        user_query: The query from the user
        
    Returns:
        A ChatResponse object containing the answer and sources
    """
    # 1. Generate query embedding using the EMBEDDING configuration
    query_embedding = llm_clients.get_embedding(user_query.query, settings)
    
    # 2. Perform vector search to find relevant chunks
    relevant_chunks = crud.search_chunks_by_embedding(
        db=db,
        query_embedding=query_embedding,
        company_symbol=user_query.company_symbol,
        filing_year=user_query.filing_year,
        limit=settings.RAG_TOP_K
    )
    
    if not relevant_chunks:
        # No relevant information found
        return ChatResponse(
            answer="I couldn't find any relevant information for your query. Please try asking something about S&P 500 companies' 10-K filings."
        )
    
    # 3. Prepare context from retrieved chunks
    context_parts = []
    sources = []
    
    for chunk in relevant_chunks:
        # Add source information
        filing = chunk.filing
        company = filing.company
        
        source_info = f"{company.name} ({company.symbol}) - {filing.filing_type} {filing.fiscal_year}"
        if source_info not in sources:
            sources.append(source_info)
        
        # Add chunk text with metadata to context
        context_parts.append(
            f"Source: {source_info}\n" +
            f"Section: {chunk.section or 'N/A'}\n" +
            f"Content: {chunk.text_content}\n"
        )
    
    context = "\n---\n".join(context_parts)
    
    # 4. Generate answer using the CHAT configuration
    prompt = (
        "You are a financial analyst assistant that provides information from company SEC filings. " +
        "Answer the user's question based ONLY on the context provided. " +
        "If the context doesn't contain the relevant information, say that you don't have enough information to answer. " +
        "Don't make up any information. Be clear, concise, and informative. " +
        "Format your answers in plain text with line breaks for readability."
    )
    
    answer = llm_clients.generate_chat_response(
        prompt=prompt, 
        context=context, 
        query=user_query.query,
        config=settings
    )
    
    return ChatResponse(
        answer=answer,
        sources=sources
    )
