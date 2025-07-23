from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_main_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔍 Найти собеседника")],
            [KeyboardButton(text="👤 Мой профиль"), KeyboardButton(text="ℹ️ Помощь")]
        ],
        resize_keyboard=True
    )
    return keyboard


def get_gender_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Мужской"), KeyboardButton(text="Женский")],
            [KeyboardButton(text="Другой")]
        ],
        resize_keyboard=True
    )
    return keyboard


def get_orientation_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Гетеро"), KeyboardButton(text="Гомо")],
            [KeyboardButton(text="Би"), KeyboardButton(text="Другое")]
        ],
        resize_keyboard=True
    )
    return keyboard

def get_chat_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👋 Раскрыть личность")],
            [KeyboardButton(text="❌ Завершить чат")]
        ],
        resize_keyboard=True
    )
    return keyboard

def get_deanon_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Согласен"), KeyboardButton(text="❌ Отказываюсь")]
        ],
        resize_keyboard=True
    )
    return keyboard
