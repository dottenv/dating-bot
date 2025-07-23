from aiogram import types, Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardRemove, ContentType

from database.db import get_db
from database.models import User
from services.user_service import get_user_by_tg_id
from services.chat_service import (
    find_available_chat_partner, create_chat, get_active_chat,
    end_chat, create_deanon_request, get_deanon_request, update_deanon_approval
)
from keyboards.reply import get_main_keyboard, get_chat_keyboard, get_deanon_keyboard
from states.user_states import AnonymousChatting

router = Router()

# Поиск собеседника
@router.message(F.text == "🔍 Найти собеседника")
async def cmd_find_chat(message: types.Message, state: FSMContext):
    await state.clear()
    db = next(get_db())
    user = get_user_by_tg_id(db, message.from_user.id)

    if not user:
        await message.answer("Пожалуйста, сначала зарегистрируйтесь с помощью команды /start")
        return

    active_chat = get_active_chat(db, user.id)
    if active_chat:
        await message.answer(
            "Ты уже находишься в чате. Используй клавиатуру для управления.",
            reply_markup=get_chat_keyboard()
        )
        await state.set_state(AnonymousChatting.chatting)
        return

    partner = find_available_chat_partner(db, user.id)
    if partner:
        chat = create_chat(db, user.id, partner.id)
        await message.answer(
            "Собеседник найден! Теперь вы можете общаться анонимно.",
            reply_markup=get_chat_keyboard()
        )
        bot = message.bot
        await bot.send_message(
            partner.tg_id,
            "Собеседник найден! Теперь вы можете общаться анонимно.",
            reply_markup=get_chat_keyboard()
        )
        await state.set_state(AnonymousChatting.chatting)
        await state.update_data(chat_id=chat.id, partner_id=partner.id)
    else:
        await message.answer(
            "Ищем собеседника... Пожалуйста, подожди.",
            reply_markup=ReplyKeyboardRemove()
        )
        await state.set_state(AnonymousChatting.waiting)

# Сообщения в чате
@router.message(AnonymousChatting.chatting, ~F.text.in_(["👋 Раскрыть личность", "❌ Завершить чат"]))
async def process_chat_message(message: types.Message, state: FSMContext):
    db = next(get_db())
    user = get_user_by_tg_id(db, message.from_user.id)
    chat = get_active_chat(db, user.id)
    if not chat:
        await message.answer(
            "У тебя нет активного чата. Хочешь найти собеседника?",
            reply_markup=get_main_keyboard()
        )
        await state.clear()
        return

    partner_id = chat.user2_id if chat.user1_id == user.id else chat.user1_id
    partner = db.query(User).filter(User.id == partner_id).first()
    if not partner:
        await message.answer("Произошла ошибка. Чат завершен.")
        end_chat(db, chat.id)
        await state.clear()
        return

    if message.content_type == ContentType.TEXT:
        await message.bot.send_message(partner.tg_id, message.text)
    elif message.content_type == ContentType.PHOTO:
        await message.bot.send_photo(
            partner.tg_id,
            message.photo[-1].file_id,
            caption=message.caption
        )
    elif message.content_type == ContentType.VIDEO:
        await message.bot.send_video(
            partner.tg_id,
            message.video.file_id,
            caption=message.caption
        )
    elif message.content_type == ContentType.VOICE:
        await message.bot.send_voice(
            partner.tg_id,
            message.voice.file_id
        )
    elif message.content_type == ContentType.DOCUMENT:
        await message.bot.send_document(
            partner.tg_id,
            message.document.file_id,
            caption=message.caption
        )
    elif message.content_type == ContentType.AUDIO:
        await message.bot.send_audio(
            partner.tg_id,
            message.audio.file_id,
            caption=message.caption
        )
    elif message.content_type == ContentType.STICKER:
        await message.bot.send_sticker(
            partner.tg_id,
            message.sticker.file_id
        )

# Завершение чата
@router.message(AnonymousChatting.chatting, F.text == "❌ Завершить чат")
async def cmd_end_chat(message: types.Message, state: FSMContext):
    db = next(get_db())
    user = get_user_by_tg_id(db, message.from_user.id)
    chat = get_active_chat(db, user.id)
    if not chat:
        await message.answer(
            "У тебя нет активного чата.",
            reply_markup=get_main_keyboard()
        )
        await state.clear()
        return

    partner_id = chat.user2_id if chat.user1_id == user.id else chat.user1_id
    partner = db.query(User).filter(User.id == partner_id).first()
    end_chat(db, chat.id)
    await message.answer(
        "Чат завершен. Хочешь найти нового собеседника?",
        reply_markup=get_main_keyboard()
    )
    if partner:
        await message.bot.send_message(
            partner.tg_id,
            "Собеседник завершил чат. Хочешь найти нового собеседника?",
            reply_markup=get_main_keyboard()
        )
    await state.clear()

# Запрос на раскрытие личности
@router.message(AnonymousChatting.chatting, F.text == "👋 Раскрыть личность")
async def cmd_deanon_request(message: types.Message, state: FSMContext):
    db = next(get_db())
    user = get_user_by_tg_id(db, message.from_user.id)
    chat = get_active_chat(db, user.id)
    if not chat:
        await message.answer(
            "У тебя нет активного чата.",
            reply_markup=get_main_keyboard()
        )
        await state.clear()
        return

    deanon_request = get_deanon_request(db, chat.id)
    if not deanon_request:
        deanon_request = create_deanon_request(db, chat.id)

    partner_id = chat.user2_id if chat.user1_id == user.id else chat.user1_id
    partner = db.query(User).filter(User.id == partner_id).first()
    user_position = 1 if chat.user1_id == user.id else 2
    update_deanon_approval(db, deanon_request.id, user_position, True)

    await message.answer(
        "Ты отправил запрос на раскрытие личности. Ожидаем ответа собеседника.",
        reply_markup=get_chat_keyboard()
    )
    if partner:
        await message.bot.send_message(
            partner.tg_id,
            "Собеседник хочет раскрыть личность. Ты согласен?",
            reply_markup=get_deanon_keyboard()
        )

