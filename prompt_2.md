# **LLM Code Generation Prompt: S&P 500 10-K RAG Chatbot (Fixed Embedding, Flexible Chat)**

**Persona:** Act as an expert full-stack software engineer specializing in Python, React, PostgreSQL, Docker, and building AI-powered applications with RAG pipelines. You understand the importance of using a consistent embedding model for document indexing and query embedding, while allowing flexibility in the final chat generation LLM.

**Overall Goal:** Generate the complete codebase and configuration files for a RAG (Retrieval-Augmented Generation) chatbot. This chatbot allows users to ask questions about the 10-K filings of S&P 500 companies. The system features:
1.  A data pipeline for fetching and processing filings, where text chunks are embedded using a **single, specifically configured embedding model** (e.g., from OpenAI or Gemini).
2.  A PostgreSQL database with pgvector for storing these text chunks and their corresponding vectors.
3.  A FastAPI backend API implementing the RAG logic:
    *   It embeds the incoming user query using the **exact same embedding model** used for the documents.
    *   It performs vector similarity search to find relevant document chunks.
    *   It passes the retrieved text chunks as context to a **separately configured chat generation LLM** (e.g., from OpenAI, Gemini, or Claude) to produce the final answer.
4.  A React frontend for user interaction.
The entire system must be containerized using Docker and Docker Compose. Include a "Demo Mode".

**Core Technologies:**
*   **Backend:** Python 3.10+, FastAPI, Uvicorn, SQLAlchemy (or psycopg2-binary directly), **LLM Clients (OpenAI, Google Generative AI, Anthropic)**, python-dotenv, tiktoken, requests, beautifulsoup4.
*   **Database:** PostgreSQL (latest stable), pgvector extension.
*   **Frontend:** React.js (latest stable), axios (or fetch API).
*   **AI / LLM APIs & Configuration:**
    *   **Embedding Process (Used for BOTH documents and queries):**
        *   `EMBEDDING_PROVIDER`: Specifies the provider for embedding (e.g., 'OPENAI', 'GEMINI').
        *   `EMBEDDING_MODEL`: The specific model name for embeddings (e.g., 'text-embedding-ada-002', 'models/embedding-001').
        *   `EMBEDDING_DIMENSION`: The output dimension of the `EMBEDDING_MODEL` (e.g., 1536, 768). **Must be correctly set and match the DB schema.**
        *   Requires the API key for the `EMBEDDING_PROVIDER`.
    *   **Chat Generation Process (Used ONLY for final answer generation):**
        *   `CHAT_PROVIDER`: Specifies the provider for chat completion (e.g., 'OPENAI', 'GEMINI', 'CLAUDE').
        *   `CHAT_MODEL`: The specific model name for chat (e.g., 'gpt-3.5-turbo', 'gemini-1.5-flash', 'claude-3-sonnet-20240229').
        *   Requires the API key for the `CHAT_PROVIDER`.
*   **Containerization:** Docker, Docker Compose.

**Project Structure:**
(Structure remains the same as previous versions, including `llm_clients.py`)

your-project-name/
├── backend/
│   ├── app/
│   │   ├── ... (main, api, models, db)
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   └── config.py     # <-- Modified: Reflect clear separation of Embed/Chat config
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── llm_clients.py  # <-- Modified: Functions clearly use Embed OR Chat config
│   │   │   └── rag_service.py  # <-- Modified: Explicitly uses embedding model for query
│   ├── data_updater/
│   │   ├── ... (fetch, process)
│   │   ├── create_embeddings.py # <-- Uses ONLY Embedding config
│   │   └── update_job.py
│   ├── Dockerfile
│   ├── requirements.txt        # Add openai, google-generativeai, anthropic
│   └── .env.example            # Reflect separate Embed/Chat config
│
├── frontend/ ... (Standard structure)
│
├── postgres/
│   └── init.sql
│
├── .env                     # User-managed, reflect separate Embed/Chat config
├── docker-compose.yml       # Pass separate Embed/Chat config to backend
├── README.md                # Explain the fixed embedding / flexible chat setup
└── .gitignore

**Step-by-Step Implementation Details:**

**1. Database Setup (PostgreSQL + pgvector):**
    *   `postgres/init.sql`: `CREATE EXTENSION IF NOT EXISTS vector;`.
    *   `backend/app/db/database.py`: Standard setup.
    *   `backend/app/db/crud.py`:
        *   Functions for storing info, filings, chunks.
        *   **Storing/Updating embeddings:** `embedding` column must be `VECTOR(dimension)` where `dimension` is read from `config.EMBEDDING_DIMENSION`. **Emphasize:** DB schema dimension MUST match the configured dimension for the chosen `EMBEDDING_MODEL`.
        *   Vector similarity search: Use `<=>` operator.

