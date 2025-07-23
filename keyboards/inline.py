from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_profile_edit_keyboard():
    """Клавиатура для редактирования профиля"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✏️ Имя", callback_data="edit_name"),
                InlineKeyboardButton(text="🔢 Возраст", callback_data="edit_age")
            ],
            [
                InlineKeyboardButton(text="🧬 Пол", callback_data="edit_gender"),
                InlineKeyboardButton(text="💞 Ориентация", callback_data="edit_orientation")
            ],
            [
                InlineKeyboardButton(text="🏙️ Город", callback_data="edit_city"),
                InlineKeyboardButton(text="📝 О себе", callback_data="edit_bio")
            ],
            [
                InlineKeyboardButton(text="🖼️ Фото", callback_data="edit_photo"),
                InlineKeyboardButton(text="🏷️ Интересы", callback_data="edit_tags")
            ],
            [
                InlineKeyboardButton(text="🔄 Переключить активность", callback_data="toggle_activity")
            ]
        ]
    )
    return keyboard

def get_activity_status_keyboard(is_active):
    """Клавиатура для отображения статуса активности"""
    status = "🟢 Активен" if is_active else "🔴 Неактивен"
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=f"Статус: {status}", callback_data="toggle_activity")
            ],
            [
                InlineKeyboardButton(text="🔄 Переключить", callback_data="toggle_activity")
            ]
        ]
    )
    return keyboard

def get_deanon_keyboard():
    """Клавиатура для запроса на раскрытие личности"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Согласен", callback_data="deanon_approve"),
                InlineKeyboardButton(text="❌ Отказываюсь", callback_data="deanon_reject")
            ]
        ]
    )
    return keyboard

def get_chat_inline_keyboard():
    """Inline клавиатура для чата"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="👋 Раскрыть личность", callback_data="request_deanon"),
                InlineKeyboardButton(text="❌ Завершить чат", callback_data="end_chat")
            ],
            [
                InlineKeyboardButton(text="📊 Инфо о чате", callback_data="chat_info"),
                InlineKeyboardButton(text="💡 Советы", callback_data="chat_tips")
            ]
        ]
    )
    return keyboard

def get_help_keyboard():
    """Клавиатура для раздела помощи"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="❓ Как пользоваться", callback_data="help_usage"),
                InlineKeyboardButton(text="🔍 Поиск собеседника", callback_data="help_search")
            ],
            [
                InlineKeyboardButton(text="👤 Профиль", callback_data="help_profile"),
                InlineKeyboardButton(text="💬 Чат", callback_data="help_chat")
            ]
        ]
    )
    return keyboard

def get_main_inline_keyboard():
    """Основная клавиатура с главными функциями"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔍 Найти собеседника", callback_data="find_chat")
            ],
            [
                InlineKeyboardButton(text="👤 Мой профиль", callback_data="my_profile"),
                InlineKeyboardButton(text="ℹ️ Помощь", callback_data="help")
            ]
        ]
    )
    return keyboard

def get_cancel_search_keyboard():
    """Клавиатура для отмены поиска собеседника"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="❌ Отменить поиск", callback_data="cancel_search")
            ]
        ]
    )
    return keyboard

def get_gender_inline_keyboard():
    """Inline клавиатура для выбора пола"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Мужской", callback_data="gender_male"),
                InlineKeyboardButton(text="Женский", callback_data="gender_female")
            ],
            [
                InlineKeyboardButton(text="Другой", callback_data="gender_other")
            ]
        ]
    )
    return keyboard

def get_orientation_inline_keyboard():
    """Inline клавиатура для выбора ориентации"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Гетеро", callback_data="orientation_hetero"),
                InlineKeyboardButton(text="Гомо", callback_data="orientation_homo")
            ],
            [
                InlineKeyboardButton(text="Би", callback_data="orientation_bi"),
                InlineKeyboardButton(text="Другое", callback_data="orientation_other")
            ]
        ]
    )
    return keyboard