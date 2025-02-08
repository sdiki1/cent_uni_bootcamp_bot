from aiogram.types import (
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)


def choose_chats(chats):
    markup = InlineKeyboardMarkup()
    for chat in chats:
        markup.add(
            InlineKeyboardButton(
                text=f'💬 {chat["title"]}', callback_data="CHAT_ID_" + str(chat["chat_id"])
            )
        )
    markup.row(
        InlineKeyboardButton(
            text="❓ Нужна помощь?",
            callback_data="HELP_ADDING_TO_CHAT"
        )
    )
    return markup

async def generate_chats_keyboard(chats, selected_chats):
    markup = InlineKeyboardMarkup()
    
    for chat in chats:
        emoji = "✅" if chat['chat_id'] in selected_chats else "✖️"
        btn_text = f"{emoji} 💬 {chat['title']}"
        markup.add(InlineKeyboardButton(
            text=btn_text,
            callback_data=f"TOGGLE_CHAT_{chat['chat_id']}"
        ))
    
    if selected_chats:
        markup.row(InlineKeyboardButton(
            text="🚀 Далее",
            callback_data="PROCEED_TO_CATEGORY"
        ))
    
    markup.row(InlineKeyboardButton(
        text="❓ Помощь",
        callback_data="HELP_ADDING_TO_CHAT"
    ))
    return markup

def check_again_keyboard():
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton(
            text="✅ Сделал! Проверить!",
            callback_data="CHECK_BOT"
        )
    )
    return markup
def get_help_markup():
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton(
            text="❓ Нужна помощь?",
            callback_data="HELP_ADDING_TO_CHAT"
        )
    )
    return markup

def choose_period():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(text="Завтра", callback_data="period_tomorrow"))
    markup.add(
        InlineKeyboardButton(text="В течение недели", callback_data="period_week")
    )
    markup.add(
        InlineKeyboardButton(text="В течение месяца", callback_data="period_month")
    )
    return markup


def choose_category():
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton(text="Нетворкинг", callback_data="CATEGORY_networking")
    )
    markup.add(InlineKeyboardButton(text="Досуг", callback_data="CATEGORY_dosug"))
    markup.add(
        InlineKeyboardButton(text="Дедлайны", callback_data="CATEGORY_deadlines")
    )
    return markup
