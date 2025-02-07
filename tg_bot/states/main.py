from aiogram.dispatcher.filters.state import State, StatesGroup


class SummaryState(StatesGroup):
    choosing_chat = State()
    choosing_period = State()
    summarizing = State()
    choosing_category = State()
