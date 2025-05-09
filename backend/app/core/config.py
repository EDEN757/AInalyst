from typing import Optional, Literal, Any, Dict
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database settings
    DATABASE_URL: str

    # Application mode (kept for backward compatibility)
    APP_MODE: Literal["CSV_ONLY"] = "CSV_ONLY"
    
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
    SEC_API_KEY: Optional[str] = None

    # Number of chunks to retrieve for RAG
    RAG_TOP_K: int = 5
    
    @field_validator("EMBEDDING_DIMENSION")
    def validate_embedding_dimension(cls, v: int, info: Any) -> int:
        # Known dimensions for specific models
        model_dimensions = {
            "text-embedding-ada-002": 1536,
            "models/embedding-001": 768,
            # Add more models as needed
        }
        
        # Get values from the model being validated
        values = info.data
        
        model = values.get("EMBEDDING_MODEL")
        if model in model_dimensions and v != model_dimensions[model]:
            raise ValueError(
                f"EMBEDDING_DIMENSION {v} does not match expected dimension "
                f"{model_dimensions[model]} for model {model}"
            )
        return v
    
    @model_validator(mode='after')
    def validate_api_keys(self) -> 'Settings':
        """Validate that the appropriate API keys are provided based on providers selected."""
        
        # Check if OpenAI API key is provided when OpenAI is used
        if (self.EMBEDDING_PROVIDER == "OPENAI" or self.CHAT_PROVIDER == "OPENAI") and not self.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required when using OpenAI services")
        
        # Check if Google API key is provided when Gemini is used
        if (self.EMBEDDING_PROVIDER == "GEMINI" or self.CHAT_PROVIDER == "GEMINI") and not self.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY is required when using Gemini services")
        
        # Check if Anthropic API key is provided when Claude is used
        if self.CHAT_PROVIDER == "CLAUDE" and not self.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY is required when using Claude services")
        
        return self
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
