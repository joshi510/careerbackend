from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import settings
import os

# Check if we're on Render (PostgreSQL) or using MySQL
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    # Render provides DATABASE_URL for PostgreSQL
    # Format: postgresql://user:password@host:port/dbname
    if DATABASE_URL.startswith("postgres://"):
        # Render uses postgres:// but SQLAlchemy needs postgresql://
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=300,
        echo=settings.DEBUG
    )
else:
    # Fallback to MySQL configuration
    DATABASE_URL = f"mysql+pymysql://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=300,
        echo=settings.DEBUG
    )

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db():
    """Dependency for getting database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

