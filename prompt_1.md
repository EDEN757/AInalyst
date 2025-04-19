# **LLM Code Generation Prompt: S&P 500 10-K RAG Chatbot**

**Persona:** Act as an expert full-stack software engineer specializing in Python, React, PostgreSQL, Docker, and building AI-powered applications with RAG pipelines using OpenAI.

**Overall Goal:** Generate the complete codebase and configuration files for a RAG (Retrieval-Augmented Generation) chatbot. This chatbot allows users to ask questions about the 10-K filings of S&P 500 companies. The system features a data pipeline for fetching and processing filings, a PostgreSQL database with pgvector for storage and retrieval, a FastAPI backend API implementing the RAG logic with OpenAI, and a React frontend for user interaction. The entire system must be containerized using Docker and Docker Compose for easy setup and deployment. Include a "Demo Mode" for quick testing using only Apple's 2024 10-K.

**Core Technologies:**
*   **Backend:** Python 3.10+, FastAPI, Uvicorn, SQLAlchemy (or psycopg2-binary directly), OpenAI Python client, python-dotenv, tiktoken, requests, beautifulsoup4 (consider `sec-edgar-downloader` library logic if feasible).
*   **Database:** PostgreSQL (latest stable), pgvector extension.
*   **Frontend:** React.js (latest stable), axios (or fetch API).
*   **AI:** OpenAI API (Embeddings: e.g., `text-embedding-ada-002`, Chat: e.g., `gpt-3.5-turbo` or `gpt-4`).
*   **Containerization:** Docker, Docker Compose.
*   **Vector Embedding Dimension:** Assume 1536 (for `text-embedding-ada-002`).

**Project Structure:**
Generate files according to this directory structure:

your-project-name/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   └── chat.py
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   └── config.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   └── rag_service.py
│   │   ├── models/             # Pydantic models
│   │   │   ├── __init__.py
│   │   │   └── chat_models.py
│   │   └── db/
│   │       ├── __init__.py
│   │       ├── database.py     # DB Session setup, pgvector check
│   │       └── crud.py         # Functions to interact with DB tables
│   ├── data_updater/
│   │   ├── __init__.py
│   │   ├── fetch_sec.py
│   │   ├── process_docs.py
│   │   ├── create_embeddings.py
│   │   └── update_job.py       # Orchestrator script
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   ├── public/
│   │   └── index.html
│   ├── src/
│   │   ├── App.js
│   │   ├── components/
│   │   │   ├── ChatInterface.js
│   │   │   └── LoadingSpinner.js # Optional simple spinner
│   │   └── services/
│   │       └── api.js
│   ├── Dockerfile
│   ├── package.json        # Include necessary dependencies (react, react-dom, axios)
│   └── .env.example        # Example: REACT_APP_API_BASE_URL=http://localhost:8000
│
├── postgres/
│   └── init.sql            # Optional: Script to CREATE EXTENSION IF NOT EXISTS vector;
│
├── .env                     # User-managed, GITIGNORED
├── docker-compose.yml
├── README.md
└── .gitignore

**Step-by-Step Implementation Details:**

**1. Database Setup (PostgreSQL + pgvector):**
    *   **`postgres/init.sql` (Optional):** Include `CREATE EXTENSION IF NOT EXISTS vector;`. This ensures the extension is enabled when the container starts.
    *   **`backend/app/db/database.py`:**
        *   Define PostgreSQL connection string retrieval from environment variable `DATABASE_URL`.
        *   Set up SQLAlchemy engine and session maker (or direct psycopg2 connection pool).
        *   Include a function to check if the `pgvector` extension is installed and raise an error if not.
    *   **`backend/app/db/crud.py`:** Define functions for:
        *   Storing company info (CIK, ticker, name).
        *   Storing filing metadata (linking to company, filing date, type, SEC URL).
        *   Storing text chunks (`chunk_text`, `filing_id`).
        *   Storing/Updating embeddings (`embedding` VECTOR(1536)) for text chunks.
        *   Performing vector similarity search: Given a query vector, retrieve the top `k` most similar `chunk_text` entries using the `<=>` operator (`ORDER BY embedding <=> query_embedding LIMIT k`).
        *   Marking filings/chunks as processed.
        *   Potentially clearing data for a specific company if re-processing is needed.

