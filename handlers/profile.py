from aiogram import types, Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from database.db import get_db
from services.user_service import get_user_by_tg_id
from keyboards.reply import get_main_keyboard

router = Router()

@router.message(F.text == "👤 Мой профиль")
async def cmd_profile(message: types.Message, state: FSMContext):
    await state.clear()
    
    db = next(get_db())
    user = get_user_by_tg_id(db, message.from_user.id)
    
    if not user:
        await message.answer("Пожалуйста, сначала зарегистрируйтесь с помощью команды /start")
        return
    
    profile_text = (
        f"Твой профиль:\n"
        f"Имя: {user.first_name}\n"
        f"Возраст: {user.age if user.age else 'Не указан'}\n"
        f"Пол: {user.gender if user.gender else 'Не указан'}\n"
        f"Ориентация: {user.orientation if user.orientation else 'Не указана'}\n"
        f"Город: {user.city if user.city else 'Не указан'}\n"
        f"О себе: {user.bio if user.bio else 'Не указано'}\n"
        f"Интересы: {user.tags if user.tags else 'Не указаны'}"
    )
    
    if user.photo_id:
        await message.answer_photo(user.photo_id, caption=profile_text, reply_markup=get_main_keyboard())
    else:
        await message.answer(profile_text, reply_markup=get_main_keyboard())

@router.message(F.text == "ℹ️ Помощь")
@router.message(Command("help"))
async def cmd_help(message: types.Message):
    help_text = (
        "🤖 Бот для анонимных знакомств\n\n"
        "Команды:\n"
        "/start - Начать работу с ботом\n"
        "🔍 Найти собеседника - Поиск анонимного собеседника\n"
        "👤 Мой профиль - Просмотр своего профиля\n"
        "ℹ️ Помощь - Показать это сообщение\n\n"
        "В анонимном чате:\n"
        "👋 Раскрыть личность - Отправить запрос на раскрытие личности\n"
        "❌ Завершить чат - Завершить текущий чат"
    )
    
    await message.answer(help_text, reply_markup=get_main_keyboard())