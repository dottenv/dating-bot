from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Константы для callback_data
# Основные разделы
MAIN_MENU = "main_menu"
FIND_CHAT = "find_chat"
MY_PROFILE = "my_profile"
HELP_MENU = "help_menu"
BACK_TO_MAIN = "back_to_main"

# Профиль
EDIT_PROFILE = "edit_profile"
TOGGLE_ACTIVITY = "toggle_activity"
EDIT_NAME = "edit_name"
EDIT_AGE = "edit_age"
EDIT_GENDER = "edit_gender"
EDIT_ORIENTATION = "edit_orientation"
EDIT_CITY = "edit_city"
EDIT_BIO = "edit_bio"
EDIT_PHOTO = "edit_photo"
EDIT_TAGS = "edit_tags"
BACK_TO_PROFILE = "back_to_profile"

# Чат
CHAT_MENU = "chat_menu"
REQUEST_DEANON = "request_deanon"
END_CHAT = "end_chat"
CHAT_INFO = "chat_info"
REPORT_USER = "report_user"
CANCEL_SEARCH = "cancel_search"
CONFIRM_CHAT = "confirm_chat"
REJECT_CHAT = "reject_chat"

# Деанон
DEANON_APPROVE = "deanon_approve"
DEANON_REJECT = "deanon_reject"

# Жалобы - упрощенная версия

# Помощь
HELP_USAGE = "help_usage"
HELP_SEARCH = "help_search"
HELP_PROFILE = "help_profile"
HELP_CHAT = "help_chat"
BACK_TO_HELP = "back_to_help"

# Админ
ADMIN_APPROVE_REPORT = "admin_approve_report_"
ADMIN_REJECT_REPORT = "admin_reject_report_"
ADMIN_VIEW_REPORT = "admin_view_report_"

# Выбор пола и ориентации
GENDER_MALE = "gender_male"
GENDER_FEMALE = "gender_female"
GENDER_OTHER = "gender_other"
ORIENTATION_HETERO = "orientation_hetero"
ORIENTATION_HOMO = "orientation_homo"
ORIENTATION_BI = "orientation_bi"
ORIENTATION_OTHER = "orientation_other"

def get_main_inline_keyboard():
    """Основная клавиатура с главными функциями"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔍 Найти собеседника", callback_data=FIND_CHAT)
            ],
            [
                InlineKeyboardButton(text="👤 Мой профиль", callback_data=MY_PROFILE),
                InlineKeyboardButton(text="ℹ️ Помощь", callback_data=HELP_MENU)
            ]
        ]
    )
    return keyboard

def get_profile_menu_keyboard(is_active=True):
    """Клавиатура для меню профиля"""
    status = "🟢 Активен" if is_active else "🔴 Неактивен"
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✏️ Редактировать профиль", callback_data=EDIT_PROFILE)
            ],
            [
                InlineKeyboardButton(text=f"Статус: {status}", callback_data=TOGGLE_ACTIVITY)
            ],
            [
                InlineKeyboardButton(text="🔄 Переключить активность", callback_data=TOGGLE_ACTIVITY)
            ],
            [
                InlineKeyboardButton(text="◀️ Назад в главное меню", callback_data=BACK_TO_MAIN)
            ]
        ]
    )
    return keyboard

def get_profile_edit_keyboard():
    """Клавиатура для редактирования профиля"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✏️ Имя", callback_data=EDIT_NAME),
                InlineKeyboardButton(text="🔢 Возраст", callback_data=EDIT_AGE)
            ],
            [
                InlineKeyboardButton(text="🧬 Пол", callback_data=EDIT_GENDER),
                InlineKeyboardButton(text="💞 Ориентация", callback_data=EDIT_ORIENTATION)
            ],
            [
                InlineKeyboardButton(text="🏙️ Город", callback_data=EDIT_CITY),
                InlineKeyboardButton(text="📝 О себе", callback_data=EDIT_BIO)
            ],
            [
                InlineKeyboardButton(text="🖼️ Фото", callback_data=EDIT_PHOTO),
                InlineKeyboardButton(text="🏷️ Интересы", callback_data=EDIT_TAGS)
            ],
            [
                InlineKeyboardButton(text="◀️ Назад к профилю", callback_data=BACK_TO_PROFILE)
            ]
        ]
    )
    return keyboard

