from sqlalchemy.orm import Session
from database.models import User
from typing import Optional

def get_user_by_tg_id(db: Session, tg_id: int) -> Optional[User]:
    return db.query(User).filter(User.tg_id == tg_id).first()

def create_user(db: Session, tg_id: int, username: str, first_name: str, last_name: str = None) -> User:
    user = User(
        tg_id=tg_id,
        username=username,
        first_name=first_name,
        last_name=last_name
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def update_user_profile(db: Session, user: User, **kwargs) -> User:
    for key, value in kwargs.items():
        if hasattr(user, key):
            setattr(user, key, value)
    
    db.commit()
    db.refresh(user)
    return user