from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
import config


def main_menu_kb() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="💬 Чат с ИИ"),
        KeyboardButton(text="🎨 Создать картинку")
    )
    builder.row(
        KeyboardButton(text="📸 Решить по фото"),
        KeyboardButton(text="👤 Профиль")
    )
    builder.row(
        KeyboardButton(text="💎 Тарифы"),
        KeyboardButton(text="💰 Пополнить")
    )
    builder.row(
        KeyboardButton(text="🔗 Рефералка"),
        KeyboardButton(text="ℹ️ Помощь")
    )
    return builder.as_markup(resize_keyboard=True)


def profile_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="💎 Тарифы", callback_data="tariffs"))
    builder.row(InlineKeyboardButton(text="💰 Пополнить баланс", callback_data="topup"))
    builder.row(InlineKeyboardButton(text="🔗 Реферальная система", callback_data="referral"))
    builder.row(InlineKeyboardButton(text="« Назад", callback_data="back_to_menu"))
    return builder.as_markup()


def tariffs_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for key, tariff in config.TARIFFS.items():
        builder.row(InlineKeyboardButton(
            text=f"{tariff['name']} — {tariff['price']} ₽",
            callback_data=f"buy_tariff:{key}"
        ))
    builder.row(InlineKeyboardButton(text="« Назад", callback_data="profile"))
    return builder.as_markup()


def topup_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    amounts = [50, 100, 200, 500, 1000]
    for amount in amounts:
        builder.row(InlineKeyboardButton(
            text=f"{amount} ₽",
            callback_data=f"topup_amount:{amount}"
        ))
    builder.row(InlineKeyboardButton(text="Другая сумма", callback_data="topup_custom"))
    builder.row(InlineKeyboardButton(text="« Назад", callback_data="profile"))
    return builder.as_markup()


def cancel_kb() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="❌ Отмена"))
    return builder.as_markup(resize_keyboard=True)


def admin_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"))
    builder.row(InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users"))
    builder.row(InlineKeyboardButton(text="💰 Выдать баланс", callback_data="admin_give_balance"))
    builder.row(InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast"))
    return builder.as_markup()


# ================== ЗАГЛУШКИ ПОД БУДУЩИЕ ФУНКЦИИ ==================

def future_features_kb() -> InlineKeyboardMarkup:
    """Клавиатура с будущими платными функциями (пока заглушки)"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🎬 Оживить фото (скоро)", callback_data="soon_animate"))
    builder.row(InlineKeyboardButton(text="🌐 Создать сайт (скоро)", callback_data="soon_site"))
    builder.row(InlineKeyboardButton(text="📱 Создать Mini App (скоро)", callback_data="soon_miniapp"))
    builder.row(InlineKeyboardButton(text="🖥️ Деплой на сервер (скоро)", callback_data="soon_deploy"))
    builder.row(InlineKeyboardButton(text="« Назад", callback_data="back_to_menu"))
    return builder.as_markup()