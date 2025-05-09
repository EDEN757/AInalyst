import requests
import logging
import time
import os
import sys
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
from bs4 import BeautifulSoup
import re
import random
import json
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

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

# Constants for SEC EDGAR API
EDGAR_BASE_URL = "https://www.sec.gov/Archives"
EDGAR_SEARCH_URL = "https://www.sec.gov/cgi-bin/browse-edgar"
EDGAR_CIK_LOOKUP_URL = "https://www.sec.gov/edgar/search/efts_cik_lookup_data.json"

# Rate limiting for SEC API
SEC_REQUEST_DELAY_MIN = 0.1  # 100ms minimum delay
SEC_REQUEST_DELAY_MAX = 0.3  # 300ms maximum delay

# Common filing types
FILING_TYPES = {
    "10-K": "Annual report",
    "10-K/A": "Annual report amendment",
    "10-Q": "Quarterly report",
    "10-Q/A": "Quarterly report amendment",
    "8-K": "Current report",
    "8-K/A": "Current report amendment"
}

# Create a requests session with retry functionality
def create_sec_session():
    """Create a requests session with retry functionality for SEC API"""
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update({
        "User-Agent": settings.EDGAR_USER_AGENT,
        "Accept-Encoding": "gzip, deflate",
        "Host": "www.sec.gov"
    })
    return session

# CIK lookup cache to avoid repeated lookups
CIK_LOOKUP_CACHE = {}

def lookup_cik(ticker: str) -> Optional[str]:
    """
    Look up the CIK number for a ticker symbol.
    
    Parameters:
    - ticker: The company ticker symbol
    
    Returns:
    - CIK number as a string or None if not found
    """
    # Check cache first
    if ticker in CIK_LOOKUP_CACHE:
        return CIK_LOOKUP_CACHE[ticker]
    
    try:
        logger.info(f"Looking up CIK for ticker: {ticker}")
        
        # Create a session for SEC API
        session = create_sec_session()
        
        # Make request to CIK lookup endpoint
        response = session.get(EDGAR_CIK_LOOKUP_URL)
        
        # Apply rate limiting delay
        time.sleep(random.uniform(SEC_REQUEST_DELAY_MIN, SEC_REQUEST_DELAY_MAX))
        
        # Check response status
        if response.status_code != 200:
            logger.error(f"Error looking up CIK: {response.status_code} - {response.text}")
            return None
        
        # Parse JSON response
        data = response.json()
        
        # Search for ticker in the data
        for entry in data.get('data', []):
            if entry[0].upper() == ticker.upper():
                cik = entry[1]
                # Add leading zeros to make it 10 digits
                cik_padded = cik.zfill(10)
                
                # Add to cache
                CIK_LOOKUP_CACHE[ticker] = cik_padded
                
                logger.info(f"Found CIK for {ticker}: {cik_padded}")
                return cik_padded
        
        logger.warning(f"CIK not found for ticker: {ticker}")
        return None
    
    except Exception as e:
        logger.error(f"Error looking up CIK: {str(e)}")
        return None

