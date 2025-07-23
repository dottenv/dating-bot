from sqlalchemy.orm import Session
from database.models import AnonymousChat, DeanonRequest, User, ChatHistory
from typing import Optional, Tuple, List
from sqlalchemy import and_, or_, not_, func
import datetime

from utils.debug import dbg

def is_compatible_orientation(user1: User, user2: User) -> bool:
    """
    Проверяет совместимость пола, ориентации и цели знакомства между двумя пользователями
    """
    # По умолчанию, если нет данных о поле или ориентации, считаем совместимыми
    if not user1.gender or not user2.gender or not user1.orientation or not user2.orientation:
        return True
    
    # Проверка цели знакомства
    # Если у пользователя цель "дружба" или "общение", то пол и ориентация не важны
    try:
        if hasattr(user1, 'dating_goal') and user1.dating_goal:
            if user1.dating_goal.lower() in ['дружба', 'общение']:
                return True
    except AttributeError:
        pass
    
    # Для гетеросексуалов: противоположный пол
    if user1.orientation.lower() == 'гетеро':
        # Если пользователь мужчина, ищем женщину
        if user1.gender.lower() == 'мужской':
            return user2.gender.lower() == 'женский'
        # Если пользователь женщина, ищем мужчину
        elif user1.gender.lower() == 'женский':
            return user2.gender.lower() == 'мужской'
    
    # Для гомосексуалов: тот же пол
    elif user1.orientation.lower() == 'гомо':
        return user1.gender.lower() == user2.gender.lower()
    
    # Для бисексуалов: любой пол, но нужно проверить совместимость с ориентацией второго пользователя
    elif user1.orientation.lower() == 'би':
        # Если второй пользователь гетеро, то полы должны быть противоположными
        if user2.orientation.lower() == 'гетеро':
            if user2.gender.lower() == 'мужской':
                return user1.gender.lower() == 'женский'
            elif user2.gender.lower() == 'женский':
                return user1.gender.lower() == 'мужской'
        # Если второй пользователь гомо, то полы должны совпадать
        elif user2.orientation.lower() == 'гомо':
            return user1.gender.lower() == user2.gender.lower()
        # Если второй пользователь тоже би, то совместимы в любом случае
        elif user2.orientation.lower() == 'би':
            return True
    
    # По умолчанию, если не попали ни в одно из условий
    return False

def get_rating_category(rating: int) -> str:
    """
    Возвращает категорию пользователя на основе его рейтинга
    """
    if rating < 40:
        return 'low'
    elif rating < 70:
        return 'medium'
    else:
        return 'high'

async def find_available_chat_partner(db: Session, user_id: int) -> Tuple[Optional[User], List[User], str]:
    """Находит подходящего партнера для чата с учетом пола, ориентации и цели знакомства."""
    try:
        # Проверяем, не находится ли пользователь уже в активном чате
        active_chat = get_active_chat(db, user_id)
        if active_chat:
            return None, [], "Пользователь уже в активном чате"

        # Получаем текущего пользователя
        current_user = db.query(User).filter(User.id == user_id).first()
        if not current_user:
            return None, [], "Пользователь не найден"
        
        # Проверяем, полностью ли заполнен профиль пользователя
        if not current_user.profile_completed:
            return None, [], "Профиль не полностью заполнен. Заполните все обязательные поля профиля для участия в поиске."
        
        # Получаем ID занятых пользователей
        busy_users = db.query(User.id).join(
            AnonymousChat, 
            or_(
                User.id == AnonymousChat.user1_id,
                User.id == AnonymousChat.user2_id
            )
        ).filter(AnonymousChat.is_active == True).distinct().all()
        
        busy_user_ids = [user[0] for user in busy_users]
        
        # Получаем рейтинг пользователя
        user_rating = current_user.user_rating if hasattr(current_user, 'user_rating') else 100
        user_rating_category = get_rating_category(user_rating)
        
        # Находим всех доступных пользователей
        query = db.query(User).filter(
            User.id != user_id,
            User.is_active == True,
            ~User.id.in_(busy_user_ids),
            User.profile_completed == True
        )
        
        # Учитываем рейтинг пользователя при подборе собеседников
        if user_rating_category == "low":
            # Пользователям с низким рейтингом подбираем только таких же
            query = query.filter(User.user_rating < 40)
        elif user_rating_category == "medium":
            # Пользователям со средним рейтингом подбираем средних и высоких
            query = query.filter(User.user_rating >= 40)
        else:
            # Для пользователей с высоким рейтингом подбираем только пользователей с высоким рейтингом
            query = query.filter(User.user_rating >= 70)
        
        # Получаем всех доступных пользователей
        available_users = query.all()
        
        if not available_users:
            return None, [], "Нет доступных пользователей"
        
        # Фильтрация кандидатов по полу и ориентации
        filtered_users = [user for user in available_users if is_compatible_orientation(current_user, user)]
        
        if not filtered_users:
            return None, [], "Нет подходящих кандидатов по полу и ориентации"

        # Выбираем первого подходящего пользователя
        matched_user = filtered_users[0]
        alternative_candidates = filtered_users[1:] if len(filtered_users) > 1 else []
        
        # Проверяем рейтинг пользователя и кандидата
        matched_user_rating = matched_user.user_rating if hasattr(matched_user, 'user_rating') else 100
        matched_user_rating_category = get_rating_category(matched_user_rating)
        
        # Если пользователь с высоким или средним рейтингом, а кандидат с низким, требуется подтверждение
        if (user_rating_category in ["high", "medium"]) and matched_user_rating_category == "low":
            return matched_user, alternative_candidates, "Найден собеседник с низким рейтингом. Требуется подтверждение."
        
        return matched_user, alternative_candidates, "Собеседник найден"
    except Exception as e:
        dbg(f"Ошибка при поиске собеседника: {e}", "CHAT_ERROR")
        return None, [], f"Ошибка при поиске собеседника"

