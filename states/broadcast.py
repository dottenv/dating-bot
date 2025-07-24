from aiogram.fsm.state import State, StatesGroup

class BroadcastStates(StatesGroup):
    waiting_content = State()
    waiting_buttons = State()
    confirm = State()