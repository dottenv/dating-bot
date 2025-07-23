from sqlalchemy.orm import Session
from database.models import AnonymousChat, DeanonRequest, User
from typing import Optional, Tuple, List

from services.ai_filters import find_best_match
from utils.debug import dbg

def is_compatible_orientation(user1: User, user2: User) -> bool:
    """
    Проверяет совместимость пола, ориентации и цели знакомства между двумя пользователями
    """
    dbg(f"Проверка совместимости между {user1.first_name} (пол: {user1.gender}, ориентация: {user1.orientation}) и "
         f"{user2.first_name} (пол: {user2.gender}, ориентация: {user2.orientation})", "CHAT")
    
    # Проверка цели знакомства
    # Если у пользователя цель "дружба" или "общение", то пол и ориентация не важны
    try:
        if hasattr(user1, 'dating_goal') and user1.dating_goal:
            if user1.dating_goal.lower() in ['дружба', 'общение']:
                dbg(f"Цель знакомства {user1.first_name} - {user1.dating_goal}, пол и ориентация не важны", "CHAT")
                return True
    except AttributeError:
        # Если столбец еще не добавлен в БД, игнорируем проверку цели знакомства
        dbg("Столбец dating_goal еще не добавлен в БД, игнорируем проверку цели знакомства", "CHAT")
    
    # По умолчанию, если нет данных о поле или ориентации, считаем совместимыми
    if not user1.gender or not user2.gender or not user1.orientation or not user2.orientation:
        dbg("Нет данных о поле или ориентации, считаем совместимыми", "CHAT")
        return True
    
    # Для гетеросексуалов: противоположный пол
    if user1.orientation.lower() == 'гетеро':
        # Если пользователь мужчина, ищем женщину
        if user1.gender.lower() == 'мужской':
            compatible = user2.gender.lower() == 'женский'
            dbg(f"Пользователь {user1.first_name} - гетеро мужчина, совместимость: {compatible}", "CHAT")
            return compatible
        # Если пользователь женщина, ищем мужчину
        elif user1.gender.lower() == 'женский':
            compatible = user2.gender.lower() == 'мужской'
            dbg(f"Пользователь {user1.first_name} - гетеро женщина, совместимость: {compatible}", "CHAT")
            return compatible
    
    # Для гомосексуалов: тот же пол
    elif user1.orientation.lower() == 'гомо':
        compatible = user1.gender.lower() == user2.gender.lower()
        dbg(f"Пользователь {user1.first_name} - гомо, совместимость: {compatible}", "CHAT")
        return compatible
    
    # Для бисексуалов: любой пол, но нужно проверить совместимость с ориентацией второго пользователя
    elif user1.orientation.lower() == 'би':
        # Если второй пользователь гетеро, то полы должны быть противоположными
        if user2.orientation.lower() == 'гетеро':
            if user2.gender.lower() == 'мужской':
                compatible = user1.gender.lower() == 'женский'
                dbg(f"Пользователь {user1.first_name} - би, а {user2.first_name} - гетеро мужчина, совместимость: {compatible}", "CHAT")
                return compatible
            elif user2.gender.lower() == 'женский':
                compatible = user1.gender.lower() == 'мужской'
                dbg(f"Пользователь {user1.first_name} - би, а {user2.first_name} - гетеро женщина, совместимость: {compatible}", "CHAT")
                return compatible
        # Если второй пользователь гомо, то полы должны совпадать
        elif user2.orientation.lower() == 'гомо':
            compatible = user1.gender.lower() == user2.gender.lower()
            dbg(f"Пользователь {user1.first_name} - би, а {user2.first_name} - гомо, совместимость: {compatible}", "CHAT")
            return compatible
        # Если второй пользователь тоже би, то совместимы в любом случае
        elif user2.orientation.lower() == 'би':
            dbg(f"Оба пользователя бисексуальны, совместимы", "CHAT")
            return True
    
    # По умолчанию, если не попали ни в одно из условий
    dbg(f"Не удалось определить совместимость, считаем несовместимыми", "CHAT")
    return False

