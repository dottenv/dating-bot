from aiogram import types, Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
import asyncio
from typing import Union, Optional

from database.db import get_db
from services.user_service import get_user_by_tg_id, update_user_profile, toggle_user_activity
from keyboards.inline import (
    get_main_inline_keyboard, get_profile_menu_keyboard, get_profile_edit_keyboard,
    get_gender_inline_keyboard, get_orientation_inline_keyboard, get_back_to_profile_keyboard,
    get_edit_or_back_keyboard, BACK_TO_MAIN, BACK_TO_PROFILE, EDIT_PROFILE, MY_PROFILE,
    TOGGLE_ACTIVITY, GENDER_MALE, GENDER_FEMALE, GENDER_OTHER,
    ORIENTATION_HETERO, ORIENTATION_HOMO, ORIENTATION_BI, ORIENTATION_OTHER
)
from states.user_states import UserRegistration

router = Router()

# Обработчик для главного меню
@router.callback_query(F.data == BACK_TO_MAIN)
async def back_to_main_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()

    await callback.message.edit_text(
        "Главное меню:",
        reply_markup=get_main_inline_keyboard()
    )

# Обработчик для просмотра профиля
@router.message(F.text == "👤 Мой профиль")
@router.callback_query(F.data == MY_PROFILE)
async def cmd_profile(message_or_callback: Union[Message, CallbackQuery], state: FSMContext):
    await state.clear()

    # Определяем, это сообщение или callback
    is_callback = isinstance(message_or_callback, CallbackQuery)
    if is_callback:
        await message_or_callback.answer()
        user_id = message_or_callback.from_user.id
        message = message_or_callback.message
        bot = message_or_callback.bot
    else:
        user_id = message_or_callback.from_user.id
        message = message_or_callback
        bot = message.bot

    # Добавляем эффект загрузки фото
    await bot.send_chat_action(user_id, "upload_photo")
    await asyncio.sleep(0.5)

    db = next(get_db())
    user = get_user_by_tg_id(db, user_id)

    if not user:
        if is_callback:
            await message.edit_text(
                "Пожалуйста, сначала зарегистрируйтесь с помощью команды /start",
                reply_markup=None
            )
        else:
            await message.answer("Пожалуйста, сначала зарегистрируйтесь с помощью команды /start")
        return

    # Добавляем статус активности в профиль
    activity_status = "🟢 Активен" if user.is_active else "🔴 Неактивен"

    profile_text = (
        f"Твой профиль:\n"
        f"Имя: {user.first_name}\n"
        f"Возраст: {user.age if user.age else 'Не указан'}\n"
        f"Пол: {user.gender if user.gender else 'Не указан'}\n"
        f"Ориентация: {user.orientation if user.orientation else 'Не указана'}\n"
        f"Город: {user.city if user.city else 'Не указан'}\n"
        f"О себе: {user.bio if user.bio else 'Не указано'}\n"
        f"Интересы: {user.tags if user.tags else 'Не указаны'}\n"
        f"Статус: {activity_status}"
    )

    # Отправляем профиль с фото или без
    if hasattr(user, 'photo_id') and user.photo_id:
        if is_callback:
            # Для callback нельзя редактировать сообщение с фото, отправляем новое
            await message.delete()
            sent_message = await bot.send_photo(
                user_id,
                user.photo_id,
                caption=profile_text
            )
            # Отправляем меню профиля отдельным сообщением
            await bot.send_message(
                user_id,
                "Управление профилем:",
                reply_markup=get_profile_menu_keyboard(user.is_active)
            )
        else:
            # Для обычного сообщения отправляем фото и меню
            await message.answer_photo(
                user.photo_id,
                caption=profile_text
            )
            await message.answer(
                "Управление профилем:",
                reply_markup=get_profile_menu_keyboard(user.is_active)
            )
    else:
        if is_callback:
            # Редактируем текущее сообщение
            await message.edit_text(
                profile_text,
                reply_markup=get_profile_menu_keyboard(user.is_active)
            )
        else:
            # Отправляем новое сообщение
            await message.answer(
                profile_text,
                reply_markup=get_profile_menu_keyboard(user.is_active)
            )

