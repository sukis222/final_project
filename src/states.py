from aiogram.fsm.state import StatesGroup, State

class ProfileStates(StatesGroup):
    NAME = State()
    AGE = State()
    GENDER = State()
    PHOTO = State()
    GOAL = State()
    DESCRIPTION = State()
    AWAIT_MODERATION = State()