# ONVUG Bot

Telegram-бот с ИИ, балансами, рефералкой и поддержкой зеркал (white-label).

## Возможности

- Умный чат с ротацией API-ключей (бутерброд)
- Генерация картинок
- Решение задач по фото
- Три баланса: основной / бонусный / выводимый
- Гибкая реферальная система
- Тарифы и пополнение
- Админка с добавлением API-ключей прямо в боте
- Архитектура под full и empty зеркала

## Быстрый старт (локально)

1. Создай бота у [@BotFather](https://t.me/BotFather)
2. Скопируй `.env.example` → `.env`
3. Впиши токен и свой Telegram ID:

```env
BOT_TOKEN=123456:ABC...
ADMIN_IDS=твой_id
```

4. Установи зависимости:

```bash
pip install -r requirements.txt
```

5. Запусти:

```bash
python main.py
```

## Добавление API-ключей

После запуска бота:

1. Напиши боту `/admin`
2. Нажми **🔑 API ключи** → **➕ Добавить ключ**
3. По шагам введи провайдера, название, ключ, модель, URL и лимит

Поддерживаются любые OpenAI-совместимые API: Groq, OpenRouter, Gemini, Together и др.

## Деплой

Бот готов к запуску на любом сервисе, который умеет держать Python-процесс:

- Railway
- Render
- Fly.io
- Koyeb
- VPS

Нужные переменные окружения:
- `BOT_TOKEN`
- `ADMIN_IDS`

База SQLite будет создаваться автоматически в папке `data/`.

## Структура

```
onvug_bot/
├── main.py
├── config.py
├── database.py
├── keyboards.py
├── handlers/
│   ├── start.py
│   ├── profile.py
│   ├── ai_chat.py
│   └── admin.py
└── services/
    ├── ai.py          # ротация ключей
    ├── balance.py     # балансы
    └── mirrors.py     # зеркала
```
