import requests
import time
import datetime
import logging
from typing import List, Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# SEC API constants
SEC_HEADERS = {
    'User-Agent': 'S&P500RagBot edoardo.schiatti@gmail.com'
}
SEC_BASE_URL = "https://data.sec.gov/submissions"

# Demo mode companies - top 10 by market cap (example)
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


def extract_10k_filings(submissions_data: Dict[str, Any], limit: int = 5) -> List[Dict[str, Any]]:
    """Extract 10-K filings from SEC submission data.
    
    Args:
        submissions_data: SEC submission data for a company
        limit: Maximum number of 10-K filings to extract
    
    Returns:
        List of dictionaries with 10-K filing information
    """
    filings = []
    recent_filings = submissions_data.get('filings', {}).get('recent', {})
    
    # Check if we have the necessary data
    if not recent_filings:
        return filings
    
    # Get the indices of 10-K filings
    form_types = recent_filings.get('form', [])
    accession_numbers = recent_filings.get('accessionNumber', [])
    filing_dates = recent_filings.get('filingDate', [])
    primary_doc_urls = recent_filings.get('primaryDocument', [])
    filing_count = len(form_types)
    
    # Extract 10-K filings
    count = 0
    for i in range(filing_count):
        if form_types[i] == '10-K' and count < limit:
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
                
                filings.append({
                    'accession_number': accession_numbers[i],
                    'filing_type': '10-K',
                    'filing_date': filing_date,
                    'filing_url': filing_url,
                    'fiscal_year': fiscal_year,
                    'fiscal_period': 'FY'  # 10-K is always annual
                })
                
                count += 1
            except Exception as e:
                logger.error(f"Error processing filing {accession_numbers[i]}: {str(e)}")
    
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


def fetch_companies_and_filings(mode: str = 'DEMO', filing_limit: int = 2) -> Dict[str, List]:
    """Fetch companies and their 10-K filings based on the mode.
    
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