async def find_available_chat_partner(db: Session, user_id: int) -> Tuple[Optional[User], List[User], str]:
    """Находит подходящего партнера для чата с учетом пола, ориентации и цели знакомства.
    
    Returns:
        Tuple[Optional[User], List[User], str]: Кортеж из (лучший партнер, альтернативные партнеры, сообщение)
    """
    try:
        dbg(f"Поиск собеседника для пользователя ID: {user_id}", "CHAT")
        
        # Find users who are active and not in a chat
        active_chat_users = db.query(AnonymousChat).filter(
            (AnonymousChat.user1_id == user_id) | (AnonymousChat.user2_id == user_id),
            AnonymousChat.is_active == True
        ).all()

        if active_chat_users:
            dbg(f"Пользователь уже в активном чате", "CHAT")
            return None  # User is already in a chat

        # Find all active chats to exclude users who are already chatting
        active_chats = db.query(AnonymousChat).filter(AnonymousChat.is_active == True).all()
        busy_user_ids = []
        for chat in active_chats:
            busy_user_ids.extend([chat.user1_id, chat.user2_id])

        dbg(f"Пользователи в активных чатах: {busy_user_ids}", "CHAT")
        
        # Find all available users
        available_users = db.query(User).filter(
            User.id != user_id,
            User.is_active == True,
            ~User.id.in_(busy_user_ids) if busy_user_ids else True
        ).all()

        dbg(f"Найдено доступных пользователей: {len(available_users)}", "CHAT")
        
        if not available_users:
            dbg("Нет доступных пользователей", "CHAT")
            return None

        # Get current user data
        current_user = db.query(User).filter(User.id == user_id).first()
        if not current_user:
            dbg(f"Текущий пользователь не найден", "CHAT")
            return None

        dbg(f"Текущий пользователь: {current_user.first_name}, ID: {current_user.id}", "CHAT")
        
        # Convert users to dictionaries for AI analysis
        current_user_data = {
            'first_name': current_user.first_name,
            'age': current_user.age,
            'city': current_user.city,
            'about': current_user.bio,
            'tags': current_user.tags,
            'gender': current_user.gender,
            'orientation': current_user.orientation
        }
        
        # Проверяем наличие столбца dating_goal в БД
        try:
            current_user_data['dating_goal'] = current_user.dating_goal if current_user.dating_goal else 'Не указана'
        except AttributeError:
            current_user_data['dating_goal'] = 'Не указана'
            dbg("Столбец dating_goal еще не добавлен в БД", "CHAT")
        
        # Фильтрация кандидатов по полу и ориентации
        filtered_users = []
        for user in available_users:
            # Проверка совместимости по полу и ориентации
            if is_compatible_orientation(current_user, user):
                filtered_users.append(user)
            else:
                dbg(f"Кандидат {user.first_name} (ID: {user.id}) отфильтрован по полу/ориентации", "CHAT")
        
        dbg(f"После фильтрации по полу/ориентации осталось кандидатов: {len(filtered_users)}", "CHAT")
        
        # Если нет подходящих кандидатов по полу/ориентации
        if not filtered_users:
            dbg("Нет подходящих кандидатов по полу/ориентации", "CHAT")
            return None, [], "Нет подходящих кандидатов по полу и ориентации"

        candidates = []
        for user in filtered_users:
            candidate_data = {
                'id': user.id,
                'first_name': user.first_name,
                'age': user.age,
                'city': user.city,
                'about': user.bio,
                'tags': user.tags,
                'gender': user.gender,
                'orientation': user.orientation
            }
            
            # Проверяем наличие столбца dating_goal в БД
            try:
                candidate_data['dating_goal'] = user.dating_goal if user.dating_goal else 'Не указана'
            except AttributeError:
                candidate_data['dating_goal'] = 'Не указана'
            
            candidates.append(candidate_data)
            dbg(f"Кандидат: {user.first_name}, ID: {user.id}", "CHAT")

        # Find best match using AI
        if candidates:
            dbg("Запуск ИИ для поиска лучшего совпадения", "CHAT")
            best_match, score = await find_best_match(current_user_data, candidates)
            
            # Получаем альтернативных кандидатов (все кроме лучшего)
            alternative_candidates = []
            if best_match:
                for user in filtered_users:
                    if user.id != best_match['id']:
                        alternative_candidates.append(user)
                
                dbg(f"Лучшее совпадение найдено: ID {best_match['id']}, оценка: {score}", "CHAT")
                # Get the user object for the best match
                matched_user = db.query(User).filter(User.id == best_match['id']).first()
                if matched_user and hasattr(matched_user, 'is_active') and matched_user.is_active:
                    dbg(f"Возвращаем пользователя: {matched_user.first_name}", "CHAT")
                    return matched_user, alternative_candidates, f"Найден идеальный кандидат с оценкой {score:.2f}"
            
            # Если оценка низкая, предлагаем рассмотреть альтернативы
            if score < 0.5 and filtered_users:
                dbg(f"Низкая оценка совместимости: {score}, предлагаем альтернативы", "CHAT")
                return filtered_users[0], filtered_users[1:] if len(filtered_users) > 1 else [], "Идеального кандидата нет, но есть варианты"

        # If AI matching fails, fall back to the first available filtered user
        if filtered_users:
            dbg(f"ИИ не нашел совпадений, возвращаем первого доступного пользователя: {filtered_users[0].first_name}", "CHAT")
            return filtered_users[0], filtered_users[1:] if len(filtered_users) > 1 else [], "ИИ не смог найти идеальное совпадение"

        dbg("Нет доступных пользователей", "CHAT")
        return None, [], "Нет доступных пользователей"
    except Exception as e:
        dbg(f"Ошибка при поиске собеседника: {e}", "CHAT_ERROR")
        return None, [], f"Ошибка при поиске собеседника: {e}"




