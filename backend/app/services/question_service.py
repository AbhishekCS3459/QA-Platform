from sqlalchemy import desc
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from uuid import UUID

from app.dto.question import AnswerDTO, QuestionDTO
from app.models.question import Answer, Question, QuestionStatus
from app.models.user import User
from app.utils.auth import get_user_by_id


def get_questions(db: Session, skip: int = 0, limit: int = 100) -> List[Question]:
    return (
        db.query(Question)
        .options(joinedload(Question.user), joinedload(Question.answers).joinedload(Answer.user))
        .order_by(
            desc(Question.status == QuestionStatus.ESCALATED),
            desc(Question.created_at)
        )
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_question_by_id(db: Session, question_id: UUID) -> Optional[Question]:
    return (
        db.query(Question)
        .options(joinedload(Question.user), joinedload(Question.answers).joinedload(Answer.user))
        .filter(Question.id == question_id)
        .first()
    )


def create_question(
    db: Session,
    message: str,
    user_id: UUID,
    classification_label: Optional[str] = None,
    moderation_action: Optional[str] = None,
    moderation_reason: Optional[str] = None,
) -> Question:
    try:
        question = Question(
            message=message,
            user_id=user_id,
            status=QuestionStatus.PENDING,
            classification_label=classification_label,
            moderation_action=moderation_action,
            moderation_reason=moderation_reason,
        )
        db.add(question)
        db.commit()
        db.refresh(question)
        question = db.query(Question).options(joinedload(Question.user)).filter(Question.id == question.id).first()
        if not question:
            raise ValueError("Failed to reload question after creation")
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
    try:
        answer = Answer(
            question_id=question_id,
            message=message,
            user_id=user_id,
        )
        db.add(answer)
        db.commit()
        db.refresh(answer)
        answer = db.query(Answer).options(joinedload(Answer.user)).filter(Answer.id == answer.id).first()
        if not answer:
            raise ValueError("Failed to reload answer after creation")
        return answer
    except Exception as e:
        db.rollback()
        raise ValueError(f"Failed to create answer: {str(e)}") from e


def mark_question_answered(db: Session, question_id: UUID) -> Optional[Question]:
    question = get_question_by_id(db, question_id)
    if question:
        question.status = QuestionStatus.ANSWERED
        db.commit()
        db.refresh(question)
    return question


def question_to_dto(
    question: Question,
    classification: Optional[dict] = None,
    db: Optional[Session] = None,
) -> QuestionDTO:
    if not db:
        raise ValueError("Database session is required for question_to_dto")
    
    classificationLabel = question.classification_label
    moderationAction = question.moderation_action
    moderationReason = question.moderation_reason
    
    if classification:
        classificationLabel = classification.get("label")
        moderationAction = classification.get("action")
        moderationReason = classification.get("reason")

    question_user = get_user_by_id(db, str(question.user_id))
    username = question_user.username if question_user else "Unknown"
    user_is_active = question_user.is_active if question_user else True
    
    answer_dtos = []
    for answer in question.answers:
        answer_user = get_user_by_id(db, str(answer.user_id))
        answer_username = answer_user.username if answer_user else "Unknown"
        answer_user_is_active = answer_user.is_active if answer_user else True
        
        answer_dtos.append(
            AnswerDTO(
                id=str(answer.id),
                questionId=str(answer.question_id),
                message=answer.message,
                userId=str(answer.user_id),
                username=answer_username,
                userIsActive=answer_user_is_active,
                timestamp=answer.created_at,
            )
        )
    
    return QuestionDTO(
        id=str(question.id),
        message=question.message,
        timestamp=question.created_at,
        status=question.status.value,
        userId=str(question.user_id),
        username=username,
        userIsActive=user_is_active,
        answers=answer_dtos,
        classificationLabel=classificationLabel,
        moderationAction=moderationAction,
        moderationReason=moderationReason,
    )

