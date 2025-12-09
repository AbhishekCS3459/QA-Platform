"""
Guest User Utilities
"""
from sqlalchemy.orm import Session
from app.models.user import User, UserRole
from app.utils.auth import get_user_by_email
from app.services.auth_service import register_user


def get_or_create_guest_user(db: Session) -> User:
    """Get or create the system guest user"""
    guest_user = get_user_by_email(db, "guest@system.local")
    if not guest_user:
        guest_user = register_user(
            db,
            username="Guest",
            email="guest@system.local",
            password="guest_password_not_used",
            role=UserRole.GUEST,
        )
    return guest_user

