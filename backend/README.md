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
HOST=0.0.0.0
PORT=8000
ENVIRONMENT=development
CORS_ORIGINS=http://localhost:3000,http://localhost:3001

# Database URL
DATABASE_URL=postgresql://postgres:password@localhost:5432/postgres
# vector url 
TIMESCALE_SERVICE_URL=postgres://postgres:password@localhost:5432/postgres

SECRET_KEY="secret"
GROQ_API_KEY=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
```

## Development Notes
- API docs available at `/docs` in non-production environments.
- Vector store initialization runs at startup; ensure PostgreSQL has the `vector` extension installed/enabled.

