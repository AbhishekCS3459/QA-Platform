# Backend Setup Guide

## Prerequisites
- Python 3.11+ and `pip`
- PostgreSQL with the `vector` extension available (e.g., via `pgvector`)
- (Optional) TimescaleDB service if you use the timeseries features referenced by `TIMESCALE_SERVICE_URL`

## Setup
1. Create and activate a virtual environment  
   - Windows: `python -m venv venv && venv\\Scripts\\activate`  
   - macOS/Linux: `python -m venv venv && source venv/bin/activate`
2. Install dependencies: `pip install -r requirements.txt`
3. Create a `.env` file in `backend/` using the template below.
4. Initialize the vector table/index (runs automatically on startup); ensure the database has the `vector` extension enabled.
5. Run the API: `uvicorn main:app --reload --host 0.0.0.0 --port 8000`

## Environment Variables (`.env` template)
```
# App
PROJECT_NAME=Q&A Dashboard API
VERSION=1.0.0
API_V1_PREFIX=/api/v1
HOST=0.0.0.0
PORT=8000
ENVIRONMENT=development  # development|production

# Database
DATABASE_URL=postgresql+psycopg2://user:pass@localhost:5432/db_name
TIMESCALE_SERVICE_URL=http://localhost:9000  # if applicable

# Security
SECRET_KEY=change-me

# CORS (comma-separated origins)
CORS_ORIGINS=http://localhost:3000

# Groq / LLM
GROQ_API_KEY=your-groq-key
GROQ_MODEL=llama-3.3-70b-versatile
GROQ_TEMPERATURE=1.0
GROQ_MAX_COMPLETION_TOKENS=8192
GROQ_TOP_P=1.0
GROQ_REASONING_EFFORT=

# Embeddings / Vector store
EMBEDDING_MODEL=all-MiniLM-L6-v2
VECTOR_TABLE_NAME=question_embeddings
VECTOR_EMBEDDING_DIMENSIONS=384
```

## Development Notes
- API docs available at `/docs` in non-production environments.
- Vector store initialization runs at startup; ensure PostgreSQL has the `vector` extension installed/enabled.

