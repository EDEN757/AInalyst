<<<<<<< Updated upstream
# AInalyst

A Retrieval-Augmented Generation (RAG) chatbot that enables users to query information from SEC 10-K filings of companies using natural language.

## Project Structure

```
AInalyst/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── chat.py             # Chat endpoint for RAG interactions
│   │   │   ├── companies.py        # Endpoints for company data
│   │   │   └── companies_csv.py    # CSV import endpoint for companies
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   └── config.py           # Configuration with Embed/Chat separation
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   ├── crud.py             # Database operations
│   │   │   └── database.py         # Database connection setup
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── chat_models.py      # Pydantic models for the API
│   │   │   └── database_models.py  # SQLAlchemy database models
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── llm_clients.py      # LLM provider integrations
│   │   │   └── rag_service.py      # Core RAG implementation
│   │   ├── __init__.py
│   │   └── main.py                 # FastAPI application
│   ├── data_updater/
│   │   ├── __init__.py
│   │   ├── create_embeddings.py    # Uses ONLY Embedding config
│   │   ├── fetch_sec.py            # Fetches SEC 10-K filings
│   │   ├── process_docs.py         # Processes filings into chunks
│   │   └── update_job.py           # Main update pipeline
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── public/
│   │   └── index.html
│   ├── src/
│   │   ├── components/
│   │   │   ├── ChatMessage.js      # Chat message component
│   │   │   ├── CompanySelect.js    # Company dropdown component
│   │   │   └── CompanyManagement.js # Company management interface
│   │   ├── App.css
│   │   ├── App.js                  # Main React application
│   │   ├── index.css
│   │   └── index.js
│   ├── Dockerfile
│   └── package.json
├── postgres/
│   └── init.sql                    # pgvector extension setup
├── companies_to_import.csv         # CSV file with companies to import
├── docker-compose.yml              # Container orchestration
├── LICENSE                         # MIT License
└── README.md                       # This file
```

## Architecture Overview

This application features a clear separation between the **embedding process** and the **chat generation process**:

1. **Fixed Embedding Model**: A single, consistent embedding model (configured via `EMBEDDING_*` variables) is used for both:
   - Processing document chunks during indexing
   - Embedding user queries during RAG retrieval

2. **Flexible Chat Model**: A separate chat model (configured via `CHAT_*` variables) is used exclusively for:
   - Generating the final response based on retrieved text chunks

This separation allows you to optimize for different use cases:
- Use smaller, faster embedding models for vector search
- Use more powerful chat models for high-quality answer generation

## Key Features

- **Vector Similarity Search**: Uses PostgreSQL with pgvector extension to store and query document vectors
- **Configurable Models**: Set different providers and models for embedding vs. chat generation
- **Interactive Chat Interface**: React-based UI with filtering by company and year
- **Company Management Interface**: Add, view, and delete companies directly through the UI
- **Document Processing Pipeline**: Fetches, extracts, chunks, and embeds SEC 10-K filings
- **CSV Import**: Import companies from a CSV file
- **Containerized Architecture**: Everything runs in Docker containers for easy deployment

## Technology Stack

- **Backend**: Python 3.10+, FastAPI, SQLAlchemy, pgvector
- **Database**: PostgreSQL with pgvector extension
- **Frontend**: React.js, Axios
- **AI Services**:
  - **Embedding**: OpenAI
  - **Chat**: OpenAI
- **Containerization**: Docker, Docker Compose

## Setup Instructions

### Prerequisites

- Docker and Docker Compose
- API keys for OpenAI

### Installation

1. Clone this repository:
   ```
   git clone <repository-url>
   cd AInalyst
   ```

2. Create a `.env` file from the example:
   ```
   cp .env.example .env
   ```

3. Configure your `.env` file:

   a. **Embedding Configuration** (Used for BOTH documents and queries):
      ```
      EMBEDDING_PROVIDER=OPENAI
      EMBEDDING_MODEL=text-embedding-3-small
      EMBEDDING_DIMENSION=1536
      ```

   b. **Chat Generation Configuration** (Used ONLY for final answer generation):
      ```
      CHAT_PROVIDER=OPENAI
      CHAT_MODEL=gpt-4-turbo
      ```

   c. **API Keys**:
      ```
      OPENAI_API_KEY=your_openai_key
      ```

   d. **SEC Settings**:
      ```
      SEC_EMAIL=youremail@example.com
      ```

   e. **Database Settings**:
      ```
      DATABASE_URL=postgresql://postgres:postgres@db:5432/sp500_db
      POSTGRES_USER=postgres
      POSTGRES_PASSWORD=postgres
      POSTGRES_DB=sp500_db
      ```

   f. **Application Configuration**:
      ```
      # Application mode
      APP_MODE=FULL
      ```