# Обработчик для переключения активности
@router.callback_query(F.data == TOGGLE_ACTIVITY)
async def toggle_activity(callback: CallbackQuery):
    await callback.answer()

    db = next(get_db())
    user = get_user_by_tg_id(db, callback.from_user.id)

    if not user:
        await callback.message.edit_text(
            "Пожалуйста, сначала зарегистрируйтесь с помощью команды /start",
            reply_markup=None
        )
        return

    # Переключаем статус активности
    user = toggle_user_activity(db, user)

    # Получаем новый статус
    activity_status = "🟢 Активен" if user.is_active else "🔴 Неактивен"
    status_message = (
        f"Статус активности изменен на: {activity_status}\n\n"
        f"{'Теперь другие пользователи могут найти тебя при поиске собеседника.' if user.is_active else 'Теперь другие пользователи не смогут найти тебя при поиске собеседника.'}"
    )

    # Редактируем текущее сообщение
    await callback.message.edit_text(
        status_message,
        reply_markup=get_profile_menu_keyboard(user.is_active)
    )

# Обработчик для меню редактирования профиля
@router.callback_query(F.data == EDIT_PROFILE)
async def show_edit_profile_menu(callback: CallbackQuery):
    await callback.answer()

    await callback.message.edit_text(
        "Выберите, что хотите изменить в своем профиле:",
        reply_markup=get_profile_edit_keyboard()
    )

