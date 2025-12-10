import logging
import json
from typing import List, Optional, Dict, Any
import uuid
import threading

from sentence_transformers import SentenceTransformer
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings

logger = logging.getLogger(__name__)

_embedding_model_cache = {}
_model_lock = threading.Lock()


class VectorStore:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(VectorStore, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self.settings = settings
        self.embedding_model_name = self.settings.EMBEDDING_MODEL
        self.table_name = self.settings.VECTOR_TABLE_NAME
        self.embedding_dimensions = self.settings.VECTOR_EMBEDDING_DIMENSIONS
        
        self.embedding_model = self._get_embedding_model()
        self._initialized = True
    
    def _get_embedding_model(self):
        if self.embedding_model_name not in _embedding_model_cache:
            with _model_lock:
                if self.embedding_model_name not in _embedding_model_cache:
                    try:
                        logger.info(f"Loading embedding model: {self.embedding_model_name}")
                        _embedding_model_cache[self.embedding_model_name] = SentenceTransformer(self.embedding_model_name)
                        logger.info(f"Embedding model {self.embedding_model_name} loaded successfully")
                    except Exception as e:
                        logger.error(f"Failed to load embedding model: {str(e)}")
                        raise
        return _embedding_model_cache[self.embedding_model_name]

    def get_embedding(self, text: str) -> List[float]:
        text = text.replace("\n", " ").strip()
        if not text:
            raise ValueError("Text cannot be empty")
        
        try:
            embedding = self.embedding_model.encode(text, convert_to_numpy=True).tolist()
            return embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            raise

    def create_tables(self, db: Session) -> None:
        try:
            db.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            db.commit()
        except Exception:
            db.rollback()

        try:
            create_table_query = f"""
            CREATE TABLE IF NOT EXISTS {self.table_name} (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                content TEXT NOT NULL,
                metadata JSONB,
                embedding vector({self.embedding_dimensions}),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
            db.execute(text(create_table_query))
            db.commit()
        except Exception as e:
            logger.error(f"Error creating table: {str(e)}")
            db.rollback()
            raise

    def create_index(self, db: Session) -> None:
        try:
            index_query = f"""
            CREATE INDEX IF NOT EXISTS {self.table_name}_embedding_idx 
            ON {self.table_name} 
            USING hnsw (embedding vector_cosine_ops)
            """
            db.execute(text(index_query))
            db.commit()
        except Exception:
            db.rollback()

    def upsert(
        self,
        db: Session,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        record_id: Optional[str] = None
    ) -> str:
        embedding = self.get_embedding(content)
        
        if record_id:
            try:
                uuid.UUID(record_id)
            except ValueError:
                raise ValueError(f"Invalid UUID format: {record_id}")
        else:
            record_id = str(uuid.uuid4())

        metadata_json = metadata or {}
        embedding_str = "[" + ",".join(str(float(x)) for x in embedding) + "]"
        metadata_json_str = json.dumps(metadata_json)
        
        upsert_query = f"""
        INSERT INTO {self.table_name} (id, content, metadata, embedding)
        VALUES (:id, :content, CAST(:metadata AS jsonb), '{embedding_str}'::vector)
        ON CONFLICT (id) 
        DO UPDATE SET 
            content = EXCLUDED.content,
            metadata = EXCLUDED.metadata,
            embedding = EXCLUDED.embedding,
            created_at = CURRENT_TIMESTAMP
        """
        
        db.execute(
            text(upsert_query),
            {
                "id": record_id,
                "content": content,
                "metadata": metadata_json_str
            }
        )
        db.commit()
        return record_id

    def search(
        self,
        db: Session,
        query_text: str,
        limit: int = 5,
        metadata_filter: Optional[Dict[str, Any]] = None,
        threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        query_embedding = self.get_embedding(query_text)
        embedding_str = "[" + ",".join(str(float(x)) for x in query_embedding) + "]"
        
        base_query = f"""
        SELECT 
            id,
            content,
            metadata,
            1 - (embedding <=> '{embedding_str}'::vector) as similarity
        FROM {self.table_name}
        WHERE 1 - (embedding <=> '{embedding_str}'::vector) >= :threshold
        """
        
        params = {"threshold": threshold}
        
        if metadata_filter:
            metadata_conditions = []
            for key, value in metadata_filter.items():
                metadata_conditions.append(f"metadata->>'{key}' = :{key}")
                params[key] = str(value)
            
            if metadata_conditions:
                base_query += " AND " + " AND ".join(metadata_conditions)
        
        base_query += f"""
        ORDER BY embedding <=> '{embedding_str}'::vector
        LIMIT :limit
        """
        params["limit"] = limit
        
        result = db.execute(text(base_query), params)
        rows = result.fetchall()
        
        results = []
        for row in rows:
            results.append({
                "id": str(row[0]),
                "content": row[1],
                "metadata": row[2] or {},
                "similarity": float(row[3])
            })
        
        return results

    def delete(
        self,
        db: Session,
        record_id: Optional[str] = None,
        metadata_filter: Optional[Dict[str, Any]] = None,
        delete_all: bool = False
    ) -> int:
        if sum(bool(x) for x in (record_id, metadata_filter, delete_all)) != 1:
            raise ValueError(
                "Provide exactly one of: record_id, metadata_filter, or delete_all"
            )

        if delete_all:
            query = f"DELETE FROM {self.table_name}"
            params = {}
        elif record_id:
            query = f"DELETE FROM {self.table_name} WHERE id = :id"
            params = {"id": record_id}
        elif metadata_filter:
            conditions = []
            params = {}
            for key, value in metadata_filter.items():
                conditions.append(f"metadata->>'{key}' = :{key}")
                params[key] = str(value)
            query = f"DELETE FROM {self.table_name} WHERE " + " AND ".join(conditions)
        else:
            return 0

        result = db.execute(text(query), params)
        db.commit()
        return result.rowcount

