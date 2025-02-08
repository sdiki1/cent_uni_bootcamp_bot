from aiogram import Dispatcher, Bot, types
from tg_bot import keyboards
from tg_bot.models import Chat, sessionmaker, engine, save_message_to_db
from tg_bot.models import create_chat
import asyncio
from tg_bot.services import get_user_chats, process_chat_summary
from tg_bot.keyboards import choose_chats, choose_period, choose_category, check_again_keyboard, generate_chats_keyboard
from datetime import datetime, timedelta
from aiogram.utils.exceptions import MessageToDeleteNotFound, TelegramAPIError
import pytz
from typing import Optional
from tg_bot.states import SummaryState
from aiogram.dispatcher import FSMContext
import logging

logger = logging.getLogger(__name__)




async def chat_chosen_handler(callback_query: types.CallbackQuery, state: FSMContext):
    chat_id = int(callback_query.data.replace("CHAT_ID_", ""))
    await state.update_data(chat_id=chat_id)
    keyboard = choose_category()
    await callback_query.message.edit_text(
        "🔹 <b>Отлично!</b> Теперь выберите категорию: 🎭🤝⏳", reply_markup=keyboard
    )
    await state.set_state(SummaryState.choosing_category)


# ---- Обработчик выбора категории ----
async def category_chosen_handler(callback_query: types.CallbackQuery, state: FSMContext):
    category = callback_query.data.replace("CATEGORY_", "")
    await state.update_data(category=category)
    keyboard = choose_period()
    await callback_query.message.edit_text(
        "📅 <b>Супер!</b> Теперь укажите период: 🔜📆", reply_markup=keyboard
    )
    await state.set_state(SummaryState.choosing_period)


# ---- Обработчик выбора периода ----
async def period_chosen_handler(callback_query: types.CallbackQuery, state: FSMContext):
    period_key = callback_query.data
    periods = {
        "period_tomorrow": timedelta(days=1),
        "period_week": timedelta(days=7),
        "period_month": timedelta(days=30),
    }
    user_data = await state.get_data()
    category = user_data.get("category")
    if period_key not in periods:
        await callback_query.answer(
            "<b>⚠️ Ой! Что-то не так.</b> Пожалуйста, выберите корректный период. ❌"
        )
        return
    chats = user_data.get("selected_chats")
    result = await process_chat_summary(
        chats, callback_query.from_user.id, period_key, category, callback_query.bot, callback_query.message
    )
    await state.finish()

async def toggle_chat_handler(callback: types.CallbackQuery, state: FSMContext):
    chat_id = int(callback.data.replace("TOGGLE_CHAT_", ""))
    
    async with state.proxy() as data:
        selected_chats = data.get('selected_chats', [])
        
        if chat_id in selected_chats:
            selected_chats.remove(chat_id)
        else:
            selected_chats.append(chat_id)
        
        data['selected_chats'] = selected_chats
        
        # Обновляем клавиатуру
        chats = await get_user_chats(callback.from_user.id, callback.bot)
        keyboard = await generate_chats_keyboard(chats, selected_chats)
        
        try:
            await callback.message.edit_reply_markup(reply_markup=keyboard)
        except:
            await callback.answer("Обновлено!")
    
    await callback.answer()

async def proceed_to_category_handler(callback: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        if not data.get('selected_chats'):
            await callback.answer("Выберите хотя бы один чат!", show_alert=True)
            return
    
    await show_category_selection(callback.message, state)
    await callback.answer()

async def show_category_selection(message: types.Message, state: FSMContext):
    keyboard = choose_category()
    
    async with state.proxy() as data:
        selected_chats = data['selected_chats']
        chat_count = len(selected_chats)
        chat_text = "чат" if chat_count == 1 else "чата" if 2 <= chat_count <= 4 else "чатов"
        
        text = (
            f"🔹 <b>Отлично!</b> Вы выбрали {chat_count} {chat_text}\n"
            "Теперь выберите категорию:"
        )
        
        try:
            await message.edit_text(text, reply_markup=keyboard)
        except:
            await message.answer(text, reply_markup=keyboard)
    
    await SummaryState.choosing_category.set()

async def help_adding_handler(callback: types.CallbackQuery):
    
    help_text = (
        "🛠 <b>Как добавить бота в чат:</b>\n\n"
        "1. Откройте настройки чата\n"
        "2. Выберите 'Добавить участника'\n"
        "3. Найдите @username_бота\n"
        "4. Назначьте права администратора\n"
        "5. Сохраните изменения\n\n"
        "✅ После этих действий бот появится в списке!"
    )
    keyboard = check_again_keyboard()
    await callback.message.edit_text(help_text, reply_markup=keyboard)

def register_main_handlers(dp: Dispatcher):

    dp.register_callback_query_handler(
        chat_chosen_handler,
        lambda c: c.data.startswith("CHAT_ID_"),
        state=SummaryState.choosing_chat,
    )
    dp.register_callback_query_handler(
        category_chosen_handler,
        lambda c: c.data.startswith("CATEGORY_"),
        state=SummaryState.choosing_category,
    )
    dp.register_callback_query_handler(
        period_chosen_handler,
        lambda c: c.data.startswith("period_"),
        state=SummaryState.choosing_period,
    )

    dp.register_callback_query_handler(help_adding_handler, text="HELP_ADDING_TO_CHAT")
    dp.register_callback_query_handler(help_adding_handler, text="HELP_ADDING_TO_CHAT", state="*")

    dp.register_callback_query_handler(
        toggle_chat_handler,
        lambda c: c.data.startswith("TOGGLE_CHAT_"),
        state=SummaryState.choosing_chats
    )
    dp.register_callback_query_handler(
        proceed_to_category_handler,
        lambda c: c.data == "PROCEED_TO_CATEGORY",
        state=SummaryState.choosing_chats
    )
