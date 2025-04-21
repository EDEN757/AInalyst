# AInalyst

A Retrieval-Augmented Generation (RAG) chatbot that enables users to query information from the 10-K filings of S&P 500 companies using natural language.

## Project Structure

```
AInalyst/
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
├── .env.example                    # Example environment variables
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
- **Document Processing Pipeline**: Fetches, extracts, chunks, and embeds 10-K filings
- **Containerized Architecture**: Everything runs in Docker containers for easy deployment
- **Demo Companies**: Easily load sample companies (Apple, Microsoft, Google) to explore the system

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

   e. **Application Configuration**:
      ```
      # This setting is now used for internal processing, not for enabling/disabling demo mode
      APP_MODE=FULL
      ```

4. **CRITICAL**: The `EMBEDDING_DIMENSION` parameter MUST accurately match the output dimension of your chosen `EMBEDDING_MODEL`. The database will create a `VECTOR(dimension)` column based on this value.

### Running the Application

1. Start all services:
   ```
   docker-compose up --build -d
   ```

2. Access the application - no initial setup needed:
   
   When you first access the application, you'll be prompted to add companies to the database:
   - You can use the "Load Demo Companies" button to quickly add Apple, Microsoft, and Google
   - Or you can manually add companies by entering their ticker symbols (e.g., "AAPL", "MSFT", "GOOGL")
   
   Note: The embedding process for new companies happens in the background and may take some time to complete.

3. Access the application:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000

### API Documentation

Once running, you can access the API documentation at:
- http://localhost:8000/docs

## Usage

1. **Company Management**: Access the "Company Management" tab to:
   - View companies currently in your database
   - See details of company filings
   - Add new companies by ticker symbol
   - Load demo companies with a single click
   - Delete companies you no longer need

2. **Chat Interface**: Enter questions about companies' 10-K filings:
   - Filter by specific companies using the dropdown
   - Filter by specific filing year
   - View source documents for each answer

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

## Deployment on a Linux Server via SSH

### Prerequisites
- Linux server with SSH access
- Docker and Docker Compose installed on the server
- Git installed on the server

### Deployment Steps

1. **SSH into your server**:
   ```bash
   ssh username@your-server-ip
   ```

2. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/AInalyst.git
   cd AInalyst
   ```

3. **Configure environment variables**:
   ```bash
   cp .env.example .env
   nano .env  # Edit the file with your API keys and configuration
   ```

4. **Build and start the Docker containers**:
   ```bash
   docker-compose up -d --build
   ```

5. **Access the application**:
   ```bash
   # No manual database initialization needed
   # Just access the frontend and use the Company Management interface
   ```

6. **Configure firewall (if needed)**:
   Make sure ports 3000 (frontend) and 8000 (backend) are accessible:
   ```bash
   sudo ufw allow 3000
   sudo ufw allow 8000
   ```

7. **Access the application**:
   - Frontend: `http://your-server-ip:3000`
   - Backend API: `http://your-server-ip:8000`
   - API Docs: `http://your-server-ip:8000/docs`

### Production Considerations

For a production deployment, consider the following additional steps:

1. **Set up a reverse proxy (Nginx or Traefik)** to handle SSL termination and route traffic.

2. **Configure domain names** instead of using IP addresses:
   ```nginx
   # Example Nginx configuration
   server {
       listen 80;
       server_name chat.yourdomain.com;
       
       location / {
           proxy_pass http://localhost:3000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   
   server {
       listen 80;
       server_name api.yourdomain.com;
       
       location / {
           proxy_pass http://localhost:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

3. **Set up SSL certificates** using Let's Encrypt:
   ```bash
   sudo certbot --nginx -d chat.yourdomain.com -d api.yourdomain.com
   ```

4. **Set up container monitoring** with tools like Portainer or Prometheus + Grafana.

5. **Configure automatic backups** for the PostgreSQL database:
   ```bash
   # Add a cron job for daily backups
   crontab -e
   # Add this line:
   0 2 * * * docker exec sp500_rag_db pg_dump -U postgres sp500_db > /path/to/backups/sp500_backup_$(date +\%Y\%m\%d).sql
   ```

## License

[MIT License](LICENSE)

## Troubleshooting

### No Context Found / Empty Search Results

If the system reports "No context found" or gives generic responses despite having companies in the database, the embeddings may not be fully generated. Run this command to create missing embeddings:

```bash
docker exec -it sp500_rag_backend python -c 'from app.db.database import SessionLocal; from data_updater.create_embeddings import create_embeddings; db = SessionLocal(); print(create_embeddings(db)); db.close()'
```

This process may take some time depending on how many text chunks need embeddings. You can monitor progress with:

```bash
docker exec -it sp500_rag_db psql -U postgres -d <your_db_name> -c "SELECT COUNT(*) as total_chunks, SUM(CASE WHEN embedded THEN 1 ELSE 0 END) as embedded_chunks FROM text_chunks;"
```

Replace `<your_db_name>` with your database name (default is `sp500_db`).

## Acknowledgments

- This project uses the SEC's EDGAR database for company filings
- Built with multiple LLM providers for flexible deployment options