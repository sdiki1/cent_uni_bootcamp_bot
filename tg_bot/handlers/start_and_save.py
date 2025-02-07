from aiogram import types, Dispatcher
from tg_bot.models import save_message_to_db
from tg_bot.models import create_chat
import asyncio
from tg_bot.services import get_user_chats
from tg_bot.keyboards import choose_chats
from datetime import datetime, timedelta
from aiogram.utils.exceptions import MessageToDeleteNotFound, TelegramAPIError
from typing import Optional
from tg_bot.states import SummaryState
import logging

logger = logging.getLogger(__name__)


async def add_handler(message: types.Message):
    bot = message.bot
    bot_id = (await bot.get_me()).id
    new_members = message.new_chat_members
    
    welcome_text = (
        "Приветствую вас! 😊 Спасибо, что добавили меня в этот канал! "
        "Я очень рад быть здесь!\n\nЧто я могу для вас сделать? 🤔\n\n"
        "- Составить краткий и структурированный пересказ данных за любой период\n"
        "- Напомнить о ближайших дедлайнах ⏰\n"
        "- Подсказать, чем можно заняться в течение следующего месяца 📅\n"
        "- Рассказать о волонтерских движениях и мероприятиях 🤝\n\n"
        "Просто обратитесь - и я помогу!"
    )
    if any(member.id == bot_id for member in new_members):
        chat_id = message.chat.id
        
        try:
            if create_chat(chat_id):
                await asyncio.gather(
                    message.answer(welcome_text)
                )
            else:
                logger.info(f"Бот повторно добавлен в чат {chat_id}")
        except MessageToDeleteNotFound:
            logger.warning(f"Сообщение уже удалено в чате {chat_id}")
        except TelegramAPIError as e:
            logger.error(f"Ошибка Telegram API в чате {chat_id}: {e}")
        except Exception as e:
            logger.exception(f"Неожиданная ошибка в чате {chat_id}:")


async def save_message_handler(message: types.Message) -> None:
    try:
        if message.chat.id > 0:
            await handle_private_chat(message)
            return

        if not await process_group_message(message):
            logger.warning(f"Не удалось сохранить сообщение из чата {message.chat.id}")

    except Exception as e:
        logger.error(f"Ошибка обработки сообщения: {str(e)}", exc_info=True)
        await handle_error(message)

async def handle_private_chat(message: types.Message) -> None:
    await message.answer(
        "⚠️ Вы выбрали не ту команду. Для старта используйте: /start\n\n"
        "Для работы с ботом в групповых чатах:\n"
        "1. Добавьте бота в группу\n"
        "2. Выдайте права администратора\n"
        "3. Напишите любое сообщение в группе"
    )

async def process_group_message(message: types.Message) -> bool:
    message_link = generate_message_link(message)
    message_text = message.text or ""

    try:
        save_message_to_db(
            chat_id=message.chat.id,
            user_id=message.from_user.id,
            message_text=message_text,
            link=message_link
        )
        
        log_message_details(message, message_link)
        return True

    except Exception as e:
        logger.error(f"Ошибка сохранения сообщения: {str(e)}", exc_info=True)
        return False

def generate_message_link(message: types.Message) -> Optional[str]:
    try:
        if message.chat.username:
            return f"https://t.me/{message.chat.username}/{message.message_id}"
        return None
    except AttributeError:
        logger.warning(f"Чат {message.chat.id} не имеет username")
        return None

def log_message_details(message: types.Message, link: Optional[str]) -> None:
    log_data = {
        "chat_id": message.chat.id,
        "user_id": message.from_user.id,
        "message_id": message.message_id,
        "text": message.text,
        "link": link
    }
    logger.info("Сообщение сохранено: %s", log_data)

async def handle_error(message: types.Message) -> None:
    """Отправляет пользователю сообщение об ошибке."""
    error_text = (
        "⚠️ Произошла ошибка при обработке сообщения. "
        "Попробуйте повторить позже или обратитесь в поддержку."
    )
    
    try:
        await message.answer(error_text)
    except TelegramAPIError as e:
        logger.error(f"Не удалось отправить сообщение об ошибке: {str(e)}")


async def start_handler(message: types.Message):
    if message.chat.id < 0:
        return
    chats = await get_user_chats(target_user_id=message.from_user.id, bot=message.bot)
    print(chats, " - CHATS")
    if chats != []:
        keyboard = choose_chats(chats)
        await message.answer("Выберите чат:", reply_markup=keyboard)
    else:
        await message.answer(
            "Вы не добавили меня ни в один чат. 😕\n\nИли я не могу читать сообщения  😕 Назначьте меня пожалуйтста админом группы! Тогда я смогу читать все сообщения и делать краткую выжимку)"
        )
        
    await SummaryState.choosing_chat.set()

def register_start_handlers(dp: Dispatcher):
    dp.register_message_handler(start_handler, commands=["start"])
    dp.register_message_handler(save_message_handler, content_types=types.ContentType.TEXT)
    dp.register_message_handler(add_handler, content_types=["new_chat_members"])
    