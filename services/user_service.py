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
        last_name=last_name,
        is_active=True  # По умолчанию пользователь активен
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def update_user_profile(db: Session, user: User, **kwargs) -> User:
    # Проверяем, что user является объектом User
    if not user or not hasattr(user, 'id'):
        raise ValueError("User object is invalid")
        
    for key, value in kwargs.items():
        if hasattr(user, key):
            # Проверка типа для полей, которые должны быть определенного типа
            if key == 'age':
                if isinstance(value, str) and value.isdigit():
                    value = int(value)
                elif not isinstance(value, int):
                    continue  # Пропускаем неверный тип
                    
            # Проверка на None и пустую строку
            if value is not None and value != '':
                try:
                    setattr(user, key, value)
                except Exception as e:
                    print(f"Error setting {key}={value}: {e}")
    
    try:
        # Проверяем полноту профиля после обновления
        from services.user_rating_service import update_profile_completeness
        update_profile_completeness(db, user)
        
        db.commit()
        db.refresh(user)
    except Exception as e:
        db.rollback()
        print(f"Error committing changes: {e}")
        raise
        
    return user

def toggle_user_activity(db: Session, user: User) -> User:
    """Переключает статус активности пользователя"""
    user.is_active = not user.is_active
    db.commit()
    db.refresh(user)
    return user

def get_user_activity_status(user: User) -> str:
    """Возвращает текстовый статус активности пользователя"""
    return "Активен" if user.is_active else "Неактивен"