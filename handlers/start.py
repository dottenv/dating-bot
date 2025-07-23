from aiogram import types, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from database.db import get_db
from services.user_service import get_user_by_tg_id, create_user
from keyboards.reply import get_main_keyboard
from states.user_states import UserRegistration

router = Router()

@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()  # Reset any active state
    
    # Get database session
    db = next(get_db())
    
    # Check if user exists
    user = get_user_by_tg_id(db, message.from_user.id)
    
    if not user:
        # Create new user
        user = create_user(
            db=db,
            tg_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name
        )
        
        await message.answer(
            f"Привет, {user.first_name}! Добро пожаловать в анонимный чат-бот для знакомств. "
            f"Давай заполним твой профиль. Как тебя зовут?"
        )
        await state.set_state(UserRegistration.first_name)
    else:
        # User already exists
        await message.answer(
            f"С возвращением, {user.first_name}! Что будем делать сегодня?",
            reply_markup=get_main_keyboard()
        )