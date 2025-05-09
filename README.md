# AInalyst

A Retrieval-Augmented Generation (RAG) chatbot that enables users to query information from SEC filings of companies using natural language.

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
│   │   ├── fetch_sec.py            # Fetches SEC filings
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
- **Document Processing Pipeline**: Fetches, extracts, chunks, and embeds SEC filings
- **CSV Import**: Import companies from a CSV file
- **Containerized Architecture**: Everything runs in Docker containers for easy deployment

## Technology Stack

- **Backend**: Python 3.10+, FastAPI, SQLAlchemy, pgvector
- **Database**: PostgreSQL with pgvector extension
- **Frontend**: React.js, Axios
- **AI Services**:
  - **Embedding**: OpenAI or Google Generative AI (Gemini)
  - **Chat**: OpenAI, Google Generative AI, or Anthropic Claude
- **Containerization**: Docker, Docker Compose

## Setup Instructions

### Prerequisites

- Docker and Docker Compose
- API keys for the LLM providers you plan to use (OpenAI, Google, Anthropic)

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
      CHAT_PROVIDER=CLAUDE
      CHAT_MODEL=claude-3-sonnet-20240229
      ```

   c. **API Keys** (Add keys for the providers you selected above):
      ```
      OPENAI_API_KEY=your_openai_key
      GOOGLE_API_KEY=your_google_key
      ANTHROPIC_API_KEY=your_anthropic_key
      ```

   d. **SEC Settings**:
      ```
      SEC_EMAIL=youremail@example.com
      # Optional: For using SEC API to query multiple filing types
      # Get your key from https://sec-api.io
      SEC_API_KEY=your_sec_api_key_here
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

1. Start all services:
   ```
   docker-compose up --build -d
   ```

2. Access the application:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

3. Import companies using the CSV method:
   - Edit `companies_to_import.csv` in the project root
   - Go to Company Management tab in the UI
   - Click "Import from CSV"

## Importing Companies from CSV

The system uses a CSV file to import companies and their filings from the SEC. The CSV file should be placed in the project root directory as `companies_to_import.csv`.

### CSV Format

The CSV file should contain the following columns:

- `ticker`: Company ticker symbol (e.g., AAPL) - **Required**
- `cik`: SEC Central Index Key (e.g., 0000320193) - *Optional but recommended*
- `doc_type`: SEC filing type (e.g., 10-K, 10-Q, 8-K) - **Required**
- `start_date`: Start date in ISO format (YYYY-MM-DD) - *Optional*
- `end_date`: End date in ISO format (YYYY-MM-DD) - *Optional*

Example:
```
ticker,cik,doc_type,start_date,end_date
AAPL,0000320193,10-K,2020-01-01,2023-12-31
MSFT,0000789019,10-K,2020-01-01,2023-12-31
GOOGL,0001652044,10-K,2020-01-01,2023-12-31
```

#### Notes:
- If `cik` is provided, it speeds up the import process
- If `start_date` or `end_date` are not provided, reasonable defaults will be used
- Valid `doc_type` values include: 10-K, 10-Q, 8-K, 10-K/A, 10-Q/A, 8-K/A, S-1, etc.
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

2. **Chat Interface**: Enter questions about companies' filings:
   - Filter by specific companies using the dropdown
   - Filter by specific filing year
   - View source documents for each answer

Example questions:
- "What are Apple's main risk factors?"
- "How did Microsoft's revenue change from 2021 to 2022?"
- "What is Amazon's strategy for international expansion?"

## Troubleshooting

### CSV Import Issues

- Make sure the CSV file is named exactly `companies_to_import.csv`
- Place the file in the project root directory (not inside backend or frontend folders)
- Check that the CSV has the correct format and headers
- Verify that the Docker containers have access to the file

### Connection Issues

If the frontend can't connect to the backend:

1. Check that both containers are running: `docker-compose ps`
2. Verify the backend logs for errors: `docker-compose logs backend`
3. Make sure the frontend is configured with the correct API URL
4. Check for CORS issues in the backend logs

### No Context Found / Empty Search Results

If the system reports "No context found" or gives generic responses despite having companies in the database, the embeddings may not be fully generated. Run this command to create missing embeddings:

```bash
docker exec -it sp500_rag_backend python -c 'from app.db.database import SessionLocal; from data_updater.create_embeddings import create_embeddings; db = SessionLocal(); print(create_embeddings(db)); db.close()'
```

You can monitor progress with:

```bash
docker exec -it sp500_rag_db psql -U postgres -d <your_db_name> -c "SELECT COUNT(*) as total_chunks, SUM(CASE WHEN embedded THEN 1 ELSE 0 END) as embedded_chunks FROM text_chunks;"
```

## License

[MIT License](LICENSE)

## Acknowledgments

- This project uses the SEC's EDGAR database for company filings
- Built with multiple LLM providers for flexible deployment options