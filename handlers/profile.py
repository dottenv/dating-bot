from aiogram import types, Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from database.db import get_db
from services.user_service import get_user_by_tg_id, update_user_profile, toggle_user_activity, get_user_activity_status
from keyboards.inline import (
    get_profile_edit_keyboard, get_help_keyboard, get_main_inline_keyboard,
    get_gender_inline_keyboard, get_orientation_inline_keyboard, get_activity_status_keyboard
)
from states.user_states import UserRegistration

router = Router()

# Обработчики для редактирования профиля
@router.message(F.text == "👤 Мой профиль")
@router.callback_query(F.data == "my_profile")
async def cmd_profile(message_or_callback: types.Message | types.CallbackQuery, state: FSMContext):
    await state.clear()
    
    # Определяем, это сообщение или callback
    is_callback = isinstance(message_or_callback, types.CallbackQuery)
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
    
    # Импортируем asyncio для задержки
    import asyncio
    await asyncio.sleep(1.0)
    
    db = next(get_db())
    user = get_user_by_tg_id(db, user_id)
    
    if not user:
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
    
    if user.photo_id:
        await message.answer_photo(
            user.photo_id, 
            caption=profile_text
        )
    else:
        await message.answer(profile_text)
    
    # Добавляем эффект набора текста перед отправкой кнопок
    await bot.send_chat_action(user_id, "typing")
    await asyncio.sleep(0.5)
    
    # Добавляем кнопки редактирования и возврата в главное меню
    await message.answer("Хочешь отредактировать профиль?", reply_markup=get_profile_edit_keyboard())
    
    # Добавляем кнопку переключения активности
    await message.answer(
        f"Текущий статус: {activity_status}",
        reply_markup=get_activity_status_keyboard(user.is_active)
    )
    
    await message.answer("Вернуться в главное меню:", reply_markup=get_main_inline_keyboard())

@router.callback_query(F.data == "toggle_activity")
async def toggle_activity(callback: types.CallbackQuery):
    await callback.answer()
    
    # Добавляем эффект набора текста
    await callback.bot.send_chat_action(callback.from_user.id, "typing")
    
    # Импортируем asyncio для задержки
    import asyncio
    await asyncio.sleep(0.5)
    
    db = next(get_db())
    user = get_user_by_tg_id(db, callback.from_user.id)
    
    if not user:
        await callback.message.answer("Пожалуйста, сначала зарегистрируйтесь с помощью команды /start")
        return
    
    # Переключаем статус активности
    user = toggle_user_activity(db, user)
    
    # Получаем новый статус
    activity_status = "🟢 Активен" if user.is_active else "🔴 Неактивен"
    
    await callback.message.answer(
        f"Статус активности изменен на: {activity_status}\n\n"
        f"{'Теперь другие пользователи могут найти тебя при поиске собеседника.' if user.is_active else 'Теперь другие пользователи не смогут найти тебя при поиске собеседника.'}"
    )
    
    # Обновляем кнопку статуса
    await callback.message.answer(
        f"Текущий статус: {activity_status}",
        reply_markup=get_activity_status_keyboard(user.is_active)
    )

@router.callback_query(F.data.startswith("edit_"))
async def process_edit_profile(callback: types.CallbackQuery, state: FSMContext):
    action = callback.data.split("_")[1]
    
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
    
    # Добавляем эффект набора текста
    await callback.bot.send_chat_action(callback.from_user.id, "typing")
    
    # Импортируем asyncio для задержки
    import asyncio
    await asyncio.sleep(0.5)
    
    if action == "gender":
        await callback.message.answer(edit_messages[action], reply_markup=get_gender_inline_keyboard())
    elif action == "orientation":
        await callback.message.answer(edit_messages[action], reply_markup=get_orientation_inline_keyboard())
    else:
        await callback.message.answer(edit_messages[action])
    
    await state.set_state(states_map[action])
    await state.update_data(edit_mode=True)