4. **CRITICAL**: The `EMBEDDING_DIMENSION` parameter MUST accurately match the output dimension of your chosen `EMBEDDING_MODEL`. The database will create a `VECTOR(dimension)` column based on this value.

### Running the Application

1. Edit the `companies_to_import.csv` file in the project root with the companies you want to analyze:
   ```
   ticker,cik,start_date,end_date
   AAPL,0000320193,2020-01-01,2023-12-31
   MSFT,0000789019,2020-01-01,2023-12-31
   GOOGL,0001652044,2020-01-01,2023-12-31
   ```

2. Start all services:
   ```
   docker-compose up --build -d
   ```

3. Access the application:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

4. Import companies using the CSV method:
   - Go to Company Management tab in the UI
   - Click "Import from CSV"

## Importing Companies Using CSV

The system uses a CSV file to import companies and their 10-K filings from the SEC. The CSV file should be placed in the project root directory as `companies_to_import.csv`.

### CSV Format

The CSV file should contain the following columns:

- `ticker`: Company ticker symbol (e.g., AAPL) - **Required**
- `cik`: SEC Central Index Key (e.g., 0000320193) - *Optional but recommended for faster processing*
- `start_date`: Start date in ISO format (YYYY-MM-DD) - *Optional (defaults to 3 years ago)*
- `end_date`: End date in ISO format (YYYY-MM-DD) - *Optional (defaults to current year)*

Example:
```
ticker,cik,start_date,end_date
AAPL,0000320193,2020-01-01,2023-12-31
MSFT,0000789019,2020-01-01,2023-12-31
GOOGL,0001652044,2020-01-01,2023-12-31
```

#### Notes:
- This application only supports 10-K filings
- If `cik` is provided, it speeds up the import process
- If `start_date` or `end_date` are not provided, reasonable defaults will be used
- Processing happens in the background - check the status in the UI

### Import Process

1. Prepare the CSV file with the companies you want to import
2. Place the file at the project root as `companies_to_import.csv`
3. Go to the Company Management tab in the UI
4. Click "Import from CSV"
5. The system will process the companies in the background
6. You can check the import status on the Company Management page

## Usage

1. **Company Management**: Access the "Company Management" tab to:
   - View companies currently in your database
   - See details of company filings
   - Import companies via CSV
   - Delete companies you no longer need

2. **Chat Interface**: Enter questions about companies' 10-K filings:
   - Filter by specific companies using the dropdown
   - Filter by specific filing year
   - View source documents for each answer

Example questions:
- "What are Apple's main risk factors?"
- "How did Microsoft's revenue change from 2021 to 2022?"
- "What is Amazon's strategy for international expansion?"

## Troubleshooting

### CSV Import Issues

- **Missing CSV File**: Make sure the CSV file is named exactly `companies_to_import.csv` and placed in the project root directory.
  
  - **Solution**: If the file doesn't exist, the system will create a template file automatically. You can also use the API endpoint `GET /companies/csv-template` to get a template.

- **CSV Format Issues**: Ensure the CSV has at least a ticker column. The system logs will show which rows were skipped and why.
  
  - **Solution**: Follow the format described in the "CSV Format" section above.

- **No Companies Found**: Check the logs to see if any companies were successfully extracted from the CSV.
  
  - **Solution**: Verify that the CSV contains valid ticker symbols.

### SEC API Rate Limits

- **Rate Limit Errors**: The SEC API has rate limits that can cause fetch failures.
  
  - **Solution**: The system includes pauses to respect rate limits, but if you're processing many companies, you might need to split the imports into smaller batches.

### Connection Issues

If the frontend can't connect to the backend:

1. Check that both containers are running: `docker-compose ps`
2. Verify the backend logs for errors: `docker-compose logs backend`
3. Make sure the frontend is configured with the correct API URL
4. Check for CORS issues in the backend logs

### No Context Found / Empty Search Results

If the system reports "No context found" or gives generic responses despite having companies in the database:

1. **Check Database Status**: Verify that companies, filings, and chunks are properly imported:
   ```bash
   docker-compose exec db psql -U postgres -d sp500_db -c "SELECT COUNT(*) FROM companies;"
   docker-compose exec db psql -U postgres -d sp500_db -c "SELECT COUNT(*) FROM filings;"
   docker-compose exec db psql -U postgres -d sp500_db -c "SELECT COUNT(*) FROM text_chunks WHERE embedded = true;"
   ```

