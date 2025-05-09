import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from typing import Optional

# Load environment variables from .env file
load_dotenv()

class Settings(BaseSettings):
    # OpenAI API Configuration
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    # SEC EDGAR API Configuration
    EDGAR_USER_AGENT: str = os.getenv("EDGAR_USER_AGENT", "AInalyst example@youremail.com")
    
    # PostgreSQL Database Configuration
    POSTGRES_URI: str = os.getenv("POSTGRES_URI", "postgresql://postgres:postgres@localhost:5432/finance_rag_db")
    
    # Data and Model Configuration
    COMPANIES_CSV_PATH: str = os.getenv("COMPANIES_CSV_PATH", "./companies.csv")
    DEFAULT_EMBEDDING_MODEL: str = os.getenv("DEFAULT_EMBEDDING_MODEL", "text-embedding-3-small")
    EMBEDDING_DIMENSION: int = int(os.getenv("EMBEDDING_DIMENSION", "1536"))
    DEFAULT_CHAT_MODEL: str = os.getenv("DEFAULT_CHAT_MODEL", "gpt-3.5-turbo")
    
    # API and Logging Configuration
    API_AUTH_KEY: Optional[str] = os.getenv("API_AUTH_KEY")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # API Configuration
    API_PREFIX: str = "/api/v1"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Create settings instance
settings = Settings()