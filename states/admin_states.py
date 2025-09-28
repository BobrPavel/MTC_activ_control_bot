from aiogram.fsm.state import StatesGroup, State

class AddCard(StatesGroup):
    name = State()
    image = State()

class AddUser(StatesGroup):
    name = State()
