from pydantic import BaseModel
from typing import List, Optional, Dict


class Message(BaseModel):
    role: str  # 'user' or 'assistant'
    content: str


class UserQuery(BaseModel):
    query: str
    company_symbols: Optional[List[str]] = None  # Filter by companies if provided
    filing_year: Optional[int] = None  # Filter by filing year if provided
    previous_message: Optional[Message] = None  # Previous message in the conversation
    previous_response: Optional[Message] = None  # Previous response in the conversation


class ChatResponse(BaseModel):
    answer: str
    sources: List[str] = []  # References to the source documents
