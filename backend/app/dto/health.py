"""
Health Check DTOs
Pydantic models for health check endpoints
"""
from pydantic import BaseModel
from typing import Dict, Any, Optional
from datetime import datetime


class HealthResponse(BaseModel):
    """Basic health check response"""
    status: str
    service: str
    version: str
    timestamp: datetime


class DetailedHealthResponse(BaseModel):
    """Detailed health check response"""
    status: str
    service: str
    version: str
    timestamp: datetime
    system: Optional[Dict[str, Any]] = None
    resources: Optional[Dict[str, Any]] = None
    application: Optional[Dict[str, Any]] = None