# Кнопки согласия/отказа на раскрытие личности
@router.message(AnonymousChatting.chatting, F.text.in_(["✅ Согласен", "❌ Отказываюсь"]))
async def process_deanon_buttons(message: types.Message, state: FSMContext):
    await process_deanon_response(message, state)

# Ответ на запрос раскрытия личности
@router.message(AnonymousChatting.deanon_request, F.text.in_(["✅ Согласен", "❌ Отказываюсь"]))
async def process_deanon_response(message: types.Message, state: FSMContext):
    db = next(get_db())
    user = get_user_by_tg_id(db, message.from_user.id)
    chat = get_active_chat(db, user.id)
    if not chat:
        await message.answer(
            "У тебя нет активного чата.",
            reply_markup=get_main_keyboard()
        )
        await state.clear()
        return

    partner_id = chat.user2_id if chat.user1_id == user.id else chat.user1_id
    partner = db.query(User).filter(User.id == partner_id).first()
    user_position = 1 if chat.user1_id == user.id else 2
    deanon_request = get_deanon_request(db, chat.id)
    if not deanon_request:
        await message.answer(
            "Запрос на раскрытие личности не найден.",
            reply_markup=get_chat_keyboard()
        )
        await state.set_state(AnonymousChatting.chatting)
        return

    if message.text == "✅ Согласен":
        update_deanon_approval(db, deanon_request.id, user_position, True)
        # Получаем обновленный объект из базы
        deanon_request = get_deanon_request(db, chat.id)
        if deanon_request.user1_approved and deanon_request.user2_approved:
            user1 = db.query(User).filter(User.id == chat.user1_id).first()
            user2 = db.query(User).filter(User.id == chat.user2_id).first()

            profile_caption_1 = (
                f"Профиль собеседника:\n"
                f"Имя: {user1.first_name}\n"
                f"Возраст: {user1.age}\n"
                f"Город: {user1.city}\n"
                f"О себе: {user1.bio}\n"
                f"Интересы: {user1.tags}\n"
                f"Telegram: [Открыть профиль](tg://user?id={user1.tg_id})"
            )
            profile_caption_2 = (
                f"Профиль собеседника:\n"
                f"Имя: {user2.first_name}\n"
                f"Возраст: {user2.age}\n"
                f"Город: {user2.city}\n"
                f"О себе: {user2.bio}\n"
                f"Интересы: {user2.tags}\n"
                f"Telegram: [Открыть профиль](tg://user?id={user2.tg_id})"
            )

            # user1 -> user2
            if user1.photo_id:
                await message.bot.send_photo(
                    user2.tg_id,
                    user1.photo_id,
                    caption=profile_caption_1,
                    parse_mode="Markdown"
                )
            else:
                await message.bot.send_message(
                    user2.tg_id,
                    profile_caption_1,
                    parse_mode="Markdown"
                )
            # user2 -> user1
            if user2.photo_id:
                await message.bot.send_photo(
                    user1.tg_id,
                    user2.photo_id,
                    caption=profile_caption_2,
                    parse_mode="Markdown"
                )
            else:
                await message.bot.send_message(
                    user1.tg_id,
                    profile_caption_2,
                    parse_mode="Markdown"
                )

            await message.bot.send_message(
                user1.tg_id,
                "Личности раскрыты! Теперь вы можете продолжить общение.",
                reply_markup=get_chat_keyboard()
            )
            if user1.tg_id != message.from_user.id:
                await message.bot.send_message(
                    user2.tg_id,
                    "Личности раскрыты! Теперь вы можете продолжить общение.",
                    reply_markup=get_chat_keyboard()
                )
        else:
            await message.answer(
                "Ты согласился на раскрытие личности. Ожидаем ответа собеседника.",
                reply_markup=get_chat_keyboard()
            )
    else:
        update_deanon_approval(db, deanon_request.id, user_position, False)
        await message.answer(
            "Ты отказался от раскрытия личности.",
            reply_markup=get_chat_keyboard()
        )
        if partner:
            await message.bot.send_message(
                partner.tg_id,
                "Собеседник отказался от раскрытия личности.",
                reply_markup=get_chat_keyboard()
            )
    await state.set_state(AnonymousChatting.chatting)

# Установка состояния для второго пользователя при старте чата
@router.message(F.text == "Собеседник найден! Теперь вы можете общаться анонимно.")
async def partner_chat_start(message: types.Message, state: FSMContext):
    db = next(get_db())
    user = get_user_by_tg_id(db, message.from_user.id)
    chat = get_active_chat(db, user.id)
    if chat:
        await state.set_state(AnonymousChatting.chatting)
        partner_id = chat.user2_id if chat.user1_id == user.id else chat.user1_id
        await state.update_data(chat_id=chat.id, partner_id=partner_id)

# Гарантируем корректное состояние FSM для любого сообщения
@router.message()
async def ensure_chat_state(message: types.Message, state: FSMContext):
    db = next(get_db())
    user = get_user_by_tg_id(db, message.from_user.id)
    chat = get_active_chat(db, user.id)
    current_state = await state.get_state()
    if chat and current_state != AnonymousChatting.chatting:
        await state.set_state(AnonymousChatting.chatting)
        partner_id = chat.user2_id if chat.user1_id == user.id else chat.user1_id
        await state.update_data(chat_id=chat.id, partner_id=partner_id)
        # Можно сразу обработать это сообщение как чат, если хотите:
        await process_chat_message(message, state)
