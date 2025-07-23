from aiogram import types, Router, F
from aiogram.filters import Command
import asyncio

from keyboards.inline import (
    get_main_inline_keyboard, get_help_menu_keyboard, get_help_section_keyboard,
    HELP_MENU, HELP_USAGE, HELP_SEARCH, HELP_PROFILE, HELP_CHAT, BACK_TO_HELP, BACK_TO_MAIN
)

router = Router()

# Обработчик для меню помощи
@router.message(Command("help"))
@router.message(F.text == "ℹ️ Помощь")
@router.callback_query(F.data == HELP_MENU)
async def cmd_help(message_or_callback: types.Message | types.CallbackQuery):
    # Определяем, это сообщение или callback
    is_callback = isinstance(message_or_callback, types.CallbackQuery)
    if is_callback:
        await message_or_callback.answer()
        message = message_or_callback.message
    else:
        message = message_or_callback

    help_text = (
        "🤖 Бот для анонимных знакомств\n\n"
        "Команды:\n"
        "/start - Начать работу с ботом\n"
        "🔍 Найти собеседника - Поиск анонимного собеседника\n"
        "👤 Мой профиль - Просмотр своего профиля\n"
        "ℹ️ Помощь - Показать это сообщение\n\n"
        "Выберите раздел для получения подробной информации:"
    )

    if is_callback:
        await message.edit_text(help_text, reply_markup=get_help_menu_keyboard())
    else:
        await message.answer(help_text, reply_markup=get_help_menu_keyboard())

# Обработчик для возврата в меню помощи
@router.callback_query(F.data == BACK_TO_HELP)
async def back_to_help(callback: types.CallbackQuery):
    await callback.answer()
    await cmd_help(callback)

# Обработчики для разделов помощи
@router.callback_query(F.data.startswith("help_"))
async def process_help_sections(callback: types.CallbackQuery):
    section = callback.data.split("_")[1]
    await callback.answer()

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

    await callback.message.edit_text(
        help_sections[section],
        reply_markup=get_help_section_keyboard()
    )