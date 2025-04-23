from typing import List, Optional
import os
from ..core.config import Settings

# Import the necessary libraries based on provider
try:
    import openai
except ImportError:
    openai = None

try:
    import google.generativeai as genai
except ImportError:
    genai = None

try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None


def get_embedding(text: str, config: Settings) -> List[float]:
    """Generate an embedding vector using the configured embedding provider and model.
    
    Args:
        text: The text to embed
        config: The application configuration
        
    Returns:
        A list of floating point numbers representing the embedding vector
        
    Raises:
        ValueError: If the embedding provider is not supported or API key is missing
        Exception: If the API call fails
    """
    if not text.strip():
        raise ValueError("Text cannot be empty for embedding generation")
    
    # Use OpenAI embeddings
    if config.EMBEDDING_PROVIDER == "OPENAI":
        if not openai:
            raise ImportError("OpenAI package is not installed. Run 'pip install openai'")
        
        try:
            # Use the updated OpenAI client (v1.0+)
            client = openai.OpenAI(api_key=config.OPENAI_API_KEY)
            
            response = client.embeddings.create(
                input=text,
                model=config.EMBEDDING_MODEL
            )
            embedding = response.data[0].embedding
            
            # Validate dimension
            if len(embedding) != config.EMBEDDING_DIMENSION:
                raise ValueError(
                    f"Received embedding dimension {len(embedding)} does not match "
                    f"configured dimension {config.EMBEDDING_DIMENSION}"
                )
                
            return embedding
        
        except Exception as e:
            raise Exception(f"Error generating OpenAI embedding: {str(e)}")
    
    # Use Google Gemini embeddings
    elif config.EMBEDDING_PROVIDER == "GEMINI":
        if not genai:
            raise ImportError("Google Generative AI package is not installed. Run 'pip install google-generativeai'")
        
        # Configure API key
        genai.configure(api_key=config.GOOGLE_API_KEY)
        
        try:
            embedding_model = genai.get_model(config.EMBEDDING_MODEL)
            result = embedding_model.embed_content(content=text)
            embedding = result["embedding"]
            
            # Validate dimension
            if len(embedding) != config.EMBEDDING_DIMENSION:
                raise ValueError(
                    f"Received embedding dimension {len(embedding)} does not match "
                    f"configured dimension {config.EMBEDDING_DIMENSION}"
                )
                
            return embedding
            
        except Exception as e:
            raise Exception(f"Error generating Google Gemini embedding: {str(e)}")
    
    else:
        raise ValueError(f"Unsupported embedding provider: {config.EMBEDDING_PROVIDER}")


def generate_chat_response(prompt: str, context: str, query: str, config: Settings, conversation_context: str = "") -> str:
    """Generate a chat response using the configured chat provider and model.
    
    Args:
        prompt: The system prompt/instructions for the model
        context: The retrieved documents/context to inform the response
        query: The user query
        config: The application configuration
        conversation_context: Optional previous conversation context
        
    Returns:
        The generated text response
        
    Raises:
        ValueError: If the chat provider is not supported or API key is missing
        Exception: If the API call fails
    """
    
    # Use OpenAI for chat generation
    if config.CHAT_PROVIDER == "OPENAI":
        if not openai:
            raise ImportError("OpenAI package is not installed. Run 'pip install openai'")
        
        try:
            # Create OpenAI client with new API style
            client = openai.OpenAI(api_key=config.OPENAI_API_KEY)
            
            user_content = f"{conversation_context}Context:\n{context}\n\nUser Query: {query}"
            
            response = client.chat.completions.create(
                model=config.CHAT_MODEL,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": user_content}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            raise Exception(f"Error generating OpenAI chat response: {str(e)}")
    
    # Use Google Gemini for chat generation
    elif config.CHAT_PROVIDER == "GEMINI":
        if not genai:
            raise ImportError("Google Generative AI package is not installed. Run 'pip install google-generativeai'")
        
        # Configure API key
        genai.configure(api_key=config.GOOGLE_API_KEY)
        
        try:
            full_prompt = f"{prompt}\n\n{conversation_context}Context:\n{context}\n\nUser Query: {query}\n\nAnswer:"
            
            model = genai.GenerativeModel(config.CHAT_MODEL)
            response = model.generate_content(full_prompt)
            
            return response.text.strip()
            
        except Exception as e:
            raise Exception(f"Error generating Google Gemini chat response: {str(e)}")
    
    # Use Anthropic Claude for chat generation
    elif config.CHAT_PROVIDER == "CLAUDE":
        if not Anthropic:
            raise ImportError("Anthropic package is not installed. Run 'pip install anthropic'")
        
        try:
            client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
            
            user_content = f"{conversation_context}Context:\n{context}\n\nUser Query: {query}"
            
            response = client.messages.create(
                model=config.CHAT_MODEL,
                max_tokens=500,
                temperature=0.3,
                system=prompt,
                messages=[
                    {"role": "user", "content": user_content}
                ]
            )
            
            return response.content[0].text.strip()
            
        except Exception as e:
            raise Exception(f"Error generating Anthropic Claude chat response: {str(e)}")
    
    else:
        raise ValueError(f"Unsupported chat provider: {config.CHAT_PROVIDER}")
