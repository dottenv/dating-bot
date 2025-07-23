from aiogram.fsm.state import State, StatesGroup

class UserRegistration(StatesGroup):
    first_name = State()
    age = State()
    gender = State()
    orientation = State()
    city = State()
    bio = State()
    photo = State()
    tags = State()

class AnonymousChatting(StatesGroup):
    waiting = State()     # Ожидание собеседника
    confirming = State()  # Подтверждение чата с пользователем с низким рейтингом
    chatting = State()    # Активный чат
    deanon_request = State()  # Запрос на раскрытие личности

# Состояния для жалоб удалены, так как они больше не нужны