2. **Manually Create Embeddings**: If necessary, force the creation of embeddings:
   ```bash
   docker-compose exec backend python -c 'from app.db.database import SessionLocal; from data_updater.create_embeddings import create_embeddings; db = SessionLocal(); print(create_embeddings(db)); db.close()'
   ```

3. **Run Data Updater**: Process any unprocessed filings:
   ```bash
   docker-compose exec backend python run_data_updater.py
   ```

4. **Monitor Progress**: Check embedding progress with:
   ```bash
   docker-compose exec db psql -U postgres -d sp500_db -c "SELECT COUNT(*) as total_chunks, SUM(CASE WHEN embedded THEN 1 ELSE 0 END) as embedded_chunks FROM text_chunks;"
   ```

### API Implementation Issues

If you encounter problems with the API:

1. **Check OpenAI API Key**: Verify that your OpenAI API key is valid and has sufficient credits.
2. **Enable Debug Logging**: Add `LOG_LEVEL=DEBUG` to your .env file for more detailed logs.
3. **Inspect API Documentation**: Visit http://localhost:8000/docs to explore available endpoints.

## Common Issues and Solutions

### Problem: Import Process Takes Too Long

- **Cause**: Processing many companies at once or SEC API rate limits.
- **Solution**: Import fewer companies at a time or provide CIK values to speed up lookups.

### Problem: Search Returns No Results

- **Cause**: No embedded chunks or query not matching available content.
- **Solution**: Verify embeddings exist (see above). Try different search terms or filter by companies that you know have data.

### Problem: Database Connection Errors

- **Cause**: PostgreSQL not fully initialized or incorrect credentials.
- **Solution**: Check if the database container is running and verify credentials in .env file.

## License

[MIT License](LICENSE)

## Acknowledgments

- This project uses the SEC's EDGAR database for company filings
- Built with OpenAI for embeddings and chat generation
=======
## README

### Overview
This Python script **download_filings.py** automates fetching 10-K filings from the SEC EDGAR system for a list of US companies, preparing them for retrieval-augmented generation (RAG) workflows. You provide a CSV of tickers and date ranges; it downloads each 10-K, extracts the main text, and saves it as a JSON file with metadata.

### Requirements
- Python **3.7** or higher  
- Packages:
  ```bash
  pip install requests python-dateutil
### Input CSV Format
	•	ticker,start_date,end_date
AAPL,2020-01-01,2021-12-31
MSFT,2019-07-01,2020-06-30
	ticker: Stock symbol (e.g. AAPL)
	•	start_date, end_date: Date range in YYYY-MM-DD for the filings
### Usage
python download_filings.py companies.csv \
  --user-agent "YourName YourApp your.email@example.com"
Optional flags:
	•	--output-dir: where to store downloaded data (default data/)
	•	--mapping-file: local path for the ticker→CIK mapping JSON (default company_tickers.json)

### How It Works
	1.	Mapping: Loads or downloads SEC’s company_tickers.json to map tickers → CIKs.
	2.	Submissions Index: Queries https://data.sec.gov/submissions/CIK{CIK}.json for each company.
	3.	Filtering: Selects filings where form == "10-K" and the filingDate falls in your CSV’s date range.
	4.	Idempotency: Checks if data/<TICKER>/<ACCESSION>.json already exists; skips downloads to avoid duplicates.
	5.	Downloading: Fetches the raw text file from https://www.sec.gov/Archives/edgar/data/{CIK}/{ACCESSIONNODASH}/{ACCESSIONNODASH}.txt.
	6.	Extraction: Parses out the <TEXT> section of the 10-K document.
	7.	Serialization: Saves a JSON record per filing containing:
	•	ticker, cik, accession
	•	filing_date, form, document_url
	•	text (the extracted filing body)

### Output Structure
data/
└─ AAPL/
   ├─ 0000320193-21-000010.json
   ├─ 0000320193-20-000010.json
   └─ ...
└─ MSFT/
   ├─ 0000789019-20-000010.json
   └─ ...
### Customization & Best Practices
	•	User-Agent: SEC requires a descriptive User-Agent; set it to your app name and contact email.
	•	Rate Limiting: The script includes a short time.sleep(0.1) between downloads to respect SEC limits. Adjust if needed.
>>>>>>> Stashed changes
