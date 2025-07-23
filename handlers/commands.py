from aiogram import types, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
import datetime

from database.db import get_db
from services.user_service import get_user_by_tg_id
from services.chat_service import get_active_chat, end_chat, get_chat_partner_id
from keyboards.inline import get_main_inline_keyboard, get_chat_inline_keyboard
from states.user_states import AnonymousChatting
from utils.debug import dbg
from handlers.chat_message_handler import clear_message_mapping_for_chat

router = Router()

# Обработчик команды /profile
@router.message(Command("profile"))
async def cmd_profile(message: types.Message, state: FSMContext):
    """Обработчик команды /profile для просмотра профиля"""
    # Импортируем функцию из модуля profile
    from handlers.profile import cmd_profile as profile_handler
    await profile_handler(message, state)

# Обработчик команды /end для завершения чата
@router.message(Command("end"))
async def cmd_end_chat(message: types.Message, state: FSMContext):
    """Обработчик команды /end для завершения чата"""
    db = next(get_db())
    user = get_user_by_tg_id(db, message.from_user.id)
    
    if not user:
        await message.answer("Пожалуйста, сначала зарегистрируйтесь с помощью команды /start")
        return
    
    chat = get_active_chat(db, user.id)
    if not chat:
        await message.answer(
            "У тебя нет активного чата.",
            reply_markup=get_main_inline_keyboard()
        )
        await state.clear()
        return
    
    partner_id, partner = await get_partner_info(db, chat, user.id)
    
    # Очищаем соответствия ID сообщений для этого чата
    clear_message_mapping_for_chat(chat.id)
    
    end_chat(db, chat.id)
    await message.answer(
        "Чат завершен. Хочешь найти нового собеседника?",
        reply_markup=get_main_inline_keyboard()
    )
    
    if partner and partner.tg_id:
        try:
            await message.bot.send_message(
                partner.tg_id,
                "Собеседник завершил чат. Хочешь найти нового собеседника?",
                reply_markup=get_main_inline_keyboard()
            )
        except Exception as e:
            dbg(f"Ошибка при отправке уведомления партнеру: {e}", "CHAT_ERROR")
    
    await state.clear()

# Обработчик команды /info для получения информации о чате
@router.message(Command("info"))
async def cmd_chat_info(message: types.Message, state: FSMContext):
    """Обработчик команды /info для получения информации о чате"""
    db = next(get_db())
    user = get_user_by_tg_id(db, message.from_user.id)
    
    if not user:
        await message.answer("Пожалуйста, сначала зарегистрируйтесь с помощью команды /start")
        return
    
    chat = get_active_chat(db, user.id)
    if not chat:
        await message.answer(
            "У тебя нет активного чата.",
            reply_markup=get_main_inline_keyboard()
        )
        await state.clear()
        return
    
    # Формируем информацию о чате
    chat_duration = datetime.datetime.now() - chat.start_time
    hours, remainder = divmod(chat_duration.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    duration_str = f"{hours}ч {minutes}м {seconds}с" if hours > 0 else f"{minutes}м {seconds}с"
    
    info_text = (
        f"📊 Информация о текущем чате:\n"
        f"⏱️ Длительность: {duration_str}\n"
        f"💬 Количество сообщений: {chat.messages_count}\n"
    )
    
    await message.answer(
        info_text,
        reply_markup=get_chat_inline_keyboard()
    )

# Обработчик команды /cancel для отмены поиска
@router.message(Command("cancel"))
async def cmd_cancel_search(message: types.Message, state: FSMContext):
    """Обработчик команды /cancel для отмены поиска собеседника"""
    current_state = await state.get_state()
    
    if current_state == AnonymousChatting.waiting.state:
        await message.answer(
            "Поиск собеседника отменен.",
            reply_markup=get_main_inline_keyboard()
        )
        await state.clear()
    else:
        await message.answer(
            "Ты не в режиме поиска собеседника.",
            reply_markup=get_main_inline_keyboard()
        )

# Вспомогательная функция для получения информации о партнере
async def get_partner_info(db, chat, user_id):
    """Получает информацию о партнере в чате"""
    partner_id = chat.user2_id if chat.user1_id == user_id else chat.user1_id
    from database.models import User
    partner = db.query(User).filter(User.id == partner_id).first()
    return partner_id, partner