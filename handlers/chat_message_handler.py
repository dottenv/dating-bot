import asyncio
from typing import Optional, Dict, Any, Tuple
from aiogram import types, Bot
from aiogram.fsm.context import FSMContext
from sqlalchemy.orm import Session

from database.db import get_db
from database.models import User, AnonymousChat
from services.user_service import get_user_by_tg_id
from services.chat_service import get_active_chat, end_chat, increment_messages_count
from keyboards.inline import get_main_inline_keyboard, get_chat_inline_keyboard
from utils.debug import dbg

# Словарь для хранения соответствия ID сообщений
message_mapping: Dict[int, int] = {}

# Типы контента и соответствующие действия
CONTENT_ACTIONS = {
    "text": "typing",
    "photo": "upload_photo",
    "video": "upload_video",
    "voice": "record_voice",
    "document": "upload_document",
    "audio": "upload_voice",
    "sticker": None  # Для стикеров не нужен эффект
}

async def get_chat_data(db: Session, user_id: int) -> Tuple[Optional[User], Optional[User], Optional[AnonymousChat]]:
    """Получает данные о чате, пользователе и партнере"""
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        return None, None, None
    
    # Получаем активный чат напрямую из БД
    chat = get_active_chat(db, user.id)
    
    if not chat:
        return user, None, None
    
    # Если чат не активен, возвращаем None
    if not chat.is_active:
        return user, None, None
    
    # Получаем партнера
    partner_id = chat.user2_id if chat.user1_id == user.id else chat.user1_id
    partner = db.query(User).filter(User.id == partner_id).first()
    
    # Если партнер не найден, завершаем чат
    if not partner:
        end_chat(db, chat.id)
        return user, None, None
    
    return user, partner, chat

async def send_chat_action(bot: Bot, user_id: int, content_type: str) -> None:
    """Отправляет эффект действия в чате (набор текста, загрузка фото и т.д.)"""
    action = CONTENT_ACTIONS.get(content_type)
    if action:
        try:
            await bot.send_chat_action(user_id, action)
        except Exception as e:
            dbg(f"Ошибка при отправке эффекта {action}: {e}", "CHAT_ERROR")

async def get_reply_message_id(message: types.Message) -> Optional[int]:
    """Получает ID сообщения для ответа"""
    if not message.reply_to_message:
        return None
        
    original_message_id = message.reply_to_message.message_id
    
    if original_message_id in message_mapping:
        reply_id = message_mapping[original_message_id]
        return reply_id
    
    return None

async def send_media_message(bot: Bot, partner_id: int, message: types.Message, reply_to_message_id: Optional[int] = None) -> Optional[types.Message]:
    """Отправляет медиа-сообщение партнеру"""
    content_type = None
    file_id = None
    caption = message.caption
    
    if message.photo:
        content_type = "photo"
        file_id = message.photo[-1].file_id
    elif message.video:
        content_type = "video"
        file_id = message.video.file_id
    elif message.voice:
        content_type = "voice"
        file_id = message.voice.file_id
    elif message.document:
        content_type = "document"
        file_id = message.document.file_id
    elif message.audio:
        content_type = "audio"
        file_id = message.audio.file_id
    elif message.sticker:
        content_type = "sticker"
        file_id = message.sticker.file_id
    
    if not content_type or not file_id:
        return None
    
    # Отправляем эффект действия
    try:
        await send_chat_action(bot, partner_id, content_type)
    except Exception as e:
        dbg(f"Ошибка при отправке эффекта действия: {e}", "CHAT_ERROR")
    
    # Небольшая задержка для реалистичности
    await asyncio.sleep(0.5)
    
    # Отправляем сообщение
    try:
        dbg(f"Отправка {content_type} пользователю {partner_id}", "CHAT")
        if content_type == "photo":
            return await bot.send_photo(partner_id, file_id, caption=caption, reply_to_message_id=reply_to_message_id)
        elif content_type == "video":
            return await bot.send_video(partner_id, file_id, caption=caption, reply_to_message_id=reply_to_message_id)
        elif content_type == "voice":
            return await bot.send_voice(partner_id, file_id, reply_to_message_id=reply_to_message_id)
        elif content_type == "document":
            return await bot.send_document(partner_id, file_id, caption=caption, reply_to_message_id=reply_to_message_id)
        elif content_type == "audio":
            return await bot.send_audio(partner_id, file_id, caption=caption, reply_to_message_id=reply_to_message_id)
        elif content_type == "sticker":
            return await bot.send_sticker(partner_id, file_id, reply_to_message_id=reply_to_message_id)
    except Exception as e:
        dbg(f"Ошибка при отправке {content_type}: {e}", "CHAT_ERROR")
        raise  # Пробрасываем ошибку для обработки на уровне выше
        
    return None

