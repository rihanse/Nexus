"""
Database engine and session configuration for the Enterprise Copilot.
"""
import os
from typing import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

load_dotenv()

DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./enterprise_copilot.db")

# SQLite needs connect_args for multi-threaded use
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides a database session per request.
    Ensures the session is always closed after use.
    """
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
