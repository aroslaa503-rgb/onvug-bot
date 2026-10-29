import os
from dotenv import load_dotenv

load_dotenv()

# === Основные настройки ===
BOT_TOKEN = os.getenv("BOT_TOKEN", "ВАШ_ТОКЕН_СЮДА")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "123456789").split(",") if x.strip()]

# === База данных ===
# ИСПРАВЛЕНО: используем /tmp, чтобы сервер мог создать базу
DB_PATH = "/tmp/bot.db"

# === Лимиты бесплатного тарифа ===
FREE_DAILY_REQUESTS = 15
FREE_DAILY_IMAGES = 3
FREE_COOLDOWN_SECONDS = 8

# === Реферальная система ===
REFERRAL_ENABLED = True
REFERRAL_PERCENT = 7
REFERRAL_WITHDRAWABLE_SHARE = 0.5
REFERRAL_BONUS_FOR_INVITER = 30
REFERRAL_BONUS_FOR_NEWBIE = 15

# === Зеркала ===
MIN_TARIFF_PRICES = {
    "week": 39,
    "month": 399,
    "pro": 899,
    "business": 1790,
}
EMPTY_MIRROR_FIXED_PRICE = 1990
EMPTY_MIRROR_DEFAULT_PERCENT = 30
FULL_MIRROR_PRICE = 990

# === Тарифы ===
TARIFFS = {
    "week": {
        "name": "Тест • 7 дней",
        "price": 39,
        "days": 7,
        "daily_requests": 80,
        "daily_images": 15,
    },
    "month": {
        "name": "Стандарт • 30 дней",
        "price": 399,
        "days": 30,
        "daily_requests": 200,
        "daily_images": 40,
    },
    "pro": {
        "name": "PRO • 30 дней",
        "price": 899,
        "days": 30,
        "daily_requests": 500,
        "daily_images": 100,
    },
    "business": {
        "name": "Бизнес • 30 дней",
        "price": 1790,
        "days": 30,
        "daily_requests": 2000,
        "daily_images": 300,
    },
}

PRICES = {
    "image_gen": 5,
    "photo_solve": 3,
}

# ================== ТЕКСТЫ ==================

WELCOME_TEXT = """👋 <b>Привет!</b>

Я — ИИ-помощник для учёбы, работы и творчества.

<b>Что умею:</b>
• Решать задачи по фото
• Отвечать на любые вопросы
• Генерировать картинки
• Помогать с домашкой и текстами

Бесплатно доступно несколько запросов в день.
Подписка снимает ограничения.

Выбери действие в меню 👇"""

HELP_TEXT = """ℹ️ <b>Помощь</b>

<b>Основные функции:</b>
• Просто напиши вопрос — отвечу
• Пришли фото задачи — решу по шагам
• Напиши «нарисуй ...» — создам картинку

<b>Лимиты:</b>
На бесплатном тарифе есть дневные ограничения.
Чтобы убрать их — оформи подписку в разделе «Тарифы».

<b>Скоро:</b>
• Оживление фото
• Создание сайтов
• Mini App
• Деплой кода

По вопросам пиши администратору."""

PROFILE_TEMPLATE = """👤 <b>Профиль</b>

ID: <code>{user_id}</code>
С нами: {days_with_us} дн.

💰 <b>Баланс</b>
Основной: {main_balance} ₽
Бонусный: {bonus_balance} ₽
К выводу: {withdrawable_balance} ₽

📊 Сегодня:
Запросы: {used_requests}/{max_requests}
Картинки: {used_images}/{max_images}

🔗 Твоя ссылка:
<code>https://t.me/{bot_username}?start={user_id}</code>"""

REFERRAL_TEXT = """🔗 <b>Реферальная система</b>

Твоя ссылка:
<code>https://t.me/{bot_username}?start={user_id}</code>

Приглашено: {invited}
Заработано: {earned} ₽

Ты получаешь <b>{percent}%</b> с каждого пополнения друга.
Новичок получает {newbie_bonus} ₽ бонусом, ты — {inviter_bonus} ₽."""

TARIFFS_TEXT = """💎 <b>Тарифы</b>

Выбери подходящий план:"""
