from datetime import datetime, timedelta
import secrets

from sqlalchemy.orm import Session
from app.models import User, SessionToken
from app.utils.security import hash_password, verify_password


def authenticate(db: Session, email: str, password: str) -> User | None:
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def create_user(db: Session, email: str, password: str, role: str = "user") -> User:
    user = User(email=email, password_hash=hash_password(password), role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_session(db: Session, user_id: int, hours: int = 12) -> SessionToken:
    token_value = f"token-{user_id}-{secrets.token_hex(8)}"
    session = SessionToken(
        user_id=user_id,
        token=token_value,
        expires_at=datetime.utcnow() + timedelta(hours=hours),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_session_by_token(db: Session, token: str) -> SessionToken | None:
    return (
        db.query(SessionToken)
        .filter(SessionToken.token == token, SessionToken.expires_at > datetime.utcnow())
        .first()
    )


def delete_session_by_token(db: Session, token: str) -> bool:
    sess = db.query(SessionToken).filter(SessionToken.token == token).first()
    if not sess:
        return False
    db.delete(sess)
    db.commit()
    return True


def delete_sessions_by_user(db: Session, user_id: int) -> int:
    count = db.query(SessionToken).filter(SessionToken.user_id == user_id).delete()
    db.commit()
    return count
