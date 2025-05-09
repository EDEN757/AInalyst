# AInalyst: Finance Chatbot with RAG

AInalyst is a Retrieval-Augmented Generation (RAG) powered finance chatbot that provides insights from SEC filings of U.S. public companies. The system intelligently fetches 10-K filings, processes them into semantic chunks, and provides a natural language interface for querying financial information.

## 🎯 Features

- **Automated SEC Filing Ingestion**: Automatically ingests 10-K filings for public companies specified in a CSV file
- **Semantic Processing**: Parses and embeds text using OpenAI Embedding API, enabling semantic search
- **Vector Database**: Efficiently stores and retrieves embeddings using PostgreSQL with pgvector extension
- **Interactive UI**: Provides a React-based Chat UI with streaming responses and a comprehensive Database Explorer
- **Scheduled Updates**: Auto-updates new filings on startup and via scheduled cron jobs
- **Multi-model Support**: Supports different OpenAI models for embeddings and chat generation
- **Easy Deployment**: Simple setup using Docker and Docker Compose

## 🧩 System Architecture

AInalyst follows a modular architecture:

1. **Data Ingestion Pipeline**:
   - Fetches SEC filings based on ticker symbols and year ranges from `companies.csv`
   - Processes and extracts key sections from filings
   - Chunks text into semantically meaningful units

2. **Vector Database**:
   - PostgreSQL with pgvector extension for efficient similarity search
   - HNSW index for fast approximate nearest neighbor search
   - Stores document metadata and vector embeddings

3. **Backend API**:
   - FastAPI REST endpoints for chat, retrieval, and company information
   - Streaming support for real-time chat responses
   - Robust error handling and validation

4. **Frontend Application**:
   - React-based UI with responsive design
   - Real-time chat with streaming responses
   - Database explorer for monitoring ingested data

## 🛠️ Tech Stack

- **Backend**: Python, FastAPI, SQLAlchemy, asyncio
- **Database**: PostgreSQL with pgvector extension
- **Frontend**: React, React Router, SSE (Server-Sent Events)
- **Embedding**: OpenAI Embedding API (text-embedding-3-small)
- **LLM**: OpenAI Chat Completions API (supports both GPT-3.5-Turbo and GPT-4)
- **Deployment**: Docker & Docker Compose
- **Scheduling**: Cron for automated updates

## 🚀 Getting Started

### Prerequisites