def create_chat(db: Session, user1_id: int, user2_id: int) -> Optional[AnonymousChat]:
    try:
        dbg(f"Создание чата между пользователями {user1_id} и {user2_id}", "CHAT")
        chat = AnonymousChat(
            user1_id=user1_id,
            user2_id=user2_id,
            is_active=True
        )
        db.add(chat)
        db.commit()
        db.refresh(chat)
        dbg(f"Чат создан с ID: {chat.id}", "CHAT")
        return chat
    except Exception as e:
        dbg(f"Ошибка при создании чата: {e}", "CHAT_ERROR")
        db.rollback()
        return None

def get_active_chat(db: Session, user_id: int) -> Optional[AnonymousChat]:
    try:
        dbg(f"Получение активного чата для пользователя {user_id}", "CHAT")
        chat = db.query(AnonymousChat).filter(
            ((AnonymousChat.user1_id == user_id) | (AnonymousChat.user2_id == user_id)),
            AnonymousChat.is_active == True
        ).first()
        if chat:
            dbg(f"Найден активный чат ID: {chat.id}", "CHAT")
        else:
            dbg(f"Активный чат не найден для пользователя {user_id}", "CHAT")
        return chat
    except Exception as e:
        dbg(f"Ошибка при получении активного чата: {e}", "CHAT_ERROR")
        return None

def end_chat(db: Session, chat_id: int) -> bool:
    try:
        dbg(f"Завершение чата ID: {chat_id}", "CHAT")
        chat = db.query(AnonymousChat).filter(AnonymousChat.id == chat_id).first()
        if chat:
            chat.is_active = False
            db.commit()
            dbg(f"Чат ID: {chat_id} успешно завершен", "CHAT")
            return True
        dbg(f"Чат ID: {chat_id} не найден", "CHAT")
        return False
    except Exception as e:
        dbg(f"Ошибка при завершении чата: {e}", "CHAT_ERROR")
        db.rollback()
        return False

def create_deanon_request(db: Session, chat_id: int) -> Optional[DeanonRequest]:
    try:
        dbg(f"Создание запроса на раскрытие личности для чата ID: {chat_id}", "CHAT")
        request = DeanonRequest(
            chat_id=chat_id,
            user1_approved=False,
            user2_approved=False
        )
        db.add(request)
        db.commit()
        db.refresh(request)
        dbg(f"Запрос на раскрытие личности создан с ID: {request.id}", "CHAT")
        return request
    except Exception as e:
        dbg(f"Ошибка при создании запроса на раскрытие личности: {e}", "CHAT_ERROR")
        db.rollback()
        return None

def get_deanon_request(db: Session, chat_id: int) -> Optional[DeanonRequest]:
    try:
        dbg(f"Получение запроса на раскрытие личности для чата ID: {chat_id}", "CHAT")
        request = db.query(DeanonRequest).filter(DeanonRequest.chat_id == chat_id).first()
        if request:
            dbg(f"Найден запрос на раскрытие личности ID: {request.id}", "CHAT")
        else:
            dbg(f"Запрос на раскрытие личности не найден для чата ID: {chat_id}", "CHAT")
        return request
    except Exception as e:
        dbg(f"Ошибка при получении запроса на раскрытие личности: {e}", "CHAT_ERROR")
        return None

def update_deanon_approval(db: Session, request_id: int, user_position: int, approved: bool) -> Optional[DeanonRequest]:
    try:
        dbg(f"Обновление статуса раскрытия личности для запроса ID: {request_id}, пользователь: {user_position}, статус: {approved}", "CHAT")
        request = db.query(DeanonRequest).filter(DeanonRequest.id == request_id).first()
        if request:
            if user_position == 1:
                request.user1_approved = approved
                dbg(f"Установлен статус user1_approved = {approved}", "CHAT")
            elif user_position == 2:
                request.user2_approved = approved
                dbg(f"Установлен статус user2_approved = {approved}", "CHAT")
            db.commit()
            db.refresh(request)
            dbg(f"Статусы после обновления: user1_approved = {request.user1_approved}, user2_approved = {request.user2_approved}", "CHAT")
        else:
            dbg(f"Запрос на раскрытие личности с ID: {request_id} не найден", "CHAT")
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
            dbg(f"Увеличен счетчик сообщений в чате ID: {chat_id}, текущее значение: {chat.messages_count}", "CHAT")
            return True
        dbg(f"Чат ID: {chat_id} не найден при попытке увеличить счетчик сообщений", "CHAT")
        return False
    except Exception as e:
        dbg(f"Ошибка при увеличении счетчика сообщений: {e}", "CHAT_ERROR")
        db.rollback()
        return False
