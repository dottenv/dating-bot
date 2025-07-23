from sqlalchemy.orm import Session
from database.models import User, AnonymousChat
from typing import Optional, List, Dict, Any
from utils.debug import dbg

def check_profile_completeness(user: User) -> bool:
    """
    Проверяет, полностью ли заполнен профиль пользователя
    
    Обязательные поля:
    - first_name
    - age
    - gender
    - orientation
    - city
    - bio
    - photo_id
    - tags
    """
    required_fields = [
        user.first_name,
        user.age,
        user.gender,
        user.orientation,
        user.city,
        user.bio,
        user.photo_id,
        user.tags
    ]
    
    # Проверяем, что все обязательные поля заполнены
    is_complete = all(field is not None and field != "" for field in required_fields)
    
    return is_complete

def update_profile_completeness(db: Session, user: User) -> bool:
    """
    Обновляет статус заполнения профиля пользователя
    
    Возвращает True, если профиль полностью заполнен, иначе False
    """
    is_complete = check_profile_completeness(user)
    
    # Обновляем статус заполнения профиля
    if user.profile_completed != is_complete:
        user.profile_completed = is_complete
        db.commit()
        dbg(f"Обновлен статус заполнения профиля пользователя {user.id}: {is_complete}", "USER_RATING")
    
    return is_complete

def update_user_rating(db: Session, user_id: int, rating_change: int, reason: str) -> Optional[User]:
    """
    Обновляет рейтинг пользователя
    
    Args:
        db: Сессия базы данных
        user_id: ID пользователя
        rating_change: Изменение рейтинга (положительное или отрицательное)
        reason: Причина изменения рейтинга
    
    Returns:
        Обновленный объект пользователя или None в случае ошибки
    """
    try:
        dbg(f"Попытка обновления рейтинга пользователя {user_id} на {rating_change}. Причина: {reason}", "USER_RATING")
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            dbg(f"Пользователь с ID {user_id} не найден", "USER_RATING_ERROR")
            return None
        
        # Обновляем рейтинг, но не выходим за пределы 0-100
        old_rating = user.user_rating
        new_rating = max(0, min(100, old_rating + rating_change))
        
        dbg(f"Текущий рейтинг пользователя {user_id}: {old_rating}, новый рейтинг: {new_rating}", "USER_RATING")
        
        if old_rating != new_rating:
            user.user_rating = new_rating
            db.commit()
            dbg(f"Рейтинг пользователя {user_id} изменен с {old_rating} на {new_rating}. Причина: {reason}", "USER_RATING")
        else:
            dbg(f"Рейтинг пользователя {user_id} не изменился, остался {old_rating}", "USER_RATING")
        
        # Получаем категорию рейтинга
        rating_category = get_rating_category(new_rating)
        dbg(f"Категория рейтинга пользователя {user_id}: {rating_category}", "USER_RATING")
        
        return user
    except Exception as e:
        dbg(f"Ошибка при обновлении рейтинга пользователя {user_id}: {e}", "USER_RATING_ERROR")
        db.rollback()
        return None

async def analyze_message_with_ai(message_text: str) -> Dict[str, Any]:
    """
    Анализирует сообщение с помощью ИИ и возвращает оценку
    
    Интеграция с ai_filters.py для более точного анализа сообщений
    
    Returns:
        Словарь с результатами анализа:
        {
            'is_toxic': bool,
            'toxicity_score': float,  # от 0 до 1
            'sentiment': str,  # 'positive', 'neutral', 'negative'
            'rating_change': int  # рекомендуемое изменение рейтинга
        }
    """
    # Используем функцию из ai_filters.py для анализа сообщений
    from services.ai_filters import analyze_user_message
    
    try:
        # Вызываем функцию анализа из ai_filters.py
        result = await analyze_user_message(message_text)
        dbg(f"Анализ сообщения с помощью AI: {result}", "USER_RATING")
        return result
    except Exception as e:
        dbg(f"Ошибка при анализе сообщения: {e}", "USER_RATING_ERROR")
        
        # В случае ошибки возвращаем нейтральный результат
        return {
            'is_toxic': False,
            'toxicity_score': 0.0,
            'sentiment': 'neutral',
            'rating_change': 0
        }

def get_rating_category(rating: int) -> str:
    """
    Возвращает категорию пользователя на основе его рейтинга
    
    Args:
        rating: Рейтинг пользователя (0-100)
    
    Returns:
        Категория пользователя: 'low', 'medium', 'high'
    """
    if rating < 40:
        return 'low'
    elif rating < 70:
        return 'medium'
    else:
        return 'high'