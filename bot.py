import os
import asyncio
import random
from datetime import datetime, timedelta
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import FSInputFile
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import google.generativeai as genai
from tavily import TavilyClient
import requests
from icalendar import Calendar, Event
import pytz

# Загрузка переменных окружения
load_dotenv()

# Конфигурация
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
TAVILY_API_KEY = os.getenv('TAVILY_API_KEY')
OPENWEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY')
GOOGLE_SHEETS_ID = os.getenv('GOOGLE_SHEETS_ID')
GOOGLE_CREDENTIALS_FILE = os.getenv('GOOGLE_CREDENTIALS_FILE', 'credentials.json')

# Инициализация
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
genai.configure(api_key=GEMINI_API_KEY)
tavily_client = TavilyClient(api_key=TAVILY_API_KEY)

# Google Sheets подключение
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_CREDENTIALS_FILE, scope)
sheets_client = gspread.authorize(creds)
spreadsheet = sheets_client.open_by_key(GOOGLE_SHEETS_ID)

# Листы Google Sheets
profile_sheet = spreadsheet.worksheet('Profile')
tasks_sheet = spreadsheet.worksheet('Tasks')
habits_sheet = spreadsheet.worksheet('Habits')
stats_sheet = spreadsheet.worksheet('Stats')

# Gemini модель
model = genai.GenerativeModel('gemini-2.0-flash-exp')

# Системный промпт для Оли-ли
SYSTEM_PROMPT = """Ты — Оля-ля, цифровая стерва-ассистентка и лучшая подруга пользователя.

ТВОЙ ХАРАКТЕР:
- Жёсткая, саркастичная, говоришь прямо и без жалости
- Используешь мат естественно, как в разговоре с близкой подругой
- Не жалеешь, а мотивируешь и прокачиваешь
- Профессиональный психолог, коуч и ментор
- Спокойно говоришь о сексе, отношениях, эмоциях
- Даёшь дельные советы, но с сарказмом
- Провокационная, задаёшь неудобные вопросы
- Никогда не предашь, но и не будешь нянчиться

СТИЛЬ ОБЩЕНИЯ:
- Короткие, ёмкие фразы
- Сарказм и ирония
- Мат к месту
- Без лишней вежливости
- Прямые вопросы в лоб
- Мотивация через жёсткость

ПРИМЕРЫ ФРАЗ:
- "Вставай, лентяй, мир не будет ждать твою жопу"
- "Опять ноешь? Давай по делу, что случилось"
- "Ты сам знаешь ответ, хватит прятаться"
- "Ебать, ну ты и размазня. Соберись уже"
- "Хорош страдать хуйнёй, делай что надо"

Ты знаешь о пользователе ВСЁ (профиль загружается из базы). Используй эту информацию для персонализированных советов."""

# Вопросы для онбординга
ONBOARDING_QUESTIONS = [
    "Ну что, давай знакомиться. Как тебя зовут?",
    "Окей, теперь о сексе. Что тебе нравится? Какие позы, с кем, когда, где? Не стесняйся, я не твоя мамка.",
    "В отношениях сейчас? Если нет — почему рассталась? Давай без соплей, честно.",
    "Какую музыку слушаешь? Что заводит, что успокаивает?",
    "Любимые фильмы? Что пересматриваешь, когда хреново?",
    "Какое время года любишь и почему?",
    "Как любишь отдыхать? Активно или лежать пластом?",
    "Кого любишь? Людей, животных, себя?",
    "А кого ненавидишь? Давай честно, без политкорректности."
]

# Хранилище состояний онбординга
onboarding_states = {}

# === ФУНКЦИИ РАБОТЫ С GOOGLE SHEETS ===

def get_user_profile(user_id):
    """Получить профиль пользователя"""
    try:
        records = profile_sheet.get_all_records()
        for record in records:
            if str(record.get('user_id')) == str(user_id):
                return record
        return None
    except Exception as e:
        print(f"Ошибка получения профиля: {e}")
        return None

def save_user_profile(user_id, profile_data):
    """Сохранить профиль пользователя"""
    try:
        existing = get_user_profile(user_id)
        if existing:
            # Обновить существующую запись
            records = profile_sheet.get_all_records()
            for i, record in enumerate(records, start=2):
                if str(record.get('user_id')) == str(user_id):
                    row_data = [user_id] + list(profile_data.values())
                    profile_sheet.update(f'A{i}:J{i}', [row_data])
                    return
        else:
            # Добавить новую запись
            row_data = [user_id] + list(profile_data.values())
            profile_sheet.append_row(row_data)
    except Exception as e:
        print(f"Ошибка сохранения профиля: {e}")

def get_user_tasks(user_id):
    """Получить задачи пользователя"""
    try:
        records = tasks_sheet.get_all_records()
        return [r for r in records if str(r.get('user_id')) == str(user_id) and not r.get('completed')]
    except Exception as e:
        print(f"Ошибка получения задач: {e}")
        return []