# Обработчики для выбора пола и ориентации через inline кнопки
@router.callback_query(F.data.startswith("gender_"))
async def process_gender_choice(callback: types.CallbackQuery, state: FSMContext):
    gender_map = {
        "gender_male": "Мужской",
        "gender_female": "Женский",
        "gender_other": "Другой"
    }
    
    gender = gender_map.get(callback.data, "Другой")
    await callback.answer()
    
    current_state = await state.get_state()
    if current_state == UserRegistration.gender.state:
        data = await state.get_data()
        edit_mode = data.get("edit_mode", False)
        
        if edit_mode:
            # Добавляем эффект набора текста
            await callback.bot.send_chat_action(callback.from_user.id, "typing")
            
            # Импортируем asyncio для задержки
            import asyncio
            await asyncio.sleep(0.5)
            
            db = next(get_db())
            user = get_user_by_tg_id(db, callback.from_user.id)
            update_user_profile(db, user, gender=gender)
            
            await callback.message.answer(f"Пол успешно обновлен на: {gender}")
            await callback.message.answer("Хочешь изменить что-то еще?", reply_markup=get_profile_edit_keyboard())
            await state.clear()
        else:
            await state.update_data(gender=gender)
            await callback.message.answer("Укажи свою ориентацию:", reply_markup=get_orientation_inline_keyboard())
            await state.set_state(UserRegistration.orientation)

@router.callback_query(F.data.startswith("orientation_"))
async def process_orientation_choice(callback: types.CallbackQuery, state: FSMContext):
    orientation_map = {
        "orientation_hetero": "Гетеро",
        "orientation_homo": "Гомо",
        "orientation_bi": "Би",
        "orientation_other": "Другое"
    }
    
    orientation = orientation_map.get(callback.data, "Другое")
    await callback.answer()
    
    current_state = await state.get_state()
    if current_state == UserRegistration.orientation.state:
        data = await state.get_data()
        edit_mode = data.get("edit_mode", False)
        
        if edit_mode:
            # Добавляем эффект набора текста
            await callback.bot.send_chat_action(callback.from_user.id, "typing")
            
            # Импортируем asyncio для задержки
            import asyncio
            await asyncio.sleep(0.5)
            
            db = next(get_db())
            user = get_user_by_tg_id(db, callback.from_user.id)
            update_user_profile(db, user, orientation=orientation)
            
            await callback.message.answer(f"Ориентация успешно обновлена на: {orientation}")
            await callback.message.answer("Хочешь изменить что-то еще?", reply_markup=get_profile_edit_keyboard())
            await state.clear()
        else:
            await state.update_data(orientation=orientation)
            await callback.message.answer("В каком городе ты находишься?")
            await state.set_state(UserRegistration.city)

# Обработчики для обновления профиля
@router.message(UserRegistration.first_name)
async def update_first_name(message: types.Message, state: FSMContext):
    data = await state.get_data()
    edit_mode = data.get("edit_mode", False)
    
    if edit_mode:
        # Добавляем эффект набора текста
        await message.bot.send_chat_action(message.from_user.id, "typing")
        
        # Импортируем asyncio для задержки
        import asyncio
        await asyncio.sleep(0.5)
        
        db = next(get_db())
        user = get_user_by_tg_id(db, message.from_user.id)
        update_user_profile(db, user, first_name=message.text)
        
        await message.answer(f"Имя успешно обновлено на: {message.text}")
        await message.answer("Хочешь изменить что-то еще?", reply_markup=get_profile_edit_keyboard())
        await state.clear()
    else:
        # Стандартная обработка для регистрации
        await state.update_data(first_name=message.text)
        await message.answer("Отлично! Сколько тебе лет?")
        await state.set_state(UserRegistration.age)