**2. Data Acquisition & Processing Pipeline (`backend/data_updater/`):**
    *   **Environment Variable for Mode:** Use an environment variable `APP_MODE` (e.g., `APP_MODE=DEMO` or `APP_MODE=FULL`). Default to `FULL` if not set.
    *   **`fetch_sec.py`:**
        *   If `APP_MODE == 'DEMO'`:
            *   Target *only* Apple (AAPL, CIK: 0000320193).
            *   Attempt to download *only* its 2024 10-K filing. If not found, log a warning.
        *   If `APP_MODE == 'FULL'`:
            *   Fetch/update a list of S&P 500 tickers and their CIKs (suggest a simple source like a hardcoded list or a reliable free source). Store/update in the DB.
            *   For each company, check the DB for the last processed filing date.
            *   Query SEC EDGAR (respecting rate limits with delays) to find and download any *new* 10-K filings since the last check.
        *   Store basic filing metadata (URL, date, company link) in the database, marking it as "downloaded".
    *   **`process_docs.py`:**
        *   Fetch unprocessed (downloaded) filings from the DB.
        *   Read the filing content (likely HTML). Use BeautifulSoup4 to parse and extract relevant text (e.g., from sections like "Item 1A", "Item 7"). Clean the text (remove boilerplate, excessive whitespace).
        *   Implement robust text chunking: Use `tiktoken` to estimate token count. Split text into meaningful chunks (e.g., by paragraphs or sections) aiming for a max token count per chunk (e.g., 500 tokens). Ensure chunks don't awkwardly split sentences if possible.
        *   Store each text chunk in the `text_chunks` table, linked to its parent filing, and mark it as "chunked".
    *   **`create_embeddings.py`:**
        *   Fetch "chunked" text chunks from the DB that don't yet have an embedding.
        *   Retrieve `OPENAI_API_KEY` from environment variables via `backend/app/core/config.py`.
        *   Batch the chunks (respecting OpenAI API limits).
        *   Call the OpenAI Embeddings API (`text-embedding-ada-002` or preferred model) to get vector embeddings for each chunk.
        *   Store the returned vectors in the `embedding` column for the corresponding chunks in the DB. Implement error handling and retries for API calls. Mark chunks as "embedded".
    *   **`update_job.py`:**
        *   Main script to orchestrate the pipeline.
        *   Reads `APP_MODE` environment variable.
        *   Calls `fetch_sec.py`, `process_docs.py`, and `create_embeddings.py` in sequence.
        *   Include clear logging for each step (e.g., "Starting fetch...", "Fetched X filings...", "Processing file Y...", "Generating embeddings for Z chunks...").
        *   This script is intended to be run periodically (e.g., via cron or a Docker scheduled task).

