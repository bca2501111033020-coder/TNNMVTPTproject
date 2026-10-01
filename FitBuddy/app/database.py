"""
database.py
------------
Sets up the SQLite database connection and SQLAlchemy session handling
for the FitBuddy application. The database file (fitbuddy.db) and all
tables are created automatically the first time the application starts,
so no manual SQL setup is required.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'fitbuddy.db')}"

# check_same_thread=False is required because FastAPI can use the
# same SQLite connection across different threads/requests.
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def init_db():
    """Create all tables if they do not already exist."""
    # Import models here so that they are registered on Base.metadata
    # before create_all() is called.
    from app import models  # noqa: F401
    Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI dependency that yields a database session and closes it afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
