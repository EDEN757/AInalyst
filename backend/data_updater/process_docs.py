import re
import logging
import tiktoken
import uuid
import os
import sys
import json
from typing import List, Dict, Any, Optional, Tuple
from bs4 import BeautifulSoup, Comment
import unicodedata
import html

# Add app directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.core.config import settings

# Configure logging
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(settings.LOG_LEVEL)

# Initialize tokenizer for splitting text
tokenizer = tiktoken.get_encoding("cl100k_base")  # OpenAI's encoding used by most models

# Section patterns to identify important parts of 10-K filings
SECTION_PATTERNS = {
    "Business": [
        r"Item\s*1\.?\s*Business",
        r"Item\s*1\s*[–-]\s*Business",
        r"ITEM\s*1\.?\s*BUSINESS",
        r"PART I.*\n.*ITEM 1\.?\s*BUSINESS"
    ],
    "Risk Factors": [
        r"Item\s*1A\.?\s*Risk\s*Factors",
        r"Item\s*1A\s*[–-]\s*Risk\s*Factors",
        r"ITEM\s*1A\.?\s*RISK\s*FACTORS",
        r"RISK\s*FACTORS"
    ],
    "Management Discussion": [
        r"Item\s*7\.?\s*Management'?s?\s*Discussion\s*and\s*Analysis",
        r"Item\s*7\s*[–-]\s*Management'?s?\s*Discussion\s*and\s*Analysis",
        r"ITEM\s*7\.?\s*MANAGEMENT'?S?\s*DISCUSSION\s*AND\s*ANALYSIS",
        r"Management'?s?\s*Discussion\s*and\s*Analysis"
    ],
    "Financial Statements": [
        r"Item\s*8\.?\s*Financial\s*Statements",
        r"Item\s*8\s*[–-]\s*Financial\s*Statements",
        r"ITEM\s*8\.?\s*FINANCIAL\s*STATEMENTS",
        r"Consolidated\s*Financial\s*Statements"
    ],
    "Controls and Procedures": [
        r"Item\s*9A\.?\s*Controls\s*and\s*Procedures",
        r"Item\s*9A\s*[–-]\s*Controls\s*and\s*Procedures",
        r"ITEM\s*9A\.?\s*CONTROLS\s*AND\s*PROCEDURES"
    ],
    "Properties": [
        r"Item\s*2\.?\s*Properties",
        r"Item\s*2\s*[–-]\s*Properties",
        r"ITEM\s*2\.?\s*PROPERTIES"
    ],
    "Legal Proceedings": [
        r"Item\s*3\.?\s*Legal\s*Proceedings",
        r"Item\s*3\s*[–-]\s*Legal\s*Proceedings",
        r"ITEM\s*3\.?\s*LEGAL\s*PROCEEDINGS"
    ],
    "Market Information": [
        r"Item\s*5\.?\s*Market\s*for\s*Registrant'?s?\s*Common\s*Equity",
        r"Item\s*5\s*[–-]\s*Market\s*for\s*Registrant'?s?\s*Common\s*Equity",
        r"ITEM\s*5\.?\s*MARKET\s*FOR\s*REGISTRANT'?S?\s*COMMON\s*EQUITY"
    ]
}

# Define next item patterns to help with section boundary detection
NEXT_ITEM_PATTERN = r"(Item|ITEM)\s*\d+[A-Z]?\.?\s*[A-Za-z\s]+"

def clean_html(html_content: str) -> str:
    """
    Clean HTML content by removing scripts, styles, comments, and other non-content elements.
    
    Parameters:
    - html_content: HTML content as a string
    
    Returns:
    - Cleaned text
    """
    try:
        # Parse HTML
        soup = BeautifulSoup(html_content, "html.parser")
        
        # Remove scripts, styles, and comments
        for element in soup(["script", "style", "meta", "head", "noscript"]):
            element.decompose()
        
        # Remove comment nodes
        for comment in soup.find_all(text=lambda text: isinstance(text, Comment)):
            comment.extract()
        
        # Get text content
        text = soup.get_text(separator=" ")
        
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        return text
    except Exception as e:
        logger.error(f"Error cleaning HTML: {str(e)}")
        # Return original content if parsing fails
        return html_content

