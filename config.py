import os
from dotenv import load_dotenv

load_dotenv()

# === Основные настройки ===
BOT_TOKEN = os.getenv("BOT_TOKEN", "ВАШ_ТОКЕН_СЮДА")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "123456789").split(",") if x.strip()]

# === База данных ===
# ИСПРАВЛЕНО: используем /tmp и новое имя файла, чтобы база создалась заново
DB_PATH = "/tmp/bot_v2.db"

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

# === Зеркала / White-label ===
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
    "week": {"name": "Тест на неделю", "price": 39, "days": 7, "daily_requests": 80, "daily_images": 15},
    "month": {"name": "Месяц", "price": 399, "days": 30, "daily_requests": 200, "daily_images": 40},
    "pro": {"name": "PRO на месяц", "price": 899, "days": 30, "daily_requests": 500, "daily_images": 100},
    "business": {"name": "Бизнес", "price": 1790, "days": 30, "daily_requests": 2000, "daily_images": 300},
}

# === Цены разовых услуг ===
PRICES = {
    "image_gen": 5,
    "photo_solve": 3,
}

# === Сообщения ===
WELCOME_TEXT = """👋 Привет! Я — твой универсальный ИИ-помощник.

Что я умею прямо сейчас:

📸 <b>Решение задач по фото</b> — просто пришли фото задачи
💬 <b>Умный чат</b> — задавай любые вопросы
🎨 <b>Генерация картинок</b> — напиши «нарисуй ...»
📖 Помощь с домашкой, сочинениями, объяснениями

Бесплатно доступно ограниченное количество запросов в день.
Подписка открывает гораздо больше возможностей.

Нажми кнопку ниже, чтобы начать 👇"""

PROFILE_TEMPLATE = """👤 <b>Твой профиль</b>

🆔 ID: <code>{user_id}</code>
📅 С нами: {days_with_us} дн.

💰 <b>Баланс</b>
• Бесплатный: {free_balance} ₽
• Бонусный: {bonus_balance} ₽
• Платный: {paid_balance} ₽

📊 Сегодня использовано:
• Запросов: {used_requests}/{max_requests}
• Картинок: {used_images}/{max_images}

🔗 Реферальная ссылка:
<code>https://t.me/{bot_username}?start={user_id}</code>

Приглашай друзей — получай {ref_percent}% с их пополнений!"""
