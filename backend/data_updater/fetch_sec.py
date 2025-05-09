import requests
import time
import datetime
import logging
import json
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
SEC_API_URL = "https://api.sec-api.io"

# Demo mode companies - top 10 by market cap (example)
# This is only used for the demo mode and should not be used for lookups
DEMO_COMPANIES = [
    {"symbol": "AAPL", "name": "Apple Inc.", "cik": "0000320193"},
    {"symbol": "MSFT", "name": "Microsoft Corporation", "cik": "0000789019"},
    {"symbol": "GOOGL", "name": "Alphabet Inc.", "cik": "0001652044"},
    {"symbol": "AMZN", "name": "Amazon.com, Inc.", "cik": "0001018724"},
    {"symbol": "NVDA", "name": "NVIDIA Corporation", "cik": "0001045810"},
    {"symbol": "META", "name": "Meta Platforms, Inc.", "cik": "0001326801"},
    {"symbol": "BRK-B", "name": "Berkshire Hathaway Inc.", "cik": "0001067983"},
    {"symbol": "JPM", "name": "JPMorgan Chase & Co.", "cik": "0000019617"},
    {"symbol": "JNJ", "name": "Johnson & Johnson", "cik": "0000200406"},
    {"symbol": "V", "name": "Visa Inc.", "cik": "0001403161"}
]


def get_sp500_companies() -> List[Dict[str, str]]:
    """Get current S&P 500 companies list.
    
    In a real application, you would fetch this from an API or a reliable source.
    For simplicity, this example returns a partial/static list.
    
    Returns:
        List of dictionaries with company info (symbol, name, cik)
    """
    # In a full implementation, you would fetch the real S&P 500 components
    # For demo purposes, we'll return just 10 major companies
    return DEMO_COMPANIES


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


