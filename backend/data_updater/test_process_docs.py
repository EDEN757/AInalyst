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
from data_updater.process_docs import process_filings, save_chunks_to_json

def main():
    """Test document processing functionality"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Test document processing")
    parser.add_argument("--ticker", type=str, help="Specific ticker to process (default: use companies.csv)")
    parser.add_argument("--start-year", type=int, help="Start year for fetching filings")
    parser.add_argument("--end-year", type=int, help="End year for fetching filings")
    parser.add_argument("--output", type=str, default="processed_chunks.json", help="Output file for JSON results")
    parser.add_argument("--skip-download", action="store_true", help="Skip downloading files (use existing input file)")
    parser.add_argument("--input", type=str, help="Input file with previously downloaded filings")
    parser.add_argument("--limit", type=int, default=1, help="Limit the number of filings to process")
    args = parser.parse_args()
    
    try:
        # Determine input data
        filings = []
        
        if args.skip_download and args.input:
            # Read filings from input file
            logger.info(f"Reading filings from input file: {args.input}")
            with open(args.input, "r") as f:
                filings = json.load(f)
            
            # Limit number of filings if requested
            if args.limit and args.limit > 0:
                filings = filings[:args.limit]
                logger.info(f"Limited to {len(filings)} filings from input file")
        
        else:
            # Fetch filings from SEC
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
                end_year = start_year  # Just use the start year for testing
                
                # Fetch filings for company
                logger.info(f"Fetching filings for {ticker} from {start_year} to {end_year}")
                filings = fetch_filings_for_company(ticker, start_year, end_year)
            
            # Limit number of filings if requested
            if args.limit and args.limit > 0 and len(filings) > args.limit:
                filings = filings[:args.limit]
                logger.info(f"Limited to {len(filings)} filings")
            
            # Download document content
            if filings:
                logger.info(f"Downloading document content for {len(filings)} filings")
                filings = download_filing_contents(filings)
                
                # Save filings to file
                input_file = args.input or "downloaded_filings.json"
                with open(input_file, "w") as f:
                    json.dump(filings, f, indent=2)
                logger.info(f"Saved downloaded filings to {input_file}")
        
        # Process filings into chunks
        if filings:
            logger.info(f"Processing {len(filings)} filings into chunks")
            chunks = process_filings(filings)
            
            if chunks:
                logger.info(f"Successfully processed {len(chunks)} chunks from {len(filings)} filings")
                
                # Save chunks to file
                output_file = args.output
                save_chunks_to_json(chunks, output_file)
                
                # Print sample chunk
                if chunks:
                    sample_chunk = chunks[0].copy()
                    sample_chunk["chunk_text"] = sample_chunk["chunk_text"][:200] + "..."  # Truncate text for display
                    print("\nSample chunk:")
                    print(json.dumps(sample_chunk, indent=2))
                
                # Print chunk statistics
                sections = {}
                for chunk in chunks:
                    section = chunk.get("section_name", "Unknown")
                    if section not in sections:
                        sections[section] = 0
                    sections[section] += 1
                
                print("\nChunks by section:")
                for section, count in sections.items():
                    print(f"  {section}: {count}")
            else:
                logger.warning("No chunks were generated from the filings")
        else:
            logger.warning("No filings to process")
        
        # Return success
        return 0
    
    except Exception as e:
        # Log error
        logger.error(f"Error testing document processing: {str(e)}")
        
        # Return failure
        return 1

if __name__ == "__main__":
    sys.exit(main())