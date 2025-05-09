import openai
from typing import List, Dict, Any, Optional, Union, Tuple
import logging
import time
import asyncio
import numpy as np
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
    retry_if_exception_type
)

from ..core.config import settings

# Configure logging
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(settings.LOG_LEVEL)

# Configure OpenAI client
client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)

# Embedding model dimension for validation
EMBEDDING_DIMENSIONS = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536
}

@retry(
    wait=wait_random_exponential(min=1, max=60),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type((openai.APIError, openai.APIConnectionError, openai.RateLimitError))
)
def create_embedding_sync(
    text: str, 
    model: Optional[str] = None,
    retry_on_empty: bool = True
) -> List[float]:
    """
    Create an embedding for the given text using OpenAI's API (synchronous version).
    
    Parameters:
    - text: The text to embed
    - model: The embedding model to use (defaults to setting in config)
    - retry_on_empty: Whether to retry with dummy text if input is empty
    
    Returns:
    - List of floats representing the embedding vector
    """
    try:
        # Check for empty text
        if not text or len(text.strip()) == 0:
            if retry_on_empty:
                logger.warning("Empty text provided for embedding, using placeholder text")
                text = "Empty document placeholder"
            else:
                logger.error("Empty text provided for embedding")
                # Return zero vector of appropriate dimension
                embedding_model = model or settings.DEFAULT_EMBEDDING_MODEL
                dim = EMBEDDING_DIMENSIONS.get(embedding_model, settings.EMBEDDING_DIMENSION)
                return [0.0] * dim
        
        # Use the specified model or default
        embedding_model = model or settings.DEFAULT_EMBEDDING_MODEL
        
        # Create the embedding
        response = client.embeddings.create(
            model=embedding_model,
            input=text,
            encoding_format="float"
        )
        
        # Extract the embedding vector
        embedding = response.data[0].embedding
        
        # Validate embedding dimension
        expected_dim = EMBEDDING_DIMENSIONS.get(embedding_model, settings.EMBEDDING_DIMENSION)
        if len(embedding) != expected_dim:
            logger.warning(f"Embedding dimension mismatch: expected {expected_dim}, got {len(embedding)}")
        
        return embedding
    
    except Exception as e:
        logger.error(f"Error creating embedding: {str(e)}")
        raise

@retry(
    wait=wait_random_exponential(min=1, max=60),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type((openai.APIError, openai.APIConnectionError, openai.RateLimitError))
)
async def create_embedding(text: str, model: Optional[str] = None) -> List[float]:
    """
    Create an embedding for the given text using OpenAI's API (async version).
    
    Parameters:
    - text: The text to embed
    - model: The embedding model to use (defaults to setting in config)
    
    Returns:
    - List of floats representing the embedding vector
    """
    # Use the sync version in an async context
    return await asyncio.to_thread(create_embedding_sync, text, model)

def create_embeddings_batch(
    texts: List[str], 
    model: Optional[str] = None, 
    batch_size: int = 32
) -> List[List[float]]:
    """
    Create embeddings for multiple texts in batches.
    
    Parameters:
    - texts: List of texts to embed
    - model: The embedding model to use (defaults to setting in config)
    - batch_size: Number of texts to embed in each batch
    
    Returns:
    - List of embedding vectors
    """
    if not texts:
        return []
    
    # Use the specified model or default
    embedding_model = model or settings.DEFAULT_EMBEDDING_MODEL
    
    # Process in batches
    all_embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        try:
            # Create embeddings for batch
            response = client.embeddings.create(
                model=embedding_model,
                input=batch,
                encoding_format="float"
            )
            
            # Extract embeddings
            embeddings = [data.embedding for data in response.data]
            
            # Add to all embeddings
            all_embeddings.extend(embeddings)
            
            # Log progress
            logger.info(f"Embedded batch {i//batch_size + 1}/{(len(texts)-1)//batch_size + 1}, "
                        f"processed {min(i+batch_size, len(texts))}/{len(texts)} texts")
            
            # Rate limiting
            if i + batch_size < len(texts):
                time.sleep(0.5)  # Avoid hitting rate limits
        
        except Exception as e:
            # Handle errors in batch
            logger.error(f"Error creating embeddings for batch {i//batch_size + 1}: {str(e)}")
            
            # Process individually to isolate problematic texts
            batch_embeddings = []
            for j, text in enumerate(batch):
                try:
                    embedding = create_embedding_sync(text, embedding_model)
                    batch_embeddings.append(embedding)
                except Exception as e2:
                    logger.error(f"Error creating embedding for text {i+j}: {str(e2)}")
                    # Add zero vector as placeholder
                    dim = EMBEDDING_DIMENSIONS.get(embedding_model, settings.EMBEDDING_DIMENSION)
                    batch_embeddings.append([0.0] * dim)
                
                # Rate limiting for individual requests
                time.sleep(0.5)
            
            # Add batch embeddings to all embeddings
            all_embeddings.extend(batch_embeddings)
    
    return all_embeddings

