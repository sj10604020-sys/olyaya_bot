# 🔥 Оля-ля — Цифровая Стерва-Ассистентка

Telegram-бот на базе Google Gemini AI, который знает о тебе всё, будит в 7:00 с сарказмом и не жалеет, а прокачивает.

## 🎯 Возможности

- **Онбординг**: Провокационные вопросы о сексе, отношениях, музыке, фильмах
- **Утренние сообщения**: Каждый день в 7:00 (погода + задачи + сарказм)
- **Случайные сообщения**: 3-5 раз в день с пошлыми провокациями
- **AI-чат**: Жёсткие советы с матом от лучшей подруги
- **Команды**:
  - `/start` — онбординг
  - `/tasks` — экспорт задач в .ics для iOS
  - `/stats` — статистика по настроению/продуктивности

## 🚀 Установка

### 1. Клонируй репозиторий

```bash
git clone https://github.com/твой-username/olyalya-bot.git
cd olyalya-bot
2. Установи зависимости
pip install -r requirements.txt
3. Настрой API ключи
Создай файл .env (скопируй из .env.example):

cp .env.example .env
Заполни все ключи:

TELEGRAM_BOT_TOKEN=8343550292:AAH-8vti-5Xxuef7ikMKoBhW-MVXLfq36Ts
TELEGRAM_CHAT_ID=760163261
GEMINI_API_KEY=AIzaSyA0Qa9NXly1oprXNIzHYXsmAqWPBfFx27g
TAVILY_API_KEY=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
OPENWEATHER_API_KEY=6dc1bb3b42fe36099970bfa778c92e98
GOOGLE_SHEETS_ID=1DRfeO9LsRkG5LbNBcmsxemW8oST5AqZnCSVVfLd2kek
4. Настрой Google Sheets
Создай Service Account в Google Cloud Console
Скачай JSON ключ и сохрани как credentials.json
Дай доступ к таблице (email из JSON)
Создай 4 листа: Profile, Tasks, Habits, Stats
5. Запусти бота
python bot.py
📦 Деплой на Railway
Создай аккаунт на Railway.app
Подключи GitHub репозиторий
Добавь переменные окружения (все из .env)
Загрузи credentials.json через Railway CLI или переменную
Deploy!
📊 Структура Google Sheets
Лист "Profile":

user_id | name | sex_preferences | relationships | music | movies | season | vacation | loves | hates
Лист "Tasks":

task_id | user_id | task | date | completed
Лист "Habits":

habit_id | user_id | habit | frequency | last_done
Лист "Stats":

date | user_id | mood | productivity | notes
🔧 Технологии
Python 3.11+
aiogram — Telegram Bot API
Google Gemini — AI модель
Tavily — поиск информации
OpenWeatherMap — погода
Google Sheets — база данных
Railway — хостинг
📝 Лицензия
MIT

💬 Автор
Создано с любовью и сарказмом 🔥
