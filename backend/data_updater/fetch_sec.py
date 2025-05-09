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
from ratelimit import limits, sleep_and_retry  # Added as per fix.md

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
# URL for the SEC's official company tickers list
EDGAR_COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
# URL for alternate tickers list with exchange info
EDGAR_COMPANY_TICKERS_EXCHANGE_URL = "https://www.sec.gov/files/company_tickers_exchange.json"

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

# SEC rate limit decorator - allows up to 10 requests per second
@sleep_and_retry
@limits(calls=10, period=1)
def _get_sec_url(url: str, headers: Optional[Dict[str, str]] = None, **kwargs) -> requests.Response:
    """Wrapper for GET requests to SEC, applying rate limits and headers."""
    logger.info(f"Fetching URL: {url}")
    if headers is None:
        headers = {"User-Agent": settings.EDGAR_USER_AGENT}
    response = requests.get(url, headers=headers, **kwargs)
    response.raise_for_status()  # Raise an exception for HTTP error codes
    return response

# CIK lookup cache to avoid repeated lookups
CIK_LOOKUP_CACHE = {}

def get_cik_from_ticker(ticker: str) -> Optional[str]:
    """Return zero-padded 10-digit CIK for a given stock ticker."""
    # Check cache first
    if ticker in CIK_LOOKUP_CACHE:
        return CIK_LOOKUP_CACHE[ticker]

    try:
        logger.info(f"Looking up CIK for ticker: {ticker}")

        # This mapping file can be large; we're retrieving it once and caching locally
        resp = _get_sec_url("https://www.sec.gov/files/company_tickers.json")
        data = resp.json()

        for company_info in data.values():  # The structure is a dict with integer keys
            if company_info.get("ticker", "").upper() == ticker.upper():
                cik = str(company_info["cik_str"]).zfill(10)

                # Add to cache
                CIK_LOOKUP_CACHE[ticker] = cik

                logger.info(f"Found CIK for {ticker}: {cik}")
                return cik

        # If we reach here, the ticker wasn't found in the API
        logger.warning(f"CIK not found for ticker: {ticker}")
        return None

    except Exception as e:
        logger.error(f"Error looking up CIK: {str(e)}")
        return None

def fetch_company_submissions(cik: str) -> dict:
    """Return the submissions JSON for this CIK (includes ALL filing types)."""
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    return _get_sec_url(url).json()

def find_10k_filing_indices(submissions_data: dict, start_year: int, end_year: int) -> List[Dict[str, Any]]:
    """
    Scan the 'recent' filings for all 10-Ks in the given year range.
    Returns list of { 'filing_date', 'report_date', 'accession_number', 'primary_document', etc. } entries.

    Uses the primaryDocument field directly from the JSON response to construct the correct URL.
    """
    if "filings" not in submissions_data or "recent" not in submissions_data["filings"]:
        logger.warning(f"Warning: 'filings' or 'recent' key not found in submissions data for CIK {submissions_data.get('cik')}. Skipping.")
        return []

    filings_recent = submissions_data["filings"]["recent"]
    # Ensure all expected keys are present to avoid KeyErrors
    required_keys = ["form", "filingDate", "reportDate", "accessionNumber", "primaryDocument"]
    for key in required_keys:
        if key not in filings_recent:
            logger.warning(f"Warning: Expected key '{key}' not found in 'recent' filings. Skipping CIK {submissions_data.get('cik')}.")
            return []

    forms = filings_recent["form"]
    filing_dates = filings_recent["filingDate"]
    report_dates = filings_recent["reportDate"]
    accession_numbers = filings_recent["accessionNumber"]
    primary_documents = filings_recent["primaryDocument"]  # This is the actual filename uploaded by the company

    # Get the CIK number
    cik_str = submissions_data.get("cik", "")
    if not cik_str:
        logger.warning("CIK not found in submissions data. Skipping.")
        return []

    # Convert to integer for URL construction (remove leading zeros)
    try:
        cik_int = int(cik_str)
    except ValueError:
        logger.warning(f"Could not convert CIK to int: {cik_str}")
        cik_int = cik_str  # Use string as fallback

    matches = []

    for i in range(len(forms)):
        form = forms[i]
        filing_date_str = filing_dates[i]
        report_date_str = report_dates[i]
        accession_no = accession_numbers[i]
        primary_doc_name = primary_documents[i]

        try:
            filing_year = int(filing_date_str[:4])
        except ValueError:
            logger.warning(f"Warning: Could not parse year from filingDate '{filing_date_str}'. Skipping.")
            continue

        if form == "10-K" and start_year <= filing_year <= end_year:
            # Remove dashes from accession number for URL path
            acc_nodash = accession_no.replace("-", "")

            # URLs for the filing - use the primary document name directly from the JSON
            index_url = (
                f"https://www.sec.gov/Archives/edgar/data/"
                f"{cik_int}/{acc_nodash}/{accession_no}-index.html"
            )
            primary_doc_url = (
                f"https://www.sec.gov/Archives/edgar/data/"
                f"{cik_int}/{acc_nodash}/{primary_doc_name}"
            )

            matches.append({
                "filing_date": filing_date_str,
                "report_date": report_date_str,
                "accession_number": accession_no,
                "primary_document_name": primary_doc_name,
                "primary_document_url": primary_doc_url,  # Direct URL to the primary document
                "index_url": index_url,  # URL to the index page
                "filing_type": "10-K",
                "year": filing_year,
                "ticker": "UNKNOWN"  # Will be replaced with actual ticker later
            })

            logger.info(f"Found 10-K filing for year {filing_year}, document: {primary_doc_name}")

    return matches

