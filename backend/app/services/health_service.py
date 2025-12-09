"""
Health Service
Business logic for health check operations
"""
from typing import Dict, Any
from datetime import datetime
import platform
import sys
import psutil

from app.core.config import settings


def get_basic_health() -> Dict[str, Any]:
    """
    Get basic health status
    
    Returns:
        Basic health information
    """
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "timestamp": datetime.utcnow().isoformat(),
    }


def get_detailed_health() -> Dict[str, Any]:
    """
    Get detailed health status with system information
    
    Returns:
        Detailed health information including system metrics
    """
    try:
        system_info = {
            "platform": platform.system(),
            "platform_version": platform.version(),
            "python_version": sys.version.split()[0],
            "architecture": platform.machine(),
        }
        
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        
        resource_usage = {
            "cpu": {
                "percent": cpu_percent,
                "count": psutil.cpu_count(),
            },
            "memory": {
                "total_gb": round(memory.total / (1024 ** 3), 2),
                "available_gb": round(memory.available / (1024 ** 3), 2),
                "used_gb": round(memory.used / (1024 ** 3), 2),
                "percent": memory.percent,
            },
        }
        
        app_config = {
            "environment": settings.ENVIRONMENT,
            "api_version": settings.API_V1_PREFIX,
            "host": settings.HOST,
            "port": settings.PORT,
        }
        
        return {
            "status": "healthy",
            "service": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "timestamp": datetime.utcnow().isoformat(),
            "system": system_info,
            "resources": resource_usage,
            "application": app_config,
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }

