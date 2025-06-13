# AInalyst

**AI-Powered Financial Document Analysis Platform**

AInalyst is a sophisticated Retrieval-Augmented Generation (RAG) system that provides intelligent analysis of SEC filings using OpenAI's language models. Built with a modern tech stack, it enables users to query financial documents through natural language and receive contextual insights backed by official SEC data.

## 🏗️ Architecture

The platform consists of three main components:

1. **Data Pipeline**: Automated SEC filing download and processing
2. **RAG Backend**: FastAPI service with FAISS vector search and OpenAI integration
3. **Frontend Interface**: Next.js chat application with real-time responses

## 📁 Project Structure

```
AInalyst/
├── api/
│   └── app.py                      # FastAPI backend with RAG endpoints
├── frontend/                       # Next.js 15 frontend application
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx           # Landing page with animated UI
│   │   │   └── chat/
│   │   │       └── page.tsx       # Chat interface
│   │   └── components/            # Reusable UI components
│   └── package.json               # Frontend dependencies
├── data/                          # Downloaded SEC filings (JSON format)
├── download_filings.py            # SEC EDGAR filing downloader
├── incremental_chunk_embed.py     # Document chunking and embedding
├── query_rag.py                   # CLI retrieval testing tool
├── requirements.txt               # Python dependencies
├── faiss_index.idx               # FAISS vector index (generated)
└── faiss_metadata.json          # Document metadata (generated)
```

## ⚙️ Prerequisites

- **Python 3.8+**
- **Node.js 18+** and **npm**
- **OpenAI API Key** (with access to embeddings and chat completions)

## 🚀 Quick Start

### 1. Environment Setup

Clone the repository and set up your environment:

```bash
git clone https://github.com/your-username/AInalyst.git
cd AInalyst
```

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=sk-your-openai-api-key-here
START_DATE=2023-01-01
MODE=DEMO
USER_AGENT="Your Name Your Project <your.email@example.com>"
CORS_ORIGINS=http://localhost:3000
```

### 2. Install Dependencies

**Backend:**
```bash
pip install -r requirements.txt
```

**Frontend:**
```bash
cd frontend
npm install
cd ..
```

### 3. Download and Process Data

Download SEC filings (starts with Apple in DEMO mode):

```bash
python download_filings.py
```

Create embeddings and build the search index:

```bash
python incremental_chunk_embed.py
```

### 4. Launch the Application

**Start the backend API:**
```bash
uvicorn api.app:app --reload --host 0.0.0.0 --port 8000
```

**Start the frontend (in a new terminal):**
```bash
cd frontend
npm run dev
```

Visit **http://localhost:3000** to access AInalyst.

## 🔧 Configuration Options

### Data Collection Modes

- **DEMO**: Downloads filings for Apple only (fast setup)
- **FULL**: Downloads all S&P 500 company filings (comprehensive dataset)

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | Your OpenAI API key | Required |
| `START_DATE` | Beginning date for filing collection | `2023-01-01` |
| `MODE` | Data collection mode (`DEMO` or `FULL`) | `DEMO` |
| `USER_AGENT` | SEC API user agent (required) | Required |
| `CORS_ORIGINS` | Allowed frontend origins | `http://localhost:3000` |

## 💡 Usage Examples

### CLI Testing

Test the retrieval system directly:

```bash
python query_rag.py --query "What are Apple's main revenue streams?" --k 5
```

### API Endpoints

**POST `/ask`**
```json
{
  "query": "What were Tesla's R&D expenses last year?",
  "k": 5,
  "api_key": "sk-your-key",
  "chat_model": "gpt-4.1-mini-2025-04-14"
}
```

Response:
```json
{
  "answer": "Based on Tesla's financial filings...",
  "context": [
    {
      "ticker": "TSLA",
      "accession": "0000950170-23-027673",
      "text": "Research and development expenses...",
      "score": 0.85,
      "filing_date": "2023-01-26",
      "form": "10-K",
      "url": "https://www.sec.gov/Archives/edgar/data/..."
    }
  ]
}
```

## 🛠️ Technical Details

### Data Processing Pipeline

1. **SEC Filing Download**: Fetches 10-K, 10-Q, and Company Facts from SEC EDGAR API
2. **Text Extraction**: Cleans HTML/XML and extracts relevant content sections
3. **Document Chunking**: Splits documents into 1000-token chunks with 200-token overlap
4. **Vector Embedding**: Uses OpenAI's `text-embedding-3-small` model
5. **FAISS Indexing**: Stores embeddings for efficient similarity search

### RAG Implementation

- **Retrieval**: FAISS cosine similarity search finds top-K relevant chunks
- **Augmentation**: Assembles context from retrieved documents
- **Generation**: OpenAI chat completion with retrieved context

### Frontend Features

- **Animated Landing Page**: Cyberpunk-themed interface with spotlight effects
- **Real-time Chat**: WebSocket-like experience with streaming responses
- **Source Attribution**: Links to original SEC filings for verification
- **Dark/Light Mode**: Adaptive theme support
- **Responsive Design**: Mobile and desktop optimized