def download_filing_document_new(filing_info: Dict[str, Any], ticker: str, output_directory: Optional[str] = None) -> Optional[str]:
    """Downloads the primary filing document (HTML/text) and writes to disk if output_directory is provided."""
    # We want the primary document URL, not the index URL for the final content
    document_url = filing_info["primary_document_url"]
    try:
        content = _get_sec_url(document_url).text

        # If output directory is provided, save to file
        if output_directory:
            # Use accession number for uniqueness, and include filing date for clarity
            # Ensure filename is OS-compatible
            safe_primary_doc_name = filing_info["primary_document_name"].replace("/", "_")
            fname = f"{ticker}_{filing_info['filing_date']}_{filing_info['accession_number']}_{safe_primary_doc_name}"
            # Ensure filename doesn't get too long or have problematic characters
            fname = "".join(c if c.isalnum() or c in ['_', '-','.'] else '_' for c in fname)

            path = os.path.join(output_directory, fname)
            os.makedirs(output_directory, exist_ok=True)  # Ensure dir exists

            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            logger.info(f"Saved {filing_info['filing_date']} ({filing_info['accession_number']}) → {path}")
            return path

        # If no output directory, just return the content
        return content
    except requests.exceptions.RequestException as e:
        logger.error(f"Error downloading {document_url}: {e}")
        return None
    except IOError as e:
        logger.error(f"Error saving file for {document_url}: {e}")
        return None

