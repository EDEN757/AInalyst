from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

class RetrieveQuery(BaseModel):
    """Model for retrieve query."""
    query: str = Field(..., description="The query to search for")
    k: int = Field(5, description="Number of results to return", ge=1, le=50)
    ticker: Optional[str] = Field(None, description="Filter by ticker")
    year: Optional[int] = Field(None, description="Filter by year")
    document_type: Optional[str] = Field(None, description="Filter by document type")
    section_name: Optional[str] = Field(None, description="Filter by section name")
    similarity_threshold: Optional[float] = Field(0.5, description="Minimum similarity score threshold", ge=0.0, le=1.0)

class RetrieveResult(BaseModel):
    """Model for a single retrieve result."""
    doc_id: str
    ticker: str
    year: int
    document_type: str
    filing_date: Optional[str]
    section_name: Optional[str]
    source_url: Optional[str]
    page_number: Optional[int]
    similarity_score: float
    chunk_text: Optional[str] = None
    
class RetrieveResponse(BaseModel):
    """Model for retrieve response."""
    results: List[RetrieveResult]

class ChatRequest(BaseModel):
    """Model for chat request."""
    message: str = Field(..., description="User message")
    session_id: Optional[str] = Field(None, description="Session ID for conversation history")
    ticker: Optional[str] = Field(None, description="Filter by ticker")
    year: Optional[int] = Field(None, description="Filter by year")
    document_type: Optional[str] = Field(None, description="Filter by document type")
    section_name: Optional[str] = Field(None, description="Filter by section name")
    model: Optional[str] = Field(None, description="Chat model to use")
    max_tokens: Optional[int] = Field(1000, description="Maximum tokens in response", ge=50, le=4000)
    temperature: Optional[float] = Field(0.2, description="Sampling temperature (0.0 to 1.0)", ge=0.0, le=1.0)

class ChatSource(BaseModel):
    """Model for a chat source."""
    ticker: str
    year: int
    document_type: str
    section: Optional[str]
    similarity_score: float
    url: Optional[str]

class ChatMessage(BaseModel):
    """Model for a chat message."""
    role: str
    content: str

class ChatResponse(BaseModel):
    """Model for chat response."""
    message: str
    sources: List[Dict[str, Any]]
    session_id: str

class ChatHistoryItem(BaseModel):
    """Model for a chat history item."""
    id: int
    session_id: str
    user_message: str
    assistant_message: str
    created_at: datetime
    sources: List[Dict[str, Any]]

class ChatHistoryResponse(BaseModel):
    """Model for chat history response."""
    history: List[ChatHistoryItem]