from aiogram.fsm.state import State, StatesGroup

class AdStates(StatesGroup):
    waiting_content = State()
    waiting_buttons = State()
    waiting_settings = State()
    confirm = State()
    creating = State()  # Новое состояние для пошагового создания