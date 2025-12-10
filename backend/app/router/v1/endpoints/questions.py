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
    RAGSuggestionResponse,
)
from app.services.question_service import (
    get_questions,
    get_question_by_id,
    create_question,
    create_answer,
    mark_question_answered,
    question_to_dto,
)
from app.services.moderation_service import ModerationService
from app.dependencies import get_current_user_optional, get_current_user
from app.models.user import User
from app.router.v1.endpoints.websocket import manager
from app.utils.auth import get_user_by_id
from app.utils.guest_user import get_or_create_guest_user

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=list[QuestionDTO])
async def fetch_questions(db: Session = Depends(get_db)):
    questions = get_questions(db)
    return [question_to_dto(q, db=db) for q in questions]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_question_endpoint(
    request: CreateQuestionRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    try:
        if current_user:
            user_id = current_user.id
        else:
            guest_user = get_or_create_guest_user(db)
            user_id = guest_user.id
        
        classification = None
        try:
            moderation_service = ModerationService()
            classification = moderation_service.classify(request.message)
        except Exception:
            pass
        
        question = create_question(
            db,
            message=request.message,
            user_id=user_id,
            classification_label=classification.get("label") if classification else None,
            moderation_action=classification.get("action") if classification else None,
            moderation_reason=classification.get("reason") if classification else None,
        )

        if classification and classification.get("action") == "ban":
            user_banned = moderation_service.ban_user(db, str(user_id))
            
            if not user_banned:
                user = db.query(User).filter(User.id == UUID(str(user_id))).first()
                if user:
                    db.delete(user)
                    db.commit()
            
            verify_user = db.query(User).filter(User.id == UUID(str(user_id))).first()
            if verify_user:
                logger.error(f"CRITICAL: User {user_id} still exists after deletion attempt!")
            else:
                logger.warning(
                    "User %s banned and deleted: %s - %s",
                    user_id,
                    classification.get("label"),
                    classification.get("reason")
                )
            
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Your question was removed due to content policy violation: {classification.get('reason')}. Your account has been banned."
            )
        
        rag_suggestion = None
        try:
            from app.services.rag_service import RAGService
            rag_service = RAGService()
            rag_suggestion = rag_service.generate_answer(
                db=db,
                question=request.message,
                limit=3,
                similarity_threshold=0.6
            )
        except Exception:
            pass
        
        question_dto = question_to_dto(question, db=db)
        websocket_message = json.dumps({
            "type": "question_created",
            "data": {
                "id": question_dto.id,
                "message": question_dto.message,
                "timestamp": question_dto.timestamp.isoformat(),
                "status": question_dto.status,
                "userId": question_dto.userId,
                "username": question_dto.username,
                "answers": [],
                "classificationLabel": question_dto.classificationLabel,
                "moderationAction": question_dto.moderationAction,
                "moderationReason": question_dto.moderationReason,
                "ragSuggestion": rag_suggestion if rag_suggestion and rag_suggestion.get("confidence", 0) > 0.6 else None
            }
        })
        await manager.broadcast(websocket_message)
        
        response = {"id": str(question.id), "message": "Question created successfully"}
        if rag_suggestion and rag_suggestion.get("confidence", 0) > 0.6:
            response["ragSuggestion"] = rag_suggestion
        
        return response
    except HTTPException as http_exc:
        raise http_exc
    except ValueError as e:
        logger.error(f"ValueError creating question: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
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
    
    try:
        moderation_service = ModerationService()
        classification = moderation_service.classify(request.message)
        
        if classification.get("action") == "ban":
            moderation_service.ban_user(db, str(user_id))
            logger.warning(
                "User %s banned due to moderation action on answer: %s",
                user_id,
                classification.get("label")
            )
    except Exception:
        pass
    
    try:
        from app.services.rag_service import RAGService
        rag_service = RAGService()
        rag_service.add_to_knowledge_base(
            db=db,
            question=question.message,
            answer=request.message,
            question_id=str(q_id),
            metadata={"question_id": str(q_id), "answer_id": str(answer.id)},
        )
    except Exception:
        pass
    
    answer_user = get_user_by_id(db, str(answer.user_id))
    answer_dto = AnswerDTO(
        id=str(answer.id),
        questionId=str(answer.question_id),
        message=answer.message,
        userId=str(answer.user_id),
        username=answer_user.username if answer_user else "Unknown",
        userIsActive=answer_user.is_active if answer_user else True,
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
                "userIsActive": answer_dto.userIsActive,
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


@router.post("/{question_id}/rag-suggestion", response_model=RAGSuggestionResponse)
async def get_rag_suggestion(
    question_id: str,
    db: Session = Depends(get_db),
):
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

    try:
        from app.services.rag_service import RAGService
        rag_service = RAGService()
        
        suggestion = rag_service.generate_answer(
            db=db,
            question=question.message,
            limit=3,
            similarity_threshold=0.6
        )
        
        return RAGSuggestionResponse(**suggestion)
    except Exception as e:
        logger.error(f"Error generating RAG suggestion: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating suggestion: {str(e)}",
        )


@router.post("/rag-suggest", response_model=RAGSuggestionResponse)
async def get_rag_suggestion_for_text(
    request: CreateQuestionRequest,
    db: Session = Depends(get_db),
):
    try:
        from app.services.rag_service import RAGService
        rag_service = RAGService()
        
        suggestion = rag_service.generate_answer(
            db=db,
            question=request.message,
            limit=3,
            similarity_threshold=0.6
        )
        
        return RAGSuggestionResponse(**suggestion)
    except Exception as e:
        logger.error(f"Error generating RAG suggestion: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating suggestion: {str(e)}",
        )

