import asyncio
import datetime
import time
from typing import Optional, Tuple

from aiogram import types, Router, F
from aiogram.fsm.context import FSMContext

from database.db import get_db
from database.models import User, AnonymousChat
from services.user_service import get_user_by_tg_id
from services.chat_service import (
    find_available_chat_partner, create_chat, get_active_chat,
    end_chat, create_deanon_request, get_deanon_request, update_deanon_approval
)
from keyboards.inline import (
    get_chat_inline_keyboard, get_deanon_keyboard, get_main_inline_keyboard, 
    get_profile_edit_keyboard, get_cancel_search_keyboard, get_confirm_chat_keyboard,
    FIND_CHAT, END_CHAT, REQUEST_DEANON, CHAT_INFO, REPORT_USER,
    DEANON_APPROVE, DEANON_REJECT, CANCEL_SEARCH, CONFIRM_CHAT, REJECT_CHAT
)
from states.user_states import AnonymousChatting
from utils.debug import dbg
from handlers.chat_message_handler import process_chat_message, clear_message_mapping_for_chat

router = Router()

# Вспомогательные функции
async def setup_chat_state(state: FSMContext, chat_id: int, partner_id: int):
    """Устанавливает состояние чата и сохраняет данные"""
    await state.set_state(AnonymousChatting.chatting)
    await state.update_data(chat_id=chat_id, partner_id=partner_id)

