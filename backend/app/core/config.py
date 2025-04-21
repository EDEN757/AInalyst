from typing import Optional, Literal
from pydantic import validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database settings
    DATABASE_URL: str
    
    # Application mode
    APP_MODE: Literal["DEMO", "FULL"] = "DEMO"
    
    # Embedding configuration (used for BOTH documents and queries)
    EMBEDDING_PROVIDER: Literal["OPENAI", "GEMINI"] = "OPENAI"
    EMBEDDING_MODEL: str = "text-embedding-ada-002"
    EMBEDDING_DIMENSION: int = 1536  # Must match the output dimension of the chosen model
    
    # Chat generation configuration (used ONLY for final answer generation)
    CHAT_PROVIDER: Literal["OPENAI", "GEMINI", "CLAUDE"] = "OPENAI"
    CHAT_MODEL: str = "gpt-3.5-turbo"
    
    # API keys
    OPENAI_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    
    # SEC data fetching
    SEC_EMAIL: str = "your_email@example.com"
    
    # Number of chunks to retrieve for RAG
    RAG_TOP_K: int = 5
    
    @validator("OPENAI_API_KEY", "GOOGLE_API_KEY", "ANTHROPIC_API_KEY", pre=True)
    def validate_api_keys(cls, v, values, info):
        return v
    
    @validator("EMBEDDING_DIMENSION")
    def validate_embedding_dimension(cls, v, values, info):
        # Known dimensions for specific models
        model_dimensions = {
            "text-embedding-ada-002": 1536,
            "models/embedding-001": 768,
            # Add more models as needed
        }
        
        model = values.get("EMBEDDING_MODEL")
        if model in model_dimensions and v != model_dimensions[model]:
            raise ValueError(
                f"EMBEDDING_DIMENSION {v} does not match expected dimension "
                f"{model_dimensions[model]} for model {model}"
            )
        return v
    
    @validator("OPENAI_API_KEY", "GOOGLE_API_KEY", "ANTHROPIC_API_KEY")
    def validate_required_api_keys(cls, v, values, info):
        field_name = info.field_name
        
        # Check if OpenAI API key is provided when OpenAI is used
        if field_name == "OPENAI_API_KEY" and (
            values.get("EMBEDDING_PROVIDER") == "OPENAI" or 
            values.get("CHAT_PROVIDER") == "OPENAI"
        ) and not v:
            raise ValueError("OPENAI_API_KEY is required when using OpenAI services")
        
        # Check if Google API key is provided when Gemini is used
        if field_name == "GOOGLE_API_KEY" and (
            values.get("EMBEDDING_PROVIDER") == "GEMINI" or 
            values.get("CHAT_PROVIDER") == "GEMINI"
        ) and not v:
            raise ValueError("GOOGLE_API_KEY is required when using Gemini services")
        
        # Check if Anthropic API key is provided when Claude is used
        if field_name == "ANTHROPIC_API_KEY" and (
            values.get("CHAT_PROVIDER") == "CLAUDE"
        ) and not v:
            raise ValueError("ANTHROPIC_API_KEY is required when using Claude services")
        
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