def get_user_stats(user_id):
    """Получить статистику пользователя"""
    try:
        records = stats_sheet.get_all_records()
        return [r for r in records if str(r.get('user_id')) == str(user_id)]
    except Exception as e:
        print(f"Ошибка получения статистики: {e}")
        return []

# === ФУНКЦИИ ВНЕШНИХ API ===

def get_weather(city="Kostroma"):
    """Получить погоду через OpenWeatherMap"""
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_API_KEY}&units=metric&lang=ru"
        response = requests.get(url)
        data = response.json()
        
        temp = data['main']['temp']
        feels_like = data['main']['feels_like']
        description = data['weather'][0]['description']
        
        return f"🌡 {temp}°C (ощущается как {feels_like}°C), {description}"
    except Exception as e:
        print(f"Ошибка получения погоды: {e}")
        return "Погода недоступна"

def search_web(query):
    """Поиск через Tavily"""
    try:
        response = tavily_client.search(query, max_results=3)
        results = []
        for result in response.get('results', []):
            results.append(f"• {result['title']}: {result['content'][:200]}...")
        return "\n".join(results) if results else "Ничего не найдено"
    except Exception as e:
        print(f"Ошибка поиска: {e}")
        return "Поиск недоступен"

def generate_ics_file(tasks, user_id):
    """Генерация .ics файла для iOS календаря"""
    try:
        cal = Calendar()
        cal.add('prodid', '-//Оля-ля Bot//Tasks//RU')
        cal.add('version', '2.0')
        
        for task in tasks:
            event = Event()
            event.add('summary', task['task'])
            event.add('dtstart', datetime.strptime(task['date'], '%Y-%m-%d'))
            event.add('dtend', datetime.strptime(task['date'], '%Y-%m-%d') + timedelta(hours=1))
            event.add('description', f"Задача от Оли-ли")
            cal.add_component(event)
        
        filename = f'tasks_{user_id}.ics'
        with open(filename, 'wb') as f:
            f.write(cal.to_ical())
        
        return filename
    except Exception as e:
        print(f"Ошибка генерации .ics: {e}")
        return None

# === GEMINI AI ФУНКЦИИ ===

async def generate_ai_response(prompt, user_profile=None, use_search=False):
    """Генерация ответа через Gemini"""
    try:
        # Формируем контекст
        context = SYSTEM_PROMPT
        if user_profile:
            context += f"\n\nИНФОРМАЦИЯ О ПОЛЬЗОВАТЕЛЕ:\n{user_profile}"
        
        # Если нужен поиск
        if use_search and "?" in prompt:
            search_results = search_web(prompt)
            context += f"\n\nРЕЗУЛЬТАТЫ ПОИСКА:\n{search_results}"
        
        # Генерация
        full_prompt = f"{context}\n\nСООБЩЕНИЕ ПОЛЬЗОВАТЕЛЯ: {prompt}\n\nТВОЙ ОТВЕТ:"
        response = model.generate_content(full_prompt)
        
        return response.text
    except Exception as e:
        print(f"Ошибка Gemini: {e}")
        return "Блять, что-то с AI сломалось. Попробуй ещё раз."

