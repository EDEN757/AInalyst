import logging
import time
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
import traceback
import sys

from .api import chat, companies
from .core.config import settings
from .db.database import engine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="S&P 500 10-K RAG Chatbot API",
    description="A RAG-based chatbot for querying S&P 500 companies' 10-K filings",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat.router, prefix="/api/v1", tags=["chat"])
app.include_router(companies.router, prefix="/api/v1", tags=["companies"])

# Middleware for request logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = str(time.time())
    request.state.start_time = time.time()
    request.state.request_id = request_id
    
    client_ip = request.client.host if request.client else "unknown"
    logger.info(f"Request {request_id} started: {request.method} {request.url.path} from {client_ip}")
    
    try:
        response = await call_next(request)
        
        process_time = time.time() - request.state.start_time
        logger.info(
            f"Request {request_id} completed: {request.method} {request.url.path} "
            f"status={response.status_code} duration={process_time:.3f}s"
        )
        
        # Add processing time header
        response.headers["X-Process-Time"] = str(process_time)
        return response
    except Exception as e:
        logger.error(f"Request {request_id} failed: {str(e)}")
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"},
        )

# Startup event to check database connection and initialize tables
@app.on_event("startup")
async def startup_db_client():
    logger.info("Starting up application...")
    
    # First attempt - try standard database initialization
    try:
        # Verify database connection
        from sqlalchemy import text
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            if result:
                logger.info("✅ Successfully connected to the database")
            else:
                logger.error("❌ Failed to validate database connection")
        
        # Initialize database tables if they don't exist
        from app.db.database import Base
        from app.models.database_models import Company, Filing, TextChunk
        logger.info("Creating database tables if they don't exist...")
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables created or verified")
        
        # Verify tables were actually created
        try:
            with engine.connect() as conn:
                # Try to query the companies table
                conn.execute(text("SELECT 1 FROM companies LIMIT 1"))
                logger.info("✓ Verified companies table exists")
        except Exception as table_error:
            logger.warning(f"Companies table check failed: {str(table_error)}")
            # If this fails, we'll try more aggressively below
            raise
                
        # Log configuration information
        logger.info(f"Application Mode: {settings.APP_MODE}")
        logger.info(f"Embedding Provider: {settings.EMBEDDING_PROVIDER}")
        logger.info(f"Embedding Model: {settings.EMBEDDING_MODEL}")
        logger.info(f"Chat Provider: {settings.CHAT_PROVIDER}")
        logger.info(f"Chat Model: {settings.CHAT_MODEL}")
        
    except Exception as e:
        # Log the error but don't exit - try more aggressively
        logger.error(f"❌ Database initialization error: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Second attempt - more forceful approach with explicit SQL
        logger.warning("Attempting alternative database initialization...")
        try:
            # Force-create tables with SQL
            with engine.connect() as conn:
                # Create vector extension first
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                
                # Companies table
                conn.execute(text("""
                CREATE TABLE IF NOT EXISTS companies (
                    id SERIAL PRIMARY KEY,
                    symbol VARCHAR(10) UNIQUE,
                    name VARCHAR(255),
                    sector VARCHAR(255),
                    industry VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """))
                
                # Filings table
                conn.execute(text("""
                CREATE TABLE IF NOT EXISTS filings (
                    id SERIAL PRIMARY KEY,
                    company_id INTEGER REFERENCES companies(id),
                    filing_type VARCHAR(10),
                    filing_date TIMESTAMP,
                    filing_url TEXT,
                    accession_number VARCHAR(100) UNIQUE,
                    fiscal_year INTEGER,
                    fiscal_period VARCHAR(10),
                    processed BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """))
                
                # Text chunks table with vector support
                conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS text_chunks (
                    id SERIAL PRIMARY KEY,
                    filing_id INTEGER REFERENCES filings(id),
                    chunk_index INTEGER,
                    text_content TEXT,
                    section VARCHAR(255),
                    page_number INTEGER,
                    embedded BOOLEAN DEFAULT FALSE,
                    embedding vector({settings.EMBEDDING_DIMENSION}),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """))
                
                conn.commit()
                logger.info("✅ Database tables created with SQL")
                
        except Exception as sql_error:
            logger.error(f"💥 Failed to create tables with SQL: {str(sql_error)}")
            logger.error(traceback.format_exc())

# Shutdown event to clean up resources
@app.on_event("shutdown")
async def shutdown_db_client():
    logger.info("Shutting down application...")
    # Engine has built-in cleanup

@app.get("/")
async def root():
    try:
        # Test database connection
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            db_status = "connected"
    except Exception as e:
        logger.error(f"Database connection check failed: {str(e)}")
        db_status = f"error: {str(e)}"
    
    return {
        "message": "S&P 500 10-K RAG Chatbot API",
        "mode": settings.APP_MODE,
        "embedding_provider": settings.EMBEDDING_PROVIDER,
        "embedding_model": settings.EMBEDDING_MODEL,
        "chat_provider": settings.CHAT_PROVIDER,
        "chat_model": settings.CHAT_MODEL,
        "database_status": db_status
    }

@app.get("/health")
async def health_check():
    # Check database connection
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            db_status = "ok"
    except Exception as e:
        logger.error(f"Health check database connection failed: {str(e)}")
        db_status = "error"
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "error",
                "database": db_status,
                "error": str(e)
            }
        )
    
    return {
        "status": "ok",
        "database": db_status,
        "version": "1.0.0"
    }
