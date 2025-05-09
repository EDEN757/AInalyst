import requests
import time
import datetime
import logging
import re
from typing import List, Dict, Any, Optional
from app.core.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# SEC API constants
SEC_HEADERS = {
    'User-Agent': f'S&P500RagBot {settings.SEC_EMAIL}'
}
SEC_BASE_URL = "https://data.sec.gov/submissions"
SEC_API_URL = "https://api.sec.io"

def get_company_submissions(cik: str) -> Dict[str, Any]:
    """Fetch SEC submission history for a company by CIK.
    
    Args:
        cik: Company CIK number (with or without leading zeros)
    
    Returns:
        Dictionary with company submission data
        
    Raises:
        Exception: If there's an error fetching the data
    """
    # Ensure CIK is properly formatted (10 digits with leading zeros)
    cik = cik.lstrip('0')
    padded_cik = cik.zfill(10)
    
    url = f"{SEC_BASE_URL}/CIK{padded_cik}.json"
    
    try:
        response = requests.get(url, headers=SEC_HEADERS)
        response.raise_for_status()  # Raise exception for HTTP errors
        
        # Respect SEC API rate limits (10 requests per second)
        time.sleep(0.1)
        
        return response.json()
    
    except Exception as e:
        logger.error(f"Error fetching submissions for CIK {cik}: {str(e)}")
        raise

def lookup_company_cik_from_sec(symbol: str) -> Optional[str]:
    """Look up a company's CIK number directly from SEC.
    
    Args:
        symbol: Company stock symbol (e.g., "AAPL")
        
    Returns:
        CIK number as a string, or None if not found
    """
    try:
        # Use the SEC's ticker-to-CIK mapping endpoint
        url = "https://www.sec.gov/files/company_tickers.json"
        response = requests.get(url, headers=SEC_HEADERS)
        response.raise_for_status()
        
        # Respect SEC rate limits
        time.sleep(0.1)
        
        # The SEC returns a JSON object with numeric keys
        companies_data = response.json()
        
        # Convert to list for easier searching
        companies_list = [companies_data[str(key)] for key in companies_data]
        
        # Find matching ticker (case-insensitive)
        for company in companies_list:
            if company.get('ticker', '').upper() == symbol.upper():
                # Format CIK as a string with leading zeros (10 digits)
                cik = str(company.get('cik_str', '')).zfill(10)
                logger.info(f"Found CIK {cik} for {symbol} via SEC API")
                return cik
                
        logger.warning(f"Could not find CIK for {symbol} via SEC API")
        return None
        
    except Exception as e:
        logger.error(f"Error looking up CIK for {symbol}: {str(e)}")
        return None

def get_10k_filing_url(cik: str, accession_number: str, primary_doc: str) -> str:
    """Construct the SEC filing URL for a 10-K document.
    
    Args:
        cik: Company CIK number (without leading zeros)
        accession_number: SEC accession number
        primary_doc: Primary document filename
        
    Returns:
        Full URL to the SEC filing
    """
    # Format accession number by removing dashes
    accession_clean = accession_number.replace('-', '')
    
    # Construct the URL to the filing
    return f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_clean}/{primary_doc}"

