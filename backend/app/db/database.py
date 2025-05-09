from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from ..core.config import settings

# Create SQLAlchemy engine
engine = create_engine(settings.POSTGRES_URI)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for SQLAlchemy models
Base = declarative_base()

# Define metadata
metadata = MetaData()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()