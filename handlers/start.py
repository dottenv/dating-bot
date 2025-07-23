from aiogram import types, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from database.db import get_db
from services.user_service import get_user_by_tg_id, create_user
from keyboards.inline import get_main_inline_keyboard, get_gender_inline_keyboard
from states.user_states import UserRegistration
from utils.debug import dbg

router = Router()

@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()  # Reset any active state
    dbg(f"Получена команда /start от пользователя {message.from_user.id}", "START")
    
    # Get database session
    db = next(get_db())
    
    # Check if user exists
    user = get_user_by_tg_id(db, message.from_user.id)
    
    if not user:
        # Create new user
        dbg(f"Пользователь {message.from_user.id} не найден, создаем нового", "START")
        user = create_user(
            db=db,
            tg_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name
        )
        dbg(f"Создан новый пользователь ID: {user.id}, имя: {user.first_name}", "START")
        
        await message.answer(
            f"Привет, {user.first_name}! Добро пожаловать в анонимный чат-бот для знакомств. "
            f"Давай заполним твой профиль. Как тебя зовут?"
        )
        await state.set_state(UserRegistration.first_name)
        dbg(f"Установлено состояние UserRegistration.first_name для пользователя {user.id}", "START")
    else:
        # User already exists
        dbg(f"Пользователь {message.from_user.id} найден, имя: {user.first_name}", "START")
        await message.answer(
            f"С возвращением, {user.first_name}! Что будем делать сегодня?",
            reply_markup=get_main_inline_keyboard()
        )

# Обработчик для кнопки "Найти собеседника" в главном меню
@router.callback_query(lambda c: c.data == "find_chat")
async def find_chat_callback(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    dbg(f"Получен запрос на поиск собеседника от пользователя {callback.from_user.id}", "START")
    
    # Вместо перенаправления на обработчик в chat.py, реализуем логику здесь
    db = next(get_db())
    user = get_user_by_tg_id(db, callback.from_user.id)

    if not user:
        dbg(f"Пользователь {callback.from_user.id} не найден", "START")
        await callback.message.answer("Пожалуйста, сначала зарегистрируйтесь с помощью команды /start")
        return

    # Импортируем необходимые функции
    from services.chat_service import find_available_chat_partner, create_chat, get_active_chat
    from keyboards.inline import get_chat_inline_keyboard
    from states.user_states import AnonymousChatting

    active_chat = get_active_chat(db, user.id)
    if active_chat:
        dbg(f"У пользователя {user.id} уже есть активный чат ID: {active_chat.id}", "START")
        await callback.message.answer(
            "Ты уже находишься в чате. Используй эти кнопки для управления:",
            reply_markup=get_chat_inline_keyboard()
        )
        await state.set_state(AnonymousChatting.chatting)
        dbg(f"Установлено состояние AnonymousChatting.chatting для пользователя {user.id}", "START")
        return

    try:
        # Показываем эффект поиска
        await callback.bot.send_chat_action(callback.from_user.id, "typing")
        
        # Импортируем asyncio для задержки
        import asyncio
        await asyncio.sleep(1.0)  # Имитация поиска
    except Exception as e:
        print(f"Ошибка при отправке эффекта поиска: {e}")
    
    partner = await find_available_chat_partner(db, user.id)
    if partner:
        chat = create_chat(db, user.id, partner.id)
        
        # Отправляем уведомление о найденном собеседнике
        await callback.message.answer(
            "Собеседник найден! Теперь вы можете общаться анонимно.",
            reply_markup=get_chat_inline_keyboard()
        )
        
        bot = callback.bot
        try:
            # Показываем эффект набора текста партнеру
            await bot.send_chat_action(partner.tg_id, "typing")
            await asyncio.sleep(0.5)
        except Exception as e:
            print(f"Ошибка при отправке эффекта набора текста партнеру: {e}")
        
        try:
            await bot.send_message(
                partner.tg_id,
                "Собеседник найден! Теперь вы можете общаться анонимно.",
                reply_markup=get_chat_inline_keyboard()
            )
        except Exception as e:
            print(f"Ошибка при отправке сообщения партнеру: {e}")
            await callback.message.answer(
                "Произошла ошибка при уведомлении собеседника. Попробуйте еще раз."
            )
            return
            
        await state.set_state(AnonymousChatting.chatting)
        await state.update_data(chat_id=chat.id, partner_id=partner.id)
    else:
        # Показываем анимацию поиска
        await callback.message.answer(
            "Ищем собеседника... Пожалуйста, подожди."
        )
        # Добавляем кнопку для отмены поиска
        await callback.message.answer(
            "Вернуться в главное меню:",
            reply_markup=get_main_inline_keyboard()
        )
        await state.set_state(AnonymousChatting.waiting)