def fetch_filings_by_query(query_params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Fetch filings from SEC API using the query parameters.
    
    Args:
        query_params: Dictionary with query parameters
            Example: {
                "query": "formType:\"10-K\" AND ticker:AAPL AND filedAt:[2020-01-01 TO 2025-12-31]",
                "from": "0", 
                "size": "50",
                "sort": [{ "filedAt": { "order": "desc" } }]
            }
    
    Returns:
        List of dictionaries with filing information
    """
    # Check if SEC API key is available
    if not settings.SEC_API_KEY:
        logger.error("SEC_API_KEY is not configured. Please add it to your .env file.")
        logger.info("Falling back to legacy SEC data fetching method")

        # Extract information from the query to use with legacy method
        ticker = None
        doc_type = None
        limit = 5
        start_date = None
        end_date = None

        # Parse the query string
        query = query_params.get("query", "")
        if "ticker:" in query:
            ticker_match = re.search(r'ticker:([A-Z]+)', query)
            if ticker_match:
                ticker = ticker_match.group(1)

        if "formType:" in query:
            form_match = re.search(r'formType:"([^"]+)"', query)
            if form_match:
                doc_type = form_match.group(1)
                
        # Extract date range from query
        if "filedAt:" in query:
            date_match = re.search(r'filedAt:\[([0-9-]+) TO ([0-9-]+)\]', query)
            if date_match:
                start_date = date_match.group(1)
                end_date = date_match.group(2)
                logger.info(f"Extracted date range: {start_date} to {end_date}")

        # Only proceed if we could extract a ticker
        if ticker and doc_type:
            logger.info(f"Using legacy method to fetch {doc_type} filings for {ticker} with date range {start_date} to {end_date}")

            # Look up the company's CIK (important: don't use the cached list, always query SEC)
            cik = lookup_company_cik_from_sec(ticker)
            if cik:
                # Get company information
                company = {
                    'symbol': ticker,
                    'name': f"{ticker}",
                    'cik': cik
                }

                # Try to get a better company name
                try:
                    submissions = get_company_submissions(cik)
                    if submissions and 'name' in submissions:
                        company['name'] = submissions['name']

                    # Extract filings of the requested document type
                    filings = []
                    if doc_type == "10-K":
                        filings = extract_10k_filings(submissions, limit=limit)
                    else:
                        # For other document types, try to extract them from recent filings
                        filings = extract_filings_by_type(submissions, doc_type, limit=limit)

                    # Filter by date range if provided
                    if start_date and end_date and filings:
                        start_dt = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
                        end_dt = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()

                        filtered_filings = []
                        for filing in filings:
                            filing_date = filing['filing_date'].date()
                            if start_dt <= filing_date <= end_dt:
                                filtered_filings.append(filing)

                        logger.info(f"Filtered filings by date range {start_date} to {end_date}: "
                                  f"{len(filings)} -> {len(filtered_filings)}")
                        filings = filtered_filings

                    # Format the filings to match the API response format
                    formatted_filings = []
                    for filing in filings:
                        formatted_filings.append({
                            'accessionNo': filing['accession_number'],
                            'formType': filing['filing_type'],
                            'filedAt': filing['filing_date'].strftime('%Y-%m-%dT%H:%M:%S.000Z'),
                            'linkToFilingDetails': filing['filing_url'],
                            'ticker': ticker,
                            'companyName': company['name'],
                            'periodOfReport': filing['filing_date'].strftime('%Y-%m-%d'),
                            'cik': cik
                        })

                    logger.info(f"Found {len(formatted_filings)} filings using legacy method")
                    return formatted_filings
                except Exception as e:
                    logger.error(f"Error using legacy method: {str(e)}")

        logger.error("Could not extract required information from query or legacy method failed")
        return []

    url = f"{SEC_API_URL}/api/1/filings"
    headers = {
        'Authorization': settings.SEC_API_KEY,
        'Content-Type': 'application/json'
    }
    
    try:
        logger.info(f"Fetching filings with query: {query_params['query']}")
        response = requests.post(url, headers=headers, json=query_params)
        response.raise_for_status()
        
        result = response.json()
        filings = result.get("filings", [])
        
        logger.info(f"Found {len(filings)} filings matching query")
        return filings
    
    except Exception as e:
        logger.error(f"Error fetching filings by query: {str(e)}")
        return []


def extract_filing_info(filing: Dict[str, Any], company_info: Dict[str, str]) -> Dict[str, Any]:
    """Extract relevant information from a filing.
    
    Args:
        filing: Filing data from SEC API
        company_info: Company information
    
    Returns:
        Dictionary with standardized filing information
    """
    # Extract filing date
    filing_date = datetime.datetime.strptime(filing.get('filedAt', ''), '%Y-%m-%dT%H:%M:%S.%fZ')
    
    # Determine fiscal year (use filed year as an approximation if not provided)
    fiscal_year = filing.get('periodOfReport', '')
    if fiscal_year:
        fiscal_year = datetime.datetime.strptime(fiscal_year, '%Y-%m-%d').year
    else:
        fiscal_year = filing_date.year
    
    # Determine fiscal period
    filing_type = filing.get('formType', '')
    fiscal_period = 'FY' if filing_type in ['10-K', '10-K/A'] else 'Q'
    
    # Extract filing URL
    filing_url = filing.get('linkToFilingDetails', '')
    
    return {
        'accession_number': filing.get('accessionNo', ''),
        'filing_type': filing_type,
        'filing_date': filing_date,
        'filing_url': filing_url,
        'fiscal_year': fiscal_year,
        'fiscal_period': fiscal_period,
        'company_symbol': company_info.get('symbol', ''),
        'company_name': company_info.get('name', ''),
        'company_cik': company_info.get('cik', '')
    }


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


def lookup_company_cik_from_sec(symbol: str) -> Optional[str]:
    """Look up a company's CIK number directly from SEC, without using the demo list.
    
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


def lookup_company_cik(symbol: str) -> Optional[str]:
    """Look up a company's CIK number by its ticker symbol.
    
    Args:
        symbol: Company stock symbol (e.g., "AAPL")
        
    Returns:
        CIK number as a string, or None if not found
    """
    # First check our demo list for a quick match - FOR DEMO MODE ONLY 
    # This will be used when explicitly using the demo mode functions
    demo_company = next((c for c in DEMO_COMPANIES if c['symbol'] == symbol), None)
    if demo_company:
        return demo_company['cik']
    
    # For normal operation (including CSV imports), always look up from SEC
    return lookup_company_cik_from_sec(symbol)


def fetch_filings_by_query_params(ticker: str, doc_type: str, start_date: str, end_date: str, limit: int = 50) -> Dict[str, List]:
    """Fetch company and filing information based on SEC API query.
    
    Args:
        ticker: Company ticker symbol (e.g., "AAPL")
        doc_type: Document type (e.g., "10-K", "10-Q", "8-K")
        start_date: Start date in ISO format (e.g., "2020-01-01")
        end_date: End date in ISO format (e.g., "2025-12-31")
        limit: Maximum number of filings to fetch (default: 50)
    
    Returns:
        Dictionary with companies and filings lists
    """
    results = {
        'companies': [],
        'filings': []
    }
    
    logger.info(f"Processing company with symbol: {ticker} for {doc_type} documents from {start_date} to {end_date}")
    
    try:
        # Look up the company's CIK - use direct SEC lookup to avoid caching effects
        cik = lookup_company_cik_from_sec(ticker)
        
        if cik:
            company = {
                'symbol': ticker,
                'name': f"{ticker}",  # We'll get a better name when we fetch submissions
                'cik': cik
            }
            
            logger.info(f"Using CIK {cik} for company {ticker}")
            
            # Try to get a better company name from the submissions data
            try:
                submissions = get_company_submissions(cik)
                if submissions and 'name' in submissions:
                    company['name'] = submissions['name']
            except Exception as e:
                logger.error(f"Error getting better name for {ticker}: {str(e)}")
        else:
            logger.error(f"Could not find CIK for {ticker}. Cannot fetch filings.")
            return results
            
        # Add company to results
        results['companies'].append({
            'symbol': company['symbol'],
            'name': company['name'],
            'cik': company.get('cik'),
            'sector': company.get('sector'),
            'industry': company.get('industry')
        })
        
        # Build the query
        query_params = {
            "query": f'formType:"{doc_type}" AND ticker:{ticker} AND filedAt:[{start_date} TO {end_date}]',
            "from": "0",
            "size": str(min(limit, 50)),  # API has a limit of 50 results per request
            "sort": [{ "filedAt": { "order": "desc" } }]
        }
        
        # Fetch filings using the SEC API query
        filings_data = fetch_filings_by_query(query_params)
        
        # Process filings
        for filing in filings_data:
            filing_info = extract_filing_info(filing, company)
            results['filings'].append(filing_info)
        
        logger.info(f"Found {len(results['filings'])} {doc_type} filings for {ticker}")
        
    except Exception as e:
        logger.error(f"Error processing company {ticker}: {str(e)}")
    
    return results


# Legacy functions maintained for backward compatibility
def extract_10k_filings(submissions_data: Dict[str, Any], limit: int = 5) -> List[Dict[str, Any]]:
    """Extract 10-K filings from SEC submission data.

    Args:
        submissions_data: SEC submission data for a company
        limit: Maximum number of 10-K filings to extract

    Returns:
        List of dictionaries with 10-K filing information
    """
    return extract_filings_by_type(submissions_data, '10-K', limit)


def extract_filings_by_type(submissions_data: Dict[str, Any], form_type: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Extract filings of a specific type from SEC submission data.

    Args:
        submissions_data: SEC submission data for a company
        form_type: Type of filing to extract (e.g., '10-K', '10-Q', '8-K')
        limit: Maximum number of filings to extract

    Returns:
        List of dictionaries with filing information
    """
    filings = []
    recent_filings = submissions_data.get('filings', {}).get('recent', {})

    # Check if we have the necessary data
    if not recent_filings:
        logger.warning(f"No recent filings data found for this company")
        return filings

    # Get the indices of the specified filing type
    form_types = recent_filings.get('form', [])
    accession_numbers = recent_filings.get('accessionNumber', [])
    filing_dates = recent_filings.get('filingDate', [])
    primary_doc_urls = recent_filings.get('primaryDocument', [])
    filing_count = len(form_types)

    logger.info(f"Found {filing_count} filings in recent data, looking for {form_type}")

    # Extract filings of the requested type
    count = 0
    for i in range(filing_count):
        if form_types[i] == form_type and count < limit:
            # Convert filing date to datetime
            try:
                filing_date = datetime.datetime.strptime(filing_dates[i], '%Y-%m-%d')
                fiscal_year = filing_date.year

                # Extract the primary document URL
                accession_num = accession_numbers[i].replace('-', '')
                primary_doc = primary_doc_urls[i]
                cik = submissions_data.get('cik')

                # Construct the filing URL
                filing_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_num}/{primary_doc}"

                # Determine fiscal period based on filing type
                fiscal_period = 'FY'  # Default for 10-K
                if form_type == '10-Q' or form_type == '10-Q/A':
                    # Determine quarter based on filing date
                    month = filing_date.month
                    if 1 <= month <= 3:
                        fiscal_period = 'Q1'
                    elif 4 <= month <= 6:
                        fiscal_period = 'Q2'
                    elif 7 <= month <= 9:
                        fiscal_period = 'Q3'
                    else:
                        fiscal_period = 'Q4'
                elif form_type == '8-K' or form_type == '8-K/A':
                    fiscal_period = 'Current'

                filings.append({
                    'accession_number': accession_numbers[i],
                    'filing_type': form_type,
                    'filing_date': filing_date,
                    'filing_url': filing_url,
                    'fiscal_year': fiscal_year,
                    'fiscal_period': fiscal_period
                })

                count += 1
                logger.info(f"Found {form_type} filing from {filing_date}")
            except Exception as e:
                logger.error(f"Error processing filing {accession_numbers[i]}: {str(e)}")

    logger.info(f"Extracted {len(filings)} {form_type} filings")
    return filings


def fetch_companies_and_filings(mode: str = 'DEMO', filing_limit: int = 2) -> Dict[str, List]:
    """Legacy function to fetch companies and their 10-K filings based on the mode.
    
    This function is kept for backward compatibility.
    
    Args:
        mode: 'DEMO' for a subset of companies, 'FULL' for all S&P 500
        filing_limit: Maximum number of 10-K filings to fetch per company
    
    Returns:
        Dictionary with companies and filings lists
    """
    results = {
        'companies': [],
        'filings': []
    }
    
    # Get companies based on mode
    companies = get_sp500_companies()
    
    if mode == 'DEMO':
        # In demo mode, use just a few companies
        companies = companies[:3]  # Limit to 3 companies for demo
    
    for company in companies:
        logger.info(f"Processing company: {company['symbol']} - {company['name']}")
        
        # Add company to results
        results['companies'].append({
            'symbol': company['symbol'],
            'name': company['name'],
            'cik': company['cik'],
            'sector': company.get('sector'),
            'industry': company.get('industry')
        })
        
        try:
            # Get company submissions from SEC
            submissions = get_company_submissions(company['cik'])
            
            # Extract 10-K filings
            filings = extract_10k_filings(submissions, limit=filing_limit)
            
            # Add filings to results with company info
            for filing in filings:
                filing['company_symbol'] = company['symbol']
                filing['company_name'] = company['name']
                filing['company_cik'] = company['cik']
                results['filings'].append(filing)
            
            logger.info(f"Found {len(filings)} 10-K filings for {company['symbol']}")
            
        except Exception as e:
            logger.error(f"Error processing company {company['symbol']}: {str(e)}")
    
    logger.info(f"Finished processing {len(results['companies'])} companies")
    logger.info(f"Total 10-K filings found: {len(results['filings'])}")
    
    return results


def fetch_companies_and_filings_by_symbol(symbol: str, filing_limit: int = 2, filing_years: List[int] = None) -> Dict[str, List]:
    """Legacy function to fetch company information and filings for a specific ticker symbol.
    
    This function is kept for backward compatibility.
    
    Args:
        symbol: Company stock symbol (e.g., "AAPL")
        filing_limit: Maximum number of 10-K filings to fetch
        filing_years: Optional list of specific years to fetch filings for
    
    Returns:
        Dictionary with company and filings lists
    """
    # Use the new function to fetch filings with some reasonable defaults
    today = datetime.datetime.now()
    end_date = today.strftime("%Y-%m-%d")
    
    # Default to looking back 5 years if no specific years are provided
    if filing_years:
        # Convert filing_years to date range
        earliest_year = min(filing_years)
        latest_year = max(filing_years)
        start_date = f"{earliest_year}-01-01"
        end_date = f"{latest_year}-12-31"
    else:
        # Default to 5 years back
        start_date = f"{today.year - 5}-01-01"
    
    return fetch_filings_by_query_params(
        ticker=symbol,
        doc_type="10-K",
        start_date=start_date,
        end_date=end_date,
        limit=filing_limit
    )