def get_gender_inline_keyboard(include_back=True):
    """Inline клавиатура для выбора пола"""
    buttons = [
        [
            InlineKeyboardButton(text="Мужской", callback_data=GENDER_MALE),
            InlineKeyboardButton(text="Женский", callback_data=GENDER_FEMALE)
        ],
        [
            InlineKeyboardButton(text="Другой", callback_data=GENDER_OTHER)
        ]
    ]

    if include_back:
        buttons.append([
            InlineKeyboardButton(text="◀️ Назад", callback_data=EDIT_PROFILE)
        ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard

def get_orientation_inline_keyboard(include_back=True):
    """Inline клавиатура для выбора ориентации"""
    buttons = [
        [
            InlineKeyboardButton(text="Гетеро", callback_data=ORIENTATION_HETERO),
            InlineKeyboardButton(text="Гомо", callback_data=ORIENTATION_HOMO)
        ],
        [
            InlineKeyboardButton(text="Би", callback_data=ORIENTATION_BI),
            InlineKeyboardButton(text="Другое", callback_data=ORIENTATION_OTHER)
        ]
    ]

    if include_back:
        buttons.append([
            InlineKeyboardButton(text="◀️ Назад", callback_data=EDIT_PROFILE)
        ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard

def get_chat_inline_keyboard():
    """Inline клавиатура для чата"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="👋 Раскрыть личность", callback_data=REQUEST_DEANON),
                InlineKeyboardButton(text="❌ Завершить чат", callback_data=END_CHAT)
            ],
            [
                InlineKeyboardButton(text="📊 Инфо о чате", callback_data=CHAT_INFO),
            ]
        ]
    )
    return keyboard

def get_deanon_keyboard():
    """Клавиатура для запроса на раскрытие личности"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Согласен", callback_data=DEANON_APPROVE),
                InlineKeyboardButton(text="❌ Отказываюсь", callback_data=DEANON_REJECT)
            ]
        ]
    )
    return keyboard

# Функция get_report_confirmation_keyboard удалена, так как больше не нужна

def get_admin_report_keyboard(report_id: int):
    """Клавиатура для администратора для обработки жалобы"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Принять", callback_data=f"{ADMIN_APPROVE_REPORT}{report_id}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"{ADMIN_REJECT_REPORT}{report_id}")
            ],
            [
                InlineKeyboardButton(text="🔍 Подробнее", callback_data=f"{ADMIN_VIEW_REPORT}{report_id}")
            ]
        ]
    )
    return keyboard

def get_help_menu_keyboard():
    """Клавиатура для раздела помощи"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="❓ Как пользоваться", callback_data=HELP_USAGE),
                InlineKeyboardButton(text="🔍 Поиск собеседника", callback_data=HELP_SEARCH)
            ],
            [
                InlineKeyboardButton(text="👤 Профиль", callback_data=HELP_PROFILE),
                InlineKeyboardButton(text="💬 Чат", callback_data=HELP_CHAT)
            ],
            [
                InlineKeyboardButton(text="◀️ Назад в главное меню", callback_data=BACK_TO_MAIN)
            ]
        ]
    )
    return keyboard

def get_help_section_keyboard():
    """Клавиатура для возврата из раздела помощи"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="◀️ Назад к разделам помощи", callback_data=BACK_TO_HELP)
            ],
            [
                InlineKeyboardButton(text="🏠 В главное меню", callback_data=BACK_TO_MAIN)
            ]
        ]
    )
    return keyboard

def get_cancel_search_keyboard():
    """Клавиатура для отмены поиска собеседника"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="❌ Отменить поиск", callback_data=CANCEL_SEARCH)
            ]
        ]
    )
    return keyboard

def get_back_to_profile_keyboard():
    """Клавиатура для возврата к профилю"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="◀️ Назад к профилю", callback_data=BACK_TO_PROFILE)
            ]
        ]
    )
    return keyboard

def get_confirm_chat_keyboard():
    """Клавиатура для подтверждения чата с пользователем с низким рейтингом"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить", callback_data=CONFIRM_CHAT),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=REJECT_CHAT)
            ],
            [
                InlineKeyboardButton(text="❌ Отменить поиск", callback_data=CANCEL_SEARCH)
            ]
        ]
    )
    return keyboard

def get_confirm_chat_keyboard():
    """Клавиатура для подтверждения чата с пользователем с низким рейтингом"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить", callback_data=CONFIRM_CHAT),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=REJECT_CHAT)
            ],
            [
                InlineKeyboardButton(text="❌ Отменить поиск", callback_data=CANCEL_SEARCH)
            ]
        ]
    )
    return keyboard

def get_edit_or_back_keyboard():
    """Клавиатура с кнопками редактирования и возврата"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✏️ Редактировать еще", callback_data=EDIT_PROFILE),
                InlineKeyboardButton(text="◀️ Назад к профилю", callback_data=BACK_TO_PROFILE)
            ]
        ]
    )
    return keyboard
