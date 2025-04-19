from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db.database import get_db
from ..models.chat_models import UserQuery, ChatResponse
from ..services.rag_service import generate_answer

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(query: UserQuery, db: Session = Depends(get_db)):
    """Endpoint for the RAG chatbot interaction"""
    try:
        return generate_answer(db=db, user_query=query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
