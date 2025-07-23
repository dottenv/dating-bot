from aiogram import types, Router, F
from aiogram.fsm.context import FSMContext

from database.db import get_db
from services.user_service import get_user_by_tg_id, update_user_profile
from keyboards.reply import get_main_keyboard, get_gender_keyboard, get_orientation_keyboard
from states.user_states import UserRegistration

router = Router()

@router.message(UserRegistration.first_name)
async def process_first_name(message: types.Message, state: FSMContext):
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
    
    await state.update_data(age=age)
    
    await message.answer("Укажи свой пол:", reply_markup=get_gender_keyboard())
    await state.set_state(UserRegistration.gender)

@router.message(UserRegistration.gender)
async def process_gender(message: types.Message, state: FSMContext):
    await state.update_data(gender=message.text)
    
    await message.answer("Укажи свою ориентацию:", reply_markup=get_orientation_keyboard())
    await state.set_state(UserRegistration.orientation)

@router.message(UserRegistration.orientation)
async def process_orientation(message: types.Message, state: FSMContext):
    await state.update_data(orientation=message.text)
    
    await message.answer("В каком городе ты находишься?")
    await state.set_state(UserRegistration.city)

@router.message(UserRegistration.city)
async def process_city(message: types.Message, state: FSMContext):
    await state.update_data(city=message.text)
    
    await message.answer("Расскажи немного о себе (твои интересы, хобби и т.д.):")
    await state.set_state(UserRegistration.bio)

@router.message(UserRegistration.bio)
async def process_bio(message: types.Message, state: FSMContext):
    await state.update_data(bio=message.text)
    
    await message.answer("Отправь свою фотографию:")
    await state.set_state(UserRegistration.photo)

@router.message(UserRegistration.photo, F.photo)
async def process_photo(message: types.Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    await state.update_data(photo_id=photo_id)
    
    await message.answer("Укажи свои интересы через запятую (например: спорт, музыка, путешествия):")
    await state.set_state(UserRegistration.tags)

@router.message(UserRegistration.photo)
async def process_invalid_photo(message: types.Message):
    await message.answer("Пожалуйста, отправь фотографию.")

@router.message(UserRegistration.tags)
async def process_tags(message: types.Message, state: FSMContext):
    await state.update_data(tags=message.text)
    
    # Get all data from state
    data = await state.get_data()
    
    # Save all data to database
    db = next(get_db())
    user = get_user_by_tg_id(db, message.from_user.id)
    
    update_user_profile(
        db=db,
        user=user,
        first_name=data['first_name'],
        age=data['age'],
        gender=data['gender'],
        orientation=data['orientation'],
        city=data['city'],
        bio=data['bio'],
        photo_id=data['photo_id'],
        tags=data['tags']
    )
    
    await message.answer(
        "Отлично! Твой профиль заполнен. Теперь ты можешь начать общение.",
        reply_markup=get_main_keyboard()
    )
    await state.clear()