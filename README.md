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

### Docker Support

Create a `Dockerfile` for containerized deployment:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

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