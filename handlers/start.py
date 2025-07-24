from aiogram import types, Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

from database.models import User, Profile
from states.registration import RegistrationStates
from keyboards.registration import (
    gender_keyboard, 
    orientation_keyboard, 
    dating_goal_keyboard,
    skip_keyboard,
    photo_source_keyboard
)
from keyboards.main import main_keyboard

router = Router()

@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    
    # Получаем данные пользователя
    user_data = {
        'tg_id': message.from_user.id,
        'username': message.from_user.username
    }
    
    user = await User.filter(tg_id=user_data['tg_id']).first()
    
    if user:
        # Проверяем, заполнен ли профиль
        profile = await Profile.filter(user=user).first()
        if profile and profile.profile_completed:
            await message.answer("С возвращением! Рады что вы вернулись :)", reply_markup=main_keyboard)
        else:
            await message.answer("Кажется, вы не заполнили свой профиль. Давайте сделаем это сейчас!")
            await start_registration(message, state, user)
    else:
        # Создаем нового пользователя
        user = await User.create(**user_data)
        await message.answer("Добро пожаловать! Давайте создадим ваш профиль.")
        await start_registration(message, state, user)

async def start_registration(message: types.Message, state: FSMContext, user):
    # Сохраняем ID пользователя в данных состояния
    await state.update_data(user_id=user.id)
    
    # Запрашиваем имя
    await message.answer("Как вас зовут?")
    await state.set_state(RegistrationStates.first_name)

@router.message(RegistrationStates.first_name)
async def process_first_name(message: types.Message, state: FSMContext):
    # Сохраняем имя
    await state.update_data(first_name=message.text)
    
    # Запрашиваем возраст
    await message.answer("Сколько вам лет?")
    await state.set_state(RegistrationStates.age)

@router.message(RegistrationStates.age)
async def process_age(message: types.Message, state: FSMContext):
    # Проверяем, что введено число
    if not message.text.isdigit():
        await message.answer("Пожалуйста, введите число.")
        return
    
    age = int(message.text)
    if age < 18 or age > 100:
        await message.answer("Возраст должен быть от 18 до 100 лет.")
        return
    
    # Сохраняем возраст
    await state.update_data(age=age)
    
    # Запрашиваем город
    await message.answer("В каком городе вы живете?", reply_markup=skip_keyboard)
    await state.set_state(RegistrationStates.city)

@router.message(RegistrationStates.city)
async def process_city(message: types.Message, state: FSMContext):
    if message.text != "Пропустить":
        await state.update_data(city=message.text)
    
    # Запрашиваем пол
    await message.answer("Укажите ваш пол:", reply_markup=gender_keyboard)
    await state.set_state(RegistrationStates.gender)

@router.message(RegistrationStates.gender)
async def process_gender(message: types.Message, state: FSMContext):
    await state.update_data(gender=message.text)
    
    # Запрашиваем ориентацию
    await message.answer("Укажите вашу ориентацию:", reply_markup=orientation_keyboard)
    await state.set_state(RegistrationStates.orientation)

@router.message(RegistrationStates.orientation)
async def process_orientation(message: types.Message, state: FSMContext):
    await state.update_data(orientation=message.text)
    
    # Запрашиваем цель знакомства
    await message.answer("Какова ваша цель знакомства?", reply_markup=dating_goal_keyboard)
    await state.set_state(RegistrationStates.dating_goal)

@router.message(RegistrationStates.dating_goal)
async def process_dating_goal(message: types.Message, state: FSMContext):
    await state.update_data(dating_goal=message.text)
    
    # Запрашиваем информацию о себе
    await message.answer("Расскажите немного о себе:", reply_markup=skip_keyboard)
    await state.set_state(RegistrationStates.about)

@router.message(RegistrationStates.about)
async def process_about(message: types.Message, state: FSMContext):
    if message.text != "Пропустить":
        await state.update_data(about=message.text)
    
    # Запрашиваем интересы
    await message.answer(
        "Укажите ваши интересы через запятую (например: музыка, спорт, книги):", 
        reply_markup=skip_keyboard
    )
    await state.set_state(RegistrationStates.tags)

@router.message(RegistrationStates.tags)
async def process_tags(message: types.Message, state: FSMContext):
    if message.text != "Пропустить":
        await state.update_data(tags=message.text)
    
    # Запрашиваем фото
    await message.answer(
        "Добавьте фото для вашей анкеты:", 
        reply_markup=photo_source_keyboard
    )
    await state.set_state(RegistrationStates.photo)

# Добавим новый обработчик для фото:
@router.message(RegistrationStates.photo, F.text == "Использовать фото профиля")
async def process_profile_photo(message: types.Message, state: FSMContext):
    # Получаем фото профиля пользователя
    user_profile_photos = await message.bot.get_user_profile_photos(message.from_user.id, limit=1)
    
    if user_profile_photos.total_count > 0:
        # Берем file_id первого фото профиля
        photo_id = user_profile_photos.photos[0][-1].file_id
        await state.update_data(photo_id=photo_id)
        await message.answer("Фото профиля успешно добавлено!")
        await complete_registration(message, state)
    else:
        await message.answer("У вас нет фото профиля. Пожалуйста, загрузите фото или пропустите этот шаг.")

