"""
DTOs (Data Transfer Objects)
"""
from app.dto.question import (
    QuestionDTO,
    AnswerDTO,
    CreateQuestionRequest,
    CreateAnswerRequest,
)
from app.dto.auth import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    UserResponse,
)

__all__ = [
    "QuestionDTO",
    "AnswerDTO",
    "CreateQuestionRequest",
    "CreateAnswerRequest",
    "RegisterRequest",
    "LoginRequest",
    "TokenResponse",
    "UserResponse",
]
