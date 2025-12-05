import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:2323@localhost:5432/github_repos",
)

engine = create_engine(DATABASE_URL, future=True, echo=False)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    future=True,
)

Base = declarative_base()


def get_db():
    """FastAPI dependency to inject database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()