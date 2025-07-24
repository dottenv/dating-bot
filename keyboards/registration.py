from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def create_keyboard(buttons, row_width=2):
    kb = []
    for i in range(0, len(buttons), row_width):
        row = [KeyboardButton(text=btn) for btn in buttons[i:i+row_width]]
        kb.append(row)
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

gender_keyboard = create_keyboard(["Мужской", "Женский", "Другое"])

orientation_keyboard = create_keyboard(["Гетеро", "Гомо", "Би", "Пан", "Другое"])

dating_goal_keyboard = create_keyboard([
    "Серьезные отношения", 
    "Дружба", 
    "Общение", 
    "Встречи"
])

skip_keyboard = create_keyboard(["Пропустить"], row_width=1)

photo_source_keyboard = create_keyboard(["Загрузить фото", "Использовать фото профиля", "Пропустить"])
