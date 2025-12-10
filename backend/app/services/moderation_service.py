import logging
from typing import Dict
from sqlalchemy.orm import Session
from uuid import UUID
from groq import Groq

from app.core.config import settings

logger = logging.getLogger(__name__)


class ModerationService:

    SYSTEM_PROMPT = """
You are a strict content moderation classifier. Given user text, return a JSON with:
- label: one of [SAFE, HATE_SPEECH, ABUSIVE_LANGUAGE, SEXUAL_CONTENT, SEXUAL_CONTENT_MINORS, VIOLENCE, SELF_HARM, ILLEGAL_ACTIVITY, SPAM, MISINFORMATION, SENSITIVE_POLITICAL]
- reason: brief explanation (max 25 words)

Rules:
- SEXUAL_CONTENT_MINORS is hard block if any minor sexual context.
- Be conservative: if unsure between safe and unsafe, pick the unsafe category.
- Do not include any extra text besides the JSON.
"""

    ACTION_MAP = {
        "SAFE": "allow",
        "HATE_SPEECH": "flag",
        "ABUSIVE_LANGUAGE": "ban",
        "SEXUAL_CONTENT": "ban",
        "SEXUAL_CONTENT_MINORS": "ban",
        "VIOLENCE": "flag",
        "SELF_HARM": "flag",
        "ILLEGAL_ACTIVITY": "flag",
        "SPAM": "ban",
        "MISINFORMATION": "warn",
        "SENSITIVE_POLITICAL": "flag",
    }

    def __init__(self):

        api_key = settings.GROQ_API_KEY
        if not api_key:
            raise ValueError("GROQ_API_KEY is required for moderation")
        self.client = Groq(api_key=api_key)
        self.model = settings.GROQ_MODEL

    def classify(self, text: str) -> Dict[str, str]:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT.strip()},
                    {
                        "role": "user",
                        "content": f'Classify this text:\n"""{text.strip()}"""'
                    },
                ],
                temperature=0.0,
                max_completion_tokens=300,
                top_p=1.0,
                stream=False,
            )
            raw = response.choices[0].message.content.strip()

            import json
            parsed = json.loads(raw)
            label = str(parsed.get("label", "SAFE")).upper()
            reason = parsed.get("reason", "")
        except Exception as e:
            logger.error(f"Moderation failed, defaulting to SAFE: {str(e)}")
            label = "SAFE"
            reason = "Moderation fallback"

        action = self.ACTION_MAP.get(label, "flag")
        return {"label": label, "action": action, "reason": reason}

    def ban_user(self, db: Session, user_id: str) -> bool:
        try:
            from app.models.user import User
            
            user = db.query(User).filter(User.id == UUID(user_id)).first()
            if user:
                username = user.username
                db.delete(user)
                db.commit()
                
                deleted_user = db.query(User).filter(User.id == UUID(user_id)).first()
                if deleted_user:
                    logger.error(f"User {user_id} ({username}) still exists after deletion! Attempting force delete...")
                    db.delete(deleted_user)
                    db.commit()
                    still_exists = db.query(User).filter(User.id == UUID(user_id)).first()
                    if still_exists:
                        logger.error(f"CRITICAL: User {user_id} ({username}) could not be deleted!")
                        return False
                
                logger.warning(f"User {user_id} ({username}) banned and deleted")
                return True
            else:
                return False
        except Exception as e:
            logger.error(f"Error banning user {user_id}: {str(e)}", exc_info=True)
            db.rollback()
            return False

