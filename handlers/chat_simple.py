import asyncio
import datetime

from aiogram import types, Router, F
from aiogram.fsm.context import FSMContext

from database.db import get_db
from database.models import User
from services.user_service import get_user_by_tg_id
from services.chat_service import (
    find_available_chat_partner, create_chat, get_active_chat,
    end_chat, create_deanon_request, get_deanon_request, update_deanon_approval,
    increment_messages_count
)
from keyboards.inline import get_chat_inline_keyboard, get_deanon_keyboard, get_main_inline_keyboard, get_profile_edit_keyboard, get_cancel_search_keyboard
from states.user_states import AnonymousChatting
from utils.debug import dbg

router = Router()

# Глобальный словарь для хранения соответствия ID сообщений
message_mapping = {}

# Вспомогательные функции
async def setup_chat_state(state: FSMContext, chat_id: int, partner_id: int):
    """Устанавливает состояние чата и сохраняет данные"""
    await state.set_state(AnonymousChatting.chatting)
    await state.update_data(chat_id=chat_id, partner_id=partner_id)

async def send_message_to_partner(bot, partner_tg_id: int, content_type: str, content, caption=None, reply_to_message_id=None):
    """Отправляет сообщение партнеру в зависимости от типа контента"""
    try:
        if content_type == "text":
            await bot.send_message(partner_tg_id, content, reply_to_message_id=reply_to_message_id)
        elif content_type == "photo":
            await bot.send_photo(partner_tg_id, content, caption=caption, reply_to_message_id=reply_to_message_id)
        elif content_type == "video":
            await bot.send_video(partner_tg_id, content, caption=caption, reply_to_message_id=reply_to_message_id)
        elif content_type == "voice":
            await bot.send_voice(partner_tg_id, content, reply_to_message_id=reply_to_message_id)
        elif content_type == "document":
            await bot.send_document(partner_tg_id, content, caption=caption, reply_to_message_id=reply_to_message_id)
        elif content_type == "audio":
            await bot.send_audio(partner_tg_id, content, caption=caption, reply_to_message_id=reply_to_message_id)
        elif content_type == "sticker":
            await bot.send_sticker(partner_tg_id, content, reply_to_message_id=reply_to_message_id)
        return True
    except Exception as e:
        print(f"Ошибка при отправке {content_type}: {e}")
        return False

# Поиск собеседника
@router.message(F.text == "🔍 Найти собеседника")
async def cmd_find_chat(message: types.Message, state: FSMContext):
    await state.clear()
    dbg(f"Пользователь {message.from_user.id} запросил поиск собеседника", "HANDLER")
    
    db = next(get_db())
    user = get_user_by_tg_id(db, message.from_user.id)

    if not user:
        dbg(f"Пользователь {message.from_user.id} не зарегистрирован", "HANDLER")
        await message.answer("Пожалуйста, сначала зарегистрируйтесь с помощью команды /start")
        return

    active_chat = get_active_chat(db, user.id)
    if active_chat:
        dbg(f"У пользователя {user.id} уже есть активный чат ID: {active_chat.id}", "HANDLER")
        await message.answer(
            "Ты уже находишься в чате. Используй эти кнопки для управления:",
            reply_markup=get_chat_inline_keyboard()
        )
        partner_id = active_chat.user2_id if active_chat.user1_id == user.id else active_chat.user1_id
        await setup_chat_state(state, active_chat.id, partner_id)
        return

    dbg(f"Запуск поиска собеседника для пользователя {user.id}", "HANDLER")
    await message.answer(
        "Ищем подходящего собеседника с помощью ИИ... Пожалуйста, подожди.",
        reply_markup=get_cancel_search_keyboard()
    )
    await state.set_state(AnonymousChatting.waiting)

    partner = await find_available_chat_partner(db, user.id)
    
    if partner:
        dbg(f"Найден собеседник: {partner.id} для пользователя {user.id}", "HANDLER")
        chat = create_chat(db, user.id, partner.id)
        dbg(f"Создан чат ID: {chat.id}", "HANDLER")
        
        await message.answer(
            "Собеседник найден! Теперь вы можете общаться анонимно.",
            reply_markup=get_chat_inline_keyboard()
        )
        await message.bot.send_message(
            partner.tg_id,
            "Собеседник найден! Теперь вы можете общаться анонимно.",
            reply_markup=get_chat_inline_keyboard()
        )
        await setup_chat_state(state, chat.id, partner.id)
    else:
        dbg(f"Для пользователя {user.id} не найдено собеседников", "HANDLER")
        await message.answer(
            "Пока нет доступных собеседников. Мы уведомим тебя, когда кто-то появится."
        )


