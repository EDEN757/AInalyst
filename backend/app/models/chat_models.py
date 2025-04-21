from pydantic import BaseModel
from typing import List, Optional


class UserQuery(BaseModel):
    query: str
    company_symbols: Optional[List[str]] = None  # Filter by companies if provided
    filing_year: Optional[int] = None  # Filter by filing year if provided


class ChatResponse(BaseModel):
    answer: str
    sources: List[str] = []  # References to the source documents
