from pydantic import BaseModel
from typing import List, Optional


class UserQuery(BaseModel):
    query: str
    company_symbol: Optional[str] = None  # Filter by company if provided
    filing_year: Optional[int] = None  # Filter by filing year if provided


class ChatResponse(BaseModel):
    answer: str
    sources: List[str] = []  # References to the source documents