# Обработчик для сообщений в чате и автоматической установки состояния
@router.message()
async def handle_all_messages(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    dbg(f"Получено сообщение от пользователя {message.from_user.id}, текущее состояние: {current_state}", "HANDLER")

    # Если пользователь уже в состоянии чата, обрабатываем сообщение
    if current_state == AnonymousChatting.chatting.state:
        dbg(f"Пользователь {message.from_user.id} в состоянии чата, обрабатываем сообщение", "HANDLER")
        await process_chat_message(message, state)
        return

    # Если пользователь не в состоянии чата, проверяем наличие активного чата
    db = next(get_db())
    user = get_user_by_tg_id(db, message.from_user.id)
    if not user:
        dbg(f"Пользователь {message.from_user.id} не найден в базе данных", "HANDLER")
        return

    chat = get_active_chat(db, user.id)
    if chat:
        dbg(f"Найден активный чат ID: {chat.id} для пользователя {user.id}, устанавливаем состояние", "HANDLER")
        # Устанавливаем состояние чата
        partner_id = chat.user2_id if chat.user1_id == user.id else chat.user1_id
        await setup_chat_state(state, chat.id, partner_id)

        # Обрабатываем текущее сообщение как сообщение в чате
        dbg(f"Передаем сообщение на обработку в чат", "HANDLER")
        await process_chat_message(message, state)

# Функция для обработки сообщений в чате
async def process_chat_message(message: types.Message, state: FSMContext):
    dbg(f"Обработка сообщения в чате от пользователя {message.from_user.id}", "CHAT")
    db = next(get_db())
    user = get_user_by_tg_id(db, message.from_user.id)
    chat = get_active_chat(db, user.id)

    if not chat:
        dbg(f"У пользователя {user.id} нет активного чата", "CHAT")
        await message.answer(
            "У тебя нет активного чата. Хочешь найти собеседника?",
            reply_markup=get_main_inline_keyboard()
        )
        await state.clear()
        return

    partner_id = chat.user2_id if chat.user1_id == user.id else chat.user1_id
    partner = db.query(User).filter(User.id == partner_id).first()
    dbg(f"Партнер пользователя {user.id} - пользователь {partner_id}", "CHAT")

    if not partner:
        dbg(f"Партнер не найден, завершаем чат {chat.id}", "CHAT")
        await message.answer("Произошла ошибка. Чат завершен.")
        end_chat(db, chat.id)
        await state.clear()
        return

    # Показываем эффект набора текста партнеру
    try:
        await message.bot.send_chat_action(partner.tg_id, "typing")
        dbg(f"Отправлен эффект набора текста пользователю {partner.tg_id}", "CHAT")
    except Exception as e:
        dbg(f"Ошибка при отправке эффекта набора текста: {e}", "CHAT_ERROR")

    try:
        # Увеличиваем счетчик сообщений
        increment_messages_count(db, chat.id)
        dbg(f"Увеличен счетчик сообщений в чате {chat.id}", "CHAT")

        # Проверяем, является ли сообщение ответом
        reply_to_message_id = None
        if message.reply_to_message:
            # Получаем ID оригинального сообщения партнера
            original_message_id = message.reply_to_message.message_id
            dbg(f"Сообщение является ответом на сообщение ID: {original_message_id}", "CHAT")
            if original_message_id in message_mapping:
                reply_to_message_id = message_mapping[original_message_id]
                dbg(f"Найдено соответствие для ответа: {reply_to_message_id}", "CHAT")
            else:
                dbg(f"Не найдено соответствие для ответа на сообщение ID: {original_message_id}", "CHAT")

        if message.text:
            # Задержка в зависимости от длины текста
            typing_delay = min(len(message.text) * 0.05, 3.0)  # Максимум 3 секунды
            await asyncio.sleep(typing_delay)
            dbg(f"Отправка текстового сообщения пользователю {partner.tg_id}", "CHAT")
            sent_message = await message.bot.send_message(
                partner.tg_id,
                message.text,
                reply_to_message_id=reply_to_message_id
            )
            # Сохраняем соответствие ID сообщений
            message_mapping[message.message_id] = sent_message.message_id
            dbg(f"Сохранено соответствие ID: {message.message_id} -> {sent_message.message_id}", "CHAT")
        elif message.photo:
            try:
                await message.bot.send_chat_action(partner.tg_id, "upload_photo")
                await asyncio.sleep(1.0)
                sent_message = await message.bot.send_photo(
                    partner.tg_id,
                    message.photo[-1].file_id,
                    caption=message.caption,
                    reply_to_message_id=reply_to_message_id
                )
                message_mapping[message.message_id] = sent_message.message_id
            except Exception as e:
                print(f"Ошибка при отправке фото: {e}")
                sent_message = await message.bot.send_photo(
                    partner.tg_id,
                    message.photo[-1].file_id,
                    caption=message.caption,
                    reply_to_message_id=reply_to_message_id
                )
                message_mapping[message.message_id] = sent_message.message_id
        elif message.video:
            try:
                await message.bot.send_chat_action(partner.tg_id, "upload_video")
                await asyncio.sleep(1.0)
                sent_message = await message.bot.send_video(
                    partner.tg_id,
                    message.video.file_id,
                    caption=message.caption,
                    reply_to_message_id=reply_to_message_id
                )
                message_mapping[message.message_id] = sent_message.message_id
            except Exception as e:
                print(f"Ошибка при отправке видео: {e}")
                sent_message = await message.bot.send_video(
                    partner.tg_id,
                    message.video.file_id,
                    caption=message.caption,
                    reply_to_message_id=reply_to_message_id
                )
                message_mapping[message.message_id] = sent_message.message_id
        elif message.voice:
            try:
                await message.bot.send_chat_action(partner.tg_id, "record_voice")
                await asyncio.sleep(0.5)
                sent_message = await message.bot.send_voice(
                    partner.tg_id,
                    message.voice.file_id,
                    reply_to_message_id=reply_to_message_id
                )
                message_mapping[message.message_id] = sent_message.message_id
            except Exception as e:
                print(f"Ошибка при отправке голосового сообщения: {e}")
                sent_message = await message.bot.send_voice(
                    partner.tg_id,
                    message.voice.file_id,
                    reply_to_message_id=reply_to_message_id
                )
                message_mapping[message.message_id] = sent_message.message_id
        elif message.document:
            try:
                await message.bot.send_chat_action(partner.tg_id, "upload_document")
                await asyncio.sleep(1.0)
                sent_message = await message.bot.send_document(
                    partner.tg_id,
                    message.document.file_id,
                    caption=message.caption,
                    reply_to_message_id=reply_to_message_id
                )
                message_mapping[message.message_id] = sent_message.message_id
            except Exception as e:
                print(f"Ошибка при отправке документа: {e}")
                sent_message = await message.bot.send_document(
                    partner.tg_id,
                    message.document.file_id,
                    caption=message.caption,
                    reply_to_message_id=reply_to_message_id
                )
                message_mapping[message.message_id] = sent_message.message_id
        elif message.audio:
            try:
                await message.bot.send_chat_action(partner.tg_id, "upload_voice")
                await asyncio.sleep(1.0)
                sent_message = await message.bot.send_audio(
                    partner.tg_id,
                    message.audio.file_id,
                    caption=message.caption,
                    reply_to_message_id=reply_to_message_id
                )
                message_mapping[message.message_id] = sent_message.message_id
            except Exception as e:
                print(f"Ошибка при отправке аудио: {e}")
                sent_message = await message.bot.send_audio(
                    partner.tg_id,
                    message.audio.file_id,
                    caption=message.caption,
                    reply_to_message_id=reply_to_message_id
                )
                message_mapping[message.message_id] = sent_message.message_id
        elif message.sticker:
            sent_message = await message.bot.send_sticker(
                partner.tg_id,
                message.sticker.file_id,
                reply_to_message_id=reply_to_message_id
            )
            message_mapping[message.message_id] = sent_message.message_id
    except Exception as e:
        print(f"Ошибка при отправке сообщения: {e}")
        await message.answer("Не удалось отправить сообщение собеседнику.")

# Обработчики для inline кнопок
@router.callback_query(F.data == "request_deanon")
async def inline_deanon_request(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()

    db = next(get_db())
    user = get_user_by_tg_id(db, callback.from_user.id)
    chat = get_active_chat(db, user.id)
    if not chat:
        await callback.message.answer(
            "У тебя нет активного чата.",
            reply_markup=get_main_inline_keyboard()
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

    await callback.message.answer(
        "Ты отправил запрос на раскрытие личности. Ожидаем ответа собеседника."
    )
    if partner:
        await callback.bot.send_message(
            partner.tg_id,
            "Собеседник хочет раскрыть личность. Ты согласен?",
            reply_markup=get_deanon_keyboard()
        )

@router.callback_query(F.data == "end_chat")
async def inline_end_chat(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()

    db = next(get_db())
    user = get_user_by_tg_id(db, callback.from_user.id)
    chat = get_active_chat(db, user.id)
    if not chat:
        await callback.message.answer(
            "У тебя нет активного чата.",
            reply_markup=get_main_inline_keyboard()
        )
        await state.clear()
        return

    partner_id = chat.user2_id if chat.user1_id == user.id else chat.user1_id
    partner = db.query(User).filter(User.id == partner_id).first()

    # Очищаем соответствия ID сообщений для этого чата
    global message_mapping
    # Создаем новый словарь без сообщений из этого чата
    message_mapping = {}

    end_chat(db, chat.id)
    await callback.message.answer(
        "Чат завершен. Хочешь найти нового собеседника?",
        reply_markup=get_main_inline_keyboard()
    )
    if partner:
        await callback.bot.send_message(
            partner.tg_id,
            "Собеседник завершил чат. Хочешь найти нового собеседника?",
            reply_markup=get_main_inline_keyboard()
        )
    await state.clear()

@router.callback_query(F.data == "deanon_approve")
async def inline_deanon_approve(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()

    db = next(get_db())
    user = get_user_by_tg_id(db, callback.from_user.id)
    chat = get_active_chat(db, user.id)
    if not chat:
        await callback.message.answer(
            "У тебя нет активного чата.",
            reply_markup=get_main_inline_keyboard()
        )
        await state.clear()
        return

    partner_id = chat.user2_id if chat.user1_id == user.id else chat.user1_id
    partner = db.query(User).filter(User.id == partner_id).first()
    user_position = 1 if chat.user1_id == user.id else 2
    deanon_request = get_deanon_request(db, chat.id)
    if not deanon_request:
        await callback.message.answer(
            "Запрос на раскрытие личности не найден."
        )
        await state.set_state(AnonymousChatting.chatting)
        return

    update_deanon_approval(db, deanon_request.id, user_position, True)
    # Получаем обновленный объект из базы
    deanon_request = get_deanon_request(db, chat.id)
    if deanon_request.user1_approved and deanon_request.user2_approved:
        try:
            # Показываем эффект загрузки фото
            await callback.bot.send_chat_action(callback.from_user.id, "upload_photo")
            if partner:
                await callback.bot.send_chat_action(partner.tg_id, "upload_photo")
            await asyncio.sleep(1.0)
        except Exception as e:
            print(f"Ошибка при отправке эффекта загрузки фото: {e}")

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

        try:
            # user1 -> user2
            if user1.photo_id and user2:
                await callback.bot.send_photo(
                    user2.tg_id,
                    user1.photo_id,
                    caption=profile_caption_1,
                    parse_mode="Markdown"
                )
            elif user2:
                await callback.bot.send_message(
                    user2.tg_id,
                    profile_caption_1,
                    parse_mode="Markdown"
                )

            # user2 -> user1
            if user2.photo_id and user1:
                await callback.bot.send_photo(
                    user1.tg_id,
                    user2.photo_id,
                    caption=profile_caption_2,
                    parse_mode="Markdown"
                )
            elif user1:
                await callback.bot.send_message(
                    user1.tg_id,
                    profile_caption_2,
                    parse_mode="Markdown"
                )

            # Отправляем финальные сообщения
            if user1:
                await callback.bot.send_message(
                    user1.tg_id,
                    "Личности раскрыты! Теперь вы можете продолжить общение.",
                    reply_markup=get_chat_inline_keyboard()
                )
            if user2 and user1.tg_id != callback.from_user.id:
                await callback.bot.send_message(
                    user2.tg_id,
                    "Личности раскрыты! Теперь вы можете продолжить общение.",
                    reply_markup=get_chat_inline_keyboard()
                )
        except Exception as e:
            print(f"Ошибка при раскрытии личности: {e}")
            await callback.message.answer(
                "Произошла ошибка при раскрытии личности. Попробуйте еще раз."
            )
    else:
        await callback.message.answer(
            "Ты согласился на раскрытие личности. Ожидаем ответа собеседника."
        )
    await state.set_state(AnonymousChatting.chatting)

@router.callback_query(F.data == "deanon_reject")
async def inline_deanon_reject(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()

    db = next(get_db())
    user = get_user_by_tg_id(db, callback.from_user.id)
    chat = get_active_chat(db, user.id)
    if not chat:
        await callback.message.answer(
            "У тебя нет активного чата.",
            reply_markup=get_main_inline_keyboard()
        )
        await state.clear()
        return

    partner_id = chat.user2_id if chat.user1_id == user.id else chat.user1_id
    partner = db.query(User).filter(User.id == partner_id).first()
    user_position = 1 if chat.user1_id == user.id else 2
    deanon_request = get_deanon_request(db, chat.id)
    if not deanon_request:
        await callback.message.answer(
            "Запрос на раскрытие личности не найден."
        )
        await state.set_state(AnonymousChatting.chatting)
        return

    update_deanon_approval(db, deanon_request.id, user_position, False)
    await callback.message.answer(
        "Ты отказался от раскрытия личности."
    )
    if partner:
        await callback.bot.send_message(
            partner.tg_id,
            "Собеседник отказался от раскрытия личности."
        )
    await state.set_state(AnonymousChatting.chatting)

# Обработчик для поиска нового собеседника
@router.callback_query(F.data == "find_chat")
async def find_new_chat(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()

    db = next(get_db())
    user = get_user_by_tg_id(db, callback.from_user.id)

    # Проверяем, есть ли у пользователя активный чат
    active_chat = get_active_chat(db, user.id)
    if active_chat:
        await callback.message.answer(
            "У тебя уже есть активный чат. Сначала завершите текущий чат.",
            reply_markup=get_chat_inline_keyboard()
        )
        partner_id = active_chat.user2_id if active_chat.user1_id == user.id else active_chat.user1_id
        await setup_chat_state(state, active_chat.id, partner_id)
        return

    # Проверяем, активен ли профиль пользователя
    if not user.is_active:
        await callback.message.answer(
            "Твой профиль неактивен. Активируй его в настройках профиля.",
            reply_markup=get_profile_edit_keyboard()
        )
        return

    # Ищем собеседника
    await callback.message.answer(
        "Ищем собеседника...",
        reply_markup=get_cancel_search_keyboard()
    )
    await state.set_state(AnonymousChatting.waiting)

    partner = find_available_chat_partner(db, user.id)
    if not partner:
        await callback.message.answer(
            "Пока нет доступных собеседников. Мы уведомим тебя, когда кто-то появится."
        )
        return

    # Создаем чат
    chat = create_chat(db, user.id, partner.id)
    if not chat:
        await callback.message.answer(
            "Произошла ошибка при создании чата. Попробуйте позже.",
            reply_markup=get_main_inline_keyboard()
        )
        await state.clear()
        return

    # Устанавливаем состояние и данные для текущего пользователя
    await setup_chat_state(state, chat.id, partner.id)

    # Отправляем сообщения обоим пользователям
    await callback.message.answer(
        "Собеседник найден! Теперь вы можете общаться анонимно.",
        reply_markup=get_chat_inline_keyboard()
    )

    try:
        await callback.bot.send_message(
            partner.tg_id,
            "Собеседник найден! Теперь вы можете общаться анонимно.",
            reply_markup=get_chat_inline_keyboard()
        )
    except Exception as e:
        print(f"Ошибка при отправке сообщения партнеру: {e}")
        await callback.message.answer(
            "Произошла ошибка при подключении к собеседнику. Попробуйте найти другого.",
            reply_markup=get_main_inline_keyboard()
        )
        end_chat(db, chat.id)
        await state.clear()

# Обработчик для отправки информации о чате
@router.callback_query(F.data == "chat_info")
async def chat_info(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()

    db = next(get_db())
    user = get_user_by_tg_id(db, callback.from_user.id)
    chat = get_active_chat(db, user.id)

    if not chat:
        await callback.message.answer(
            "У тебя нет активного чата.",
            reply_markup=get_main_inline_keyboard()
        )
        await state.clear()
        return

    # Формируем информацию о чате
    chat_duration = datetime.datetime.now() - chat.start_time
    hours, remainder = divmod(chat_duration.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    duration_str = f"{hours}ч {minutes}м {seconds}с" if hours > 0 else f"{minutes}м {seconds}с"

    info_text = (
        f"📊 Информация о текущем чате:\n"
        f"⏱️ Длительность: {duration_str}\n"
        f"💬 Количество сообщений: {chat.messages_count}\n"
    )

    await callback.message.answer(
        info_text,
        reply_markup=get_chat_inline_keyboard()
    )

# Обработчик для отправки подсказок по общению
@router.callback_query(F.data == "chat_tips")
async def chat_tips(callback: types.CallbackQuery):
    await callback.answer()

    tips_text = (
        "💡 Советы для общения:\n\n"
        "1️⃣ Начните с приветствия и нейтральной темы\n"
        "2️⃣ Задавайте открытые вопросы, требующие развернутого ответа\n"
        "3️⃣ Проявляйте искренний интерес к собеседнику\n"
        "4️⃣ Делитесь информацией о себе, но не перегружайте деталями\n"
        "5️⃣ Уважайте границы собеседника\n"
        "6️⃣ Если чувствуете взаимную симпатию, предложите раскрыть личности\n"
    )

    await callback.message.answer(tips_text, reply_markup=get_chat_inline_keyboard())

# Обработчик для отмены поиска собеседника через сообщение
@router.message(AnonymousChatting.waiting)
async def cancel_search_message(message: types.Message, state: FSMContext):
    if message.text == "Отменить поиск" or message.text == "/cancel":
        await message.answer(
            "Поиск собеседника отменен.",
            reply_markup=get_main_inline_keyboard()
        )
        await state.clear()
    else:
        await message.answer(
            "Ты в режиме поиска собеседника. Подожди, пока мы найдем тебе пару, или нажми кнопку \"Отменить поиск\" для отмены.",
            reply_markup=get_cancel_search_keyboard()
        )

# Обработчик для отмены поиска собеседника через кнопку
@router.callback_query(F.data == "cancel_search")
async def cancel_search_button(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()

    current_state = await state.get_state()
    if current_state == AnonymousChatting.waiting.state:
        await callback.message.answer(
            "Поиск собеседника отменен.",
            reply_markup=get_main_inline_keyboard()
        )
        await state.clear()
    else:
        await callback.message.answer(
            "Ты не в режиме поиска собеседника.",
            reply_markup=get_main_inline_keyboard()
        )
