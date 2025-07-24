from aiogram import types, Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database.models import User, Profile
from keyboards.profile import create_keyboard

router = Router()

class ProfileStates(StatesGroup):
    editing = State()
    photo_upload = State()

async def get_profile_text(profile, user):
    text = f"{profile.first_name}, {profile.age or 'не указан'} лет\n"
    text += f"{profile.city or 'город не указан'}\n"
    text += f"{profile.gender or 'пол не указан'} • {profile.orientation or 'ориентация не указана'}\n"
    text += f"Цель: {profile.dating_goal or 'не указана'}\n\n"
    if profile.about:
        text += f"{profile.about}\n\n"
    if profile.tags:
        text += f"Интересы: {profile.tags}\n\n"
    text += f"Статус: {'скрыта' if not user.is_active else 'активна'}"
    return text

async def show_profile(message_or_callback, edit=False):
    user_id = message_or_callback.from_user.id
    user = await User.filter(tg_id=user_id).first()
    
    if not user:
        text = "Сначала пройдите регистрацию /start"
        kb = None
    else:
        profile = await Profile.filter(user=user).first()
        if not profile:
            text = "Профиль не найден"
            kb = None
        else:
            text = await get_profile_text(profile, user)
            kb = create_keyboard([
                ("Редактировать", "edit"),
                ("Изменить фото", "photo"),
                ("Скрыть" if user.is_active else "Показать", "toggle")
            ])
    
    if edit and hasattr(message_or_callback, 'message'):
        try:
            if profile and profile.photo_id:
                await message_or_callback.message.edit_caption(caption=text, reply_markup=kb)
            else:
                await message_or_callback.message.edit_text(text, reply_markup=kb)
        except Exception:
            # Если не удалось редактировать, просто отвечаем
            await message_or_callback.answer("Профиль обновлен!")
    else:
        if profile and profile.photo_id:
            await message_or_callback.bot.send_photo(
                user_id, profile.photo_id, caption=text, reply_markup=kb
            )
        else:
            await message_or_callback.answer(text, reply_markup=kb)

@router.message(Command("profile"))
async def cmd_profile(message: types.Message):
    await show_profile(message)

@router.callback_query(F.data == "back")
async def back_to_profile(callback: types.CallbackQuery):
    await show_profile(callback, edit=True)

@router.callback_query(F.data == "edit")
async def edit_menu(callback: types.CallbackQuery):
    kb = create_keyboard([
        ("Имя", "edit_name"), ("Возраст", "edit_age"),
        ("Город", "edit_city"), ("О себе", "edit_about"),
        ("Интересы", "edit_tags"),
        ("Назад", "back")
    ])
    
    try:
        if callback.message.photo:
            await callback.message.edit_caption(caption="Что изменить?", reply_markup=kb)
        else:
            await callback.message.edit_text("Что изменить?", reply_markup=kb)
    except Exception:
        await callback.answer("Меню редактирования")

@router.callback_query(F.data.startswith("edit_"))
async def start_edit(callback: types.CallbackQuery, state: FSMContext):
    field = callback.data.split("_")[1]
    fields = {"name": "имя", "age": "возраст", "city": "город", "about": "о себе", "tags": "интересы"}
    
    await state.update_data(field=field)
    
    try:
        if callback.message.photo:
            await callback.message.edit_caption(caption=f"Введите новое значение для '{fields[field]}':", reply_markup=None)
        else:
            await callback.message.edit_text(f"Введите новое значение для '{fields[field]}':", reply_markup=None)
    except Exception:
        await callback.answer(f"Введите новое значение для '{fields[field]}'")
    
    await state.set_state(ProfileStates.editing)

@router.message(ProfileStates.editing)
async def process_edit(message: types.Message, state: FSMContext):
    data = await state.get_data()
    field = data["field"]
    
    user = await User.filter(tg_id=message.from_user.id).first()
    profile = await Profile.filter(user=user).first()
    
    update_data = {}
    if field == "name":
        update_data["first_name"] = message.text
    elif field == "age":
        if not message.text.isdigit() or not (18 <= int(message.text) <= 100):
            await message.answer("Возраст должен быть числом от 18 до 100")
            return
        update_data["age"] = int(message.text)
    elif field == "city":
        update_data["city"] = message.text
    elif field == "about":
        update_data["about"] = message.text
    elif field == "tags":
        update_data["tags"] = message.text
    
    await Profile.filter(id=profile.id).update(**update_data)
    await message.answer("Сохранено!")
    await show_profile(message)
    await state.clear()

@router.callback_query(F.data == "photo")
async def photo_menu(callback: types.CallbackQuery):
    kb = create_keyboard([
        ("Загрузить новое", "photo_upload"),
        ("Из профиля Telegram", "photo_profile"),
        ("Удалить фото", "photo_delete"),
        ("Назад", "back")
    ])
    
    try:
        if callback.message.photo:
            await callback.message.edit_caption(caption="Управление фото:", reply_markup=kb)
        else:
            await callback.message.edit_text("Управление фото:", reply_markup=kb)
    except Exception:
        await callback.answer("Меню фото")

@router.callback_query(F.data == "photo_upload")
async def request_photo(callback: types.CallbackQuery, state: FSMContext):
    try:
        if callback.message.photo:
            await callback.message.edit_caption(caption="Отправьте новое фото:", reply_markup=None)
        else:
            await callback.message.edit_text("Отправьте новое фото:", reply_markup=None)
    except Exception:
        await callback.answer("Отправьте новое фото")
    
    await state.set_state(ProfileStates.photo_upload)

@router.message(ProfileStates.photo_upload, F.photo)
async def process_photo(message: types.Message, state: FSMContext):
    user = await User.filter(tg_id=message.from_user.id).first()
    profile = await Profile.filter(user=user).first()
    
    await Profile.filter(id=profile.id).update(photo_id=message.photo[-1].file_id)
    await message.answer("Фото обновлено!")
    await show_profile(message)
    await state.clear()

@router.callback_query(F.data == "photo_profile")
async def use_profile_photo(callback: types.CallbackQuery):
    photos = await callback.bot.get_user_profile_photos(callback.from_user.id, limit=1)
    
    if photos.total_count == 0:
        kb = create_keyboard([("Назад", "photo")], row_width=1)
        try:
            if callback.message.photo:
                await callback.message.edit_caption(caption="У вас нет фото профиля", reply_markup=kb)
            else:
                await callback.message.edit_text("У вас нет фото профиля", reply_markup=kb)
        except Exception:
            await callback.answer("У вас нет фото профиля")
        return
    
    user = await User.filter(tg_id=callback.from_user.id).first()
    profile = await Profile.filter(user=user).first()
    
    await Profile.filter(id=profile.id).update(photo_id=photos.photos[0][-1].file_id)
    await callback.answer("Фото установлено!")
    await show_profile(callback, edit=True)

@router.callback_query(F.data == "photo_delete")
async def delete_photo(callback: types.CallbackQuery):
    user = await User.filter(tg_id=callback.from_user.id).first()
    profile = await Profile.filter(user=user).first()
    
    await Profile.filter(id=profile.id).update(photo_id=None)
    await callback.answer("Фото удалено!")
    await show_profile(callback, edit=True)

@router.callback_query(F.data == "toggle")
async def toggle_visibility(callback: types.CallbackQuery):
    user = await User.filter(tg_id=callback.from_user.id).first()
    new_status = not user.is_active
    
    await User.filter(id=user.id).update(is_active=new_status)
    status = "показана" if new_status else "скрыта"
    
    await callback.answer(f"Анкета {status}!")
    await show_profile(callback, edit=True)