@router.message(UserRegistration.age)
async def update_age(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Пожалуйста, введи возраст числом.")
        return
    
    age = int(message.text)
    if age < 18 or age > 100:
        await message.answer("Возраст должен быть от 18 до 100 лет.")
        return
    
    data = await state.get_data()
    edit_mode = data.get("edit_mode", False)
    
    if edit_mode:
        # Добавляем эффект набора текста
        await message.bot.send_chat_action(message.from_user.id, "typing")
        
        # Импортируем asyncio для задержки
        import asyncio
        await asyncio.sleep(0.5)
        
        db = next(get_db())
        user = get_user_by_tg_id(db, message.from_user.id)
        update_user_profile(db, user, age=age)
        
        await message.answer(f"Возраст успешно обновлен на: {age}")
        await message.answer("Хочешь изменить что-то еще?", reply_markup=get_profile_edit_keyboard())
        await state.clear()
    else:
        # Стандартная обработка для регистрации
        await state.update_data(age=age)
        await message.answer("Укажи свой пол:", reply_markup=get_gender_inline_keyboard())
        await state.set_state(UserRegistration.gender)

@router.message(UserRegistration.gender)
async def update_gender(message: types.Message, state: FSMContext):
    data = await state.get_data()
    edit_mode = data.get("edit_mode", False)
    
    if edit_mode:
        # Добавляем эффект набора текста
        await message.bot.send_chat_action(message.from_user.id, "typing")
        
        # Импортируем asyncio для задержки
        import asyncio
        await asyncio.sleep(0.5)
        
        db = next(get_db())
        user = get_user_by_tg_id(db, message.from_user.id)
        update_user_profile(db, user, gender=message.text)
        
        await message.answer(f"Пол успешно обновлен на: {message.text}")
        await message.answer("Хочешь изменить что-то еще?", reply_markup=get_profile_edit_keyboard())
        await state.clear()
    else:
        # Стандартная обработка для регистрации
        await state.update_data(gender=message.text)
        await message.answer("Укажи свою ориентацию:", reply_markup=get_orientation_inline_keyboard())
        await state.set_state(UserRegistration.orientation)

@router.message(UserRegistration.orientation)
async def update_orientation(message: types.Message, state: FSMContext):
    data = await state.get_data()
    edit_mode = data.get("edit_mode", False)
    
    if edit_mode:
        # Добавляем эффект набора текста
        await message.bot.send_chat_action(message.from_user.id, "typing")
        
        # Импортируем asyncio для задержки
        import asyncio
        await asyncio.sleep(0.5)
        
        db = next(get_db())
        user = get_user_by_tg_id(db, message.from_user.id)
        update_user_profile(db, user, orientation=message.text)
        
        await message.answer(f"Ориентация успешно обновлена на: {message.text}")
        await message.answer("Хочешь изменить что-то еще?", reply_markup=get_profile_edit_keyboard())
        await state.clear()
    else:
        # Стандартная обработка для регистрации
        await state.update_data(orientation=message.text)
        await message.answer("В каком городе ты находишься?")
        await state.set_state(UserRegistration.city)

@router.message(UserRegistration.city)
async def update_city(message: types.Message, state: FSMContext):
    data = await state.get_data()
    edit_mode = data.get("edit_mode", False)
    
    if edit_mode:
        # Добавляем эффект набора текста
        await message.bot.send_chat_action(message.from_user.id, "typing")
        
        # Импортируем asyncio для задержки
        import asyncio
        await asyncio.sleep(0.5)
        
        db = next(get_db())
        user = get_user_by_tg_id(db, message.from_user.id)
        update_user_profile(db, user, city=message.text)
        
        await message.answer(f"Город успешно обновлен на: {message.text}")
        await message.answer("Хочешь изменить что-то еще?", reply_markup=get_profile_edit_keyboard())
        await state.clear()
    else:
        # Стандартная обработка для регистрации
        await state.update_data(city=message.text)
        await message.answer("Расскажи немного о себе (твои интересы, хобби и т.д.):")
        await state.set_state(UserRegistration.bio)

@router.message(UserRegistration.bio)
async def update_bio(message: types.Message, state: FSMContext):
    data = await state.get_data()
    edit_mode = data.get("edit_mode", False)
    
    if edit_mode:
        # Добавляем эффект набора текста
        await message.bot.send_chat_action(message.from_user.id, "typing")
        
        # Импортируем asyncio для задержки
        import asyncio
        await asyncio.sleep(0.5)
        
        db = next(get_db())
        user = get_user_by_tg_id(db, message.from_user.id)
        update_user_profile(db, user, bio=message.text)
        
        await message.answer("Информация о себе успешно обновлена")
        await message.answer("Хочешь изменить что-то еще?", reply_markup=get_profile_edit_keyboard())
        await state.clear()
    else:
        # Стандартная обработка для регистрации
        await state.update_data(bio=message.text)
        await message.answer("Отправь свою фотографию:")
        await state.set_state(UserRegistration.photo)

@router.message(UserRegistration.photo, F.photo)
async def update_photo(message: types.Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    data = await state.get_data()
    edit_mode = data.get("edit_mode", False)
    
    if edit_mode:
        # Добавляем эффект загрузки фото
        await message.bot.send_chat_action(message.from_user.id, "upload_photo")
        
        # Импортируем asyncio для задержки
        import asyncio
        await asyncio.sleep(1.0)
        
        db = next(get_db())
        user = get_user_by_tg_id(db, message.from_user.id)
        update_user_profile(db, user, photo_id=photo_id)
        
        await message.answer("Фотография успешно обновлена")
        await message.answer("Хочешь изменить что-то еще?", reply_markup=get_profile_edit_keyboard())
        await state.clear()
    else:
        # Стандартная обработка для регистрации
        await state.update_data(photo_id=photo_id)
        await message.answer("Укажи свои интересы через запятую (например: спорт, музыка, путешествия):")
        await state.set_state(UserRegistration.tags)

@router.message(UserRegistration.photo)
async def process_invalid_photo(message: types.Message):
    await message.answer("Пожалуйста, отправь фотографию.")

@router.message(UserRegistration.tags)
async def update_tags(message: types.Message, state: FSMContext):
    data = await state.get_data()
    edit_mode = data.get("edit_mode", False)
    
    if edit_mode:
        # Добавляем эффект набора текста
        await message.bot.send_chat_action(message.from_user.id, "typing")
        
        # Импортируем asyncio для задержки
        import asyncio
        await asyncio.sleep(0.5)
        
        db = next(get_db())
        user = get_user_by_tg_id(db, message.from_user.id)
        update_user_profile(db, user, tags=message.text)
        
        await message.answer(f"Интересы успешно обновлены на: {message.text}")
        await message.answer("Хочешь изменить что-то еще?", reply_markup=get_profile_edit_keyboard())
        await state.clear()
    else:
        # Стандартная обработка для регистрации
        await state.update_data(tags=message.text)
        
        # Get all data from state
        data = await state.get_data()
        
        # Save all data to database
        db = next(get_db())
        user = get_user_by_tg_id(db, message.from_user.id)
        
        # Добавляем эффект набора текста
        await message.bot.send_chat_action(message.from_user.id, "typing")
        
        # Импортируем asyncio для задержки
        import asyncio
        await asyncio.sleep(1.0)
        
        # Обновляем только те поля, которые есть в данных
        update_params = {}
        for field in ['first_name', 'age', 'gender', 'orientation', 'city', 'bio', 'photo_id', 'tags']:
            if field in data:
                update_params[field] = data[field]
        
        update_user_profile(db=db, user=user, **update_params)
        
        await message.answer(
            "Отлично! Твой профиль заполнен. Теперь ты можешь начать общение.",
            reply_markup=get_main_inline_keyboard()
        )
        await state.clear()

@router.message(F.text == "ℹ️ Помощь")
@router.message(Command("help"))
@router.callback_query(F.data == "help")
async def cmd_help(message_or_callback: types.Message | types.CallbackQuery):
    # Определяем, это сообщение или callback
    is_callback = isinstance(message_or_callback, types.CallbackQuery)
    if is_callback:
        await message_or_callback.answer()
        message = message_or_callback.message
        bot = message_or_callback.bot
        user_id = message_or_callback.from_user.id
    else:
        message = message_or_callback
        bot = message.bot
        user_id = message.from_user.id
    
    # Добавляем эффект набора текста
    await bot.send_chat_action(user_id, "typing")
    
    # Импортируем asyncio для задержки
    import asyncio
    await asyncio.sleep(1.0)
    
    help_text = (
        "🤖 Бот для анонимных знакомств\n\n"
        "Команды:\n"
        "/start - Начать работу с ботом\n"
        "🔍 Найти собеседника - Поиск анонимного собеседника\n"
        "👤 Мой профиль - Просмотр своего профиля\n"
        "ℹ️ Помощь - Показать это сообщение\n\n"
        "В анонимном чате:\n"
        "👋 Раскрыть личность - Отправить запрос на раскрытие личности\n"
        "❌ Завершить чат - Завершить текущий чат\n\n"
        "Статус активности:\n"
        "🟢 Активен - Другие пользователи могут найти тебя\n"
        "🔴 Неактивен - Ты скрыт от поиска"
    )
    
    await message.answer(help_text)
    
    # Добавляем небольшую задержку перед отправкой кнопок
    await bot.send_chat_action(user_id, "typing")
    await asyncio.sleep(0.5)
    
    await message.answer("Выберите раздел для получения подробной информации:", reply_markup=get_help_keyboard())
    await message.answer("Вернуться в главное меню:", reply_markup=get_main_inline_keyboard())

@router.callback_query(F.data.startswith("help_"))
async def process_help_sections(callback: types.CallbackQuery):
    section = callback.data.split("_")[1]
    
    # Добавляем эффект набора текста
    await callback.bot.send_chat_action(callback.from_user.id, "typing")
    
    # Импортируем asyncio для задержки
    import asyncio
    await asyncio.sleep(1.0)
    
    help_sections = {
        "usage": (
            "❓ Как пользоваться ботом\n\n"
            "1. Заполни свой профиль при первом запуске\n"
            "2. Используй кнопку '🔍 Найти собеседника' для поиска анонимного чата\n"
            "3. Общайся анонимно с собеседником\n"
            "4. При желании можешь раскрыть свою личность или завершить чат\n"
            "5. Редактируй свой профиль в любое время через раздел '👤 Мой профиль'\n"
            "6. Управляй своей видимостью с помощью статуса активности"
        ),
        "search": (
            "🔍 Поиск собеседника\n\n"
            "Нажми на кнопку '🔍 Найти собеседника' в главном меню.\n"
            "Бот будет искать свободного пользователя для анонимного общения.\n"
            "Когда собеседник будет найден, вы сможете начать общение.\n"
            "Если собеседник не найден сразу, бот продолжит поиск в фоновом режиме.\n\n"
            "Важно: Только пользователи со статусом 🟢 Активен могут быть найдены."
        ),
        "profile": (
            "👤 Профиль\n\n"
            "В разделе 'Мой профиль' ты можешь:\n"
            "- Просмотреть свои данные\n"
            "- Редактировать любую информацию о себе\n"
            "- Обновить фотографию\n"
            "- Изменить статус активности\n\n"
            "Статус активности:\n"
            "🟢 Активен - Другие пользователи могут найти тебя\n"
            "🔴 Неактивен - Ты скрыт от поиска\n\n"
            "Чем подробнее заполнен твой профиль, тем больше шансов найти интересного собеседника!"
        ),
        "chat": (
            "💬 Анонимный чат\n\n"
            "В чате ты можешь:\n"
            "- Отправлять текстовые сообщения\n"
            "- Делиться фото, видео, голосовыми сообщениями\n"
            "- Отправлять стикеры\n\n"
            "Кнопки управления чатом:\n"
            "👋 Раскрыть личность - отправляет запрос собеседнику на раскрытие личности\n"
            "❌ Завершить чат - завершает текущий чат"
        )
    }
    
    await callback.answer()
    await callback.message.answer(help_sections[section])
    
    # Добавляем небольшую задержку перед отправкой кнопок
    await callback.bot.send_chat_action(callback.from_user.id, "typing")
    await asyncio.sleep(0.5)
    
    await callback.message.answer("Вернуться к разделам помощи:", reply_markup=get_help_keyboard())
    await callback.message.answer("Вернуться в главное меню:", reply_markup=get_main_inline_keyboard())