**2. Data Acquisition & Processing Pipeline (`backend/data_updater/`):**
    *   `fetch_sec.py`: Demo vs Full mode logic.
    *   `process_docs.py`: Parsing, chunking logic.
    *   **`create_embeddings.py`:**
        *   Fetch unprocessed chunks.
        *   Retrieve **Embedding configuration** from `config.py` (`EMBEDDING_PROVIDER`, `EMBEDDING_MODEL`, `EMBEDDING_DIMENSION`, relevant API key).
        *   Use the `llm_clients.get_embedding` function, passing the text and the **embedding-specific** configuration. This function will use the configured `EMBEDDING_PROVIDER` and `EMBEDDING_MODEL`.
        *   Batch chunks respecting the **embedding provider's** API limits.
        *   Store returned vectors (dimension must match `EMBEDDING_DIMENSION`). Mark chunks as "embedded".
        *   **This script ONLY uses the embedding configuration.**

**3. Backend API (`backend/app/`):**
    *   **`backend/app/core/config.py`:**
        *   Use Pydantic `BaseSettings`.
        *   Load `DATABASE_URL`, `APP_MODE`.
        *   **Add Explicit Embedding and Chat Configurations:**
            *   `EMBEDDING_PROVIDER: str = "OPENAI"` (Validate: 'OPENAI' or 'GEMINI').
            *   `EMBEDDING_MODEL: str = "text-embedding-ada-002"`
            *   `EMBEDDING_DIMENSION: int` (e.g., 1536 based on default model). **Load from env.**
            *   `CHAT_PROVIDER: str = "OPENAI"` (Validate: 'OPENAI', 'GEMINI', or 'CLAUDE').
            *   `CHAT_MODEL: str = "gpt-3.5-turbo"`
            *   `OPENAI_API_KEY: Optional[str] = None`
            *   `GOOGLE_API_KEY: Optional[str] = None`
            *   `ANTHROPIC_API_KEY: Optional[str] = None`
        *   **Add validation:**
            *   Ensure API key for `EMBEDDING_PROVIDER` is present.
            *   Ensure API key for `CHAT_PROVIDER` is present.
            *   Validate that `EMBEDDING_DIMENSION` corresponds to the known output dimension of the specified `EMBEDDING_MODEL`. Raise an error or warning if inconsistent.
    *   `backend/app/models/chat_models.py`: `UserQuery`, `ChatResponse`.
    *   **`backend/app/services/llm_clients.py`:**
        *   Abstract interactions with LLM APIs.
        *   Function `get_embedding(text: str, config: Settings) -> List[float]`:
            *   Takes text and the full config object.
            *   **Uses `config.EMBEDDING_PROVIDER` and `config.EMBEDDING_MODEL`** to initialize the correct client (OpenAI or Gemini).
            *   Calls the appropriate embedding endpoint using the API key for the `EMBEDDING_PROVIDER`.
            *   Returns the vector, ensuring its dimension matches `config.EMBEDDING_DIMENSION`. Handles errors.
        *   Function `generate_chat_response(prompt: str, context: str, query: str, config: Settings) -> str`:
            *   Takes context/query, and the full config object.
            *   **Uses `config.CHAT_PROVIDER` and `config.CHAT_MODEL`** to initialize the correct client (OpenAI, Gemini, or Claude).
            *   Constructs the final prompt suitable for the chat provider's API. Include RAG instructions ("Answer based *only* on context...").
            *   Calls the appropriate chat/completion API using the API key for the `CHAT_PROVIDER`. Handle provider-specific parameters.
            *   Parses and returns the text answer. Handles errors.
    *   **`backend/app/services/rag_service.py`:**
        *   Inject `Settings` from `config.py`.
        *   **Implement the core RAG logic precisely:**
            1.  Accept the `user_query` string.
            2.  **Generate query embedding:** Call `llm_clients.get_embedding(user_query, config)`. This explicitly uses the configured `EMBEDDING_PROVIDER` and `EMBEDDING_MODEL`.
            3.  **Perform vector search:** Use `db/crud.py` function to find top `k` document chunks in the database whose vectors (created using the *same* embedding model) are most similar to the query embedding.
            4.  **Prepare context:** Concatenate the text content of the retrieved chunks.
            5.  **Generate final answer:** Call `llm_clients.generate_chat_response(prompt_instructions, retrieved_chunks_text, user_query, config)`. This explicitly uses the configured `CHAT_PROVIDER` and `CHAT_MODEL`.
            6.  Return the final answer.
    *   `backend/app/api/chat.py`: Define POST `/api/v1/chat`, call `rag_service`.
    *   `backend/app/main.py`: FastAPI app setup.
    *   **`backend/requirements.txt`:** Include `openai`, `google-generativeai`, `anthropic`, etc.
    *   `backend/Dockerfile`: Standard setup.

