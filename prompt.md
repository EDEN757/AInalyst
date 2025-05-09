# 📊 Finance Chatbot with RAG — LLM Agent Playbook (v2.3.1 - Doc Lookup Directive)

## 🎯 Objective
Build and deploy a **public, open-source** Retrieval-Augmented Generation (RAG)–powered finance chatbot that:
1. Ingests 10-K filings for U.S. public companies (year ranges defined in a `companies.csv` file in the project root, editable by the user).
2. Parses and embeds text via OpenAI Embedding API (model selectable, API key managed by end-user).
3. Stores embeddings and metadata in **PostgreSQL (using the `pgvector` extension for vector storage and search)**.
4. Serves a React-based Chat UI + Database Explorer.
5. Auto-updates new filings based on `companies.csv` on launch or via cron.
6. Is designed for easy setup and deployment by the community.

---

## 📝 Open Source Project Directives
*   **Public Repository**: This project will be hosted in a public Git repository (e.g., on GitHub or GitLab).
*   **Open Source License**: Include a standard open-source license (e.g., MIT or Apache 2.0) in the repository root. The agent should select an appropriate one.
*   **No Private Information**:
    *   No private API keys (e.g., `OPENAI_API_KEY`), database credentials, or any personal/sensitive data should be hardcoded into the source code.
    *   All such configurations must be managed via environment variables or configuration files explicitly excluded from the repository (e.g., using a `.gitignore` file for `config.yaml` or `.env` files containing secrets).
    *   Provide a template configuration file (e.g., `config.example.yaml` or `.env.example`).
*   **Community Focused**: Design for ease of understanding, setup, and contribution by the open-source community. Prioritize clear documentation and standard tooling.

---

## ⚙️ Global Configuration (`config.yaml` or `.env.example`)
*   `OPENAI_API_KEY: 'your_openai_api_key_here'` (User must provide their own)
*   `EDGAR_USER_AGENT: 'YourProjectName YourContactEmailOrLink'` (Encourage users to customize)
*   `POSTGRES_URI: 'postgresql://user:password@host:port/dbname'` (This will host both metadata and vector embeddings via pgvector. Default to local setup if possible, e.g., `postgresql://postgres:postgres@localhost:5432/finance_rag_db`)
*   `COMPANIES_CSV_PATH: './companies.csv'` (Path to the CSV file, defaults to root)
*   `DEFAULT_EMBEDDING_MODEL: 'text-embedding-3-small'` (Specify vector dimension, e.g., 1536 for this model)
*   `EMBEDDING_DIMENSION: 1536` (Crucial for pgvector table creation)
*   `DEFAULT_CHAT_MODEL: 'gpt-3.5-turbo'`
*   `LOG_LEVEL: 'INFO'`
*   `API_AUTH_KEY: 'optional_secret_key_for_backend_endpoints'` (If implemented, user-configurable)

---

## 🤖 Agent Roles & Responsibilities

- **Data Ingestion Agent**
  - Monitor `companies.csv` (as per `COMPANIES_CSV_PATH` in config) for specified companies and year ranges.
  - Fetch missing 10-K (and 10-K/A) filings using EDGAR API.
  - Parse PDFs/HTML, focusing on key sections.
  - Clean and split text into chunks.
  - Emit JSON objects to Embedding Agent:
    `{ 'id': 'uuid', 'ticker': 'AAPL', ..., 'chunk_text': '...', 'source_url': '...' }`

