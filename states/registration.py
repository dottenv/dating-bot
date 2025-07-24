from aiogram.fsm.state import StatesGroup, State

class RegistrationStates(StatesGroup):
    first_name = State()
    age = State()
    city = State()
    gender = State()
    orientation = State()
    dating_goal = State()
    about = State()
    tags = State()
    photo = State()