**4. Frontend (React):**
    *   *(No changes needed)* Agnostic to backend implementation details.

**5. Container Orchestration (`docker-compose.yml`):**
    *   Define `db`, `backend`, `frontend`.
    *   **`backend` service:**
        *   Pass all necessary environment variables from `.env`: `DATABASE_URL`, `APP_MODE`, **`EMBEDDING_PROVIDER`**, **`EMBEDDING_MODEL`**, **`EMBEDDING_DIMENSION`**, **`CHAT_PROVIDER`**, **`CHAT_MODEL`**, `OPENAI_API_KEY`, `GOOGLE_API_KEY`, `ANTHROPIC_API_KEY`.

**6. Configuration and Documentation:**
    *   **`.env` (User Provided, Gitignored):**
        *   `# --- Embedding Configuration (Used for Docs AND Queries) ---`
        *   `EMBEDDING_PROVIDER=OPENAI` # Or GEMINI
        *   `EMBEDDING_MODEL=text-embedding-ada-002` # Or models/embedding-001
        *   `EMBEDDING_DIMENSION=1536` # **MUST MATCH THE OUTPUT OF EMBEDDING_MODEL and DB Schema!**
        *   `# --- Chat Generation Configuration (Used for Final Answer) ---`
        *   `CHAT_PROVIDER=CLAUDE` # Or OPENAI or GEMINI
        *   `CHAT_MODEL=claude-3-sonnet-20240229` # Or gpt-3.5-turbo, gemini-1.5-flash, etc.
        *   `# --- API Keys (Provide keys for providers used above) ---`
        *   `OPENAI_API_KEY=sk-...`
        *   `GOOGLE_API_KEY=...`
        *   `ANTHROPIC_API_KEY=...`
        *   `# --- Other Settings ---`
        *   `DATABASE_URL=...`
        *   `POSTGRES_USER=...`
        *   `POSTGRES_PASSWORD=...`
        *   `POSTGRES_DB=...`
        *   `APP_MODE=DEMO`
    *   **`.gitignore`:** Standard ignores + `.env`.
    *   **`README.md`:**
        *   **Clearly explain the architecture:** State explicitly that ONE embedding model (configured via `EMBEDDING_*` vars) is used consistently for indexing documents and embedding queries. State that a SEPARATE chat model (configured via `CHAT_*` vars) is used only for generating the final response based on retrieved text.
        *   **Setup Instructions:**
            1. Clone repo.
            2. Create `.env` from `.env.example`.
            3. Configure the **Embedding** section (`EMBEDDING_PROVIDER`, `EMBEDDING_MODEL`, `EMBEDDING_DIMENSION`).
            4. Configure the **Chat** section (`CHAT_PROVIDER`, `CHAT_MODEL`).
            5. Add API Keys for **all** providers selected in the steps above.
            6. **CRITICAL:** Emphasize that `EMBEDDING_DIMENSION` MUST accurately reflect the chosen `EMBEDDING_MODEL`'s output dimension, and the database `embedding` column (`VECTOR(dimension)`) **MUST** be created with this same dimension *before* running the data loading step (`create_embeddings.py`).
            7. Set DB credentials and `APP_MODE`.
            8. Run `docker-compose up --build -d`.
        *   **Initial Data Loading:** Command `docker-compose exec backend python /app/data_updater/update_job.py`. Costs relate to the embedding provider (during load) and chat provider (during usage).
        *   Update other sections as needed.

**Final Instructions for LLM:**
*   Generate code adhering precisely to the separation of concerns: **one consistent embedding process** defined by `EMBEDDING_*` vars, and **one separate chat generation process** defined by `CHAT_*` vars.
*   Implement `llm_clients.py` with `get_embedding` using ONLY embedding config, and `generate_chat_response` using ONLY chat config.
*   Ensure `create_embeddings.py` uses ONLY embedding config via `llm_clients.get_embedding`.
*   Ensure `rag_service.py` correctly uses `llm_clients.get_embedding` for the query and `llm_clients.generate_chat_response` for the answer, passing text context.
*   Ensure database configuration (`crud.py`, models, init scripts) uses the `EMBEDDING_DIMENSION` variable correctly for the `VECTOR` column type.
*   Generate all specified files, including updated `requirements.txt`, `docker-compose.yml`, `.env.example`, and `README.md` reflecting this specific setup.
*   Use type hints, comments, and basic error handling. Present output clearly.
* if something is not clear or needs specification ask. 
