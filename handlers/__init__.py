from aiogram import Dispatcher

from . import start, registration, chat, profile

def register_all_handlers(dp: Dispatcher):
    dp.include_router(start.router)
    dp.include_router(registration.router)
    dp.include_router(chat.router)
    dp.include_router(profile.router)