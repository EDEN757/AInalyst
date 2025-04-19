import re
import logging
import html
from typing import List, Dict, Any, Tuple
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Regular expressions for section extraction
SECTION_PATTERNS = [
    r'ITEM\s+1\.?\s*BUSINESS',
    r'ITEM\s+1A\.?\s*RISK\s+FACTORS',
    r'ITEM\s+7\.?\s*MANAGEMENT.*DISCUSSION.*ANALYSIS',
    r'ITEM\s+7A\.?\s*QUANTITATIVE.*QUALITATIVE\s+DISCLOSURES',
    r'ITEM\s+8\.?\s*FINANCIAL\s+STATEMENTS',
    r'ITEM\s+9\.?\s*CHANGES.*DISAGREEMENTS'
]


def clean_html(html_content: str) -> str:
    """Clean HTML content to extract readable text.
    
    Args:
        html_content: Raw HTML string
    
    Returns:
        Cleaned text content
    """
    if not html_content:
        return ""
    
    # Parse HTML
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remove script and style elements
    for element in soup(["script", "style", "head", "title", "meta", "[document]"]):
        element.extract()
    
    # Get text
    text = soup.get_text(separator=" ", strip=True)
    
    # Decode HTML entities
    text = html.unescape(text)
    
    # Replace multiple whitespace with single space
    text = re.sub(r'\s+', ' ', text)
    
    # Replace multiple newlines with single newline
    text = re.sub(r'\n+', '\n', text)
    
    return text.strip()


def split_into_sections(text: str) -> Dict[str, str]:
    """Split filing text into sections based on Item numbers.
    
    Args:
        text: Clean text content from filing
    
    Returns:
        Dictionary mapping section names to their content
    """
    sections = {}
    current_section = "HEADER"
    current_content = []
    
    lines = text.split('\n')
    
    for line in lines:
        # Check if line starts a new section
        new_section = None
        for pattern in SECTION_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                new_section = re.search(pattern, line, re.IGNORECASE).group(0)
                break
        
        if new_section:
            # Save the current section
            sections[current_section] = '\n'.join(current_content)
            
            # Start new section
            current_section = new_section
            current_content = [line]
        else:
            current_content.append(line)
    
    # Save the last section
    if current_content:
        sections[current_section] = '\n'.join(current_content)
    
    return sections


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 100) -> List[str]:
    """Split text into overlapping chunks of approximately equal size.
    
    Args:
        text: Text to split into chunks
        chunk_size: Target size of each chunk in characters
        overlap: Number of characters to overlap between chunks
    
    Returns:
        List of text chunks
    """
    if not text or len(text) <= chunk_size:
        return [text] if text else []
    
    chunks = []
    start = 0
    
    while start < len(text):
        # Determine end of current chunk
        end = start + chunk_size
        
        if end >= len(text):
            # Last chunk
            chunks.append(text[start:])
            break
        
        # Try to find a good break point (newline or period followed by space)
        cutoff = end
        
        # Look for paragraph break first
        paragraph_break = text.rfind('\n\n', start, end)
        if paragraph_break != -1 and paragraph_break > start + chunk_size // 2:
            cutoff = paragraph_break + 2  # Include the newlines
        else:
            # Look for sentence break
            sentence_break = text.rfind('. ', start, end)
            if sentence_break != -1 and sentence_break > start + chunk_size // 2:
                cutoff = sentence_break + 2  # Include the period and space
        
        # Add chunk and advance
        chunks.append(text[start:cutoff])
        start = cutoff - overlap  # Overlap with previous chunk
    
    return chunks


def process_filing_text(filing_text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Process a filing document into chunks with metadata.
    
    Args:
        filing_text: Raw filing text (HTML)
        metadata: Filing metadata (company, date, etc.)
    
    Returns:
        List of dictionaries containing chunks with metadata
    """
    # Clean HTML to extract text
    clean_text = clean_html(filing_text)
    
    # Split into sections
    sections = split_into_sections(clean_text)
    
    chunks_with_metadata = []
    chunk_index = 0
    
    # Process each section
    for section_name, section_text in sections.items():
        # Skip empty sections
        if not section_text.strip():
            continue
        
        # Chunk the section text
        text_chunks = chunk_text(section_text)
        
        # Add metadata to each chunk
        for chunk in text_chunks:
            if chunk.strip():  # Skip empty chunks
                chunks_with_metadata.append({
                    'chunk_index': chunk_index,
                    'text_content': chunk.strip(),
                    'section': section_name,
                    'filing_id': metadata.get('filing_id'),
                    'company_symbol': metadata.get('company_symbol'),
                    'filing_type': metadata.get('filing_type'),
                    'filing_date': metadata.get('filing_date'),
                    'fiscal_year': metadata.get('fiscal_year')
                })
                chunk_index += 1
    
    return chunks_with_metadata
