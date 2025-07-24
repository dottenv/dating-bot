from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def create_keyboard(buttons, row_width=2):
    kb = []
    for i in range(0, len(buttons), row_width):
        row = [KeyboardButton(text=btn) for btn in buttons[i:i+row_width]]
        kb.append(row)
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

main_keyboard = create_keyboard([
    "Профиль",
    "Найти собеседника", 
    "🤖 AI-Ассистент",
    "⭐ Premium",
    "Настройки"
])