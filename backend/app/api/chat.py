from fastapi import APIRouter, Depends, HTTPException, Body
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import uuid
import logging
import json
import asyncio

from ..db.database import get_db
from ..db import crud
from ..models.chat_models import ChatRequest, ChatResponse
from ..services.rag_service import get_similar_documents, generate_chat_response
from ..core.config import settings

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    """
    Send a message to the chat system and get a response.
    
    This endpoint:
    1. Takes the user's message
    2. Retrieves relevant documents from the database
    3. Generates a response using the OpenAI chat model
    4. Returns the response along with the sources used
    
    Parameters:
    - message: The user's question or message
    - session_id: Optional session ID for conversation history
    - ticker: Optional filter by company ticker
    - year: Optional filter by filing year
    - document_type: Optional filter by document type
    - model: Optional chat model to use
    
    Returns:
    - Generated response with sources used
    """
    try:
        # Log request
        logger.info(f"Chat request: '{request.message}'")
        
        # Generate a session ID if not provided
        session_id = request.session_id or str(uuid.uuid4())
        
        # Get similar documents
        similar_docs = await get_similar_documents(
            db=db,
            query=request.message,
            ticker=request.ticker,
            year=request.year,
            document_type=request.document_type,
            k=5
        )
        
        # Generate response
        response, sources = await generate_chat_response(
            query=request.message,
            documents=similar_docs,
            model=request.model
        )
        
        # Save to chat history if session ID is provided
        if request.session_id:
            # Create metadata with sources
            metadata = {"sources": sources}
            
            # Save to chat history
            crud.save_chat_history(
                db=db,
                session_id=session_id,
                user_message=request.message,
                assistant_message=response,
                metadata=metadata
            )
        
        # Log response summary
        logger.info(f"Chat response: {len(response)} characters, {len(sources)} sources")
        
        # Return response
        return ChatResponse(
            message=response,
            sources=sources,
            session_id=session_id
        )
    
    except Exception as e:
        # Log error
        logger.error(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating chat response: {str(e)}")

@router.post("/chat/stream")
async def chat_stream(request: ChatRequest = Body(...), db: Session = Depends(get_db)):
    """
    Send a message to the chat system and get a streaming response.
    
    This endpoint works similar to the regular chat endpoint, but streams the response
    as it's being generated, using server-sent events (SSE).
    
    Note: This is a mock implementation for now, as true streaming requires
    integration with specific LLM provider SDKs.
    """
    async def event_generator():
        try:
            # Generate a session ID if not provided
            session_id = request.session_id or str(uuid.uuid4())
            
            # Get similar documents
            similar_docs = await get_similar_documents(
                db=db,
                query=request.message,
                ticker=request.ticker,
                year=request.year,
                document_type=request.document_type,
                k=5
            )
            
            # Send metadata event
            yield f"data: {json.dumps({'type': 'metadata', 'session_id': session_id, 'sources_count': len(similar_docs)})}\n\n"
            
            # Generate response (non-streaming for now)
            response, sources = await generate_chat_response(
                query=request.message,
                documents=similar_docs,
                model=request.model
            )
            
            # Split response into chunks for simulated streaming
            chunks = [response[i:i+20] for i in range(0, len(response), 20)]
            
            # Send each chunk as an event
            for chunk in chunks:
                yield f"data: {json.dumps({'type': 'content', 'content': chunk})}\n\n"
                await asyncio.sleep(0.05)  # Small delay for simulated streaming
            
            # Send sources event
            yield f"data: {json.dumps({'type': 'sources', 'sources': sources})}\n\n"
            
            # Send done event
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            
            # Save to chat history if session ID is provided
            if request.session_id:
                # Create metadata with sources
                metadata = {"sources": sources}
                
                # Save to chat history
                crud.save_chat_history(
                    db=db,
                    session_id=session_id,
                    user_message=request.message,
                    assistant_message=response,
                    metadata=metadata
                )
        
        except Exception as e:
            # Log error
            logger.error(f"Error in chat stream endpoint: {str(e)}")
            # Send error event
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.get("/history")
async def get_history(session_id: str, limit: int = 10, db: Session = Depends(get_db)):
    """
    Get chat history for a session.
    
    Parameters:
    - session_id: The session ID
    - limit: Maximum number of history entries to return
    
    Returns:
    - List of chat history entries
    """
    try:
        # Get chat history
        history = crud.get_chat_history(db, session_id, limit)
        
        # Convert to response format
        history_list = []
        for entry in history:
            history_list.append({
                "id": entry.id,
                "session_id": entry.session_id,
                "user_message": entry.user_message,
                "assistant_message": entry.assistant_message,
                "created_at": entry.created_at,
                "sources": entry.message_metadata.get("sources", []) if entry.message_metadata else []
            })
        
        return {"history": history_list}
    
    except Exception as e:
        # Log error
        logger.error(f"Error in get_history endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting chat history: {str(e)}")