@router.message(RegistrationStates.photo, F.text == "Загрузить фото")
async def request_upload_photo(message: types.Message):
    await message.answer("Пожалуйста, отправьте фото:")

@router.message(RegistrationStates.photo, F.photo)
async def process_uploaded_photo(message: types.Message, state: FSMContext):
    # Получаем file_id загруженного фото
    photo_id = message.photo[-1].file_id
    await state.update_data(photo_id=photo_id)
    await message.answer("Фото успешно загружено!")
    await complete_registration(message, state)

@router.message(RegistrationStates.photo, F.text == "Пропустить")
async def skip_photo(message: types.Message, state: FSMContext):
    await message.answer("Вы пропустили добавление фото.")
    await complete_registration(message, state)

# Выделим завершение регистрации в отдельную функцию:
async def complete_registration(message: types.Message, state: FSMContext):
    # Получаем все данные
    data = await state.get_data()
    user_id = data.pop('user_id')
    
    # Создаем или обновляем профиль
    user = await User.get(id=user_id)
    profile = await Profile.filter(user=user).first()
    
    if profile:
        # Обновляем существующий профиль
        await Profile.filter(id=profile.id).update(**data, profile_completed=True)
    else:
        # Создаем новый профиль
        await Profile.create(user=user, **data, profile_completed=True)
    
    # Завершаем регистрацию
    await message.answer(
        "Спасибо! Ваш профиль успешно создан.", 
        reply_markup=main_keyboard
    )
    await state.clear()

@router.message(F.text == "Профиль")
async def my_profile(message: types.Message):
    from handlers.profile import show_profile
    await show_profile(message)

@router.message(F.text == "Найти собеседника")
async def find_companion(message: types.Message, state: FSMContext):
    from handlers.chat import start_search
    await start_search(message, state)

@router.message(F.text == "🤖 AI-Ассистент")
async def ai_assistant_button(message: types.Message):
    from handlers.assistant import cmd_assistant
    await cmd_assistant(message)

@router.message(F.text == "Настройки")
async def settings(message: types.Message):
    await message.answer("Настройки в разработке")

# Обработчики команд
@router.message(Command("find"))
async def cmd_find(message: types.Message, state: FSMContext):
    from handlers.chat import start_search
    await start_search(message, state)

@router.message(Command("cancel"))
async def cmd_cancel(message: types.Message, state: FSMContext):
    from handlers.chat import active_chats, search_queue
    
    user_id = message.from_user.id
    
    # Убираем из очереди поиска
    for tier_queue in search_queue.values():
        if user_id in tier_queue:
            tier_queue.remove(user_id)
    
    await state.clear()
    await message.answer("Поиск отменен")

@router.message(Command("end"))
async def cmd_end(message: types.Message, state: FSMContext):
    from handlers.chat import active_chats
    
    user_id = message.from_user.id
    partner_id = active_chats.get(user_id)
    
    if partner_id:
        del active_chats[user_id]
        del active_chats[partner_id]
        
        await message.answer("Чат завершен")
        await message.bot.send_message(partner_id, "Собеседник завершил чат")
    else:
        await message.answer("Нет активного чата")
    
    await state.clear()

@router.message(Command("report"))
async def cmd_report(message: types.Message):
    from handlers.chat import active_chats
    
    user_id = message.from_user.id
    partner_id = active_chats.get(user_id)
    
    if partner_id:
        await message.answer("Используйте кнопку 'Пожаловаться' в чате")
    else:
        await message.answer("Нет активного чата")

@router.message(Command("help"))
async def cmd_help(message: types.Message):
    from handlers.assistant import cmd_assistant
    await cmd_assistant(message)

@router.message(Command("stats"))
async def cmd_stats(message: types.Message):
    user = await User.filter(tg_id=message.from_user.id).first()
    if not user:
        await message.answer("Пройдите регистрацию /start")
        return
    
    total_users = await User.all().count()
    active_users = await User.filter(is_active=True).count()
    
    from handlers.chat import active_chats, search_queue
    in_chat = len(active_chats) // 2
    in_queue = sum(len(queue) for queue in search_queue.values())
    
    stats_text = f"📊 **Ваша статистика:**\n\n"
    stats_text += f"🎆 Рейтинг: {user.raiting}\n"
    stats_text += f"👤 Статус: {'Premium' if user.is_premium else 'Обычный'}\n\n"
    stats_text += f"🌍 **Общая статистика:**\n\n"
    stats_text += f"👥 Всего пользователей: {total_users}\n"
    stats_text += f"✅ Активных: {active_users}\n"
    stats_text += f"💬 В чате: {in_chat}\n"
    stats_text += f"🔍 В поиске: {in_queue}"
    
    await message.answer(stats_text, parse_mode="Markdown")

@router.message(Command("settings"))
async def cmd_settings(message: types.Message):
    user = await User.filter(tg_id=message.from_user.id).first()
    if not user:
        await message.answer("Пройдите регистрацию /start")
        return
    
    from keyboards.profile import create_keyboard
    kb = create_keyboard([
        ("🔔 Уведомления", "settings_notifications"),
        ("🚫 Черный список", "settings_blacklist"),
        ("🎯 Предпочтения", "settings_preferences"),
        ("📊 Приватность", "settings_privacy")
    ])
    
    await message.answer("⚙️ Настройки (в разработке):", reply_markup=kb)