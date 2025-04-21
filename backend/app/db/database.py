import logging
import time
from typing import Generator
from sqlalchemy import create_engine, event
from sqlalchemy.exc import SQLAlchemyError, OperationalError, DisconnectionError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.engine import Engine

from ..core.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set up database connection with connection pooling and retry settings
try:
    engine = create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,  # Test connections before using them
        pool_size=5,         # Maximum number of connections to keep open
        max_overflow=10,     # Maximum overflow connections when pool is full
        pool_timeout=30,     # Timeout for getting a connection from the pool
        pool_recycle=1800    # Recycle connections after 30 minutes (prevent stale)
    )
    logger.info(f"Database engine created successfully with connection pooling")
except Exception as e:
    logger.error(f"Failed to create database engine: {e}")
    raise

# Set up session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Log queries that take too long
@event.listens_for(Engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    conn.info.setdefault('query_start_time', []).append(time.time())
    logger.debug(f"Begin Query: {statement}")

@event.listens_for(Engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    total = time.time() - conn.info['query_start_time'].pop(-1)
    if total > 0.5:  # Log queries taking more than 500ms
        logger.warning(f"Slow Query ({total:.2f}s): {statement}")
    else:
        logger.debug(f"End Query ({total:.2f}s)")

def get_db() -> Generator[Session, None, None]:
    """
    Database dependency to get a DB session with error handling and retries.
    """
    db = SessionLocal()
    retries = 3
    retry_delay = 0.5  # seconds
    
    # Try to verify the connection
    for attempt in range(retries):
        try:
            # Test connection with a simple query
            db.execute("SELECT 1")
            break
        except (OperationalError, DisconnectionError) as e:
            logger.warning(f"Database connection failed on attempt {attempt+1}/{retries}: {e}")
            if attempt < retries - 1:
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
                db.close()
                db = SessionLocal()
            else:
                logger.error(f"Database connection failed after {retries} attempts")
                raise
    try:
        logger.debug("Database connection successful, yielding session")
        yield db
    except SQLAlchemyError as e:
        logger.error(f"Database error during session use: {e}")
        raise
    finally:
        logger.debug("Closing database session")
        db.close()
