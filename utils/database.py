from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from config import Config

# Create engine with connection pooling
engine = create_engine(
    f"postgresql://{Config.POSTGRES_USER}:{Config.POSTGRES_PASSWORD}@{Config.POSTGRES_HOST}:{Config.POSTGRES_PORT}/{Config.POSTGRES_DB}",
    echo=False,
    pool_pre_ping=True,
    pool_size=20,  # Adjust based on your needs
    max_overflow=10,  # Allow up to 10 connections beyond pool_size
    pool_timeout=30,  # Wait up to 30 seconds for a connection
    pool_recycle=1800  # Recycle connections after 30 minutes
)

# Create a thread-safe session factory
session_factory = sessionmaker(
    bind=engine,
    expire_on_commit=False
)
Session = scoped_session(session_factory)

def get_db():
    """Get a new database session for the current request."""
    db = Session()
    try:
        return db
    except Exception as e:
        db.close()
        raise e

def close_db(db):
    """Close the database session."""
    if db is not None:
        db.close()
        Session.remove()