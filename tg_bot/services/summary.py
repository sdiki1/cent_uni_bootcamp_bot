import asyncio
import re
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from datetime import datetime, timedelta
import pytz
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker
from tg_bot.models import engine, Message
from yandex_cloud_ml_sdk import YCloudML
import time
import requests
import os

TOKEN = os.getenv("TOKEN")
YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")
YANDEX_API_KEY = os.getenv("YANDEX_API_KEY")

sdk = YCloudML(folder_id=YANDEX_FOLDER_ID, auth=YANDEX_API_KEY)
def check_data(i, today_date, type_text):

    days = int(type_text)
    
    date_match = re.search(r'\*\*Дата\*\*: (\d{2}\.\d{2}\.\d{4})', i)
    if not date_match:
        return i
    event_date = datetime.strptime(date_match.group(1), "%d.%m.%Y")
    today = datetime.strptime(today_date, "%d.%m.%Y")
    min_date = today
    max_date = today + timedelta(days=days) 
    if min_date <= event_date <= max_date:
        return i
    else:
        return ""
    
def remove_first_line(i):
    lines = i.split("\n")
    if len(lines) > 1:
        return "\n".join(lines[1:])
    else:
        return i
    
def check_category(i, type_text):
    category = i.split("\n")[0].split(":")[-1].strip() 
    
    type2_text = {
        "deadlines": "дедлайны",
        "dosug": "проведение досуга",
        "networking": "нетворкинги"
    }
    if category not in ["Дедлайн", "Досуг", "Нетворкинг"]:
        return remove_first_line(i)
    if category == "Дедлайн" and type_text != type2_text["deadlines"]:
        print("WRONG", type_text, type2_text["deadlines"])
        return ""
    elif category == "Досуг" and type_text != type2_text["dosug"]:
        print("WRONG", type_text, type2_text["dosug"])
        return ""
    elif category == "Нетворкинг" and type_text != type2_text["networking"]:
        print("WRONG", type_text, type2_text["networking"])
        return ""

    return remove_first_line(i)

async def get_chat_history(chat_id: int) -> list:
    try:
        session = sessionmaker(bind=engine)()
        result = session.query(Message).filter(Message.chat_id == chat_id).all()
        session.close()
        return [
            {"text": msg.message_text, "date": msg.timestamp, "link": msg.link}
            for msg in result
        ]
    except Exception as e:
        print(f"Ошибка получения истории: {e}")
        return []
    finally:
        try:
            session.close()
        except:
            pass
