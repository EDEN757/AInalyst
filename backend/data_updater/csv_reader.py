import os
import pandas as pd
import logging
from typing import List, Dict, Any, Optional

from ..core.config import settings

# Configure logging
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(settings.LOG_LEVEL)

def read_companies_csv(csv_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Read the companies CSV file and return its contents as a list of dictionaries.
    
    Parameters:
    - csv_path: Path to the CSV file (defaults to config)
    
    Returns:
    - List of company dictionaries with ticker, company_name, start_year, end_year
    """
    # Use default path if not specified
    csv_path = csv_path or settings.COMPANIES_CSV_PATH
    
    logger.info(f"Reading companies CSV from: {csv_path}")
    
    # Check if file exists
    if not os.path.exists(csv_path):
        logger.error(f"Companies CSV file not found at: {csv_path}")
        raise FileNotFoundError(f"Companies CSV file not found at: {csv_path}")
    
    try:
        # Read CSV file
        df = pd.read_csv(csv_path)
        
        # Validate required columns
        required_columns = ["ticker", "start_year", "end_year"]
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            logger.error(f"Missing required columns in CSV: {missing_columns}")
            raise ValueError(f"CSV file must contain columns: {required_columns}")
        
        # Convert to list of dictionaries
        companies = df.to_dict(orient="records")
        
        # Validate data types
        for company in companies:
            # Ensure ticker is a string
            company["ticker"] = str(company["ticker"])
            
            # Ensure years are integers
            company["start_year"] = int(company["start_year"])
            company["end_year"] = int(company["end_year"])
            
            # Set default company_name if not present
            if "company_name" not in company or pd.isna(company["company_name"]):
                company["company_name"] = company["ticker"]
        
        logger.info(f"Successfully read {len(companies)} companies from CSV")
        return companies
    
    except pd.errors.EmptyDataError:
        logger.error(f"CSV file is empty: {csv_path}")
        return []
    
    except pd.errors.ParserError as e:
        logger.error(f"Error parsing CSV file: {str(e)}")
        raise ValueError(f"Error parsing CSV file: {str(e)}")
    
    except Exception as e:
        logger.error(f"Unexpected error reading CSV: {str(e)}")
        raise

def validate_companies_data(companies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Validate and clean the companies data.
    
    Parameters:
    - companies: List of company dictionaries
    
    Returns:
    - Validated and cleaned company dictionaries
    """
    validated_companies = []
    
    for company in companies:
        try:
            # Validate required fields
            if not company.get("ticker"):
                logger.warning(f"Skipping company with missing ticker: {company}")
                continue
            
            # Validate year range
            start_year = int(company.get("start_year", 0))
            end_year = int(company.get("end_year", 0))
            
            if start_year <= 0 or end_year <= 0:
                logger.warning(f"Skipping company with invalid years: {company}")
                continue
            
            if start_year > end_year:
                logger.warning(f"Swapping start_year and end_year for: {company}")
                company["start_year"], company["end_year"] = end_year, start_year
            
            # Add to validated companies
            validated_companies.append({
                "ticker": str(company["ticker"]),
                "company_name": str(company.get("company_name", company["ticker"])),
                "start_year": int(company["start_year"]),
                "end_year": int(company["end_year"])
            })
        
        except Exception as e:
            logger.warning(f"Error validating company data: {str(e)}")
            continue
    
    logger.info(f"Validated {len(validated_companies)} companies")
    return validated_companies

def get_companies_for_update(csv_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get a list of companies for update from the CSV file.
    
    Parameters:
    - csv_path: Path to the CSV file (defaults to config)
    
    Returns:
    - List of validated company dictionaries ready for update
    """
    # Read companies from CSV
    companies = read_companies_csv(csv_path)
    
    # Validate companies data
    validated_companies = validate_companies_data(companies)
    
    return validated_companies