from aiogram import types, Router, F
from aiogram.fsm.context import FSMContext

from database.db import get_db
from database.models import User
from services.user_service import get_user_by_tg_id
from services.user_rating_service import analyze_message_with_ai, update_user_rating
from states.user_states import AnonymousChatting
from utils.debug import dbg

router = Router()

@router.message(AnonymousChatting.chatting)
async def analyze_chat_message(message: types.Message, state: FSMContext):
    """
    Анализирует сообщения в чате, обновляет рейтинг пользователя и блокирует неприемлемые сообщения
    
    Этот обработчик работает перед основным обработчиком сообщений и может блокировать отправку
    неприемлемых сообщений
    """
    # Пропускаем анализ для медиа-файлов
    if not message.text:
        return
    
    try:
        # Получаем данные пользователя
        db = next(get_db())
        user = get_user_by_tg_id(db, message.from_user.id)
        
        if not user:
            return
        
        # Логируем начало анализа
        dbg(f"Начало анализа сообщения пользователя {user.id}", "USER_RATING")
        
        # Анализируем сообщение с помощью ИИ (асинхронно)
        analysis_result = await analyze_message_with_ai(message.text)
        
        # Если есть изменение рейтинга, обновляем его
        rating_change = analysis_result.get('rating_change', 0)
        if rating_change != 0:
            reason = f"Анализ сообщения: {analysis_result.get('sentiment', 'neutral')}"
            updated_user = update_user_rating(db, user.id, rating_change, reason)
            
            # Логируем результат анализа и обновление рейтинга
            if updated_user:
                dbg(f"Анализ сообщения пользователя {user.id}: {analysis_result}, новый рейтинг: {updated_user.user_rating}", "USER_RATING")
            else:
                dbg(f"Анализ сообщения пользователя {user.id}: {analysis_result}, но обновление рейтинга не удалось", "USER_RATING")
        else:
            dbg(f"Анализ сообщения пользователя {user.id}: {analysis_result}, рейтинг не изменился", "USER_RATING")
        
        # Проверяем, нужно ли блокировать сообщение
        if analysis_result.get('block_message', False):
            # Получаем данные о чате
            data = await state.get_data()
            chat_id = data.get("chat_id")
            partner_id = data.get("partner_id")
            
            if not chat_id or not partner_id:
                # Если данных нет в состоянии, получаем их из базы данных
                from handlers.chat_message_handler import get_chat_data
                _, partner, chat = await get_chat_data(message, state)
                
                if chat and partner:
                    chat_id = chat.id
                    partner_id = partner.id
            
            if chat_id and partner_id:
                # Отправляем уведомление пользователю о блокировке сообщения
                replacement_text = analysis_result.get('replacement_text', "Сообщение заблокировано из-за нарушения правил.")
                await message.answer(replacement_text)
                
                # Отправляем уведомление партнеру
                partner = db.query(User).filter(User.id == partner_id).first()
                if partner:
                    await message.bot.send_message(
                        partner.tg_id,
                        "Сообщение собеседника заблокировано системой из-за нарушения правил."
                    )
                
                # Прерываем обработку сообщения, чтобы оно не было отправлено
                message.text = None  # Это предотвратит отправку сообщения в основном обработчике
                return False  # Сигнализируем о том, что сообщение заблокировано
        
        return True  # Сообщение прошло проверку
    except Exception as e:
        # Не блокируем отправку сообщения в случае ошибки
        dbg(f"Ошибка при анализе сообщения: {e}", "USER_RATING_ERROR")
        return True  # В случае ошибки разрешаем отправку сообщения