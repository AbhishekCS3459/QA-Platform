import logging
from typing import List, Dict, Any, Optional
from groq import Groq
from groq import GroqError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.vector_store import VectorStore

logger = logging.getLogger(__name__)


class RAGService:

    SYSTEM_PROMPT = """
    You are an AI assistant for a Q&A forum system. Your task is to synthesize a coherent and helpful answer 
    based on the given question and relevant context retrieved from a knowledge database of previous questions and answers.

    Guidelines:
    1. Provide a clear and concise answer to the question.
    2. Use only the information from the relevant context to support your answer.
    3. The context is retrieved based on semantic similarity, so some information might be missing or irrelevant.
    4. Be transparent when there is insufficient information to fully answer the question.
    5. Do not make up or infer information not present in the provided context.
    6. If you cannot answer the question based on the given context, clearly state that.
    7. Maintain a helpful and professional tone appropriate for a forum discussion.
    8. If the context contains similar questions and answers, synthesize the best answer from them.
    
    Format your response as a natural, conversational answer that would be helpful to someone asking this question.
    """

    def __init__(self):
        import os
        api_key = settings.GROQ_API_KEY or os.getenv("GROQ_API_KEY")
        
        if not api_key:
            raise ValueError(
                "GROQ_API_KEY is required. Please set it in .env file as GROQ_API_KEY"
            )
        
        self.client = Groq(api_key=api_key)
        self.model = settings.GROQ_MODEL
        self.vector_store = VectorStore()
        self.temperature = settings.GROQ_TEMPERATURE
        self.max_completion_tokens = settings.GROQ_MAX_COMPLETION_TOKENS
        self.top_p = settings.GROQ_TOP_P
        self.reasoning_effort = settings.GROQ_REASONING_EFFORT

    def generate_answer(
        self,
        db: Session,
        question: str,
        limit: int = 3,
        similarity_threshold: float = 0.7
    ) -> Dict[str, Any]:
        try:
            try:
                similar_contexts = self.vector_store.search(
                    db=db,
                    query_text=question,
                    limit=limit,
                    threshold=similarity_threshold
                )
            except Exception as e:
                logger.error(f"Error during vector search: {str(e)}")
                return {
                    "answer": "The AI assistant encountered an error while searching the knowledge base. Please wait for community members to respond.",
                    "context_used": False,
                    "confidence": 0.0,
                    "sources": [],
                    "error": "search_error",
                    "error_message": f"Error: {str(e)}"
                }

            if not similar_contexts:
                return {
                    "answer": "I don't have enough information in the knowledge base to answer this question accurately. Please wait for community members to respond.",
                    "context_used": False,
                    "confidence": 0.0,
                    "sources": []
                }

            context_str = self._format_context(similar_contexts)
            prompt = self._build_prompt(question, context_str)
            
            completion_params = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                "temperature": self.temperature,
                "max_completion_tokens": self.max_completion_tokens,
                "top_p": self.top_p,
                "stream": False,
            }
            
            if self.reasoning_effort:
                completion_params["reasoning_effort"] = self.reasoning_effort
            
            response = self.client.chat.completions.create(**completion_params)
            answer_text = response.choices[0].message.content.strip()
            
            avg_similarity = sum(ctx["similarity"] for ctx in similar_contexts) / len(similar_contexts)
            confidence = min(avg_similarity, 1.0)
            
            return {
                "answer": answer_text,
                "context_used": True,
                "confidence": confidence,
                "sources": [
                    {
                        "id": ctx["id"],
                        "content": ctx["content"][:200] + "..." if len(ctx["content"]) > 200 else ctx["content"],
                        "similarity": ctx["similarity"]
                    }
                    for ctx in similar_contexts
                ]
            }
            
        except Exception as e:
            logger.error(f"Error generating RAG answer: {str(e)}", exc_info=True)
            return {
                "answer": "I encountered an error while generating an answer. Please wait for community members to respond.",
                "context_used": False,
                "confidence": 0.0,
                "sources": [],
                "error": str(e)
            }

    def _format_context(self, contexts: List[Dict[str, Any]]) -> str:
        formatted = []
        for i, ctx in enumerate(contexts, 1):
            content = ctx["content"]
            similarity = ctx["similarity"]
            formatted.append(
                f"--- Reference {i} (Relevance: {similarity:.1%}) ---\n{content}\n"
            )
        return "\n".join(formatted)

    def _build_prompt(self, question: str, context: str) -> str:
        return f"""You are a helpful assistant for a Q&A forum. Below is a user's question and relevant Q&A pairs from the knowledge base.

User's Question:
{question}

Relevant Q&A Pairs from Knowledge Base:
{context}

Instructions:
1. Analyze the user's question and the provided Q&A pairs
2. Synthesize a short, point-wise answer (bullet list), max 500-600 words total
3. Prefer concise bullets; if only one point, keep it as one short bullet
4. If context is partial, combine what is available; avoid speculation
5. If context is insufficient, say so clearly
6. Do not invent information not present in the provided context

Your Response:
Provide a short (<=500-600 words), bullet-point answer to the user's question based on the context above:"""

    def add_to_knowledge_base(
        self,
        db: Session,
        question: str,
        answer: str,
        question_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        content = f"""Q: {question.strip()}

A: {answer.strip()}"""
        
        if metadata is None:
            metadata = {}
        if question_id:
            metadata["question_id"] = question_id
        
        try:
            record_id = self.vector_store.upsert(
                db=db,
                content=content,
                metadata=metadata,
                record_id=question_id
            )
            return record_id
        except Exception as e:
            logger.error(f"Failed to add Q&A to knowledge base: {str(e)}")
            return None