def extract_sections(doc_content: str) -> Dict[str, str]:
    """
    Extract key sections from a 10-K filing.
    
    Parameters:
    - doc_content: The document content as a string
    
    Returns:
    - Dictionary mapping section names to section text
    """
    # Check if content is HTML
    is_html = "<html" in doc_content.lower() or "<body" in doc_content.lower()
    
    # Clean HTML if present
    if is_html:
        doc_content = clean_html(doc_content)
    
    # Normalize text by replacing unusual whitespace and normalizing characters
    doc_content = unicodedata.normalize('NFKD', doc_content)
    doc_content = doc_content.replace('\xa0', ' ')
    doc_content = re.sub(r'\s+', ' ', doc_content)
    
    # Unescape HTML entities (like &amp;, &quot;, etc.)
    doc_content = html.unescape(doc_content)
    
    # Find section boundaries
    section_boundaries = []
    for section_name, patterns in SECTION_PATTERNS.items():
        for pattern in patterns:
            matches = re.finditer(pattern, doc_content, re.IGNORECASE)
            for match in matches:
                section_boundaries.append((match.start(), section_name))
    
    # Sort boundaries by position
    section_boundaries.sort()
    
    # Extract sections
    sections = {}
    for i, (start, section_name) in enumerate(section_boundaries):
        try:
            # Set end position (either next section or end of document)
            if i < len(section_boundaries) - 1:
                end = section_boundaries[i + 1][0]
            else:
                # For the last section, try to find the next item to limit the section
                next_item_match = re.search(NEXT_ITEM_PATTERN, doc_content[start+100:])
                if next_item_match:
                    end = start + 100 + next_item_match.start()
                else:
                    end = len(doc_content)
            
            # Extract section text and clean it
            section_text = doc_content[start:end].strip()
            
            # Skip if section is too short or likely not a real section
            if len(section_text) < 500:  # Skip very short sections (likely false matches)
                continue
            
            # Store section
            sections[section_name] = section_text
        
        except Exception as e:
            logger.error(f"Error extracting section {section_name}: {str(e)}")
    
    # If no sections were found, create a "Full Document" section
    if not sections:
        sections["Full Document"] = doc_content
    
    return sections

def clean_text(text: str) -> str:
    """
    Clean text for embedding.
    
    Parameters:
    - text: The text to clean
    
    Returns:
    - The cleaned text
    """
    # Normalize unicode
    text = unicodedata.normalize('NFKD', text)
    
    # Replace HTML entities
    text = html.unescape(text)
    
    # Replace multiple spaces and whitespace characters with a single space
    text = re.sub(r'\s+', ' ', text)
    
    # Remove non-ASCII characters
    text = re.sub(r'[^\x00-\x7F]+', '', text)
    
    # Remove excessive line breaks
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Remove very long strings of digits or characters (likely garbage)
    text = re.sub(r'\d{30,}', '[REDACTED LONG NUMBER]', text)
    text = re.sub(r'[a-zA-Z]{30,}', '[REDACTED LONG STRING]', text)
    
    # Remove URLs
    text = re.sub(r'https?://\S+', '[URL]', text)
    
    # Remove email addresses
    text = re.sub(r'\S+@\S+\.\S+', '[EMAIL]', text)
    
    return text.strip()

def split_text(text: str, max_tokens: int = 1000, overlap: int = 100) -> List[str]:
    """
    Split text into chunks of specified token size with overlap.
    
    Parameters:
    - text: The text to split
    - max_tokens: Maximum tokens per chunk
    - overlap: Number of tokens to overlap between chunks
    
    Returns:
    - List of text chunks
    """
    try:
        # Skip empty text
        if not text or len(text.strip()) == 0:
            return []
        
        # Handle very short text
        if len(text) < 100:
            return [text]
        
        # Tokenize the text
        tokens = tokenizer.encode(text)
        
        # Handle case where the text is shorter than max_tokens
        if len(tokens) <= max_tokens:
            return [text]
        
        # Split into chunks
        chunks = []
        i = 0
        while i < len(tokens):
            # Get chunk of tokens
            chunk_end = min(i + max_tokens, len(tokens))
            chunk = tokens[i:chunk_end]
            
            # Decode chunk back to text
            chunk_text = tokenizer.decode(chunk)
            
            # Add to chunks list
            chunks.append(chunk_text)
            
            # Advance position (with overlap)
            i += max_tokens - overlap
            
            # Ensure we're making progress
            if max_tokens <= overlap:
                i += 1  # Avoid infinite loop
        
        # Ensure we have at least one chunk
        if not chunks:
            chunks = [text]
        
        return chunks
    
    except Exception as e:
        logger.error(f"Error splitting text: {str(e)}")
        # Return the original text as a single chunk if splitting fails
        return [text]

