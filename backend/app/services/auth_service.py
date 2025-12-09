"""
Auth Service
Business logic for authentication
"""
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID

from app.models.user import User, UserRole
from app.utils.auth import (
    get_password_hash,
    create_access_token,
    authenticate_user,
    get_user_by_email,
    get_user_by_id,
)
from datetime import timedelta


def register_user(
    db: Session, username: str, email: str, password: str, role: UserRole = UserRole.GUEST
) -> User:
    """Register a new user"""
    if get_user_by_email(db, email):
        raise ValueError("Email already registered")
    
    user = User(
        username=username,
        email=email,
        password_hash=get_password_hash(password),
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def login_user(db: Session, email: str, password: str) -> Optional[dict]:
    """Login user and return token"""
    user = authenticate_user(db, email, password)
    if not user:
        return None
    
    if not user.is_active:
        return None
    
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "role": user.role.value},
        expires_delta=timedelta(minutes=30)
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "role": user.role.value,
        }
    }

