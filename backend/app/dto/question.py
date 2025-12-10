"""
Question DTOs
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID


class AnswerDTO(BaseModel):
    id: str
    questionId: str = Field(alias="question_id")
    message: str
    userId: str = Field(alias="user_id")
    username: str
    userIsActive: Optional[bool] = Field(default=True, alias="user_is_active")
    timestamp: datetime

    class Config:
        from_attributes = True
        populate_by_name = True


class QuestionDTO(BaseModel):
    id: str
    message: str
    timestamp: datetime
    status: str
    userId: str = Field(alias="user_id")
    username: str
    userIsActive: Optional[bool] = Field(default=True, alias="user_is_active")
    answers: Optional[List[AnswerDTO]] = []
    classificationLabel: Optional[str] = None
    moderationAction: Optional[str] = None
    moderationReason: Optional[str] = None

    class Config:
        from_attributes = True
        populate_by_name = True


class CreateQuestionRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000)


class CreateAnswerRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000)


class RAGSuggestionResponse(BaseModel):
    """RAG-generated answer suggestion"""
    answer: str
    context_used: bool
    confidence: float = Field(ge=0.0, le=1.0)
    sources: Optional[List[dict]] = []

