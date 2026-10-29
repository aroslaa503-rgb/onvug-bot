from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ParseMode
from datetime import datetime

import database as db
import keyboards as kb
import config

router = Router()


@router.message(F.text == "👤 Профиль")
async def profile_handler(message: Message):
    await show_profile(message)


@router.callback_query(F.data == "profile")
async def profile_callback(callback: CallbackQuery):
    await show_profile(callback.message, edit=True)
    await callback.answer()


async def show_profile(message: Message, edit: bool = False):
    user_id = message.chat.id if edit else message.from_user.id
    user = await db.get_user(user_id)
    if not user:
        await message.answer("Сначала нажми /start")
        return

    await db.reset_daily_limits_if_needed(user_id)
    user = await db.get_user(user_id)

    # Считаем дни с нами
    registered = datetime.fromisoformat(user["registered_at"])
    days = (datetime.now() - registered).days

    # Лимиты
    max_requests = config.FREE_DAILY_REQUESTS
    max_images = config.FREE_DAILY_IMAGES
    if user["subscription"] and user["sub_until"]:
        if datetime.fromisoformat(user["sub_until"]) > datetime.now():
            tariff = config.TARIFFS.get(user["subscription"])
            if tariff:
                max_requests = tariff["daily_requests"]
                max_images = tariff["daily_images"]

    # Имя бота (для реф. ссылки)
    bot_username = (await message.bot.me()).username

    text = config.PROFILE_TEMPLATE.format(
        user_id=user_id,
        days_with_us=days,
        free_balance=round(user["free_balance"], 1),
        bonus_balance=round(user["bonus_balance"], 1),
        paid_balance=round(user["paid_balance"], 1),
        used_requests=user["used_requests_today"],
        max_requests=max_requests,
        used_images=user["used_images_today"],
        max_images=max_images,
        bot_username=bot_username,
        ref_percent=config.REFERRAL_PERCENT
    )

    if edit:
        await message.edit_text(text, reply_markup=kb.profile_kb(), parse_mode=ParseMode.HTML)
    else:
        await message.answer(text, reply_markup=kb.profile_kb(), parse_mode=ParseMode.HTML)


@router.message(F.text == "💎 Тарифы")
@router.callback_query(F.data == "tariffs")
async def tariffs_handler(event: Message | CallbackQuery):
    text = "💎 <b>Тарифы</b>\n\n"
    for key, t in config.TARIFFS.items():
        text += (
            f"<b>{t['name']}</b> — {t['price']} ₽\n"
            f"• {t['daily_requests']} запросов/день\n"
            f"• {t['daily_images']} картинок/день\n"
            f"• на {t['days']} дней\n\n"
        )
    text += "Выбери тариф:"

    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=kb.tariffs_kb(), parse_mode=ParseMode.HTML)
        await event.answer()
    else:
        await event.answer(text, reply_markup=kb.tariffs_kb(), parse_mode=ParseMode.HTML)


@router.message(F.text == "💰 Пополнить")
@router.callback_query(F.data == "topup")
async def topup_handler(event: Message | CallbackQuery):
    text = (
        "💰 <b>Пополнение баланса</b>\n\n"
        "Выбери сумму или введи свою.\n"
        "После оплаты баланс появится автоматически (или после проверки админом)."
    )
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=kb.topup_kb(), parse_mode=ParseMode.HTML)
        await event.answer()
    else:
        await event.answer(text, reply_markup=kb.topup_kb(), parse_mode=ParseMode.HTML)


@router.message(F.text == "🔗 Рефералка")
@router.callback_query(F.data == "referral")
async def referral_handler(event: Message | CallbackQuery):
    user_id = event.from_user.id
    stats = await db.get_referral_stats(user_id)
    bot_username = (await event.bot.me()).username

    text = (
        f"🔗 <b>Реферальная система</b>\n\n"
        f"Твоя ссылка:\n"
        f"<code>https://t.me/{bot_username}?start={user_id}</code>\n\n"
        f"👥 Приглашено: {stats['count']}\n"
        f"💵 Заработано: {stats['earned']} ₽\n\n"
        f"Ты получаешь <b>{config.REFERRAL_PERCENT}%</b> с каждого пополнения друга.\n"
        f"Новичок получает {config.REFERRAL_BONUS_FOR_NEWBIE} ₽ бонусного баланса,\n"
        f"а ты — {config.REFERRAL_BONUS_FOR_INVITER} ₽."
    )

    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, parse_mode=ParseMode.HTML)
        await event.answer()
    else:
        await event.answer(text, parse_mode=ParseMode.HTML)


@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery):
    await callback.message.delete()
    await callback.message.answer("Главное меню:", reply_markup=kb.main_menu_kb())
    await callback.answer()


# ================== ЗАГЛУШКИ ==================

@router.callback_query(F.data.startswith("soon_"))
async def soon_handler(callback: CallbackQuery):
    feature = callback.data.replace("soon_", "")
    names = {
        "animate": "Оживление фото",
        "site": "Создание сайтов",
        "miniapp": "Создание Mini App",
        "deploy": "Деплой на сервер"
    }
    name = names.get(feature, "Эта функция")
    await callback.answer(f"«{name}» появится позже. Мы оставили под неё место в коде.", show_alert=True)