## 📊 Deployment

### Production Configuration

For deployment, update environment variables:

```env
NEXT_PUBLIC_BACKEND_URL=https://your-api-domain.com
CORS_ORIGINS=https://your-frontend-domain.com,https://your-frontend-*.vercel.app
```

### 6. Backend Deployment on Render

#### 6.1 Create a Render Web Service
1. Log in to Render (or create an account).
2. Click **New → Web Service**.
3. Connect your GitHub repo (select **EDEN757/AInalyst**).
4. Configure the service:
   - **Name**: e.g. ainalyst-backend
   - **Region**: Choose a region close to you (e.g., Oregon or Frankfurt).
   - **Root Directory**: `api` (so Render builds from AInalyst/api/).
   - **Runtime**: Python 3.
   - Leave **Build Command** and **Start Command** blank for now.
5. Click **Create Web Service**. Render will provision a placeholder service awaiting your build settings.

#### 6.2 Set Environment Variables on Render
1. In your new Web Service, go to **Settings → Environment**.
2. Add the following variables (one at a time):

| Key | Value | Description |
|-----|-------|-------------|
| `OPENAI_API_KEY` | `sk-your-openai-key` | Your private OpenAI key used for embedding generation and fallback chat completions. |
| `START_DATE` | `2023-01-01` | Earliest filing date for download_filings.py. |
| `MODE` | `DEMO` | Mode flag used by your ingestion scripts. |
| `USER_AGENT` | `yourname youremail@example.com` | Custom User-Agent when fetching SEC EDGAR filings. |
| `CORS_ORIGINS` | `http://localhost:3000,https://a-inalyst.vercel.app` | Comma-separated list of allowed origins (development + production). |

**Note:**
- Replace `sk-your-openai-key` with your own OpenAI API key.
- Replace `https://a-inalyst.vercel.app` with your actual Vercel frontend URL once it's live.

3. Click **Save** after entering each variable.

#### 6.3 Set Build & Start Commands on Render
1. In the Web Service's **Settings**, scroll to **Build & Deploy**.
2. Populate the **Build Command** field with:
```bash
pip install -r requirements.txt
```
   - Installs all Python dependencies.

3. Populate the **Start Command** field with:
```bash
uvicorn api.app:app --host 0.0.0.0 --port $PORT
```
   - Launches the FastAPI server via Uvicorn.
   - `$PORT` is provided by Render at runtime.

#### 6.4 Data Processing Scripts
After deployment, the following scripts need to be run manually from the shell:

1. **Download SEC filings:**
```bash
python download_filings.py
```

2. **Create embeddings and build search index:**
```bash
python incremental_chunk_embed.py
```

#### 6.5 Automated Data Updates (Cron Jobs)
To keep the data fresh, set up cron jobs to run the data processing scripts periodically:

```bash
# Edit crontab
crontab -e

# Add the following lines to run daily at 2 AM
0 2 * * * cd /path/to/AInalyst && python download_filings.py
30 2 * * * cd /path/to/AInalyst && python incremental_chunk_embed.py
```

This ensures:
- New SEC filings are downloaded daily
- Embeddings are updated with fresh data
- The search index stays current with the latest financial documents

4. **Instance Type**
   - On the free tier, select the free instance.
   - Optionally upgrade to a paid instance for SSH access or persistent disks.
5. Ensure **Auto-Deploy** is toggled On (default). Pushing to main will automatically trigger a rebuild.
6. Click **Save Changes** (or **Update Service**). Render will queue a new deployment with your updated commands.

### 7. Frontend Deployment on Vercel

#### 7.1 Create a Vercel Project
1. Log in to Vercel.
2. Click **New Project**.
3. Under **Import Git Repository**, select your GitHub account and choose **EDEN757/AInalyst**.
4. Configure project settings:
   - **Root Directory**: `frontend` (so Vercel builds from AInalyst/frontend/).
   - **Framework Preset**: Should auto-detect Next.js.
   - **Build Command**: `npm run build` (default).
   - **Output Directory**: `.next` (default).
5. Click **Deploy**. Vercel will install dependencies and run npm run build in the frontend/ folder.

## 🔍 Advanced Features

### Custom CORS Handling

The backend includes intelligent CORS management for Vercel deployments, automatically allowing preview and production URLs while maintaining security.

### Incremental Updates

The embedding system supports incremental updates - only new documents are processed when running `incremental_chunk_embed.py` again.

### Extensible Architecture

- **Multiple Document Types**: Supports 10-K, 10-Q, and Company Facts
- **Configurable Chunking**: Adjustable chunk sizes and overlap
- **Model Flexibility**: Easy switching between OpenAI models
- **Vector Store Agnostic**: FAISS can be replaced with other vector databases

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **SEC EDGAR API** for providing access to financial data
- **OpenAI** for embedding and language model capabilities
- **FAISS** (Facebook AI Similarity Search) for efficient vector operations
- **Vercel** for seamless frontend deployment

---

**Built with ❤️ for financial analysis and AI-powered insights**

For questions or support, please open an issue on GitHub.
