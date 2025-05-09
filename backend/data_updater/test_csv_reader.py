import os
import sys
import logging
from dotenv import load_dotenv
import json

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

# Import the module to test
from data_updater.csv_reader import get_companies_for_update

def main():
    """Test CSV reading functionality"""
    try:
        # Get companies from CSV file
        csv_path = os.getenv("COMPANIES_CSV_PATH", "../companies.csv")
        companies = get_companies_for_update(csv_path)
        
        # Print companies as JSON
        print(f"Found {len(companies)} companies in CSV:")
        print(json.dumps(companies, indent=2))
        
        # Log success
        logger.info(f"Successfully read {len(companies)} companies from CSV")
        
        # Return success
        return 0
    
    except Exception as e:
        # Log error
        logger.error(f"Error testing CSV reader: {str(e)}")
        
        # Return failure
        return 1

if __name__ == "__main__":
    sys.exit(main())