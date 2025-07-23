from aiogram import Dispatcher

from . import start, registration, profile, chat_simple

def register_all_handlers(dp: Dispatcher):
    # Регистрируем все обработчики
    dp.include_router(start.router)
    dp.include_router(registration.router)
    dp.include_router(profile.router)
    dp.include_router(chat_simple.router)