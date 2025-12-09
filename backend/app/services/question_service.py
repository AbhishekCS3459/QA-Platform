"""
Question Service
Business logic for questions and answers
"""
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from uuid import UUID

from app.models.question import Question, Answer, QuestionStatus
from app.models.user import User
from app.dto.question import QuestionDTO, AnswerDTO


def get_questions(db: Session, skip: int = 0, limit: int = 100) -> List[Question]:
    """Get all questions with answers"""
    return (
        db.query(Question)
        .order_by(
            desc(Question.status == QuestionStatus.ESCALATED),
            desc(Question.created_at)
        )
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_question_by_id(db: Session, question_id: UUID) -> Optional[Question]:
    """Get a question by ID"""
    return db.query(Question).filter(Question.id == question_id).first()


def create_question(
    db: Session, message: str, user_id: UUID
) -> Question:
    """Create a new question"""
    try:
        question = Question(
            message=message,
            user_id=user_id,
            status=QuestionStatus.PENDING,
        )
        db.add(question)
        db.commit()
        db.refresh(question)
        return question
    except Exception as e:
        db.rollback()
        raise ValueError(f"Failed to create question: {str(e)}") from e


def create_answer(
    db: Session,
    question_id: UUID,
    message: str,
    user_id: UUID,
) -> Answer:
    """Create a new answer for a question"""
    try:
        answer = Answer(
            question_id=question_id,
            message=message,
            user_id=user_id,
        )
        db.add(answer)
        db.commit()
        db.refresh(answer)
        return answer
    except Exception as e:
        db.rollback()
        raise ValueError(f"Failed to create answer: {str(e)}") from e


def mark_question_answered(db: Session, question_id: UUID) -> Optional[Question]:
    """Mark a question as answered"""
    question = get_question_by_id(db, question_id)
    if question:
        question.status = QuestionStatus.ANSWERED
        db.commit()
        db.refresh(question)
    return question


def question_to_dto(question: Question) -> QuestionDTO:
    """Convert Question model to DTO"""
    return QuestionDTO(
        id=str(question.id),
        message=question.message,
        timestamp=question.created_at,
        status=question.status.value,
        userId=str(question.user_id),
        username=question.user.username if question.user else "Unknown",
        answers=[
            AnswerDTO(
                id=str(answer.id),
                questionId=str(answer.question_id),
                message=answer.message,
                userId=str(answer.user_id),
                username=answer.user.username if answer.user else "Unknown",
                timestamp=answer.created_at,
            )
            for answer in question.answers
        ],
    )

