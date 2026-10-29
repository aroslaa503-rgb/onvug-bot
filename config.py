import os
from dotenv import load_dotenv

load_dotenv()

# === Основные настройки ===
BOT_TOKEN = os.getenv("BOT_TOKEN", "ВАШ_ТОКЕН_СЮДА")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "123456789").split(",") if x.strip()]

# === База данных ===
DB_PATH = "data/bot.db"

# === Лимиты бесплатного тарифа ===
FREE_DAILY_REQUESTS = 15          # запросов в день
FREE_DAILY_IMAGES = 3             # картинок в день
FREE_COOLDOWN_SECONDS = 8         # минимальная пауза между запросами

# === Реферальная система (гибкая) ===
REFERRAL_ENABLED = True           # Можно полностью отключить
REFERRAL_PERCENT = 7              # Общий % с пополнения реферала

# Как делим реферальный %:
# 0.5 = 50% на выводимый баланс, 50% на бонусный
REFERRAL_WITHDRAWABLE_SHARE = 0.5

# Бонусы при регистрации по рефке (разовые)
REFERRAL_BONUS_FOR_INVITER = 30   # бонус пригласившему (на bonus_balance)
REFERRAL_BONUS_FOR_NEWBIE = 15    # бонус новичку (на bonus_balance)

# === Зеркала / White-label ===
# Минимальные цены, ниже которых full-партнёр ставить не может
MIN_TARIFF_PRICES = {
    "week": 39,
    "month": 399,
    "pro": 899,
    "business": 1790,
}

# Условия для empty-зеркал (пустой конструктор)
EMPTY_MIRROR_FIXED_PRICE = 1990      # фикс цена в месяц (если выбирает fixed)
EMPTY_MIRROR_DEFAULT_PERCENT = 30    # наша доля в % (если выбирает percent)

# Создание full-зеркала
FULL_MIRROR_PRICE = 990              # разовая или месячная цена за full-копию (можно потом изменить)

# === Тарифы (можно менять в админке позже) ===
TARIFFS = {
    "week": {
        "name": "Тест на неделю",
        "price": 39,
        "days": 7,
        "daily_requests": 80,
        "daily_images": 15,
    },
    "month": {
        "name": "Месяц",
        "price": 399,
        "days": 30,
        "daily_requests": 200,
        "daily_images": 40,
    },
    "pro": {
        "name": "PRO на месяц",
        "price": 899,
        "days": 30,
        "daily_requests": 500,
        "daily_images": 100,
    },
    "business": {
        "name": "Бизнес",
        "price": 1790,
        "days": 30,
        "daily_requests": 2000,
        "daily_images": 300,
    },
}

# === Цены разовых услуг (в рублях) ===
PRICES = {
    "image_gen": 5,           # генерация картинки
    "photo_solve": 3,         # решение задачи по фото
    # Заглушки (пока не реализованы):
    # "photo_animate": 105,
    # "create_site": 990,
    # "create_miniapp": 1490,
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