- **Embedding Agent**
  - Consume JSON objects.
  - For each object:
    1. Calculate `text_hash` (e.g., MD5 of `chunk_text`).
    2. Check Postgres `filings_metadata` for existing `text_hash`.
    3. Call OpenAI Embedding API (using `OPENAI_API_KEY` from user's config).
    4. Construct metadata record for `filings_metadata` table in Postgres.
    5. Construct vector record for `document_vectors` table in Postgres (containing the embedding vector from OpenAI).
    6. Upsert metadata and vector into their respective PostgreSQL tables within a transaction.

- **Retrieval & Chat Agent**
  - Expose `/retrieve` endpoint: query, filters → top-K contexts by querying PostgreSQL with `pgvector` similarity search.
  - Expose `/chat` endpoint: stream LLM Q&A using contexts from `/retrieve`.

- **Frontend Agent**
  - Spin up React app.
  - Implement Chat UI & DB Explorer.
  (Note: CSV upload feature removed from frontend.)

- **Scheduler Agent**
  - On service start/cron: Read `companies.csv` (as per `COMPANIES_CSV_PATH`). Diff its content vs Postgres `filings_metadata` → trigger Data Ingestion Agent for new or missing filings/years.

- **Ops Agent** (Focus on local development & easy deployment)
  - Containerize services (Docker Compose for easy local setup).
  - Instrument logging & basic metrics.
  - Provide clear instructions for running test suites.

---

## 🗂️ Project Phases & Task Breakdown

### Phase 1: Kickoff & Environment Setup
1.  **Action**: Initialize a public Git repository with chosen open-source license (e.g., MIT).
2.  **Action**: Create monorepo structure: `/backend`, `/frontend`, `/scripts`, `/docs`, `docker-compose.yml`, `README.md`, `.gitignore` (ensure `config.yaml` or `.env` are ignored). Place `companies.csv` (or a sample) in the root, to be referenced by `COMPANIES_CSV_PATH`.
3.  **Action**: Provision Python backend & React frontend skeletons.
4.  **Action**: Document setup for a local PostgreSQL instance with the **`pgvector` extension enabled**. Provide SQL scripts to create necessary tables and enable the extension if not present.
    ```sql
    -- Example for enabling extension (user might need superuser privileges)
    -- CREATE EXTENSION IF NOT EXISTS vector;
    ```
5.  **Action**: Define `companies.csv` schema (e.g., `ticker,company_name,start_year,end_year`) and create a sample `companies.csv` file in the location specified by `COMPANIES_CSV_PATH`. Create `config.example.yaml` or `.env.example`.

### Phase 2: Data Ingestion Pipeline
1.  **Task**: Read `companies.csv` (from `COMPANIES_CSV_PATH`).
2.  **Task**: For each `ticker,start_year,end_year`, query EDGAR, download filings.
3.  **Task**: Parse filings, extract sections, clean text, split into ~1000 token chunks (use `tiktoken`, respect `EMBEDDING_DIMENSION`).
4.  **Output**: JSON documents: `{ 'id': 'uuid', ..., 'chunk_text': '...' }`

### Phase 3: Embedding & Storage (PostgreSQL + pgvector)
1.  **Task**: For each JSON document chunk:
    - Calculate `text_hash`. Check for existence.
    - Call `openai.Embedding.create(model=DEFAULT_EMBEDDING_MODEL, input=chunk_text)`
    - Collect embedding vector (ensure it matches `EMBEDDING_DIMENSION`).
2.  **Task**: Define PostgreSQL schemas:
    ```sql
    -- In filings_metadata table
    CREATE TABLE IF NOT EXISTS filings_metadata (
        doc_id VARCHAR(255) PRIMARY KEY,
        ticker VARCHAR(10) NOT NULL,
        year INT NOT NULL,
        document_type VARCHAR(10) DEFAULT '10-K',
        filing_date DATE,
        section_name TEXT,
        source_url TEXT,
        page_number INT,
        embedding_model VARCHAR(50), -- Store model used for the vector
        text_hash VARCHAR(32) NOT NULL,
        ingested_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (ticker, year, document_type, section_name, text_hash)
    );

    -- In document_vectors table (for pgvector)
    CREATE TABLE IF NOT EXISTS document_vectors (
        doc_id VARCHAR(255) PRIMARY KEY,
        embedding VECTOR(<!--EMBEDDING_DIMENSION_PLACEHOLDER e.g., 1536-->), -- Agent replaces placeholder
        FOREIGN KEY (doc_id) REFERENCES filings_metadata(doc_id) ON DELETE CASCADE
    );

    -- Create an index for faster similarity search on the embeddings
    -- CREATE INDEX IF NOT EXISTS idx_hnsw_embedding ON document_vectors USING hnsw (embedding vector_l2_ops);
    ```
    *The agent must replace `<!--EMBEDDING_DIMENSION_PLACEHOLDER e.g., 1536-->` with the actual value from `EMBEDDING_DIMENSION` in the config.*
3.  **Task**: Upsert metadata into `filings_metadata` and the corresponding vector into `document_vectors` (using `doc_id` to link them). Perform these in a single transaction.

### Phase 4: Backend API & RAG Orchestration (using pgvector)
1.  **Endpoint**: `GET /retrieve`
    - Query Params: `q`, `k`, filters.
    - Logic: Embed `q`. Query `document_vectors` using `pgvector` similarity search. Join with `filings_metadata`.
    - Response: `{ "results": [ { "metadata": { ... }, "text": "...", "score": ... } ] }`
2.  **Endpoint**: `POST /chat` (uses `/retrieve` internally).
3.  **Implementation**: FastAPI + Pydantic.

### Phase 5: React Frontend
1.  **Chat UI**:
    - Model selector dropdown (for chat model).
    - Streaming message panel.
    - Input box + “Send” button.
    - Display of retrieved context/sources.
2.  **DB Explorer**:
    - Table view: tickers, years, document types, filing dates, etc.
    - Filters.
    - “View Text” modal per chunk.
(Note: The UI feature for uploading `companies.csv` is removed. Users will edit the file directly.)

### Phase 6: Auto-Update & Scheduling
1.  **On-Launch Hook** (backend startup):
    - Read `companies.csv` (from `COMPANIES_CSV_PATH`). For each `(ticker, year)` in the CSV, check if a corresponding record exists in `filings_metadata`. If not, or if an amended filing (10-K/A) is newer, queue for (re-)ingestion.
2.  **Cron Job** (e.g., `0 3 * * *` for daily at 03:00 UTC):
    - Execute a script that performs the same diff and queuing logic by reading `companies.csv` and comparing against Postgres.
3.  **Alerts**:
    - Basic logging for ingestion failures.

### Phase 7: Testing & QA
1.  **Unit Tests**: Parser, embedding wrapper, retrieval logic, API validation.
2.  **E2E Tests**: Playwright/Cypress for chat flows & DB Explorer.
3.  **Documentation**: Instructions on how to run tests.

### Phase 8: Deployment & Monitoring (Focus on Community Deployment)
1.  **Containerization**: `Dockerfile` for backend & frontend. `docker-compose.yml` for local multi-container setup (including Postgres with pgvector and mounting/accessing `companies.csv`).
    *   The `docker-compose.yml` should allow the backend container to access `companies.csv` from the host, or include it in the build context.
2.  **CI/CD Pipeline (Optional, for project maintainers)**: Documented for maintainers.
3.  **Monitoring**: Basic logging to stdout.
4.  **Cost Considerations**: Document OpenAI API costs. Explain PostgreSQL+pgvector is free software but server hosting (if not local) has costs.

---

❗ **Agent Execution Notes**
- **Prioritize Documentation Lookup**: Before implementing any new component, technology, or significant API interaction (e.g., EDGAR API, OpenAI API, PostgreSQL with pgvector, FastAPI, React, Docker Compose, specific libraries like `sec-parser` or `tiktoken`), the agent **must first search the web for the latest official documentation, relevant tutorials, and best practice examples.** This includes understanding API rate limits, authentication methods, required parameters, and common usage patterns.
- **Open Source First**: Adhere strictly to "Open Source Project Directives."
- **Parameterize**: Use values from `config.yaml` or `.env` (user-provided), including `COMPANIES_CSV_PATH`.
- **Idempotency**: Crucial for ingestion/embedding using `text_hash`.
- **Structured Logging**: JSON logs to `stdout`.
- **Clear Documentation**: `README.md` with setup, configuration (including `companies.csv` editing), usage, contribution. Explain `pgvector` index.
- **Database Migrations**: Initial SQL scripts.
- **Vector Indexing for pgvector**: Use HNSW or similar. Document creation.

---