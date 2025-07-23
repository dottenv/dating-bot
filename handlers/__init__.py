from aiogram import Dispatcher

from . import start, registration, profile, chat_simple, help, commands, message_analyzer

def register_all_handlers(dp: Dispatcher):
    # Регистрируем все обработчики
    dp.include_router(start.router)
    dp.include_router(registration.router)
    dp.include_router(help.router)  # Регистрируем обработчик помощи перед профилем
    dp.include_router(profile.router)
    dp.include_router(commands.router)  # Регистрируем обработчики команд
    dp.include_router(message_analyzer.router)  # Регистрируем обработчик анализа сообщений
    dp.include_router(chat_simple.router)  # Регистрируем обработчик чата последним