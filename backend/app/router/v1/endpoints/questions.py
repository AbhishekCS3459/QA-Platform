"""
Questions Endpoint
"""
import json
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional

from app.utils.database import get_db
from app.dto.question import (
    QuestionDTO,
    AnswerDTO,
    CreateQuestionRequest,
    CreateAnswerRequest,
)
from app.services.question_service import (
    get_questions,
    get_question_by_id,
    create_question,
    create_answer,
    mark_question_answered,
    question_to_dto,
)
from app.dependencies import get_current_user_optional, get_current_user
from app.models.user import User
from app.router.v1.endpoints.websocket import manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=list[QuestionDTO])
async def fetch_questions(db: Session = Depends(get_db)):
    """Get all questions"""
    questions = get_questions(db)
    return [question_to_dto(q) for q in questions]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_question_endpoint(
    request: CreateQuestionRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Create a new question (guests and authenticated users can post)"""
    from app.utils.guest_user import get_or_create_guest_user
    
    try:
        if current_user:
            user_id = current_user.id
            logger.info(f"Creating question for authenticated user: {user_id}")
        else:
            guest_user = get_or_create_guest_user(db)
            user_id = guest_user.id
            logger.info(f"Creating question for guest user: {user_id}")
        
        question = create_question(
            db,
            message=request.message,
            user_id=user_id,
        )
        logger.info(f"Question created successfully: {question.id}")
        
        question_dto = question_to_dto(question)
        websocket_message = json.dumps({
            "type": "question_created",
            "data": {
                "id": question_dto.id,
                "message": question_dto.message,
                "timestamp": question_dto.timestamp.isoformat(),
                "status": question_dto.status,
                "userId": question_dto.userId,
                "username": question_dto.username,
                "answers": []
            }
        })
        await manager.broadcast(websocket_message)
        
        return {"id": str(question.id), "message": "Question created successfully"}
    except ValueError as e:
        logger.error(f"ValueError creating question: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Unexpected error creating question: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while creating the question: {str(e)}",
        )


@router.post("/{question_id}/answers", status_code=status.HTTP_201_CREATED)
async def create_answer_endpoint(
    question_id: str,
    request: CreateAnswerRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Create an answer for a question (guests and authenticated users can answer)"""
    try:
        q_id = UUID(question_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid question ID format",
        )

    question = get_question_by_id(db, q_id)
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found",
        )

    from app.utils.guest_user import get_or_create_guest_user
    
    if current_user:
        user_id = current_user.id
    else:
        guest_user = get_or_create_guest_user(db)
        user_id = guest_user.id

    answer = create_answer(
        db,
        question_id=q_id,
        message=request.message,
        user_id=user_id,
    )
    
    db.refresh(answer)
    
    answer_dto = AnswerDTO(
        id=str(answer.id),
        questionId=str(answer.question_id),
        message=answer.message,
        userId=str(answer.user_id),
        username=answer.user.username if answer.user else "Unknown",
        timestamp=answer.created_at,
    )
    
    websocket_message = json.dumps({
        "type": "answer_created",
        "data": {
            "questionId": str(q_id),
            "answer": {
                "id": answer_dto.id,
                "questionId": answer_dto.questionId,
                "message": answer_dto.message,
                "timestamp": answer_dto.timestamp.isoformat(),
                "userId": answer_dto.userId,
                "username": answer_dto.username,
            }
        }
    })
    await manager.broadcast(websocket_message)
    
    return {"id": str(answer.id), "message": "Answer created successfully"}


@router.patch("/{question_id}/mark-answered", status_code=status.HTTP_200_OK)
async def mark_question_answered_endpoint(
    question_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark a question as answered (Authenticated users only)"""
    try:
        q_id = UUID(question_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid question ID format",
        )

    question = mark_question_answered(db, q_id)
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found",
        )
    
    websocket_message = json.dumps({
        "type": "question_answered",
        "data": {
            "questionId": str(q_id)
        }
    })
    await manager.broadcast(websocket_message)

    return {"message": "Question marked as answered"}

