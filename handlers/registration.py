from aiogram import types, Router, F
from aiogram.fsm.context import FSMContext

from database.db import get_db
from services.user_service import get_user_by_tg_id, update_user_profile
from keyboards.inline import (
    get_main_inline_keyboard, get_gender_inline_keyboard, 
    get_orientation_inline_keyboard
)
from states.user_states import UserRegistration

router = Router()

@router.message(UserRegistration.first_name)
async def process_first_name(message: types.Message, state: FSMContext):
    data = await state.get_data()
    edit_mode = data.get("edit_mode", False)
    
    if edit_mode:
        db = next(get_db())
        user = get_user_by_tg_id(db, message.from_user.id)
        update_user_profile(db, user, first_name=message.text)
        
        await message.answer(f"Имя успешно обновлено на: {message.text}")
        await message.answer("Хочешь изменить что-то еще?", reply_markup=get_profile_edit_keyboard())
        await state.clear()
    else:
        await state.update_data(first_name=message.text)
        await message.answer("Отлично! Сколько тебе лет?")
        await state.set_state(UserRegistration.age)

@router.message(UserRegistration.age)
async def process_age(message: types.Message, state: FSMContext):
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
        db = next(get_db())
        user = get_user_by_tg_id(db, message.from_user.id)
        update_user_profile(db, user, age=age)
        
        await message.answer(f"Возраст успешно обновлен на: {age}")
        await message.answer("Хочешь изменить что-то еще?", reply_markup=get_profile_edit_keyboard())
        await state.clear()
    else:
        await state.update_data(age=age)
        await message.answer("Укажи свой пол:", reply_markup=get_gender_inline_keyboard())
        await state.set_state(UserRegistration.gender)

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

@router.message(UserRegistration.gender)
async def process_gender(message: types.Message, state: FSMContext):
    data = await state.get_data()
    edit_mode = data.get("edit_mode", False)
    
    if edit_mode:
        db = next(get_db())
        user = get_user_by_tg_id(db, message.from_user.id)
        update_user_profile(db, user, gender=message.text)
        
        await message.answer(f"Пол успешно обновлен на: {message.text}")
        await message.answer("Хочешь изменить что-то еще?", reply_markup=get_profile_edit_keyboard())
        await state.clear()
    else:
        await state.update_data(gender=message.text)
        await message.answer("Укажи свою ориентацию:", reply_markup=get_orientation_inline_keyboard())
        await state.set_state(UserRegistration.orientation)

@router.message(UserRegistration.orientation)
async def process_orientation(message: types.Message, state: FSMContext):
    data = await state.get_data()
    edit_mode = data.get("edit_mode", False)
    
    if edit_mode:
        db = next(get_db())
        user = get_user_by_tg_id(db, message.from_user.id)
        update_user_profile(db, user, orientation=message.text)
        
        await message.answer(f"Ориентация успешно обновлена на: {message.text}")
        await message.answer("Хочешь изменить что-то еще?", reply_markup=get_profile_edit_keyboard())
        await state.clear()
    else:
        await state.update_data(orientation=message.text)
        await message.answer("В каком городе ты находишься?")
        await state.set_state(UserRegistration.city)

@router.message(UserRegistration.city)
async def process_city(message: types.Message, state: FSMContext):
    data = await state.get_data()
    edit_mode = data.get("edit_mode", False)
    
    if edit_mode:
        db = next(get_db())
        user = get_user_by_tg_id(db, message.from_user.id)
        update_user_profile(db, user, city=message.text)
        
        await message.answer(f"Город успешно обновлен на: {message.text}")
        await message.answer("Хочешь изменить что-то еще?", reply_markup=get_profile_edit_keyboard())
        await state.clear()
    else:
        await state.update_data(city=message.text)
        await message.answer("Расскажи немного о себе (твои интересы, хобби и т.д.):")
        await state.set_state(UserRegistration.bio)

@router.message(UserRegistration.bio)
async def process_bio(message: types.Message, state: FSMContext):
    data = await state.get_data()
    edit_mode = data.get("edit_mode", False)
    
    if edit_mode:
        db = next(get_db())
        user = get_user_by_tg_id(db, message.from_user.id)
        update_user_profile(db, user, bio=message.text)
        
        await message.answer("Информация о себе успешно обновлена")
        await message.answer("Хочешь изменить что-то еще?", reply_markup=get_profile_edit_keyboard())
        await state.clear()
    else:
        await state.update_data(bio=message.text)
        await message.answer("Отправь свою фотографию:")
        await state.set_state(UserRegistration.photo)

@router.message(UserRegistration.photo, F.photo)
async def process_photo(message: types.Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    data = await state.get_data()
    edit_mode = data.get("edit_mode", False)
    
    if edit_mode:
        db = next(get_db())
        user = get_user_by_tg_id(db, message.from_user.id)
        update_user_profile(db, user, photo_id=photo_id)
        
        await message.answer("Фотография успешно обновлена")
        await message.answer("Хочешь изменить что-то еще?", reply_markup=get_profile_edit_keyboard())
        await state.clear()
    else:
        await state.update_data(photo_id=photo_id)
        await message.answer("Укажи свои интересы через запятую (например: спорт, музыка, путешествия):")
        await state.set_state(UserRegistration.tags)

@router.message(UserRegistration.photo)
async def process_invalid_photo(message: types.Message):
    await message.answer("Пожалуйста, отправь фотографию.")

@router.message(UserRegistration.tags)
async def process_tags(message: types.Message, state: FSMContext):
    data = await state.get_data()
    edit_mode = data.get("edit_mode", False)
    
    if edit_mode:
        db = next(get_db())
        user = get_user_by_tg_id(db, message.from_user.id)
        update_user_profile(db, user, tags=message.text)
        
        await message.answer(f"Интересы успешно обновлены на: {message.text}")
        await message.answer("Хочешь изменить что-то еще?", reply_markup=get_profile_edit_keyboard())
        await state.clear()
    else:
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
                update_params[field] = data[field]
        
        update_user_profile(db=db, user=user, **update_params)
        
        await message.answer(
            "Отлично! Твой профиль заполнен. Теперь ты можешь начать общение.",
            reply_markup=get_main_inline_keyboard()
        )
        await state.clear()

# Импортируем клавиатуры для обработчиков
from keyboards.inline import get_profile_edit_keyboard