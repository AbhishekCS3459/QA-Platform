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
    answers: Optional[List[AnswerDTO]] = []

    class Config:
        from_attributes = True
        populate_by_name = True


class CreateQuestionRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000)


class CreateAnswerRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000)

