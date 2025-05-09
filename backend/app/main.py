from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import os
import uvicorn
import asyncio
from typing import Callable
import threading

from .core.config import settings
from .api import chat, companies, companies_csv, retrieval
from .db.database import SessionLocal
from .data_updater.scheduler import on_launch_update

# Configure logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="AInalyst API",
    description="API for AInalyst, a Finance Chatbot with RAG",
    version="0.1.0",
)

# Function to run on-launch update in the background
def run_background_update():
    """Run the on-launch update in a background thread."""
    async def async_update():
        try:
            db = SessionLocal()
            try:
                logger.info("Starting on-launch data update...")
                stats = await on_launch_update(db)
                if "error" in stats:
                    logger.error(f"On-launch update failed: {stats['error']}")
                else:
                    logger.info(f"On-launch update completed: {stats['total']}")
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Error in on-launch update: {str(e)}")

    # Create event loop for the thread
    def run_async_update():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(async_update())
        loop.close()

    # Start update in a separate thread
    thread = threading.Thread(target=run_async_update)
    thread.daemon = True
    thread.start()

# Create startup event handler
@app.on_event("startup")
def startup_event():
    """Runs when the application starts."""
    logger.info("Starting AInalyst API")
    # Run data update in the background
    run_background_update()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development; restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root endpoint
@app.get("/")
async def root():
    return {"message": "Welcome to AInalyst API!"}

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Include routers
app.include_router(retrieval.router, prefix=f"{settings.API_PREFIX}/search", tags=["Search"])
app.include_router(chat.router, prefix=f"{settings.API_PREFIX}/chat", tags=["Chat"])
app.include_router(companies.router, prefix=f"{settings.API_PREFIX}/data", tags=["Companies"])
app.include_router(companies_csv.router, prefix=f"{settings.API_PREFIX}/data", tags=["Companies CSV"])

# Error handler for generic exceptions
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred"},
    )

# Main entry point
if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)