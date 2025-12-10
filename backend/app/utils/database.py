from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

logger.info(f"Creating database engine with URL: {settings.DATABASE_URL.split('@')[0]}@***")
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

logger.info("Database engine and session factory created")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
