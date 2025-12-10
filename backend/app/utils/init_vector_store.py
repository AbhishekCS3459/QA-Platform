import logging
from app.utils.database import SessionLocal
from app.services.vector_store import VectorStore

logger = logging.getLogger(__name__)


def init_vector_store():
    db = SessionLocal()
    try:
        vector_store = VectorStore()
        vector_store.create_tables(db)
        vector_store.create_index(db)
    except Exception as e:
        logger.error(f"Error initializing vector store: {str(e)}", exc_info=True)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    init_vector_store()

