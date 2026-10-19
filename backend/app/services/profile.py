from sqlalchemy.orm import Session
from app.models import Profile, Metric, User
from app.utils.security import hash_password


def create_profile(db: Session, user_email: str, password: str, **kwargs) -> Profile:
    user = User(email=user_email, password_hash=hash_password(password))
    db.add(user)
    db.commit()
    db.refresh(user)

    profile = Profile(user_id=user.id, **kwargs)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def get_profile(db: Session, profile_id: int) -> Profile | None:
    return db.query(Profile).filter(Profile.id == profile_id).first()


def add_metrics(db: Session, profile_id: int, metrics: list[dict]) -> list[Metric]:
    items: list[Metric] = []
    for m in metrics:
        item = Metric(profile_id=profile_id, **m)
        db.add(item)
        items.append(item)
    db.commit()
    for item in items:
        db.refresh(item)
    return items