- Docker and Docker Compose
- OpenAI API key

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/AInalyst.git
   cd AInalyst
   ```

2. Copy the environment variables template:
   ```bash
   cp .env.example .env
   ```

3. Edit the `.env` file with your configuration:
   - `OPENAI_API_KEY`: Your OpenAI API key (required)
   - `EDGAR_USER_AGENT`: Your contact information for SEC EDGAR API (e.g., "AInalyst user@example.com")
   - `POSTGRES_URI`: Database connection string (defaults to "postgresql://postgres:postgres@postgres:5432/finance_rag_db")
   - `DEFAULT_EMBEDDING_MODEL`: OpenAI embedding model (defaults to "text-embedding-3-small")
   - `EMBEDDING_DIMENSION`: Embedding vector dimensions (defaults to 1536 for text-embedding-3-small)
   - `DEFAULT_CHAT_MODEL`: OpenAI chat model (defaults to "gpt-3.5-turbo")
   - `LOG_LEVEL`: Logging level (defaults to "INFO")

4. Configure companies to analyze:
   Edit the `companies.csv` file in the root directory with the following format:
   ```csv
   ticker,company_name,start_year,end_year
   AAPL,Apple Inc.,2020,2023
   MSFT,Microsoft Corporation,2020,2023
   AMZN,Amazon.com Inc.,2020,2023
   GOOGL,Alphabet Inc.,2020,2023
   META,Meta Platforms Inc.,2020,2023
   ```

5. Build and start the application:
   ```bash
   docker-compose build
   docker-compose up -d
   ```

6. Monitor logs (optional):
   ```bash
   # View all logs
   docker-compose logs -f

   # View only backend logs
   docker-compose logs -f backend
   ```

7. Access the application:
   - Frontend UI: http://localhost:3000
   - Backend API: http://localhost:8000/docs (Swagger UI for API documentation)

## 📊 Usage

### Data Ingestion

1. The application will automatically analyze `companies.csv` on startup and begin fetching any missing filings.
2. Initial data ingestion may take some time, depending on the number of companies and years.
3. The system will also run daily updates at 03:00 UTC to check for any new filings.
4. You can monitor ingestion status in the "Company Database" section of the UI.

### Chat Interface

1. Navigate to the Chat page from the main menu.
2. (Optional) Select a specific company, year, or section from the filters to focus your questions.
3. Ask questions about the companies and their financial data:
   - "What were Apple's main risk factors in 2022?"
   - "Summarize Microsoft's business strategy"
   - "How did Amazon's revenue change from 2020 to 2022?"
   - "What are the key competitive advantages of Google?"
   - "Compare the R&D spending of tech companies"
4. The system will retrieve relevant sections from the filings and generate a response.
5. View source information by clicking "Show Sources" below each assistant message.

### Database Explorer

1. Navigate to the "Company Database" page from the main menu.
2. View all companies currently in the database.
3. Monitor ingestion status for each company.
4. See which years are available for each company.
5. Track progress of data ingestion across your database.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📚 Documentation

For more detailed documentation, please refer to the [docs](docs/) directory.

## 🔧 Technical Details

### PostgreSQL Vector Database

AInalyst uses PostgreSQL with the pgvector extension for efficient similarity search:

1. **pgvector Extension**: This extension enables PostgreSQL to store and query vector embeddings.
2. **Tables**:
   - `filings_metadata`: Stores metadata about the filings (ticker, year, document type, etc.)
   - `document_vectors`: Stores the vector embeddings linked to metadata via `doc_id`
3. **HNSW Index**: AInalyst uses Hierarchical Navigable Small World (HNSW) indexing for efficient approximate nearest-neighbor search:
   ```sql
   CREATE INDEX idx_hnsw_embedding ON document_vectors USING hnsw (embedding vector_l2_ops);
   ```
   This significantly improves query performance for large vector datasets.

### Embedding and Chunking

1. **Text Embedding**: Uses OpenAI's embedding models (default: text-embedding-3-small) to create vector representations.
2. **Chunking Strategy**: Documents are split into overlapping chunks of approximately 1000 tokens to ensure context preservation.
3. **Deduplication**: Uses text hash to avoid storing duplicate content.

### Auto-Update System

1. **On-Launch Update**: When the backend starts, it automatically checks for missing filings.
2. **Scheduled Update**: A cron job runs daily at 03:00 UTC to check for new filings.
3. **Differential Updates**: Only fetches what's missing by comparing `companies.csv` against the database.

## ⚙️ Advanced Configuration

### Modifying Database Schema

If you need to modify the database schema:

1. Edit the `postgres/init.sql` file
2. Rebuild your containers:
   ```bash
   docker-compose down
   docker-compose up -d --build
   ```

### Changing Embedding Dimensions

If you want to use a different embedding model:

1. Update the `DEFAULT_EMBEDDING_MODEL` in your `.env` file
2. Make sure to update the `EMBEDDING_DIMENSION` to match (e.g., 1536 for text-embedding-3-small)
3. You'll need to recreate your database as the vector dimensions cannot be changed after creation

### Custom Deployment

For production deployment:

1. Modify `docker-compose.yml` to use non-development settings:
   - Remove volume mounts for code directories
   - Use production-ready database settings
   - Set appropriate resource limits
2. Consider using managed PostgreSQL with pgvector support
3. Update CORS settings in `backend/app/main.py`

## ❓ FAQ

**Q: How much does it cost to run?**
A: Costs are primarily associated with the OpenAI API. Embedding documents uses the Embedding API, and chatting uses the Chat Completions API. For a few companies over a 3-4 year period, expect costs of a few dollars for initial ingestion and cents per chat interaction.

**Q: How long does data ingestion take?**
A: Initial ingestion depends on the number of companies and years. SEC API has rate limits (10 requests/second), so downloading filings can take time. Processing 5 companies over 4 years might take 30-60 minutes.

**Q: Can I add companies while the system is running?**
A: Yes! Simply edit the `companies.csv` file and the system will detect new entries during the next scheduled update (daily at 03:00 UTC). Alternatively, restart the backend to trigger an immediate check.

**Q: Why PostgreSQL with pgvector instead of a dedicated vector database?**
A: This provides a single, familiar database technology that handles both metadata and vectors, simplifies deployment, and offers good performance with proper indexing.

**Q: How can I customize the document processing?**
A: You can modify the text processing and chunking logic in `backend/data_updater/process_docs.py` to adjust how documents are split or which sections are extracted.