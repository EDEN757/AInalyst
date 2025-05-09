#!/usr/bin/env python
"""
Direct database insertion script for AInalyst.

This script bypasses the SEC API fetch process and directly inserts
sample company data into the database for testing purposes.
"""

import os
import sys
import uuid
import asyncio
import logging
import hashlib
import argparse
from typing import List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

# Add app directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.db.database import engine, Base, SessionLocal
from app.models.database_models import FilingMetadata, DocumentVector, DocumentChunk
from app.core.config import settings
from app.services.llm_clients import create_embedding_sync

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Sample company data with mock filing content
SAMPLE_COMPANIES = [
    {
        "ticker": "AAPL",
        "name": "Apple Inc.",
        "years": [2020, 2021, 2022, 2023],
        "sections": ["Summary", "Risk Factors", "Management Discussion", "Financial Statements"]
    },
    {
        "ticker": "MSFT",
        "name": "Microsoft Corporation",
        "years": [2020, 2021, 2022, 2023],
        "sections": ["Summary", "Risk Factors", "Management Discussion", "Financial Statements"]
    },
    {
        "ticker": "AMZN",
        "name": "Amazon.com Inc.",
        "years": [2020, 2021, 2022, 2023],
        "sections": ["Summary", "Risk Factors", "Management Discussion", "Financial Statements"]
    },
    {
        "ticker": "GOOGL",
        "name": "Alphabet Inc.",
        "years": [2020, 2021, 2022, 2023],
        "sections": ["Summary", "Risk Factors", "Management Discussion", "Financial Statements"]
    },
    {
        "ticker": "META",
        "name": "Meta Platforms Inc.",
        "years": [2020, 2021, 2022, 2023],
        "sections": ["Summary", "Risk Factors", "Management Discussion", "Financial Statements"]
    }
]

# Sample section content templates
SECTION_TEMPLATES = {
    "Summary": "{company_name} ({ticker}) is a leading technology company. For the fiscal year {year}, "
               "the company reported strong performance across its major business segments.",
    
    "Risk Factors": "Investment in {company_name} ({ticker}) stock involves risks. In {year}, "
                   "the company faced increasing competition, regulatory challenges, and supply chain disruptions.",
    
    "Management Discussion": "Management of {company_name} ({ticker}) is pleased with the company's performance in {year}. "
                            "Revenue grew by approximately 15% compared to the previous year, driven by strong demand "
                            "for our products and services.",
    
    "Financial Statements": "Financial highlights for {company_name} ({ticker}) in {year}:\n"
                           "- Revenue: $XXX billion\n"
                           "- Net Income: $XX billion\n"
                           "- EPS: $X.XX\n"
                           "- Cash and Equivalents: $XX billion"
}

def get_db():
    """Create a database session."""
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()

def generate_text_hash(text: str) -> str:
    """Generate a hash for the given text."""
    return hashlib.md5(text.encode()).hexdigest()

async def create_embedding(text: str) -> List[float]:
    """Create an embedding for the given text."""
    try:
        embedding = await create_embedding_sync(text, settings.DEFAULT_EMBEDDING_MODEL)
        return embedding
    except Exception as e:
        logger.error(f"Error creating embedding: {str(e)}")
        # Return a dummy embedding of the correct dimension
        return [0.0] * settings.EMBEDDING_DIMENSION

async def insert_company_data(db: Session, company: Dict[str, Any]):
    """Insert data for a single company."""
    ticker = company["ticker"]
    name = company["name"]
    years = company["years"]
    sections = company["sections"]
    
    logger.info(f"Inserting data for {name} ({ticker})")
    
    for year in years:
        for section in sections:
            # Generate document content
            section_content = SECTION_TEMPLATES[section].format(
                company_name=name,
                ticker=ticker,
                year=year
            )
            
            # Generate a unique document ID
            doc_id = str(uuid.uuid4())
            
            # Calculate text hash
            text_hash = generate_text_hash(section_content)
            
            # Create filing date (just use January 1 of the year for simplicity)
            filing_date = f"{year}-01-01"
            
            # Generate embedding
            embedding = await create_embedding(section_content)
            
            # Create database records
            try:
                # 1. Insert filing metadata
                db_metadata = FilingMetadata(
                    doc_id=doc_id,
                    ticker=ticker,
                    year=year,
                    document_type="10-K",
                    filing_date=filing_date,
                    section_name=section,
                    source_url=f"https://example.com/{ticker}/{year}/10-K",
                    page_number=1,
                    embedding_model=settings.DEFAULT_EMBEDDING_MODEL,
                    text_hash=text_hash
                )
                db.add(db_metadata)
                
                # 2. Insert document vector
                db_vector = DocumentVector(
                    doc_id=doc_id,
                    embedding=embedding
                )
                db.add(db_vector)
                
                # 3. Insert document chunk
                db_chunk = DocumentChunk(
                    doc_id=doc_id,
                    chunk_text=section_content,
                    chunk_number=1,
                    total_chunks=1
                )
                db.add(db_chunk)
                
                # Commit the transaction
                db.commit()
                logger.info(f"Inserted {ticker} {year} {section}")
                
            except Exception as e:
                db.rollback()
                logger.error(f"Error inserting {ticker} {year} {section}: {str(e)}")

async def main():
    """Main function to insert sample data."""
    # Create command-line argument parser
    parser = argparse.ArgumentParser(description="Insert sample company data into the database")
    parser.add_argument("--create-tables", action="store_true", help="Create database tables if they don't exist")
    args = parser.parse_args()
    
    # Create tables if requested
    if args.create_tables:
        logger.info("Creating database tables")
        Base.metadata.create_all(bind=engine)
    
    # Get database session
    db = get_db()
    
    try:
        # Insert data for each company
        for company in SAMPLE_COMPANIES:
            await insert_company_data(db, company)
        
        logger.info("Sample data insertion complete")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(main())