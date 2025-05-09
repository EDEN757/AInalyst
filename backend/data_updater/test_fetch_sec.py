import os
import sys
import logging
from dotenv import load_dotenv
import json
import argparse

# Add the parent directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Import the modules to test
from data_updater.csv_reader import get_companies_for_update
from data_updater.fetch_sec import fetch_filings_for_company, download_filing_contents

def main():
    """Test SEC fetching functionality"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Test SEC API fetching")
    parser.add_argument("--ticker", type=str, help="Specific ticker to fetch (default: use companies.csv)")
    parser.add_argument("--start-year", type=int, help="Start year for fetching filings")
    parser.add_argument("--end-year", type=int, help="End year for fetching filings")
    parser.add_argument("--download", action="store_true", help="Download document content")
    parser.add_argument("--output", type=str, help="Output file for JSON results")
    args = parser.parse_args()
    
    try:
        if args.ticker:
            # Use command line arguments
            ticker = args.ticker
            start_year = args.start_year or 2022
            end_year = args.end_year or 2022
            
            # Fetch filings for specific ticker
            logger.info(f"Fetching filings for {ticker} from {start_year} to {end_year}")
            filings = fetch_filings_for_company(ticker, start_year, end_year)
        else:
            # Use companies from CSV
            companies = get_companies_for_update()
            if not companies:
                logger.error("No companies found in CSV file")
                return 1
            
            # Use first company for testing
            company = companies[0]
            ticker = company["ticker"]
            start_year = company["start_year"]
            end_year = company["end_year"]
            
            # Fetch filings for company
            logger.info(f"Fetching filings for {ticker} from {start_year} to {end_year}")
            filings = fetch_filings_for_company(ticker, start_year, end_year)
        
        # Download document content if requested
        if args.download and filings:
            logger.info(f"Downloading document content for {len(filings)} filings")
            filings = download_filing_contents(filings)
        
        # Output results
        if filings:
            logger.info(f"Found {len(filings)} filings")
            
            # Remove document content for display (it's too large)
            display_filings = []
            for filing in filings:
                display_filing = filing.copy()
                if "document_content" in display_filing:
                    display_filing["document_content"] = f"[{len(display_filing['document_content'])} characters]"
                display_filings.append(display_filing)
            
            # Print filings as JSON
            print(json.dumps(display_filings, indent=2))
            
            # Save to output file if specified
            if args.output:
                with open(args.output, "w") as f:
                    json.dump(filings, f, indent=2)
                logger.info(f"Saved results to {args.output}")
        else:
            logger.warning("No filings found")
        
        # Return success
        return 0
    
    except Exception as e:
        # Log error
        logger.error(f"Error testing SEC fetching: {str(e)}")
        
        # Return failure
        return 1

if __name__ == "__main__":
    sys.exit(main())