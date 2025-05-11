# AInalyst

**A Retrieval‑Augmented‑Generation (RAG) chatbot for SEC 10‑K filings**

This project lets you:

1. **Download** 10‑K filings from the SEC as JSON.
2. **Chunk** and **embed** them with OpenAI embeddings + FAISS.
3. **Serve** a FastAPI backend to retrieve top‑K snippets and call ChatGPT.
4. **Run** a Next.js + Tailwind CSS frontend for an interactive chat UI.

---

## 📁 Repository Structure

```
AInalyst/
├── .env                         # Your OpenAI API key & config
├── download_filings.py           # Download & clean 10‑K filings as JSON
├── incremental_chunk_embed.py   # One‑time or incremental chunk + FAISS embedder
├── query_rag.py                 # CLI to test retrieval (embed query & show top‑K chunks)
├── api/
│   └── app.py                   # FastAPI service `/ask` endpoint
└── frontend/                    # Next.js 13 App Router + Tailwind chat UI
    ├── src/
    │   └── app/
    │       ├── layout.tsx       # Root layout (imports globals.css)
    │       └── page.tsx         # Chat UI page (fetches `/ask`)
    ├── public/                  # Static assets
    ├── styles/                  # globals.css + Tailwind imports
    ├── package.json             # Frontend dependencies & scripts
    ├── tsconfig.json            # TypeScript config
    └── next.config.js           # Proxy `/api` to FastAPI if configured
```

---

## ⚙️ Prerequisites

* **Python 3.8+**
* **Node 18+** + **npm**
* **OpenAI API key** (set in `.env`)
* **Tailwind CLI** (installed via `npm install`)

---

## 📝 Configuration

1. Copy `.env.example` to `.env` at the repo root and set:

   ```ini
   OPENAI_API_KEY=sk-…
   CHAT_MODEL=gpt-4.1-mini-2025-04-14           # or gpt-3.5-turbo
   ```
2. (Optional) In `frontend/next.config.js` you can proxy `/api` → `http://localhost:8000`.

---

## 1) Import 10‑K Filings

Prepare a CSV `companies.csv` with columns:

```
ticker,start_date,end_date
AAPL,2020-01-01,2023-01-01
MSFT,2021-01-01,2024-01-01
```

Run the downloader:

```bash
python download_filings.py companies.csv \
  --user-agent "Your Name Your Project <your.email@example.com>"
```

Filing JSONs land in `data/<TICKER>/<ACCESSION>.json`.

---

## 2) Build or Update the Embedding Index

Install Python requirements:

```bash
pip install -r requirements.txt
```

Run the incremental embedder (one‑off or repeatable):

```bash
python incremental_chunk_embed.py
```

* Creates/updates `faiss_index.idx` and `faiss_metadata.json`.
* Skips chunks you’ve already embedded.

---

## 3) Test Retrieval via CLI

```bash
python query_rag.py \
  --query "What liquidity risks does Apple cite?" \
  --k 5
```

This prints the top‑K most similar chunks and their metadata.

---

## 4) Run the FastAPI Backend

From project root:

```bash
uvicorn api.app:app --reload
```

* Endpoint: **`POST http://localhost:8000/ask`**
* Body: `{ "query":"...", "k":5 }`
* Response: `{ answer: string, context: [{ticker, accession, chunk_index, filing_date, score, text}] }`

---

## 5) Run the Frontend Chat UI

```bash
cd frontend
npm install
npm run dev
```

Open **[http://localhost:3000](http://localhost:3000)** in your browser.

* Type a question into the input box.
* Click “Send” to POST to `/ask`.
* See the AI answer and source snippets.

---

## 🛠️ Troubleshooting

* **CORS errors**: Ensure FastAPI has:

  ```python
  from fastapi.middleware.cors import CORSMiddleware
  app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["POST","GET"],
    allow_headers=["*"],
  )
  ```
* **Module not found**: Generate UI components via shadcn:

  ```bash
  cd frontend
  npx shadcn@latest init
  npx shadcn@latest add button input card scroll-area
  ```

---

## 🚀 Next Steps

* Add authentication (API keys, OAuth).
* Persist multi-turn sessions (Redis).
* Deploy containerized (Docker) to AWS/GCP.
* Swap FAISS for a managed vector store.

---

© 2025 AInalyst Open Source Project. Feel free to fork & contribute!

## License

Licensed under the MIT License. See the full text below or in the accompanying [LICENSE](LICENSE) file.

```
MIT License

Copyright (c) Edoardo Schiatti

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```