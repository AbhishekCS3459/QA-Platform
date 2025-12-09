"""
API Router - Version 1
Main router that includes all API endpoints
"""
from fastapi import APIRouter
from app.router.v1.endpoints import health, websocket, questions, auth

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(websocket.router, tags=["websocket"])
api_router.include_router(questions.router, prefix="/questions", tags=["questions"])