def extract_10k_filings(submissions_data: Dict[str, Any], start_date: str, end_date: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Extract 10-K filings from SEC submission data within a date range.
    
    Args:
        submissions_data: SEC submission data for a company
        start_date: Start date in ISO format (YYYY-MM-DD)
        end_date: End date in ISO format (YYYY-MM-DD)
        limit: Maximum number of filings to extract
        
    Returns:
        List of dictionaries with 10-K filing information
    """
    filings = []
    recent_filings = submissions_data.get('filings', {}).get('recent', {})
    
    # Check if we have the necessary data
    if not recent_filings:
        logger.warning(f"No recent filings data found for this company")
        return filings
    
    # Convert date strings to datetime objects for comparison
    start_dt = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
    end_dt = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # Get the indices of the specified filing type
    form_types = recent_filings.get('form', [])
    accession_numbers = recent_filings.get('accessionNumber', [])
    filing_dates = recent_filings.get('filingDate', [])
    primary_doc_urls = recent_filings.get('primaryDocument', [])
    filing_count = len(form_types)
    
    logger.info(f"Found {filing_count} filings in recent data, looking for 10-K")
    
    # Extract 10-K filings within the date range
    count = 0
    for i in range(filing_count):
        if form_types[i] == '10-K' and count < limit:
            try:
                filing_date_str = filing_dates[i]
                filing_date = datetime.datetime.strptime(filing_date_str, '%Y-%m-%d').date()
                
                # Check if filing is within date range
                if start_dt <= filing_date <= end_dt:
                    fiscal_year = filing_date.year
                    
                    # Extract the primary document URL
                    accession_num = accession_numbers[i]
                    primary_doc = primary_doc_urls[i]
                    cik = submissions_data.get('cik')
                    
                    # Construct the filing URL
                    filing_url = get_10k_filing_url(cik, accession_num, primary_doc)
                    
                    filings.append({
                        'accession_number': accession_num,
                        'filing_type': '10-K',
                        'filing_date': datetime.datetime.strptime(filing_date_str, '%Y-%m-%d'),
                        'filing_url': filing_url,
                        'fiscal_year': fiscal_year,
                        'fiscal_period': 'FY'
                    })
                    
                    count += 1
                    logger.info(f"Found 10-K filing from {filing_date_str} - URL: {filing_url}")
            except Exception as e:
                logger.error(f"Error processing filing {accession_numbers[i]}: {str(e)}")
    
    logger.info(f"Extracted {len(filings)} 10-K filings within date range")
    return filings

def fetch_filing_document(filing_url: str) -> Optional[str]:
    """Fetch the actual filing document text.
    
    Args:
        filing_url: URL to the filing document
    
    Returns:
        Text content of the filing or None if there was an error
    """
    try:
        response = requests.get(filing_url, headers=SEC_HEADERS)
        response.raise_for_status()
        
        # Respect SEC API rate limits
        time.sleep(0.1)
        
        return response.text
    
    except Exception as e:
        logger.error(f"Error fetching filing document {filing_url}: {str(e)}")
        return None

def fetch_company_10k_filings(symbol: str, cik: str = None, start_date: str = None, end_date: str = None) -> Dict[str, List]:
    """Fetch 10-K filings for a company within a date range.
    
    Args:
        symbol: Company ticker symbol (e.g., "AAPL")
        cik: Company CIK number (optional, will be looked up if not provided)
        start_date: Start date in ISO format (default: 3 years ago)
        end_date: End date in ISO format (default: today)
        
    Returns:
        Dictionary with companies and filings lists
    """
    results = {
        'companies': [],
        'filings': []
    }
    
    # Set default date range if not provided
    if not start_date:
        start_date = (datetime.datetime.now() - datetime.timedelta(days=3*365)).strftime('%Y-%m-%d')
    if not end_date:
        end_date = datetime.datetime.now().strftime('%Y-%m-%d')
    
    logger.info(f"Fetching 10-K filings for {symbol} from {start_date} to {end_date}")
    
    try:
        # Look up the company's CIK if not provided
        if not cik:
            cik = lookup_company_cik_from_sec(symbol)
            if not cik:
                logger.error(f"Could not find CIK for {symbol}. Cannot fetch filings.")
                return results
        
        # Get company submissions data
        logger.info(f"Fetching submissions data for {symbol} (CIK: {cik})")
        submissions = get_company_submissions(cik)
        
        # Extract company name from submissions
        company_name = submissions.get('name', symbol)
        
        # Add company to results
        results['companies'].append({
            'symbol': symbol,
            'name': company_name,
            'cik': cik
        })
        
        # Extract 10-K filings within date range
        filings = extract_10k_filings(submissions, start_date, end_date)
        
        # Format filings for the results
        for filing in filings:
            results['filings'].append({
                'company_symbol': symbol,
                'company_name': company_name,
                'company_cik': cik,
                'accession_number': filing['accession_number'],
                'filing_type': filing['filing_type'],
                'filing_date': filing['filing_date'],
                'filing_url': filing['filing_url'],
                'fiscal_year': filing['fiscal_year'],
                'fiscal_period': filing['fiscal_period']
            })
        
        logger.info(f"Found {len(results['filings'])} 10-K filings for {symbol}")
        
    except Exception as e:
        logger.error(f"Error fetching 10-K filings for {symbol}: {str(e)}")
    
    return results