**3. Backend API (`backend/app/`):**
    *   **`backend/app/core/config.py`:** Use Pydantic's `BaseSettings` to load environment variables (`OPENAI_API_KEY`, `DATABASE_URL`, `APP_MODE`).
    *   **`backend/app/models/chat_models.py`:** Define Pydantic models for API request (`UserQuery` with `query: str`) and response (`ChatResponse` with `answer: str`, maybe `sources: List[str]`).
    *   **`backend/app/services/rag_service.py`:**
        *   Implement the core RAG logic:
            *   Accept the user query string.
            *   Get OpenAI API key from config.
            *   Generate embedding for the user query using the OpenAI Embeddings API.
            *   Use `db/crud.py` function to perform vector similarity search in the `text_chunks` table against the query embedding, retrieving top `k` (e.g., k=5) relevant text chunks.
            *   Construct the prompt for the OpenAI Chat Completions API: Include clear instructions (e.g., "Answer the user's question based *only* on the following context extracted from SEC 10-K filings. If the context doesn't contain the answer, say you don't have information based on the provided documents."), the retrieved text chunks as context, and the original user query.
            *   Call the OpenAI Chat Completions API (e.g., `gpt-3.5-turbo`).
            *   Process the response. Optionally, try to extract which company the context chunks came from to add basic sourcing.
            *   Return the final answer.
    *   **`backend/app/api/chat.py`:**
        *   Define a FastAPI router.
        *   Create a POST endpoint `/api/v1/chat`.
        *   It should accept `UserQuery` model as input.
        *   Call the `rag_service.py` function to get the answer.
        *   Return the `ChatResponse` model.
        *   Handle potential errors gracefully (e.g., return HTTP 500 if RAG fails).
    *   **`backend/app/main.py`:**
        *   Create the FastAPI app instance.
        *   Include the chat API router (`/api/v1/chat`).
        *   Implement CORS middleware to allow requests from the frontend's origin (e.g., `http://localhost:3000`).
        *   Add a root endpoint `/` that returns a simple status message (e.g., `{"status": "ok"}`).
        *   Optionally, add startup event to check DB connection and pgvector extension.
    *   **`backend/requirements.txt`:** List all Python dependencies (`fastapi`, `uvicorn[standard]`, `sqlalchemy`, `psycopg2-binary`, `openai`, `python-dotenv`, `tiktoken`, `requests`, `beautifulsoup4`, `pgvector` - ensure Python bindings if needed, e.g. `sqlalchemy-pgvector`).
    *   **`backend/Dockerfile`:**
        *   Use a Python base image (e.g., `python:3.10-slim`).
        *   Set up working directory.
        *   Copy `requirements.txt` and install dependencies.
        *   Copy the rest of the `backend` directory.
        *   Expose the API port (e.g., 8000).
        *   Set the default command to run Uvicorn (`CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]`).

**4. Frontend (React):**
    *   **`frontend/package.json`:** Include `react`, `react-dom`, `axios`.
    *   **`frontend/src/services/api.js`:**
        *   Define a function `sendQuery(query)` that:
            *   Reads the backend API base URL from React environment variables (`REACT_APP_API_BASE_URL`).
            *   Sends a POST request to `/api/v1/chat` on the backend with the user's query in the request body (`{ "query": query }`).
            *   Returns the `answer` from the JSON response.
            *   Includes error handling.
    *   **`frontend/src/components/ChatInterface.js`:**
        *   Manage state for: user input, chat history (list of `{sender: 'user'/'bot', text: 'message'}` objects), loading status.
        *   Render a chat message display area iterating over the chat history.
        *   Render a text input field and a send button.
        *   On send:
            *   Add user message to history.
            *   Set loading state to true.
            *   Call `sendQuery()` from `api.js`.
            *   On success: Add bot response to history, clear input, set loading to false.
            *   On error: Add an error message to history, set loading to false.
            *   Optionally display `LoadingSpinner.js` when loading.
    *   **`frontend/src/App.js`:** Main application component, renders `ChatInterface`.
    *   **`frontend/Dockerfile`:**
        *   Use a multi-stage build.
        *   Stage 1: Use Node image (`node:18-alpine` or similar), copy `package.json`, install dependencies (`npm install`), copy source code, build the React app (`npm run build`).
        *   Stage 2: Use a lightweight web server image (e.g., `nginx:alpine`), copy the built static files from Stage 1 (`build` directory) to the Nginx HTML directory. Configure Nginx to serve the React app (handle routing correctly). Expose port 80.
    *   **`frontend/.env.example`:** Provide `REACT_APP_API_BASE_URL=http://localhost:8000` (adjust port if necessary).

