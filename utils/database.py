from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import Config

# Connect to PostgreSQL
PostgreSQL = sessionmaker(
    create_engine(
        f"postgresql://{Config.POSTGRES_USER}:{Config.POSTGRES_PASSWORD}@{Config.POSTGRES_HOST}:{Config.POSTGRES_PORT}/{Config.POSTGRES_DB}",
        echo=False,
        pool_pre_ping=True
    ),
    expire_on_commit=False
)