async def get_partner_info(db, chat: AnonymousChat, user_id: int) -> Tuple[int, Optional[User]]:
    """Получает информацию о партнере в чате"""
    partner_id = chat.user2_id if chat.user1_id == user_id else chat.user1_id
    partner = db.query(User).filter(User.id == partner_id).first()
    return partner_id, partner

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
    search_message = await message.answer(
        "Ищем подходящего собеседника... Пожалуйста, подожди.",
        reply_markup=get_cancel_search_keyboard()
    )
    await state.set_state(AnonymousChatting.waiting)
    # Сохраняем ID сообщения для последующего редактирования
    await state.update_data(search_message_id=search_message.message_id)

    partner, alternative_partners, result_message = await find_available_chat_partner(db, user.id)
    
    if partner:
        dbg(f"Найден собеседник: {partner.id} для пользователя {user.id}", "HANDLER")
        
        # Проверяем, требуется ли подтверждение для чата с пользователем с низким рейтингом
        if "низким рейтингом" in result_message:
            dbg(f"Требуется подтверждение для чата с пользователем с низким рейтингом", "HANDLER")
            # Сохраняем данные о партнере в состоянии
            await state.update_data(pending_partner_id=partner.id)
            
            # Редактируем сообщение о поиске
            await message.bot.edit_message_text(
                "Найден собеседник с низким рейтингом. Хотите начать чат с этим пользователем?",
                chat_id=message.chat.id,
                message_id=search_message.message_id,
                reply_markup=get_confirm_chat_keyboard()
            )
            await state.set_state(AnonymousChatting.confirming)
            return
        
        # Создаем чат и начинаем общение
        chat = create_chat(db, user.id, partner.id)
        dbg(f"Создан чат ID: {chat.id}", "HANDLER")
        
        # Редактируем сообщение о поиске
        await message.bot.edit_message_text(
            "Собеседник найден! Теперь вы можете общаться анонимно.",
            chat_id=message.chat.id,
            message_id=search_message.message_id,
            reply_markup=get_chat_inline_keyboard()
        )
        
        try:
            # Отправляем сообщение партнеру
            await message.bot.send_message(
                partner.tg_id,
                "Собеседник найден! Теперь вы можете общаться анонимно.",
                reply_markup=get_chat_inline_keyboard()
            )
            
            # Устанавливаем состояние чата для обоих пользователей
            await setup_chat_state(state, chat.id, partner.id)
            
            # Устанавливаем состояние чата для партнера
            partner_state = FSMContext(message.bot.storage, partner.tg_id, partner.tg_id)
            await setup_chat_state(partner_state, chat.id, user.id)
            
            # Обновляем кэш активных чатов
            from handlers.chat_message_handler import active_chat_cache
            current_time = time.time()
            active_chat_cache[user.id] = (chat, current_time)
            active_chat_cache[partner.id] = (chat, current_time)
            
        except Exception as e:
            dbg(f"Ошибка при отправке сообщения партнеру: {e}", "CHAT_ERROR")
            # Если не удалось отправить сообщение партнеру, завершаем чат
            end_chat(db, chat.id)
            await message.bot.edit_message_text(
                "Не удалось отправить сообщение партнеру. Попробуйте найти другого собеседника.",
                chat_id=message.chat.id,
                message_id=search_message.message_id,
                reply_markup=get_main_inline_keyboard()
            )
            await state.clear()
    else:
        dbg(f"Для пользователя {user.id} не найдено собеседников: {result_message}", "HANDLER")
        # Редактируем сообщение о поиске
        await message.bot.edit_message_text(
            result_message or "Пока нет доступных собеседников. Мы уведомим тебя, когда кто-то появится.",
            chat_id=message.chat.id,
            message_id=search_message.message_id,
            reply_markup=get_main_inline_keyboard()
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
        
        # Получаем партнера из базы данных
        partner = db.query(User).filter(User.id == partner_id).first()
        if not partner:
            dbg(f"Партнер не найден, завершаем чат {chat.id}", "HANDLER")
            await message.answer("Произошла ошибка. Чат завершен.")
            end_chat(db, chat.id)
            await state.clear()
            return

        # Обрабатываем текущее сообщение как сообщение в чате
        dbg(f"Передаем сообщение на обработку в чат", "HANDLER")
        await process_chat_message(message, state)

# Обработчики для inline кнопок
@router.callback_query(F.data == REQUEST_DEANON)
async def inline_deanon_request(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()

    db = next(get_db())
    user = get_user_by_tg_id(db, callback.from_user.id)
    chat = get_active_chat(db, user.id)
    if not chat:
        await callback.message.edit_text(
            "У тебя нет активного чата.",
            reply_markup=get_main_inline_keyboard()
        )
        await state.clear()
        return

    deanon_request = get_deanon_request(db, chat.id)
    if not deanon_request:
        deanon_request = create_deanon_request(db, chat.id)

    partner_id, partner = await get_partner_info(db, chat, user.id)
    user_position = 1 if chat.user1_id == user.id else 2
    update_deanon_approval(db, deanon_request.id, user_position, True)

    await callback.message.edit_text(
        "Ты отправил запрос на раскрытие личности. Ожидаем ответа собеседника.",
        reply_markup=get_chat_inline_keyboard()
    )
    
    if partner:
        await callback.bot.send_message(
            partner.tg_id,
            "Собеседник хочет раскрыть личность. Ты согласен?",
            reply_markup=get_deanon_keyboard()
        )

@router.callback_query(F.data == END_CHAT)
async def inline_end_chat(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()

    db = next(get_db())
    user = get_user_by_tg_id(db, callback.from_user.id)
    chat = get_active_chat(db, user.id)
    if not chat:
        await callback.message.edit_text(
            "У тебя нет активного чата.",
            reply_markup=get_main_inline_keyboard()
        )
        await state.clear()
        return

    partner_id, partner = await get_partner_info(db, chat, user.id)

    # Очищаем соответствия ID сообщений для этого чата
    clear_message_mapping_for_chat(chat.id)

    # Завершаем чат
    end_chat(db, chat.id)
    
    # Очищаем кэш активных чатов
    from handlers.chat_message_handler import active_chat_cache
    active_chat_cache.pop(user.id, None)
    if partner:
        active_chat_cache.pop(partner.id, None)
    
    # Обновляем сообщения
    await callback.message.edit_text(
        "Чат завершен. Хочешь найти нового собеседника?",
        reply_markup=get_main_inline_keyboard()
    )
    
    if partner:
        try:
            await callback.bot.send_message(
                partner.tg_id,
                "Собеседник завершил чат. Хочешь найти нового собеседника?",
                reply_markup=get_main_inline_keyboard()
            )
            
            # Очищаем состояние партнера
            partner_state = FSMContext(callback.bot.storage, partner.tg_id, partner.tg_id)
            await partner_state.clear()
        except Exception as e:
            dbg(f"Ошибка при отправке сообщения партнеру о завершении чата: {e}", "CHAT_ERROR")
    
    # Очищаем состояние текущего пользователя
    await state.clear()

@router.callback_query(F.data == DEANON_APPROVE)
async def inline_deanon_approve(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()

    db = next(get_db())
    user = get_user_by_tg_id(db, callback.from_user.id)
    chat = get_active_chat(db, user.id)
    if not chat:
        await callback.message.edit_text(
            "У тебя нет активного чата.",
            reply_markup=get_main_inline_keyboard()
        )
        await state.clear()
        return

    partner_id, partner = await get_partner_info(db, chat, user.id)
    user_position = 1 if chat.user1_id == user.id else 2
    deanon_request = get_deanon_request(db, chat.id)
    if not deanon_request:
        await callback.message.edit_text(
            "Запрос на раскрытие личности не найден.",
            reply_markup=get_chat_inline_keyboard()
        )
        await state.set_state(AnonymousChatting.chatting)
        return

    update_deanon_approval(db, deanon_request.id, user_position, True)
    # Получаем обновленный объект из базы
    deanon_request = get_deanon_request(db, chat.id)
    
    if deanon_request.user1_approved and deanon_request.user2_approved:
        await process_deanon_reveal(callback, chat, db)
    else:
        await callback.message.edit_text(
            "Ты согласился на раскрытие личности. Ожидаем ответа собеседника.",
            reply_markup=get_chat_inline_keyboard()
        )
    
    await state.set_state(AnonymousChatting.chatting)

async def process_deanon_reveal(callback: types.CallbackQuery, chat: AnonymousChat, db):
    """Обрабатывает раскрытие личностей пользователей"""
    try:
        # Показываем эффект загрузки фото
        user1 = db.query(User).filter(User.id == chat.user1_id).first()
        user2 = db.query(User).filter(User.id == chat.user2_id).first()
        
        if user1:
            await callback.bot.send_chat_action(user1.tg_id, "upload_photo")
        if user2:
            await callback.bot.send_chat_action(user2.tg_id, "upload_photo")
        await asyncio.sleep(1.0)
        
        # Формируем профили пользователей
        profile1 = format_user_profile(user1)
        profile2 = format_user_profile(user2)
        
        # Отправляем профили пользователям
        await send_profile_to_user(callback.bot, user1, user2, profile2)
        await send_profile_to_user(callback.bot, user2, user1, profile1)
        
        # Отправляем финальные сообщения
        final_message = "Личности раскрыты! Теперь вы можете продолжить общение."
        if user1:
            await callback.bot.send_message(
                user1.tg_id, final_message, reply_markup=get_chat_inline_keyboard()
            )
        if user2 and user1.tg_id != callback.from_user.id:
            await callback.bot.send_message(
                user2.tg_id, final_message, reply_markup=get_chat_inline_keyboard()
            )
    except Exception as e:
        dbg(f"Ошибка при раскрытии личности: {e}", "CHAT_ERROR")
        await callback.message.edit_text(
            "Произошла ошибка при раскрытии личности. Попробуйте еще раз.",
            reply_markup=get_chat_inline_keyboard()
        )

def format_user_profile(user: User) -> str:
    """Форматирует профиль пользователя для отображения"""
    return (
        f"Профиль собеседника:\n"
        f"Имя: {user.first_name}\n"
        f"Возраст: {user.age}\n"
        f"Город: {user.city}\n"
        f"О себе: {user.bio}\n"
        f"Интересы: {user.tags}\n"
        f"Telegram: [Открыть профиль](tg://user?id={user.tg_id})"
    )

async def send_profile_to_user(bot, recipient: User, sender: User, profile_text: str):
    """Отправляет профиль пользователя получателю"""
    if not recipient:
        return
        
    if sender and sender.photo_id:
        await bot.send_photo(
            recipient.tg_id,
            sender.photo_id,
            caption=profile_text,
            parse_mode="Markdown"
        )
    else:
        await bot.send_message(
            recipient.tg_id,
            profile_text,
            parse_mode="Markdown"
        )

@router.callback_query(F.data == DEANON_REJECT)
async def inline_deanon_reject(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()

    db = next(get_db())
    user = get_user_by_tg_id(db, callback.from_user.id)
    chat = get_active_chat(db, user.id)
    if not chat:
        await callback.message.edit_text(
            "У тебя нет активного чата.",
            reply_markup=get_main_inline_keyboard()
        )
        await state.clear()
        return

    partner_id, partner = await get_partner_info(db, chat, user.id)
    user_position = 1 if chat.user1_id == user.id else 2
    deanon_request = get_deanon_request(db, chat.id)
    if not deanon_request:
        await callback.message.edit_text(
            "Запрос на раскрытие личности не найден.",
            reply_markup=get_chat_inline_keyboard()
        )
        await state.set_state(AnonymousChatting.chatting)
        return

    update_deanon_approval(db, deanon_request.id, user_position, False)
    await callback.message.edit_text(
        "Ты отказался от раскрытия личности.",
        reply_markup=get_chat_inline_keyboard()
    )
    
    if partner:
        await callback.bot.send_message(
            partner.tg_id,
            "Собеседник отказался от раскрытия личности.",
            reply_markup=get_chat_inline_keyboard()
        )
    
    await state.set_state(AnonymousChatting.chatting)

# Обработчик для поиска нового собеседника
@router.callback_query(F.data == FIND_CHAT)
async def find_new_chat(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()

    db = next(get_db())
    user = get_user_by_tg_id(db, callback.from_user.id)

    # Проверяем, есть ли у пользователя активный чат
    active_chat = get_active_chat(db, user.id)
    if active_chat:
        await callback.message.edit_text(
            "У тебя уже есть активный чат. Сначала завершите текущий чат.",
            reply_markup=get_chat_inline_keyboard()
        )
        partner_id = active_chat.user2_id if active_chat.user1_id == user.id else active_chat.user1_id
        await setup_chat_state(state, active_chat.id, partner_id)
        return

    # Проверяем, активен ли профиль пользователя
    if not user.is_active:
        await callback.message.edit_text(
            "Твой профиль неактивен. Активируй его в настройках профиля.",
            reply_markup=get_profile_edit_keyboard()
        )
        return

    # Ищем собеседника
    await callback.message.edit_text(
        "Ищем собеседника...",
        reply_markup=get_cancel_search_keyboard()
    )
    await state.set_state(AnonymousChatting.waiting)

    partner, alternative_partners, message = await find_available_chat_partner(db, user.id)
    if not partner:
        await callback.message.edit_text(
            message or "Пока нет доступных собеседников. Мы уведомим тебя, когда кто-то появится.",
            reply_markup=get_main_inline_keyboard()
        )
        return

    # Создаем чат
    chat = create_chat(db, user.id, partner.id)
    if not chat:
        await callback.message.edit_text(
            "Произошла ошибка при создании чата. Попробуйте позже.",
            reply_markup=get_main_inline_keyboard()
        )
        await state.clear()
        return

    # Устанавливаем состояние и данные для текущего пользователя
    await setup_chat_state(state, chat.id, partner.id)

    # Отправляем сообщения обоим пользователям
    await callback.message.edit_text(
        "Собеседник найден! Теперь вы можете общаться анонимно.",
        reply_markup=get_chat_inline_keyboard()
    )

    try:
        await callback.bot.send_message(
            partner.tg_id,
            "Собеседник найден! Теперь вы можете общаться анонимно.",
            reply_markup=get_chat_inline_keyboard()
        )
        # Устанавливаем состояние чата для партнера
        partner_state = FSMContext(callback.bot.storage, partner.tg_id, partner.tg_id)
        await setup_chat_state(partner_state, chat.id, user.id)
        
        # Обновляем кэш активных чатов
        from handlers.chat_message_handler import active_chat_cache
        current_time = time.time()
        active_chat_cache[user.id] = (chat, current_time)
        active_chat_cache[partner.id] = (chat, current_time)
        
    except Exception as e:
        dbg(f"Ошибка при отправке сообщения партнеру: {e}", "CHAT_ERROR")
        await callback.message.edit_text(
            "Произошла ошибка при подключении к собеседнику. Попробуйте найти другого.",
            reply_markup=get_main_inline_keyboard()
        )
        end_chat(db, chat.id)
        await state.clear()

# Обработчик для отправки информации о чате
@router.callback_query(F.data == CHAT_INFO)
async def chat_info(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()

    db = next(get_db())
    user = get_user_by_tg_id(db, callback.from_user.id)
    chat = get_active_chat(db, user.id)

    if not chat:
        await callback.message.edit_text(
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

    await callback.message.edit_text(
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

    await callback.message.edit_text(
        tips_text,
        reply_markup=get_chat_inline_keyboard()
    )

# Обработчик для отмены поиска собеседника через сообщение
@router.message(AnonymousChatting.waiting)
async def cancel_search_message(message: types.Message, state: FSMContext):
    if message.text == "Отменить поиск" or message.text == "/cancel":
        data = await state.get_data()
        search_message_id = data.get("search_message_id")
        
        if search_message_id:
            try:
                await message.bot.edit_message_text(
                    "Поиск собеседника отменен.",
                    chat_id=message.chat.id,
                    message_id=search_message_id,
                    reply_markup=get_main_inline_keyboard()
                )
                # Удаляем сообщение пользователя с командой отмены
                await message.delete()
            except Exception as e:
                dbg(f"Ошибка при редактировании сообщения: {e}", "CHAT_ERROR")
                await message.answer(
                    "Поиск собеседника отменен.",
                    reply_markup=get_main_inline_keyboard()
                )
        else:
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

# Обработчик для подтверждения чата с пользователем с низким рейтингом
@router.callback_query(F.data == CONFIRM_CHAT)
async def confirm_chat_with_low_rating(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    
    # Получаем данные о партнере из состояния
    data = await state.get_data()
    partner_id = data.get("pending_partner_id")
    
    if not partner_id:
        await callback.message.edit_text(
            "Произошла ошибка. Попробуйте найти собеседника снова.",
            reply_markup=get_main_inline_keyboard()
        )
        await state.clear()
        return
    
    db = next(get_db())
    user = get_user_by_tg_id(db, callback.from_user.id)
    partner = db.query(User).filter(User.id == partner_id).first()
    
    if not partner:
        await callback.message.edit_text(
            "Партнер больше недоступен. Попробуйте найти другого собеседника.",
            reply_markup=get_main_inline_keyboard()
        )
        await state.clear()
        return
    
    # Проверяем, не находится ли партнер уже в чате
    partner_chat = get_active_chat(db, partner.id)
    if partner_chat:
        await callback.message.edit_text(
            "Партнер уже находится в чате с другим пользователем. Попробуйте найти другого собеседника.",
            reply_markup=get_main_inline_keyboard()
        )
        await state.clear()
        return
    
    # Создаем чат
    chat = create_chat(db, user.id, partner.id)
    if not chat:
        await callback.message.edit_text(
            "Произошла ошибка при создании чата. Попробуйте позже.",
            reply_markup=get_main_inline_keyboard()
        )
        await state.clear()
        return
    
    # Редактируем сообщение
    await callback.message.edit_text(
        "Вы подтвердили чат с пользователем с низким рейтингом. Теперь вы можете общаться анонимно.",
        reply_markup=get_chat_inline_keyboard()
    )
    
    try:
        # Отправляем сообщение партнеру
        await callback.bot.send_message(
            partner.tg_id,
            "Собеседник найден! Теперь вы можете общаться анонимно.",
            reply_markup=get_chat_inline_keyboard()
        )
        
        # Устанавливаем состояние чата для обоих пользователей
        await setup_chat_state(state, chat.id, partner.id)
        
        # Устанавливаем состояние чата для партнера
        partner_state = FSMContext(callback.bot.storage, partner.tg_id, partner.tg_id)
        await setup_chat_state(partner_state, chat.id, user.id)
        
        # Обновляем кэш активных чатов
        from handlers.chat_message_handler import active_chat_cache
        current_time = time.time()
        active_chat_cache[user.id] = (chat, current_time)
        active_chat_cache[partner.id] = (chat, current_time)
        
    except Exception as e:
        dbg(f"Ошибка при отправке сообщения партнеру: {e}", "CHAT_ERROR")
        # Если не удалось отправить сообщение партнеру, завершаем чат
        end_chat(db, chat.id)
        await callback.message.edit_text(
            "Не удалось отправить сообщение партнеру. Попробуйте найти другого собеседника.",
            reply_markup=get_main_inline_keyboard()
        )
        await state.clear()

# Обработчик для отклонения чата с пользователем с низким рейтингом
@router.callback_query(F.data == REJECT_CHAT)
async def reject_chat_with_low_rating(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    
    # Очищаем состояние
    await state.clear()
    
    # Редактируем сообщение
    await callback.message.edit_text(
        "Вы отклонили чат с пользователем с низким рейтингом. Хотите найти другого собеседника?",
        reply_markup=get_main_inline_keyboard()
    )

# Обработчик для отмены поиска собеседника через кнопку
@router.callback_query(F.data == CANCEL_SEARCH)
async def cancel_search_button(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()

    current_state = await state.get_state()
    if current_state in [AnonymousChatting.waiting.state, AnonymousChatting.confirming.state]:
        await callback.message.edit_text(
            "Поиск собеседника отменен.",
            reply_markup=get_main_inline_keyboard()
        )
        await state.clear()
    else:
        await callback.message.edit_text(
            "Ты не в режиме поиска собеседника.",
            reply_markup=get_main_inline_keyboard()
        )