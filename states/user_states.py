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
    waiting = State()
    chatting = State()
    deanon_request = State()