def similar_by_vector(
    query_embedding: List[float], 
    document_embeddings: List[List[float]], 
    top_k: int = 5
) -> List[Tuple[int, float]]:
    """
    Find most similar documents by embedding vector using cosine similarity.
    
    Parameters:
    - query_embedding: Embedding vector of the query
    - document_embeddings: List of embedding vectors of documents
    - top_k: Number of most similar documents to return
    
    Returns:
    - List of tuples (document_index, similarity_score)
    """
    # Convert to numpy arrays
    query_embedding = np.array(query_embedding)
    document_embeddings = np.array(document_embeddings)
    
    # Normalize embeddings (for cosine similarity)
    query_norm = np.linalg.norm(query_embedding)
    doc_norms = np.linalg.norm(document_embeddings, axis=1)
    
    # Avoid division by zero
    if query_norm == 0:
        query_norm = 1
    doc_norms[doc_norms == 0] = 1
    
    # Normalize vectors
    query_embedding = query_embedding / query_norm
    document_embeddings = document_embeddings / doc_norms[:, np.newaxis]
    
    # Calculate cosine similarities
    similarities = np.dot(document_embeddings, query_embedding)
    
    # Get top k indices and scores
    if top_k >= len(similarities):
        # Return all results if top_k is larger than the number of documents
        indices = np.argsort(similarities)[::-1]
        scores = similarities[indices]
    else:
        # Get top k results
        indices = np.argpartition(similarities, -top_k)[-top_k:]
        indices = indices[np.argsort(similarities[indices])][::-1]
        scores = similarities[indices]
    
    # Return as list of tuples
    return [(int(idx), float(score)) for idx, score in zip(indices, scores)]

@retry(
    wait=wait_random_exponential(min=1, max=60),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type((openai.APIError, openai.APIConnectionError, openai.RateLimitError))
)
def generate_completion_sync(
    prompt: str,
    context: List[Dict[str, Any]],
    model: Optional[str] = None,
    max_tokens: int = 1000,
    temperature: float = 0.2
) -> str:
    """
    Generate a completion using OpenAI's chat API with RAG context (synchronous version).
    
    Parameters:
    - prompt: The user's query
    - context: List of context documents to include
    - model: The chat model to use (defaults to setting in config)
    - max_tokens: Maximum tokens in the response
    - temperature: Sampling temperature (0.0 to 1.0)
    
    Returns:
    - The generated response text
    """
    try:
        # Use the specified model or default
        chat_model = model or settings.DEFAULT_CHAT_MODEL
        
        # Prepare context text
        context_text = ""
        for i, doc in enumerate(context):
            ticker = doc.get("ticker", "")
            year = doc.get("year", "")
            section = doc.get("section_name", "")
            text = doc.get("chunk_text", doc.get("text", ""))
            
            context_text += f"[Document {i+1}] {ticker} ({year}) - {section}:\n{text}\n\n"
        
        # Create messages for the chat
        messages = [
            {
                "role": "system", 
                "content": (
                    "You are a helpful financial analyst assistant. "
                    "You provide information based on the data from SEC filings. "
                    "You always cite your sources by referring to the document numbers. "
                    "If you don't know the answer, say so."
                )
            },
            {
                "role": "user",
                "content": (
                    f"Please answer the following question based on the provided SEC filing information:\n\n"
                    f"Context information:\n{context_text}\n\n"
                    f"Question: {prompt}\n\n"
                    f"Answer the question based on the context information provided. "
                    f"If the context doesn't contain the answer, say that you don't have enough information."
                )
            }
        ]
        
        # Generate the completion
        response = client.chat.completions.create(
            model=chat_model,
            messages=[{"role": m["role"], "content": m["content"]} for m in messages],
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        # Extract the response text
        response_text = response.choices[0].message.content
        
        return response_text
    
    except Exception as e:
        logger.error(f"Error generating completion: {str(e)}")
        raise

@retry(
    wait=wait_random_exponential(min=1, max=60),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type((openai.APIError, openai.APIConnectionError, openai.RateLimitError))
)
async def generate_completion(
    prompt: str,
    context: List[Dict[str, Any]],
    model: Optional[str] = None,
    max_tokens: int = 1000,
    temperature: float = 0.2
) -> str:
    """
    Generate a completion using OpenAI's chat API with RAG context (async version).
    
    Parameters:
    - prompt: The user's query
    - context: List of context documents to include
    - model: The chat model to use (defaults to setting in config)
    - max_tokens: Maximum tokens in the response
    - temperature: Sampling temperature (0.0 to 1.0)
    
    Returns:
    - The generated response text
    """
    # Use the sync version in an async context
    return await asyncio.to_thread(
        generate_completion_sync, 
        prompt, 
        context, 
        model, 
        max_tokens, 
        temperature
    )