**5. Container Orchestration (`docker-compose.yml`):**
    *   Define three services: `db`, `backend`, `frontend`.
    *   **`db` service:**
        *   Use a PostgreSQL image that includes `pgvector` (e.g., `pgvector/pgvector:pg15` or build your own).
        *   Mount a named volume for data persistence (`postgres_data:/var/lib/postgresql/data`).
        *   Pass database credentials (`POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`) via environment variables loaded from the main `.env` file.
        *   Optionally mount `postgres/init.sql` to `/docker-entrypoint-initdb.d/`.
        *   Expose port 5432 only internally unless needed externally.
    *   **`backend` service:**
        *   Build from `backend/Dockerfile`.
        *   Depend on `db` (`depends_on: [db]`).
        *   Mount the `backend` directory as a volume for development hot-reloading (`./backend:/app`).
        *   Pass environment variables from the main `.env` file (`DATABASE_URL`, `OPENAI_API_KEY`, `APP_MODE`). Ensure `DATABASE_URL` uses the service name (e.g., `postgresql://user:password@db:5432/dbname`).
        *   Map backend port (e.g., `8000:8000`).
    *   **`frontend` service:**
        *   Build from `frontend/Dockerfile`.
        *   Map frontend port (e.g., `3000:80` if Nginx serves on 80).
        *   Pass build arguments or environment variables if needed (like `REACT_APP_API_BASE_URL` pointing to the backend service, although often handled by proxy or direct call to exposed backend port).
    *   Define the named volume `postgres_data`.

**6. Configuration and Documentation:**
    *   **`.env` (User Provided, Gitignored):** User needs to create this file based on `.env.example` files. Must contain:
        *   `OPENAI_API_KEY=sk-...`
        *   `DATABASE_URL=postgresql://youruser:yourpassword@db:5432/yourdb`
        *   `POSTGRES_USER=youruser`
        *   `POSTGRES_PASSWORD=yourpassword`
        *   `POSTGRES_DB=yourdb`
        *   `APP_MODE=DEMO` # Or FULL
        *   `REACT_APP_API_BASE_URL=http://localhost:8000` # For frontend .env
    *   **`.gitignore`:** Include standard ignores for Python (`__pycache__`, `.venv`), Node (`node_modules`), Docker (`.dockerignore` content if needed), and crucially `.env`.
    *   **`README.md`:** Generate a comprehensive README containing:
        *   Project Overview.
        *   Features.
        *   Architecture Diagram (text-based or link placeholder).
        *   Prerequisites (Docker, Docker Compose, Git).
        *   **Setup Instructions:**
            1.  Clone repo.
            2.  Create `.env` from `.env.example` and add `OPENAI_API_KEY` and DB credentials.
            3.  Set `APP_MODE` in `.env` (`DEMO` or `FULL`).
            4.  Run `docker-compose up --build -d`.
        *   **Initial Data Loading:**
            *   Explain that data needs to be fetched and processed.
            *   Provide the command to trigger the initial run: `docker-compose exec backend python /app/data_updater/update_job.py`
            *   **Crucially:** Explain the difference between `DEMO` mode (quick, only AAPL 2024 10-K) and `FULL` mode (S&P 500, takes significant time and OpenAI embedding costs). Advise starting with `DEMO`.
        *   **Usage:** Access frontend at `http://localhost:3000` (or configured port).
        *   **Daily Updates:** Explain the concept - the `update_job.py` needs to be run periodically. Suggest using `cron` on the host machine targeting `docker-compose exec backend python /app/data_updater/update_job.py` or setting up a dedicated scheduler container.
        *   **Troubleshooting:** Common issues (API key errors, DB connection, CORS).

**Final Instructions for LLM:**
*   Generate the code for each file specified in the structure.
*   Use type hints in Python code.
*   Include basic error handling (try-except blocks) especially around API calls, file I/O, and DB operations.
*   Add comments explaining key logic sections, especially the RAG pipeline steps and database interactions.
*   Ensure environment variables are used correctly for configuration.
*   The generated code should be functional and adhere to the structure and requirements outlined above.
*   Present the output clearly, likely file by file within code blocks.