def get_sec_filings(ticker: str, year: int, filing_type: str = "10-K") -> List[Dict[str, Any]]:
    """
    Get SEC filings for a specific ticker, year, and filing type.
    
    Parameters:
    - ticker: The company ticker symbol
    - year: The year of the filing
    - filing_type: The type of filing (default: 10-K)
    
    Returns:
    - List of filings with metadata
    """
    logger.info(f"Fetching {filing_type} filings for {ticker} for year {year}")
    
    try:
        # Create a session for SEC API
        session = create_sec_session()
        
        # Lookup CIK if ticker is not already a CIK
        cik = ticker
        if not ticker.isdigit():
            cik = lookup_cik(ticker)
            if not cik:
                logger.error(f"Could not find CIK for {ticker}")
                return []
        
        # Calculate date range for the year
        start_date = f"{year}0101"
        end_date = f"{year}1231"
        
        # Build request params
        params = {
            "action": "getcompany",
            "CIK": cik,
            "type": filing_type,
            "dateb": end_date,
            "datea": start_date,
            "owner": "exclude",
            "count": "100",
            "output": "atom"
        }
        
        # Make request to SEC EDGAR
        response = session.get(EDGAR_SEARCH_URL, params=params)
        
        # Apply rate limiting delay
        time.sleep(random.uniform(SEC_REQUEST_DELAY_MIN, SEC_REQUEST_DELAY_MAX))
        
        # Check response status
        if response.status_code != 200:
            logger.error(f"Error fetching SEC filings: {response.status_code} - {response.text}")
            return []
        
        # Parse XML response
        soup = BeautifulSoup(response.content, "lxml-xml")
        entries = soup.find_all("entry")
        
        # Process entries
        filings = []
        for entry in entries:
            try:
                # Get filing date
                filing_date = entry.find("filing-date")
                if filing_date:
                    filing_date = filing_date.text
                else:
                    filing_date = entry.find("updated").text.split("T")[0]
                
                # Get filing URL
                filing_href = None
                for link in entry.find_all("link"):
                    if link.get("rel") == "alternate":
                        filing_href = link.get("href")
                        break
                
                if not filing_href:
                    continue
                
                # Get accession number from URL
                accession_number = None
                accession_match = re.search(r'/(\d{10}-\d{2}-\d{6})', filing_href)
                if accession_match:
                    accession_number = accession_match.group(1)
                else:
                    accession_number = filing_href.split("/")[-1]
                
                # Get filing details URL
                cik_no_leading_zeros = cik.lstrip('0')
                filing_details_url = f"{EDGAR_BASE_URL}/edgar/data/{cik_no_leading_zeros}/{accession_number.replace('-', '')}"
                
                # Get title and description
                title = entry.find("title")
                title_text = title.text if title else f"{filing_type} for {ticker}"
                
                summary = entry.find("summary")
                summary_text = summary.text if summary else None
                
                # Get category information
                category = entry.find("category")
                category_term = category.get("term") if category else None
                category_label = category.get("label") if category else None
                
                # Add to filings list
                filings.append({
                    "ticker": ticker,
                    "cik": cik,
                    "year": year,
                    "filing_type": filing_type,
                    "filing_date": filing_date,
                    "accession_number": accession_number,
                    "filing_details_url": filing_details_url,
                    "title": title_text,
                    "summary": summary_text,
                    "category_term": category_term,
                    "category_label": category_label
                })
            except Exception as e:
                logger.warning(f"Error processing entry: {str(e)}")
                continue
        
        logger.info(f"Found {len(filings)} {filing_type} filings for {ticker} for year {year}")
        return filings
    
    except Exception as e:
        logger.error(f"Error fetching SEC filings: {str(e)}")
        return []

def get_filing_document_url(filing_details_url: str, session: Optional[requests.Session] = None) -> Optional[str]:
    """
    Get the URL for the actual filing document.
    
    Parameters:
    - filing_details_url: The URL for the filing details page
    - session: Optional requests session (creates a new one if None)
    
    Returns:
    - URL for the actual filing document (HTML or TXT)
    """
    try:
        # Create or use a session for SEC API
        if session is None:
            session = create_sec_session()
        
        # Make request to filing details page
        response = session.get(filing_details_url)
        
        # Apply rate limiting delay
        time.sleep(random.uniform(SEC_REQUEST_DELAY_MIN, SEC_REQUEST_DELAY_MAX))
        
        # Check response status
        if response.status_code != 200:
            logger.error(f"Error fetching filing details: {response.status_code} - {response.text}")
            return None
        
        # Parse HTML response
        soup = BeautifulSoup(response.content, "html.parser")
        
        # Look for the 10-K/10-K/A HTML file
        for table in soup.find_all("table"):
            for row in table.find_all("tr"):
                cells = row.find_all("td")
                if len(cells) >= 3:
                    cell_text = cells[2].get_text().strip()
                    if "10-K" in cell_text and ("htm" in cell_text.lower() or "html" in cell_text.lower()):
                        # Get the document URL
                        doc_link = cells[2].find("a")
                        if doc_link and doc_link.has_attr("href"):
                            doc_url = f"{EDGAR_BASE_URL}{doc_link['href']}"
                            return doc_url
        
        # If HTML not found, look for the TXT file
        for table in soup.find_all("table"):
            for row in table.find_all("tr"):
                cells = row.find_all("td")
                if len(cells) >= 3:
                    cell_text = cells[2].get_text().strip()
                    if "10-K" in cell_text and "txt" in cell_text.lower():
                        # Get the document URL
                        doc_link = cells[2].find("a")
                        if doc_link and doc_link.has_attr("href"):
                            doc_url = f"{EDGAR_BASE_URL}{doc_link['href']}"
                            return doc_url
        
        logger.warning(f"Could not find 10-K document in filing details: {filing_details_url}")
        return None
    
    except Exception as e:
        logger.error(f"Error fetching filing document: {str(e)}")
        return None