def create_text_hash(text: str) -> str:
    """
    Create a hash of the given text.
    
    Parameters:
    - text: The text to hash
    
    Returns:
    - MD5 hash of the text
    """
    import hashlib
    return hashlib.md5(text.encode()).hexdigest()

def process_filing(
    ticker: str,
    year: int,
    document_type: str,
    filing_date: str,
    document_content: str,
    source_url: str
) -> List[Dict[str, Any]]:
    """
    Process a filing document into chunks for embedding.
    
    Parameters:
    - ticker: The company ticker symbol
    - year: The year of the filing
    - document_type: The type of filing (e.g., "10-K", "10-K/A")
    - filing_date: The date of the filing
    - document_content: The document content as a string
    - source_url: The URL for the filing document
    
    Returns:
    - List of document chunks with metadata
    """
    # Check for empty or invalid content
    if not document_content or len(document_content.strip()) == 0:
        logger.warning(f"Empty document content for {ticker} {year} {document_type}")
        return []
    
    try:
        logger.info(f"Processing filing for {ticker} {year} {document_type}")
        
        # Extract sections
        sections = extract_sections(document_content)
        
        # Process each section
        doc_chunks = []
        for section_name, section_text in sections.items():
            try:
                # Clean the text
                cleaned_text = clean_text(section_text)
                
                # Skip if cleaned text is too short
                if len(cleaned_text) < 200:
                    continue
                
                # Split into chunks
                chunks = split_text(cleaned_text)
                
                # Create document chunks
                for i, chunk_text in enumerate(chunks):
                    try:
                        # Skip if chunk is too short
                        if len(chunk_text) < 100:
                            continue
                        
                        # Generate a unique document ID
                        doc_id = str(uuid.uuid4())
                        
                        # Create text hash
                        text_hash = create_text_hash(chunk_text)
                        
                        # Add to chunks list
                        doc_chunks.append({
                            "id": doc_id,
                            "ticker": ticker,
                            "year": year,
                            "document_type": document_type,
                            "filing_date": filing_date,
                            "section_name": section_name,
                            "source_url": source_url,
                            "page_number": None,  # We don't have page numbers from HTML/text
                            "chunk_number": i + 1,
                            "total_chunks": len(chunks),
                            "chunk_text": chunk_text,
                            "text_hash": text_hash
                        })
                    except Exception as e:
                        logger.error(f"Error creating chunk: {str(e)}")
            except Exception as e:
                logger.error(f"Error processing section {section_name}: {str(e)}")
        
        logger.info(f"Created {len(doc_chunks)} chunks for {ticker} {year} {document_type}")
        return doc_chunks
    
    except Exception as e:
        logger.error(f"Error processing filing: {str(e)}")
        return []

def save_chunks_to_json(chunks: List[Dict[str, Any]], output_file: str) -> None:
    """
    Save document chunks to a JSON file.
    
    Parameters:
    - chunks: List of document chunks
    - output_file: Path to the output JSON file
    """
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # Save to JSON
        with open(output_file, "w") as f:
            json.dump(chunks, f, indent=2)
        
        logger.info(f"Saved {len(chunks)} chunks to {output_file}")
    
    except Exception as e:
        logger.error(f"Error saving chunks to JSON: {str(e)}")

def process_filings(filings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Process multiple filings into chunks.
    
    Parameters:
    - filings: List of filings with metadata and document content
    
    Returns:
    - List of document chunks with metadata
    """
    all_chunks = []
    
    for filing in filings:
        try:
            # Skip if no document content
            if "document_content" not in filing:
                logger.warning(f"No document content for filing: {filing.get('ticker')} {filing.get('year')} {filing.get('filing_type')}")
                continue
            
            # Process filing
            chunks = process_filing(
                ticker=filing["ticker"],
                year=filing["year"],
                document_type=filing["filing_type"],
                filing_date=filing["filing_date"],
                document_content=filing["document_content"],
                source_url=filing.get("document_url", "")
            )
            
            # Add to all chunks list
            all_chunks.extend(chunks)
        
        except Exception as e:
            logger.error(f"Error processing filing: {str(e)}")
            continue
    
    logger.info(f"Processed {len(all_chunks)} chunks from {len(filings)} filings")
    
    return all_chunks