async def process_chat_message(message: types.Message, state: FSMContext) -> None:
    """Обрабатывает сообщение в чате и отправляет его партнеру"""
    db = next(get_db())
    
    # Получаем данные о чате из состояния
    data = await state.get_data()
    chat_id = data.get("chat_id")
    partner_id = data.get("partner_id")
    
    # Если данных нет в состоянии, получаем их из базы данных
    if not chat_id or not partner_id:
        user = get_user_by_tg_id(db, message.from_user.id)
        if not user:
            await message.answer("Произошла ошибка. Пожалуйста, начните заново с команды /start")
            await state.clear()
            return
            
        user, partner, chat = await get_chat_data(db, user.id)
        
        if not chat:
            await message.answer(
                "У тебя нет активного чата. Хочешь найти собеседника?",
                reply_markup=get_main_inline_keyboard()
            )
            await state.clear()
            return
        
        if not partner:
            await message.answer("Произошла ошибка. Чат завершен.")
            await state.clear()
            return
            
        # Сохраняем данные в состоянии
        chat_id = chat.id
        partner_id = partner.id
        await state.update_data(chat_id=chat_id, partner_id=partner_id)
    else:
        # Получаем партнера из базы данных
        partner = db.query(User).filter(User.id == partner_id).first()
        chat = db.query(AnonymousChat).filter(AnonymousChat.id == chat_id).first()
        
        if not partner or not chat:
            await message.answer("Произошла ошибка. Чат завершен.")
            if chat:
                end_chat(db, chat.id)
            await state.clear()
            return
        
        # Проверяем, активен ли чат
        if not chat.is_active:
            await message.answer(
                "Этот чат уже завершен. Хочешь найти нового собеседника?",
                reply_markup=get_main_inline_keyboard()
            )
            await state.clear()
            return
    
    # Показываем эффект набора текста партнеру
    try:
        await send_chat_action(message.bot, partner.tg_id, "typing")
    except Exception as e:
        dbg(f"Ошибка при отправке эффекта набора текста: {e}", "CHAT_ERROR")
    
    try:
        # Увеличиваем счетчик сообщений
        increment_messages_count(db, chat_id)
        
        # Получаем ID сообщения для ответа
        reply_to_message_id = await get_reply_message_id(message)
        
        sent_message = None
        
        # Обрабатываем текстовое сообщение
        if message.text:
            # Небольшая задержка для реалистичности
            await asyncio.sleep(0.3)
            
            dbg(f"Отправка текстового сообщения пользователю {partner.tg_id}", "CHAT")
            sent_message = await message.bot.send_message(
                partner.tg_id,
                message.text,
                reply_to_message_id=reply_to_message_id
            )
        else:
            # Обрабатываем медиа-сообщение
            sent_message = await send_media_message(
                message.bot, 
                partner.tg_id, 
                message, 
                reply_to_message_id
            )
        
        # Сохраняем соответствие ID сообщений
        if sent_message:
            message_mapping[message.message_id] = sent_message.message_id
            dbg(f"Сохранено соответствие ID: {message.message_id} -> {sent_message.message_id}", "CHAT")
        
    except Exception as e:
        dbg(f"Ошибка при обработке сообщения: {e}", "CHAT_ERROR")
        
        # Проверяем, не связана ли ошибка с блокировкой бота
        if "blocked" in str(e).lower() or "kicked" in str(e).lower() or "not found" in str(e).lower():
            dbg(f"Пользователь {partner.tg_id} заблокировал бота или удалил чат", "CHAT")
            end_chat(db, chat_id)
            await message.answer(
                "Собеседник заблокировал бота или удалил чат. Чат завершен.",
                reply_markup=get_main_inline_keyboard()
            )
            await state.clear()
        else:
            # Для других ошибок просто сообщаем пользователю
            await message.answer("Не удалось отправить сообщение собеседнику. Попробуйте еще раз.")

def clear_message_mapping_for_chat(chat_id: int) -> None:
    """Очищает соответствия ID сообщений для указанного чата"""
    global message_mapping
    
    # Ограничиваем размер словаря соответствий
    if len(message_mapping) > 1000:
        # Сохраняем только последние 100 соответствий
        keys = list(message_mapping.keys())
        for old_key in keys[:-100]:
            message_mapping.pop(old_key, None)
    
    dbg(f"Очищены соответствия ID сообщений для чата {chat_id}", "CHAT")