def download_filing_document(document_url: str, session: Optional[requests.Session] = None) -> Optional[str]:
    """
    Download the filing document content.
    
    Parameters:
    - document_url: The URL for the filing document
    - session: Optional requests session (creates a new one if None)
    
    Returns:
    - The document content as a string
    """
    try:
        # Create or use a session for SEC API
        if session is None:
            session = create_sec_session()
        
        # Make request to document URL
        response = session.get(document_url)
        
        # Apply rate limiting delay
        time.sleep(random.uniform(SEC_REQUEST_DELAY_MIN, SEC_REQUEST_DELAY_MAX))
        
        # Check response status
        if response.status_code != 200:
            logger.error(f"Error downloading document: {response.status_code} - {response.text}")
            return None
        
        # Return document content
        return response.text
    
    except Exception as e:
        logger.error(f"Error downloading document: {str(e)}")
        return None

def fetch_filings_for_company(ticker: str, start_year: int, end_year: int, filing_types: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Fetch SEC filings for a company over a range of years.
    
    Parameters:
    - ticker: The company ticker symbol
    - start_year: Start year for fetching filings
    - end_year: End year for fetching filings
    - filing_types: List of filing types to fetch (defaults to ["10-K", "10-K/A"])
    
    Returns:
    - List of filings with metadata and document content
    """
    # Set default filing types if not provided
    if filing_types is None:
        filing_types = ["10-K", "10-K/A"]
    
    logger.info(f"Fetching {', '.join(filing_types)} filings for {ticker} from {start_year} to {end_year}")
    
    # Create a session for SEC API
    session = create_sec_session()
    
    # Fetch filings for each year and filing type
    all_filings = []
    for year in range(start_year, end_year + 1):
        for filing_type in filing_types:
            # Get filings metadata
            filings = get_sec_filings(ticker, year, filing_type)
            
            # Skip if no filings found
            if not filings:
                continue
            
            # Get document URL and content for each filing
            for filing in filings:
                try:
                    # Get document URL
                    document_url = get_filing_document_url(filing["filing_details_url"], session)
                    if not document_url:
                        logger.warning(f"Could not find document URL for {ticker} {year} {filing_type}")
                        continue
                    
                    # Add document URL to filing metadata
                    filing["document_url"] = document_url
                    
                    # Add to all filings list
                    all_filings.append(filing)
                except Exception as e:
                    logger.error(f"Error processing filing: {str(e)}")
                    continue
    
    logger.info(f"Fetched {len(all_filings)} filings for {ticker} from {start_year} to {end_year}")
    
    return all_filings

def download_filing_contents(filings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Download the document content for each filing.
    
    Parameters:
    - filings: List of filings with metadata
    
    Returns:
    - List of filings with metadata and document content
    """
    # Create a session for SEC API
    session = create_sec_session()
    
    # Download document content for each filing
    filings_with_content = []
    for filing in filings:
        try:
            # Skip if no document URL
            if "document_url" not in filing:
                logger.warning(f"No document URL for filing: {filing.get('ticker')} {filing.get('year')} {filing.get('filing_type')}")
                continue
            
            # Download document content
            document_content = download_filing_document(filing["document_url"], session)
            if not document_content:
                logger.warning(f"Could not download document content for filing: {filing.get('ticker')} {filing.get('year')} {filing.get('filing_type')}")
                continue
            
            # Add document content to filing metadata
            filing["document_content"] = document_content
            
            # Add to filings with content list
            filings_with_content.append(filing)
        except Exception as e:
            logger.error(f"Error downloading filing content: {str(e)}")
            continue
    
    logger.info(f"Downloaded document content for {len(filings_with_content)} filings")
    
    return filings_with_content