# For backward compatibility - keep the original function signature that the rest of the codebase uses
def download_filing_document(document_url: str, session: Optional[requests.Session] = None) -> Optional[str]:
    """
    Download the filing document content.
    Maintains the original function signature for compatibility with existing code.

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
            logger.error(f"Error downloading document: {response.status_code}")
            return None

        # Return document content
        return response.text

    except Exception as e:
        logger.error(f"Error downloading document: {str(e)}")
        return None

def process_company_filings_from_csv(csv_filepath: str, output_dir: Optional[str] = None):
    """
    Process company filings from a CSV file.
    CSV must have columns: ticker, company_name (optional), start_year, end_year
    
    Parameters:
    - csv_filepath: Path to the CSV file
    - output_dir: Directory to save downloaded documents (if None, won't save files)
    
    Returns:
    - Dictionary with summary of processed files
    """
    if not os.path.exists(csv_filepath):
        logger.error(f"Error: CSV file not found at {csv_filepath}")
        return {"error": "CSV file not found"}

    processed_files_summary = {}

    with open(csv_filepath, newline="", encoding="utf-8") as csvfile:
        reader = pd.read_csv(csvfile).to_dict('records')
        for row in reader:
            try:
                ticker = row["ticker"].strip()
                company_name = row.get("company_name", ticker).strip()  # Optional company_name
                start_year = int(row["start_year"])
                end_year = int(row["end_year"])
            except KeyError as e:
                logger.error(f"Skipping row due to missing key: {e}. Row: {row}")
                continue
            except ValueError as e:
                logger.error(f"Skipping row due to invalid year format: {e}. Row: {row}")
                continue

            logger.info(f"Processing {ticker} ({company_name}) for filings from {start_year}–{end_year}")
            processed_files_summary[ticker] = []
            try:
                cik = get_cik_from_ticker(ticker)
                if not cik:
                    logger.error(f"Could not find CIK for {ticker}")
                    continue
                    
                submissions = fetch_company_submissions(cik)
                target_filings_info = find_10k_filing_indices(submissions, start_year, end_year)

                if not target_filings_info:
                    logger.warning(f"No 10-K filings found in the specified range for {ticker}.")
                    continue

                if output_dir:
                    company_specific_out_dir = os.path.join(output_dir, ticker)
                    os.makedirs(company_specific_out_dir, exist_ok=True)
                else:
                    company_specific_out_dir = None

                for filing_detail in target_filings_info:
                    # Update ticker in filing detail
                    filing_detail["ticker"] = ticker
                    
                    # Download and optionally save to disk
                    result = download_filing_document_new(filing_detail, ticker, company_specific_out_dir)

                    if result:
                        if company_specific_out_dir:
                            # If saved to disk, store the file path
                            processed_files_summary[ticker].append({
                                "path": result,
                                "filing_date": filing_detail["filing_date"],
                                "accession_number": filing_detail["accession_number"]
                            })
                        else:
                            # If not saved to disk, store the filing details for further processing
                            filing_detail["document_content"] = result
                            processed_files_summary[ticker].append(filing_detail)

                    time.sleep(0.1)  # Additional courtesy pause

            except KeyError as e:
                logger.error(f"Could not process {ticker}: {e}")
            except requests.exceptions.RequestException as e:
                logger.error(f"Network or API error for {ticker}: {e}")
            except Exception as e:
                logger.error(f"An unexpected error occurred for {ticker}: {e}")
    
    logger.info("========== SUMMARY ==========")
    for ticker, files in processed_files_summary.items():
        logger.info(f"{ticker}: Processed {len(files)} filings.")
    
    return processed_files_summary

# For backward compatibility - existing functions that the current codebase depends on

def get_sec_filings(ticker: str, year: int, filing_type: str = "10-K") -> List[Dict[str, Any]]:
    """
    Get SEC filings for a specific ticker, year, and filing type.
    Updated to use the new architecture but maintain the same interface.
    """
    logger.info(f"Fetching {filing_type} filings for {ticker} for year {year}")

    try:
        # Only support 10-K filing type in this implementation
        if filing_type != "10-K":
            logger.warning(f"This implementation only supports 10-K filings, not {filing_type}")
            return []

        # Get CIK for the ticker
        ticker_cik = get_cik_from_ticker(ticker)
        if not ticker_cik:
            logger.error(f"Could not find CIK for {ticker}")
            return []

        # Get submissions
        submissions = fetch_company_submissions(ticker_cik)
        filings = find_10k_filing_indices(submissions, year, year)

        # Format to match the old interface
        for filing in filings:
            # Add some fields expected by the old interface
            filing["filing_details_url"] = filing["index_url"]
            filing["document_url"] = filing["primary_document_url"]  # Add direct document URL
            filing["filing_type"] = filing_type
            filing["cik"] = ticker_cik
            filing["ticker"] = ticker
            filing["year"] = year
            filing["title"] = f"{filing_type} for {ticker} ({year})"
            filing["summary"] = None
            filing["category_term"] = None
            filing["category_label"] = None

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
    # This function is still needed by the existing codebase, but we can simplify it
    # to extract document URL from the details page when needed

    try:
        # Check if we're getting a filing_info dict from the new implementation
        if isinstance(filing_details_url, dict) and "primary_document_url" in filing_details_url:
            return filing_details_url["primary_document_url"]

        # Create or use a session for SEC API
        if session is None:
            session = create_sec_session()

        # Make request to filing details page
        response = session.get(filing_details_url)

        # Apply rate limiting delay
        time.sleep(random.uniform(SEC_REQUEST_DELAY_MIN, SEC_REQUEST_DELAY_MAX))

        # Check response status
        if response.status_code != 200:
            logger.error(f"Error fetching filing details: {response.status_code}")
            return None

        # Extract base URL for constructing full URLs
        base_url_parts = filing_details_url.split("-index.html")
        base_url = base_url_parts[0]

        # Parse HTML response
        soup = BeautifulSoup(response.content, "html.parser")

        # First try to find direct links to the 10-K document
        for table in soup.find_all("table"):
            for row in table.find_all("tr"):
                cells = row.find_all("td")
                if len(cells) >= 3:
                    try:
                        cell_text = cells[2].get_text().strip()
                        if "10-k" in cell_text.lower() and ("htm" in cell_text.lower() or "html" in cell_text.lower()):
                            # Get the document URL
                            doc_link = cells[2].find("a")
                            if doc_link and doc_link.has_attr("href"):
                                doc_url = f"{EDGAR_BASE_URL}{doc_link['href']}"
                                return doc_url
                    except Exception as e:
                        continue  # Skip this cell if there's an error

        # Second, try to find links to the main filing document
        for a in soup.find_all("a"):
            try:
                href = a.get("href", "")
                text = a.get_text().strip().lower()
                if href and ("10k" in text or "10-k" in text) and (".htm" in href.lower() or ".html" in href.lower()):
                    # If it's a relative URL, convert to absolute
                    if href.startswith("/"):
                        return f"https://www.sec.gov{href}"
                    elif href.startswith("http"):
                        return href
                    else:
                        # Try to construct from base URL
                        return f"{base_url}/{href}"
            except Exception as e:
                continue  # Skip this link if there's an error

        # Third approach: try to find the primary document
        try:
            acc_number = filing_details_url.split("/")[-1].split("-index.html")[0]
            acc_no_dashes = acc_number.replace("-", "")

            # Extract the parent URL
            parent_url_parts = filing_details_url.split(f"/{acc_no_dashes}/")
            if len(parent_url_parts) >= 2:
                parent_url = parent_url_parts[0]

                # Try standard naming patterns for 10-K documents
                for doc_pattern in [
                    f"{acc_no_dashes}/Filing10K.htm",
                    f"{acc_no_dashes}/Form10K.htm",
                    f"{acc_no_dashes}/10-k.htm",
                    f"{acc_no_dashes}/10k.htm"
                ]:
                    potential_url = f"{parent_url}/{doc_pattern}"
                    # We don't need to check if the URL exists, we'll just return it and
                    # the download function will handle errors
                    if potential_url:
                        return potential_url
        except Exception as e:
            logger.error(f"Error constructing potential document URL: {str(e)}")

        logger.warning(f"Could not find 10-K document in filing details: {filing_details_url}")
        return None

    except Exception as e:
        logger.error(f"Error fetching filing document: {str(e)}")
        return None

def download_filing_document_legacy(document_url: str, session: Optional[requests.Session] = None) -> Optional[str]:
    """
    Download the filing document content.
    Legacy method to maintain compatibility with the existing codebase.
    
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
            logger.error(f"Error downloading document: {response.status_code}")
            return None
        
        # Return document content
        return response.text
    
    except Exception as e:
        logger.error(f"Error downloading document: {str(e)}")
        return None

# For backward compatibility, alias the legacy function to the current one
download_filing_document_from_url = download_filing_document_legacy

def fetch_filings_for_company(ticker: str, start_year: int, end_year: int, filing_types: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Fetch SEC filings for a company over a range of years.
    
    Parameters:
    - ticker: The company ticker symbol
    - start_year: Start year for fetching filings
    - end_year: End year for fetching filings
    - filing_types: List of filing types to fetch (defaults to ["10-K"])
    
    Returns:
    - List of filings with metadata and document content
    """
    # Set default filing types if not provided
    if filing_types is None:
        filing_types = ["10-K"]
    
    # Currently we only support 10-K filings in the new implementation
    if any(ft != "10-K" for ft in filing_types):
        logger.warning("This implementation only supports 10-K filings.")
        filing_types = ["10-K"]
    
    logger.info(f"Fetching {', '.join(filing_types)} filings for {ticker} from {start_year} to {end_year}")
    
    # Get CIK for ticker
    cik = get_cik_from_ticker(ticker)
    if not cik:
        logger.error(f"Could not find CIK for {ticker}")
        return []
    
    # Get submissions data for the CIK
    submissions = fetch_company_submissions(cik)
    
    # Find all 10-K filings in the year range
    filings = find_10k_filing_indices(submissions, start_year, end_year)
    
    # Add ticker to filings data
    for filing in filings:
        filing["ticker"] = ticker
    
    logger.info(f"Found {len(filings)} filings for {ticker} from {start_year} to {end_year}")
    return filings

def download_filing_contents(filings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Download the document content for each filing.
    
    Parameters:
    - filings: List of filings with metadata
    
    Returns:
    - List of filings with metadata and document content
    """
    filings_with_content = []
    for filing in filings:
        try:
            # Skip if no document URL
            if "primary_document_url" not in filing:
                if "document_url" in filing:
                    document_url = filing["document_url"]
                else:
                    logger.warning(f"No document URL for filing: {filing.get('ticker')} {filing.get('year')} {filing.get('filing_type')}")
                    continue
            else:
                document_url = filing["primary_document_url"]
            
            # Download document content
            document_content = download_filing_document_legacy(document_url)
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