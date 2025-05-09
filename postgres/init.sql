-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create database if it doesn't exist
-- This is handled by Docker automatically, but included for documentation
-- CREATE DATABASE finance_rag_db;

-- Create tables for the application
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

-- Create indices for faster retrieval
CREATE INDEX IF NOT EXISTS idx_filings_metadata_ticker ON filings_metadata(ticker);
CREATE INDEX IF NOT EXISTS idx_filings_metadata_year ON filings_metadata(year);
CREATE INDEX IF NOT EXISTS idx_filings_metadata_document_type ON filings_metadata(document_type);
CREATE INDEX IF NOT EXISTS idx_filings_metadata_text_hash ON filings_metadata(text_hash);
CREATE INDEX IF NOT EXISTS idx_filings_metadata_ticker_year ON filings_metadata(ticker, year);
CREATE INDEX IF NOT EXISTS idx_filings_metadata_ticker_year_type ON filings_metadata(ticker, year, document_type);

-- Document vectors table (for pgvector)
CREATE TABLE IF NOT EXISTS document_vectors (
    doc_id VARCHAR(255) PRIMARY KEY,
    embedding VECTOR(1536), -- Using the default dimension for OpenAI embeddings
    FOREIGN KEY (doc_id) REFERENCES filings_metadata(doc_id) ON DELETE CASCADE
);

-- Create an index for faster similarity search on the embeddings
CREATE INDEX IF NOT EXISTS idx_hnsw_embedding ON document_vectors USING hnsw (embedding vector_l2_ops);

-- Document chunks table to store the actual text content
CREATE TABLE IF NOT EXISTS document_chunks (
    doc_id VARCHAR(255) PRIMARY KEY,
    chunk_text TEXT NOT NULL,
    chunk_number INT,
    total_chunks INT,
    FOREIGN KEY (doc_id) REFERENCES filings_metadata(doc_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_document_chunks_doc_id ON document_chunks(doc_id);

-- Create a table to store chat history
CREATE TABLE IF NOT EXISTS chat_history (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    user_message TEXT NOT NULL,
    assistant_message TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB
);

-- Create index on session_id for faster retrieval
CREATE INDEX IF NOT EXISTS idx_chat_history_session_id ON chat_history(session_id);
CREATE INDEX IF NOT EXISTS idx_chat_history_session_id_created_at ON chat_history(session_id, created_at);

-- Function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for updating timestamps
CREATE TRIGGER update_filings_metadata_modtime
BEFORE UPDATE ON filings_metadata
FOR EACH ROW
EXECUTE FUNCTION update_modified_column();

-- View for document statistics
CREATE OR REPLACE VIEW document_statistics AS
SELECT
    ticker,
    year,
    document_type,
    section_name,
    COUNT(*) as chunk_count
FROM
    filings_metadata
GROUP BY
    ticker, year, document_type, section_name
ORDER BY
    ticker, year, document_type, section_name;