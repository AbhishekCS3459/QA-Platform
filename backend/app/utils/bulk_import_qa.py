import logging
from sqlalchemy.orm import joinedload
from app.utils.database import SessionLocal
from app.services.rag_service import RAGService
from app.models.question import Question, Answer, QuestionStatus

logger = logging.getLogger(__name__)


def bulk_import_qa(
    status_filter: QuestionStatus = QuestionStatus.ANSWERED,
    use_first_answer: bool = True,
    dry_run: bool = False
) -> dict:
    db = SessionLocal()
    rag_service = RAGService()
    
    stats = {
        "total_questions": 0,
        "questions_with_answers": 0,
        "imported": 0,
        "skipped": 0,
        "errors": 0,
        "error_details": []
    }
    
    try:
        query = (
            db.query(Question)
            .join(Answer)
            .filter(Question.status == status_filter)
            .options(joinedload(Question.answers))
            .distinct()
        )
        
        questions_with_answers = query.all()
        stats["total_questions"] = len(questions_with_answers)
        
        for question in questions_with_answers:
            if not question.answers:
                stats["skipped"] += 1
                continue
            
            stats["questions_with_answers"] += 1
            
            if use_first_answer:
                best_answer = sorted(question.answers, key=lambda a: a.created_at)[0]
            else:
                best_answer = sorted(question.answers, key=lambda a: a.created_at, reverse=True)[0]
            
            if dry_run:
                stats["imported"] += 1
                continue
            
            try:
                question_text = question.message.strip()
                answer_text = best_answer.message.strip()
                
                record_id = rag_service.add_to_knowledge_base(
                    db=db,
                    question=question_text,
                    answer=answer_text,
                    question_id=str(question.id),
                    metadata={
                        "question_id": str(question.id),
                        "answer_id": str(best_answer.id),
                        "user_id": str(question.user_id),
                        "question_created_at": question.created_at.isoformat(),
                        "answer_created_at": best_answer.created_at.isoformat(),
                        "total_answers": len(question.answers),
                        "status": question.status.value,
                    }
                )
                if record_id:
                    stats["imported"] += 1
                else:
                    stats["skipped"] += 1
                
            except Exception as e:
                stats["errors"] += 1
                error_detail = {
                    "question_id": str(question.id),
                    "error": str(e)
                }
                stats["error_details"].append(error_detail)
                logger.error(f"Error importing question {question.id}: {str(e)}", exc_info=True)
        
        return stats
        
    except Exception as e:
        logger.error(f"Error during bulk import: {str(e)}", exc_info=True)
        raise
    finally:
        db.close()


def bulk_import_all_answered_questions(dry_run: bool = False) -> dict:
    return bulk_import_qa(
        status_filter=QuestionStatus.ANSWERED,
        use_first_answer=True,
        dry_run=dry_run
    )


if __name__ == "__main__":
    import sys
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Check for dry-run flag
    dry_run = "--dry-run" in sys.argv or "-d" in sys.argv
    
    if dry_run:
        print("Running in DRY RUN mode - no data will be imported")
    
    print("Starting bulk import of Q&A pairs to knowledge base...")
    stats = bulk_import_all_answered_questions(dry_run=dry_run)
    
    print("\n" + "="*50)
    print("Import Statistics:")
    print("="*50)
    print(f"Total questions found: {stats['total_questions']}")
    print(f"Questions with answers: {stats['questions_with_answers']}")
    print(f"Successfully imported: {stats['imported']}")
    print(f"Skipped: {stats['skipped']}")
    print(f"Errors: {stats['errors']}")
    
    if stats['errors'] > 0:
        print("\nErrors:")
        for error in stats['error_details']:
            print(f"  - Question {error['question_id']}: {error['error']}")
    
    print("="*50)