# === ОБРАБОТЧИКИ КОМАНД ===

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Команда /start - онбординг"""
    user_id = message.from_user.id
    
    # Проверяем профиль
    profile = get_user_profile(user_id)
    
    if profile:
        await message.answer("А, это ты. Чё надо?")
    else:
        # Начинаем онбординг
        onboarding_states[user_id] = {'step': 0, 'answers': {}}
        await message.answer(ONBOARDING_QUESTIONS[0])

@dp.message(Command("tasks"))
async def cmd_tasks(message: types.Message):
    """Команда /tasks - экспорт задач в .ics"""
    user_id = message.from_user.id
    tasks = get_user_tasks(user_id)
    
    if not tasks:
        await message.answer("У тебя нет задач. Ленивая жопа.")
        return
    
    # Генерируем .ics файл
    ics_file = generate_ics_file(tasks, user_id)
    
    if ics_file:
        file = FSInputFile(ics_file)
        await message.answer_document(file, caption="Держи свои задачи. Импортируй в iOS календарь и делай, а не страдай хуйнёй.")
        os.remove(ics_file)
    else:
        await message.answer("Не смогла создать файл. Попробуй позже.")

@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    """Команда /stats - статистика"""
    user_id = message.from_user.id
    stats = get_user_stats(user_id)
    
    if not stats:
        await message.answer("Статистики нет. Начни трекать своё состояние.")
        return
    
    # Формируем статистику
    response = "📊 ТВОЯ СТАТИСТИКА:\n\n"
    for stat in stats[-7:]:  # Последние 7 дней
        response += f"📅 {stat['date']}\n"
        response += f"😊 Настроение: {stat['mood']}\n"
        response += f"⚡ Продуктивность: {stat['productivity']}\n"
        response += f"📝 {stat['notes']}\n\n"
    
    await message.answer(response)

# === ОБРАБОТЧИК СООБЩЕНИЙ ===

@dp.message(F.text)
async def handle_message(message: types.Message):
    """Обработка всех текстовых сообщений"""
    user_id = message.from_user.id
    text = message.text
    
    # Проверяем онбординг
    if user_id in onboarding_states:
        state = onboarding_states[user_id]
        step = state['step']
        
        # Сохраняем ответ
        if step == 0:
            state['answers']['name'] = text
        elif step == 1:
            state['answers']['sex_preferences'] = text
        elif step == 2:
            state['answers']['relationships'] = text
        elif step == 3:
            state['answers']['music'] = text
        elif step == 4:
            state['answers']['movies'] = text
        elif step == 5:
            state['answers']['season'] = text
        elif step == 6:
            state['answers']['vacation'] = text
        elif step == 7:
            state['answers']['loves'] = text
        elif step == 8:
            state['answers']['hates'] = text
        
        # Следующий вопрос
        step += 1
        state['step'] = step
        
        if step < len(ONBOARDING_QUESTIONS):
            await message.answer(ONBOARDING_QUESTIONS[step])
        else:
            # Онбординг завершён
            save_user_profile(user_id, state['answers'])
            del onboarding_states[user_id]
            
            response = await generate_ai_response(
                f"Пользователь завершил онбординг. Поприветствуй его жёстко и саркастично, скажи что теперь ты знаешь о нём всё.",
                user_profile=state['answers']
            )
            await message.answer(response)
    else:
        # Обычный чат
        profile = get_user_profile(user_id)
        
        if not profile:
            await message.answer("Сначала пройди /start, чтобы я узнала тебя получше.")
            return
        
        # Генерируем ответ с учётом профиля
        response = await generate_ai_response(
            text,
            user_profile=profile,
            use_search=True
        )
        
        await message.answer(response)

# === ФОНОВЫЕ ЗАДАЧИ ===

async def send_morning_message():
    """Утреннее сообщение в 7:00"""
    while True:
        now = datetime.now(pytz.timezone('Europe/Moscow'))
        
        # Проверяем время
        if now.hour == 7 and now.minute == 0:
            try:
                # Получаем погоду
                weather = get_weather("Kostroma")
                
                # Получаем задачи
                tasks = get_user_tasks(TELEGRAM_CHAT_ID)
                tasks_text = "\n".join([f"• {t['task']}" for t in tasks[:5]]) if tasks else "Задач нет, лентяй."
                
                # Генерируем саркастическое сообщение
                prompt = f"Создай утреннее сообщение с сарказмом. Погода: {weather}. Задачи: {tasks_text}"
                message_text = await generate_ai_response(prompt)
                
                # Отправляем
                await bot.send_message(TELEGRAM_CHAT_ID, f"☀️ ДОБРОЕ УТРО, СОНЯ!\n\n{message_text}\n\n🌤 {weather}\n\n📋 ЗАДАЧИ:\n{tasks_text}")
                
                # Ждём до следующего дня
                await asyncio.sleep(86400)
            except Exception as e:
                print(f"Ошибка утреннего сообщения: {e}")
                await asyncio.sleep(60)
        else:
            await asyncio.sleep(60)

async def send_random_messages():
    """Случайные сообщения 3-5 раз в день"""
    while True:
        try:
            # Случайный интервал 3-6 часов
            interval = random.randint(3, 6) * 3600
            await asyncio.sleep(interval)
            
            # Проверяем время (только с 7:00 до 23:00)
            now = datetime.now(pytz.timezone('Europe/Moscow'))
            if 7 <= now.hour < 23:
                # Случайная тема
                topics = [
                    "Как самочувствие? Не сдохла ещё?",
                    "Чё делаешь? Опять страдаешь хуйнёй?",
                    "Задачи выполнила или опять отмазки?",
                    "Как настроение? Ноешь или действуешь?",
                    "Ебать, ты ещё жива? Отпишись."
                ]
                
                topic = random.choice(topics)
                
                # Генерируем сообщение
                profile = get_user_profile(TELEGRAM_CHAT_ID)
                message_text = await generate_ai_response(
                    f"Создай короткое провокационное сообщение на тему: {topic}",
                    user_profile=profile
                )
                
                await bot.send_message(TELEGRAM_CHAT_ID, message_text)
        except Exception as e:
            print(f"Ошибка случайного сообщения: {e}")
            await asyncio.sleep(3600)

# === ЗАПУСК БОТА ===

async def main():
    """Главная функция"""
    # Запускаем фоновые задачи
    asyncio.create_task(send_morning_message())
    asyncio.create_task(send_random_messages())
    
    # Запускаем бота
    print("🚀 Оля-ля запущена!")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
