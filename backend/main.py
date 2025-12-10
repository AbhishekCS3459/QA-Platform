from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime
import logging

from app.core.config import settings
from app.router.v1.router import api_router
from app.utils.database import engine, Base

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database connection...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created/verified")
        
        from sqlalchemy import text
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
        logger.info("Database connected successfully")
        
        try:
            from app.utils.init_vector_store import init_vector_store
            init_vector_store()
            logger.info("Vector store initialized")
        except Exception as e:
            logger.warning(f"Vector store initialization skipped: {e}")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise
    
    logger.info("Application startup complete")
    yield
    
    logger.info("Application shutdown initiated")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Q&A Dashboard API - Production Grade FastAPI Backend",
    version=settings.VERSION,
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
    openapi_url="/openapi.json" if settings.ENVIRONMENT != "production" else None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    from fastapi import HTTPException
    if isinstance(exc, HTTPException):
        raise exc
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred",
            "timestamp": datetime.utcnow().isoformat(),
        },
    )


@app.get("/")
async def root():
    return {
        "message": "Q&A Dashboard API",
        "version": settings.VERSION,
        "status": "running",
        "docs": "/docs" if settings.ENVIRONMENT != "production" else "disabled",
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.ENVIRONMENT == "development",
    )