async def yandex_gpt_summarize(text: str, type_text: str, type2_text: str, message: types.Message=None, percent=None) -> str:
    today_date = datetime.now(pytz.timezone("Europe/Moscow")).strftime("%d.%m.%Y")
    system_prompt = system_prompt = f"""
        Ты — помощник, который анализирует сообщения и извлекает из них ключевую информацию.
        Твоя задача — найти все точные {type2_text} за следующие {type_text} дней и за сегодня, выделив ключевые слова.
        !ЗАМЕНИ ВСЕ МАТНЫЕ И НЕЦЕНЗУРНЫЕ СЛОВА НА ****
        ⚠️ ВАЖНО:
        ### 1. Определения категорий:

        - **Нетворкинг**: Это волонтёрская деятельность и мероприятия, направленные на развитие студентов и установление деловых связей. Ключевые слова:
        - волонтёрство, активное мероприятие, встреча, встреча с партнёрами, деловые связи, развитие, участие, конференция, семинар, стажировка, развитие профессиональных навыков, тренинг, мастер-класс, нетворкинг, карьерный рост.
        
        - **Дедлайн**: Это сроки выполнения задач, сдача проектов, завершение работы или выполнение обязательств. Ключевые слова:
        - дедлайн, сдача, выполнение задания, стопкодинг, завершение проекта, завершение работы, срок, крайний срок, сдача отчёта, завершение работы, отчитаться, окончание, завершение, проект.

        - **Досуг**: Это мероприятия, связанные с отдыхом, развлечениями и активным отдыхом. Ключевые слова:
        - развлечение, отдых, культурное мероприятие, концерт, выставка, встреча с друзьями, активный отдых, туризм, путешествие, кино, театр, спорт, вечеринки, развлекательный центр, тренировка, мероприятие, отдых на природе, игра

        ### 2. План действий:

        1. **Определение категории**:
        - Внимательно анализируй сообщение на наличие ключевых слов из одной из категорий. Если ключевые слова присутствуют, отнеси сообщение к соответствующей категории.
        
        2. **Если сообщение не содержит явных ключевых слов**:
        - Прочитай содержание сообщения и постарайся понять, к какой категории оно относится. Например, если сообщение о важной встрече или мероприятии для карьерного роста, отнеси это к **Нетворкингу**.
        - Если сообщение связано с конкретным сроком или требованием, отнеси его к **Дедлайну**.
        - Если сообщение касается личного времени, расслабления, или мероприятия на отдых, отнеси его к **Досугу**.

        3. **Игнорирование нерелевантных сообщений**:
        - Если сообщение не имеет явных признаков из одной из категорий и не несёт полезной информации, оставь ответ пустым.
        
        4. **Проверка даты**:
        - Если дата события в сообщении не входит в указанные {type_text} дни или не является сегодняшним или завтрашним днем, проигнорируй сообщение.
        - Используй формат ДД.ММ.ГГГГ для отображения даты.
        - Если сообщение указано как "сегодня" или "завтра", отображай только соответствующие события для этих дней.

        5. **Дата события**:
        - Важно использовать дату события, а не дату отправки сообщения. Дата отправки — это только для ориентировки по времени. Отображать дату события нужно в строгом формате ДД.ММ.ГГГГ.
        
        6. **Обработка ссылок**:
        - Если в сообщении указана ссылка, добавь её в ответ.
        - Если ссылка указана как "None", игнорируй её и не добавляй в ответ.

        7. **Формат ответа**:
        - **Дата**: [дата события в формате ДД.ММ.ГГГГ]
        - **Описание**: [краткое описание события]
        - **Точное время**: [если время указано, то также включай]
        - **Ссылка**: [если ссылка есть и не равна None, добавляй её]

        8. **Пример 1**:
        Если в сообщении указано:
        - "Встреча для волонтёров по развитию бизнеса в субботу, 10.02.2025. Место: библиотека, начало в 14:00"
            - **Категория**: Нетворкинг
            - **Дата**: 10.02.2025
            - **Описание**: Встреча для волонтёров по развитию бизнеса
            - **Точное время**: 14:00
            - **Ссылка**: (если ссылка есть)

        9. **Пример 2**:
        Если в сообщении указано:
        - "Крайний срок для сдачи отчёта 12.02.2025. Необходимо отправить до 17:00"
            - **Категория**: Дедлайн
            - **Дата**: 12.02.2025
            - **Описание**: Сдача отчёта
            - **Точное время**: 17:00
            - **Ссылка**: None (если ссылка отсутствует)

        10. **Пример 3**:
        Если в сообщении указано:
        - "Выставка современного искусства в галерее, 11.02.2025, начало в 18:00"
            - **Категория**: Досуг
            - **Дата**: 11.02.2025
            - **Описание**: Выставка современного искусства
            - **Точное время**: 18:00
            - **Ссылка**: (если ссылка есть)

        #### ВАЖНО:
        - Если дата события не входит в {type_text} (например, в пределах ближайших {type_text} дней), проигнорируй сообщение.
        - Строго придерживайся формата даты, времени и ссылки.
        - Если сообщение относится к нескольким категориям, выбери ту, которая наиболее релевантна. Например, если в сообщении упоминается сдача работы и семинар, то отнеси его к **Дедлайну**, а не к **Нетворкингу**.
        - Если категория не соответствует {type2_text}, то не надо её добавлять!!!
        - Если нет сообщений, ТО НЕ НАДО ИХ ДОБАВЛЯТЬ!!!
        !!!! ПОМНИ! ВЫПОЛНЯЙ ВСЕ ТРЕБОВАНИЯ ВЫШЕ !!!!!

        Формат ответа (если есть данные):
        **Категория**: [категория]
        **Дата**: [дата]
        **Описание**: [краткое описание]
        **Точное время**: [время, если указано]
        **Ссылка**: [ссылка, если имеется и не равна None]
        """



    body = {
        "modelUri": f"gpt://{YANDEX_FOLDER_ID}/yandexgpt-32k/rc",
        "completionOptions": {"stream": False, "temperature": 0.3, "maxTokens": 20000},
        "messages": [
            {"role": "system", "text": system_prompt},
            {"role": "user", "text": text},
        ],
    }
    
    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completionAsync"
    headers = {"Content-Type": "application/json", "Authorization": f"Api-Key {YANDEX_API_KEY}"}
    
    response = requests.post(url, headers=headers, json=body)
    print(response)
    print(response.text)
    operation_id = response.json().get("id")
    if message:
        await message.edit_text(f"⏳ Обработка сообщений: {percent}%")
    
    while True:
        response = requests.get(f"https://llm.api.cloud.yandex.net:443/operations/{operation_id}", headers=headers)
        if response.json().get("done"):
            break
        time.sleep(0.5)
    data = response.json()["response"]["alternatives"][0]["message"]["text"].split("\n\n")
    text = ""
    for i in data:
        l = False
        if "**Категория**" in i:
            data = check_category(i, type2_text)
            i = data
        if "**Дата**" in i:
            data = check_data(i, today_date, type_text)
            i = data
        if "**Ссылка**: None" in i:
            l = True
            text += i.replace("**Ссылка**: None", "") + "\n\n"
        if not l and i != "":
            text += i + "\n\n"
    
    return text