# Обработчик для возврата к профилю
@router.callback_query(F.data == BACK_TO_PROFILE)
async def back_to_profile(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()

    # Перенаправляем на функцию просмотра профиля
    await cmd_profile(callback, state)

# Обработчики для редактирования профиля
@router.callback_query(F.data.startswith("edit_"))
async def process_edit_profile(callback: CallbackQuery, state: FSMContext):
    action = callback.data.split("_")[1] if callback.data else ""

    edit_messages = {
        "name": "Введи новое имя:",
        "age": "Введи новый возраст (от 18 до 100):",
        "gender": "Выбери пол:",
        "orientation": "Выбери ориентацию:",
        "city": "Введи название города:",
        "bio": "Расскажи о себе:",
        "photo": "Отправь новую фотографию:",
        "tags": "Укажи свои интересы через запятую:"
    }

    states_map = {
        "name": UserRegistration.first_name,
        "age": UserRegistration.age,
        "gender": UserRegistration.gender,
        "orientation": UserRegistration.orientation,
        "city": UserRegistration.city,
        "bio": UserRegistration.bio,
        "photo": UserRegistration.photo,
        "tags": UserRegistration.tags
    }

    await callback.answer()

    if action == "gender":
        await callback.message.edit_text(
            edit_messages[action],
            reply_markup=get_gender_inline_keyboard()
        )
    elif action == "orientation":
        await callback.message.edit_text(
            edit_messages[action],
            reply_markup=get_orientation_inline_keyboard()
        )
    else:
        await callback.message.edit_text(
            edit_messages[action],
            reply_markup=get_back_to_profile_keyboard()
        )

    await state.set_state(states_map[action])
    await state.update_data(edit_mode=True)

# Обработчики для выбора пола через inline кнопки
@router.callback_query(F.data.startswith("gender_"))
async def process_gender_choice(callback: CallbackQuery, state: FSMContext):
    gender_map = {
        GENDER_MALE: "Мужской",
        GENDER_FEMALE: "Женский",
        GENDER_OTHER: "Другой"
    }

    gender = gender_map.get(callback.data or "", "Другой")
    await callback.answer()

    current_state = await state.get_state()
    if current_state == UserRegistration.gender.state:
        data = await state.get_data()
        edit_mode = data.get("edit_mode", False)

        if edit_mode:
            db = next(get_db())
            user = get_user_by_tg_id(db, callback.from_user.id)

            # Проверяем, что user является объектом User
            if user and hasattr(user, 'id'):
                update_user_profile(db, user, gender=gender)
                await callback.message.edit_text(
                    f"Пол успешно обновлен на: {gender}",
                    reply_markup=get_edit_or_back_keyboard()
                )
            else:
                await callback.message.edit_text(
                    "Ошибка при обновлении профиля. Попробуйте еще раз.",
                    reply_markup=get_back_to_profile_keyboard()
                )
            await state.clear()
        else:
            await state.update_data(gender=gender)
            await callback.message.edit_text(
                "Укажи свою ориентацию:",
                reply_markup=get_orientation_inline_keyboard(include_back=False)
            )
            await state.set_state(UserRegistration.orientation)

# Обработчики для выбора ориентации через inline кнопки
@router.callback_query(F.data.startswith("orientation_"))
async def process_orientation_choice(callback: CallbackQuery, state: FSMContext):
    orientation_map = {
        ORIENTATION_HETERO: "Гетеро",
        ORIENTATION_HOMO: "Гомо",
        ORIENTATION_BI: "Би",
        ORIENTATION_OTHER: "Другое"
    }

    orientation = orientation_map.get(callback.data or "", "Другое")
    await callback.answer()

    current_state = await state.get_state()
    if current_state == UserRegistration.orientation.state:
        data = await state.get_data()
        edit_mode = data.get("edit_mode", False)

        if edit_mode:
            db = next(get_db())
            user = get_user_by_tg_id(db, callback.from_user.id)

            # Проверяем, что user является объектом User
            if user and hasattr(user, 'id'):
                update_user_profile(db, user, orientation=orientation)
                await callback.message.edit_text(
                    f"Ориентация успешно обновлена на: {orientation}",
                    reply_markup=get_edit_or_back_keyboard()
                )
            else:
                await callback.message.edit_text(
                    "Ошибка при обновлении профиля. Попробуйте еще раз.",
                    reply_markup=get_back_to_profile_keyboard()
                )
            await state.clear()
        else:
            await state.update_data(orientation=orientation)
            await callback.message.edit_text("В каком городе ты находишься?")
            await state.set_state(UserRegistration.city)

# Обработчики для обновления профиля через текстовые сообщения
@router.message(UserRegistration.first_name)
async def update_first_name(message: Message, state: FSMContext):
    data = await state.get_data()
    edit_mode = data.get("edit_mode", False)

    if edit_mode:
        db = next(get_db())
        user = get_user_by_tg_id(db, message.from_user.id)

        # Проверяем, что user является объектом User
        if user and hasattr(user, 'id'):
            update_user_profile(db, user, first_name=message.text)
            await message.answer(
                f"Имя успешно обновлено на: {message.text}",
                reply_markup=get_edit_or_back_keyboard()
            )
        else:
            await message.answer(
                "Ошибка при обновлении профиля. Попробуйте еще раз.",
                reply_markup=get_back_to_profile_keyboard()
            )
        await state.clear()
    else:
        # Стандартная обработка для регистрации
        await state.update_data(first_name=message.text)
        await message.answer("Отлично! Сколько тебе лет?")
        await state.set_state(UserRegistration.age)

@router.message(UserRegistration.age)
async def update_age(message: Message, state: FSMContext):
    if not message.text or not message.text.isdigit():
        await message.answer("Пожалуйста, введи возраст числом.")
        return

    age = int(message.text)
    if age < 18 or age > 100:
        await message.answer("Возраст должен быть от 18 до 100 лет.")
        return

    data = await state.get_data()
    edit_mode = data.get("edit_mode", False)

    if edit_mode:
        db = next(get_db())
        user = get_user_by_tg_id(db, message.from_user.id)

        # Проверяем, что user является объектом User
        if user and hasattr(user, 'id'):
            update_user_profile(db, user, age=age)
            await message.answer(
                f"Возраст успешно обновлен на: {age}",
                reply_markup=get_edit_or_back_keyboard()
            )
        else:
            await message.answer(
                "Ошибка при обновлении профиля. Попробуйте еще раз.",
                reply_markup=get_back_to_profile_keyboard()
            )
        await state.clear()
    else:
        # Стандартная обработка для регистрации
        await state.update_data(age=age)
        await message.answer(
            "Укажи свой пол:",
            reply_markup=get_gender_inline_keyboard(include_back=False)
        )
        await state.set_state(UserRegistration.gender)

@router.message(UserRegistration.gender)
async def update_gender(message: Message, state: FSMContext):
    data = await state.get_data()
    edit_mode = data.get("edit_mode", False)

    if edit_mode:
        db = next(get_db())
        user = get_user_by_tg_id(db, message.from_user.id)

        # Проверяем, что user является объектом User
        if user and hasattr(user, 'id'):
            update_user_profile(db, user, gender=message.text)
            await message.answer(
                f"Пол успешно обновлен на: {message.text}",
                reply_markup=get_edit_or_back_keyboard()
            )
        else:
            await message.answer(
                "Ошибка при обновлении профиля. Попробуйте еще раз.",
                reply_markup=get_back_to_profile_keyboard()
            )
        await state.clear()
    else:
        # Стандартная обработка для регистрации
        await state.update_data(gender=message.text)
        await message.answer(
            "Укажи свою ориентацию:",
            reply_markup=get_orientation_inline_keyboard(include_back=False)
        )
        await state.set_state(UserRegistration.orientation)

@router.message(UserRegistration.orientation)
async def update_orientation(message: Message, state: FSMContext):
    data = await state.get_data()
    edit_mode = data.get("edit_mode", False)

    if edit_mode:
        db = next(get_db())
        user = get_user_by_tg_id(db, message.from_user.id)

        # Проверяем, что user является объектом User
        if user and hasattr(user, 'id'):
            update_user_profile(db, user, orientation=message.text)
            await message.answer(
                f"Ориентация успешно обновлена на: {message.text}",
                reply_markup=get_edit_or_back_keyboard()
            )
        else:
            await message.answer(
                "Ошибка при обновлении профиля. Попробуйте еще раз.",
                reply_markup=get_back_to_profile_keyboard()
            )
        await state.clear()
    else:
        # Стандартная обработка для регистрации
        await state.update_data(orientation=message.text)
        await message.answer("В каком городе ты находишься?")
        await state.set_state(UserRegistration.city)

@router.message(UserRegistration.city)
async def update_city(message: Message, state: FSMContext):
    data = await state.get_data()
    edit_mode = data.get("edit_mode", False)

    if edit_mode:
        db = next(get_db())
        user = get_user_by_tg_id(db, message.from_user.id)

        # Проверяем, что user является объектом User
        if user and hasattr(user, 'id'):
            update_user_profile(db, user, city=message.text)
            await message.answer(
                f"Город успешно обновлен на: {message.text}",
                reply_markup=get_edit_or_back_keyboard()
            )
        else:
            await message.answer(
                "Ошибка при обновлении профиля. Попробуйте еще раз.",
                reply_markup=get_back_to_profile_keyboard()
            )
        await state.clear()
    else:
        # Стандартная обработка для регистрации
        await state.update_data(city=message.text)
        await message.answer("Расскажи немного о себе (твои интересы, хобби и т.д.):")
        await state.set_state(UserRegistration.bio)

@router.message(UserRegistration.bio)
async def update_bio(message: Message, state: FSMContext):
    data = await state.get_data()
    edit_mode = data.get("edit_mode", False)

    if edit_mode:
        db = next(get_db())
        user = get_user_by_tg_id(db, message.from_user.id)

        # Проверяем, что user является объектом User
        if user and hasattr(user, 'id'):
            update_user_profile(db, user, bio=message.text)
            await message.answer(
                "Информация о себе успешно обновлена",
                reply_markup=get_edit_or_back_keyboard()
            )
        else:
            await message.answer(
                "Ошибка при обновлении профиля. Попробуйте еще раз.",
                reply_markup=get_back_to_profile_keyboard()
            )
        await state.clear()
    else:
        # Стандартная обработка для регистрации
        await state.update_data(bio=message.text)
        await message.answer("Отправь свою фотографию:")
        await state.set_state(UserRegistration.photo)

@router.message(UserRegistration.photo, F.photo)
async def update_photo(message: Message, state: FSMContext):
    if not message.photo:
        await message.answer("Пожалуйста, отправь фотографию.")
        return
        
    photo_id = message.photo[-1].file_id
    data = await state.get_data()
    edit_mode = data.get("edit_mode", False)

    if edit_mode:
        # Добавляем эффект загрузки фото
        await message.bot.send_chat_action(message.from_user.id, "upload_photo")
        await asyncio.sleep(0.5)

        db = next(get_db())
        user = get_user_by_tg_id(db, message.from_user.id)

        # Проверяем, что user является объектом User
        if user and hasattr(user, 'id'):
            update_user_profile(db, user, photo_id=photo_id)
            await message.answer_photo(
                photo_id,
                caption="Фотография успешно обновлена",
                reply_markup=get_edit_or_back_keyboard()
            )
        else:
            await message.answer(
                "Ошибка при обновлении профиля. Попробуйте еще раз.",
                reply_markup=get_back_to_profile_keyboard()
            )
        await state.clear()
    else:
        # Стандартная обработка для регистрации
        await state.update_data(photo_id=photo_id)
        await message.answer("Укажи свои интересы через запятую (например: спорт, музыка, путешествия):")
        await state.set_state(UserRegistration.tags)

@router.message(UserRegistration.photo)
async def process_invalid_photo(message: Message):
    await message.answer("Пожалуйста, отправь фотографию.")

@router.message(UserRegistration.tags)
async def update_tags(message: Message, state: FSMContext):
    data = await state.get_data()
    edit_mode = data.get("edit_mode", False)

    if edit_mode:
        db = next(get_db())
        user = get_user_by_tg_id(db, message.from_user.id)

        # Проверяем, что user является объектом User
        if user and hasattr(user, 'id'):
            update_user_profile(db, user, tags=message.text)
            await message.answer(
                f"Интересы успешно обновлены на: {message.text}",
                reply_markup=get_edit_or_back_keyboard()
            )
        else:
            await message.answer(
                "Ошибка при обновлении профиля. Попробуйте еще раз.",
                reply_markup=get_back_to_profile_keyboard()
            )
        await state.clear()
    else:
        # Стандартная обработка для регистрации
        await state.update_data(tags=message.text)

        # Get all data from state
        data = await state.get_data()

        # Save all data to database
        db = next(get_db())
        user = get_user_by_tg_id(db, message.from_user.id)

        # Обновляем только те поля, которые есть в данных
        update_params = {}
        for field in ['first_name', 'age', 'gender', 'orientation', 'city', 'bio', 'photo_id', 'tags']:
            if field in data:
                # Преобразуем возраст в число, если это строка
                if field == 'age' and isinstance(data[field], str) and data[field].isdigit():
                    update_params[field] = int(data[field])
                else:
                    update_params[field] = data[field]

        # Проверяем, что user является объектом User
        if user and hasattr(user, 'id'):
            update_user_profile(db=db, user=user, **update_params)
        else:
            await message.answer("Ошибка при обновлении профиля. Попробуйте еще раз.")

        await message.answer(
            "Отлично! Твой профиль заполнен. Теперь ты можешь начать общение.",
            reply_markup=get_main_inline_keyboard()
        )
        await state.clear()