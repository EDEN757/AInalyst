# S&P 500 10-K RAG Chatbot

A Retrieval-Augmented Generation (RAG) chatbot that enables users to query information from the 10-K filings of S&P 500 companies using natural language.

## Project Structure

```
sp500_rag_chatbot/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── chat.py             # Chat endpoint for RAG interactions
│   │   │   └── companies.py        # Endpoints for company data
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
│   │   │   └── CompanySelect.js    # Company dropdown component
│   │   ├── App.css
│   │   ├── App.js                  # Main React application
│   │   ├── index.css
│   │   └── index.js
│   ├── Dockerfile
│   └── package.json
├── postgres/
│   └── init.sql                    # pgvector extension setup
├── .env.example                    # Example environment variables
├── docker-compose.yml              # Container orchestration
├── .gitignore
└── README.md
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
- **Document Processing Pipeline**: Fetches, extracts, chunks, and embeds 10-K filings
- **Containerized Architecture**: Everything runs in Docker containers for easy deployment
- **Demo Mode**: Start with a subset of companies to explore functionality

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
   cd sp500_rag_chatbot
   ```

2. Create a `.env` file from the example:
   ```
   cp .env.example .env
   ```

3. Configure your `.env` file:

   a. **Embedding Configuration** (Used for BOTH documents and queries):
      ```
      EMBEDDING_PROVIDER=OPENAI
      EMBEDDING_MODEL=text-embedding-ada-002
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

   d. **Database Settings**:
      ```
      DATABASE_URL=postgresql://postgres:postgres@db:5432/sp500_db
      POSTGRES_USER=postgres
      POSTGRES_PASSWORD=postgres
      POSTGRES_DB=sp500_db
      ```

   e. **Application Mode**:
      ```
      APP_MODE=DEMO
      ```

4. **CRITICAL**: The `EMBEDDING_DIMENSION` parameter MUST accurately match the output dimension of your chosen `EMBEDDING_MODEL`. The database will create a `VECTOR(dimension)` column based on this value.

### Running the Application

1. Start all services:
   ```
   docker-compose up --build -d
   ```

2. Load initial data (only needs to be run once):
   ```
   docker-compose exec backend python /app/data_updater/update_job.py
   ```

3. Access the application:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000

### API Documentation

Once running, you can access the API documentation at:
- http://localhost:8000/docs

## Usage

1. **Chat Interface**: Enter questions about S&P 500 companies' 10-K filings
2. **Filtering**: Optionally filter by specific company and/or filing year
3. **Sources**: Each answer includes the source documents used to generate it

Example questions:
- "What are Apple's main risk factors?"
- "How did Microsoft's revenue change from 2021 to 2022?"
- "What is Amazon's strategy for international expansion?"

## Data Update Process

The data update process involves three main stages:

1. **Fetching**: Retrieve company information and 10-K filing URLs from the SEC
2. **Processing**: Extract text, split into sections, chunk into manageable pieces
3. **Embedding**: Generate vector embeddings for each chunk using the configured embedding model

You can run the full update or specific stages:
```
# Full update
docker-compose exec backend python /app/data_updater/update_job.py

# Skip specific stages
docker-compose exec backend python /app/data_updater/update_job.py --skip-fetch
docker-compose exec backend python /app/data_updater/update_job.py --skip-process
docker-compose exec backend python /app/data_updater/update_job.py --skip-embeddings
```

## Custom Configuration

### Changing Embedding Provider

1. Update `.env`:
   ```
   EMBEDDING_PROVIDER=GEMINI
   EMBEDDING_MODEL=models/embedding-001
   EMBEDDING_DIMENSION=768
   GOOGLE_API_KEY=your_google_key
   ```

2. Ensure you provide the correct dimension for the model

### Changing Chat Provider

1. Update `.env`:
   ```
   CHAT_PROVIDER=OPENAI
   CHAT_MODEL=gpt-4
   OPENAI_API_KEY=your_openai_key
   ```

2. No database schema changes are needed when switching chat providers

## License

[MIT License](LICENSE)

## Acknowledgments

- This project uses the SEC's EDGAR database for company filings
- Built with multiple LLM providers for flexible deployment options