async def summarize_messages(messages: list, type_text: str, type2_text: str, max_percent: int, percent_now:int, message: types.Message, batch_size: int = 50) -> str:
    unique_messages = []
    seen_texts = set() 

    for msg in messages:
        if msg["text"] not in seen_texts:
            unique_messages.append(msg)
            seen_texts.add(msg["text"])
    all_text = "\n".join([f'[{msg["text"]}] - [{msg["date"]}] - [{msg["link"]}]' for msg in unique_messages])
    progress = (max_percent + percent_now*2)//3
    await message.edit_text(f"⏳ Обработка сообщений: {progress}%")
    progress = (max_percent*2 + percent_now)//3
    summary = await yandex_gpt_summarize(all_text, type_text, type2_text, message, progress)
    
    return summary

async def process_chat_summary(chats: list[int], user_id: int, days: str, category: str, bot: Bot, message: types.Message):
    type_text = {"period_month": "31", "period_week": "7", "period_day": "1"}.get(days, "1")
    type2_text = {"deadlines": "дедлайны", "dosug": "проведение досуга", "networking": "нетворкинги"}.get(category, "события")
    # await message.edit_reply_markup()
    message = await message.edit_text(f"⏳ Обработка сообщений за {type_text}...")
    summaries = []
    total_chats = len(chats)
    
    for index, chat_id in enumerate(chats, start=1):
        messages = await get_chat_history(chat_id)
        if messages:
            max_percent = (index / total_chats) * 100
            percent_now = ((index-1) / total_chats) * 100
            summary = await summarize_messages(messages, type_text, type2_text, max_percent, percent_now, message)
            if summary.strip():
                summaries.append(summary)
        progress = round((index / total_chats) * 100)
        await message.edit_text(f"⏳ Обработка сообщений: {progress}%")
    
    if summaries:
        final_summary = "\n------------------------------\n".join(summaries)
        await message.edit_text(f"📊 **Итоговая выжимка:**\n\n{final_summary}", parse_mode="Markdown")
    else:
        await message.edit_text("📊 **Нет релевантных данных за выбранный период.**", parse_mode="Markdown")