def create_chat(db: Session, user1_id: int, user2_id: int) -> Optional[AnonymousChat]:
    try:
        chat = AnonymousChat(
            user1_id=user1_id,
            user2_id=user2_id,
            is_active=True,
            start_time=datetime.datetime.now(),
            messages_count=0
        )
        db.add(chat)
        db.commit()
        db.refresh(chat)
        
        # Обновляем историю чатов между пользователями
        update_chat_history(db, user1_id, user2_id)
        
        return chat
    except Exception as e:
        dbg(f"Ошибка при создании чата: {e}", "CHAT_ERROR")
        db.rollback()
        return None

def get_active_chat(db: Session, user_id: int) -> Optional[AnonymousChat]:
    try:
        chat = db.query(AnonymousChat).filter(
            ((AnonymousChat.user1_id == user_id) | (AnonymousChat.user2_id == user_id)),
            AnonymousChat.is_active == True
        ).first()
        return chat
    except Exception as e:
        dbg(f"Ошибка при получении активного чата: {e}", "CHAT_ERROR")
        return None

def end_chat(db: Session, chat_id: int) -> bool:
    try:
        chat = db.query(AnonymousChat).filter(AnonymousChat.id == chat_id).first()
        if chat:
            chat.is_active = False
            db.commit()
            return True
        return False
    except Exception as e:
        dbg(f"Ошибка при завершении чата: {e}", "CHAT_ERROR")
        db.rollback()
        return False

def create_deanon_request(db: Session, chat_id: int) -> Optional[DeanonRequest]:
    try:
        request = DeanonRequest(
            chat_id=chat_id,
            user1_approved=False,
            user2_approved=False,
            requested_at=datetime.datetime.now()
        )
        db.add(request)
        db.commit()
        db.refresh(request)
        return request
    except Exception as e:
        dbg(f"Ошибка при создании запроса на раскрытие личности: {e}", "CHAT_ERROR")
        db.rollback()
        return None

def get_deanon_request(db: Session, chat_id: int) -> Optional[DeanonRequest]:
    try:
        request = db.query(DeanonRequest).filter(DeanonRequest.chat_id == chat_id).first()
        return request
    except Exception as e:
        dbg(f"Ошибка при получении запроса на раскрытие личности: {e}", "CHAT_ERROR")
        return None

def update_deanon_approval(db: Session, request_id: int, user_position: int, approved: bool) -> Optional[DeanonRequest]:
    try:
        request = db.query(DeanonRequest).filter(DeanonRequest.id == request_id).first()
        if request:
            if user_position == 1:
                request.user1_approved = approved
            elif user_position == 2:
                request.user2_approved = approved
            db.commit()
            db.refresh(request)
        return request
    except Exception as e:
        dbg(f"Ошибка при обновлении статуса раскрытия личности: {e}", "CHAT_ERROR")
        db.rollback()
        return None

def increment_messages_count(db: Session, chat_id: int) -> bool:
    """Увеличивает счетчик сообщений в чате"""
    try:
        chat = db.query(AnonymousChat).filter(AnonymousChat.id == chat_id).first()
        if chat:
            chat.messages_count += 1
            db.commit()
            return True
        return False
    except Exception as e:
        dbg(f"Ошибка при увеличении счетчика сообщений: {e}", "CHAT_ERROR")
        db.rollback()
        return False

def get_chat_partner_id(chat: AnonymousChat, user_id: int) -> Optional[int]:
    """Получает ID собеседника в чате"""
    if chat.user1_id == user_id:
        return chat.user2_id
    elif chat.user2_id == user_id:
        return chat.user1_id
    return None

def update_chat_history(db: Session, user1_id: int, user2_id: int) -> None:
    """Обновляет историю чатов между пользователями"""
    try:
        # Упорядочиваем ID пользователей для уникальности записи
        sorted_ids = sorted([user1_id, user2_id])
        user1_id, user2_id = sorted_ids[0], sorted_ids[1]
        
        # Проверяем, есть ли уже запись в истории
        history = db.query(ChatHistory).filter(
            ChatHistory.user1_id == user1_id,
            ChatHistory.user2_id == user2_id
        ).first()
        
        if history:
            # Если запись есть, увеличиваем счетчик и обновляем дату
            history.chat_count += 1
            history.last_chat_at = datetime.datetime.now()
        else:
            # Если записи нет, создаем новую
            history = ChatHistory(
                user1_id=user1_id,
                user2_id=user2_id,
                chat_count=1,
                last_chat_at=datetime.datetime.now()
            )
            db.add(history)
        
        db.commit()
    except Exception as e:
        db.rollback()
        dbg(f"Ошибка при обновлении истории чатов: {e}", "CHAT_ERROR")

def get_chat_history_count(db: Session, user1_id: int, user2_id: int) -> int:
    """Получает количество чатов между пользователями"""
    try:
        # Упорядочиваем ID пользователей
        sorted_ids = sorted([user1_id, user2_id])
        user1_id, user2_id = sorted_ids[0], sorted_ids[1]
        
        history = db.query(ChatHistory).filter(
            ChatHistory.user1_id == user1_id,
            ChatHistory.user2_id == user2_id
        ).first()
        
        return history.chat_count if history else 0
    except Exception as e:
        dbg(f"Ошибка при получении истории чатов: {e}", "CHAT_ERROR")
        return 0