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

    registered = datetime.fromisoformat(user["registered_at"])
    days = (datetime.now() - registered).days

    max_requests = config.FREE_DAILY_REQUESTS
    max_images = config.FREE_DAILY_IMAGES
    if user.get("subscription") and user.get("sub_until"):
        try:
            if datetime.fromisoformat(user["sub_until"]) > datetime.now():
                tariff = config.TARIFFS.get(user["subscription"])
                if tariff:
                    max_requests = tariff["daily_requests"]
                    max_images = tariff["daily_images"]
        except Exception:
            pass

    bot_username = (await message.bot.me()).username

    # Новые названия балансов
    main_balance = user.get("main_balance") or user.get("paid_balance") or 0
    bonus_balance = user.get("bonus_balance") or 0
    withdrawable_balance = user.get("withdrawable_balance") or 0

    text = config.PROFILE_TEMPLATE.format(
        user_id=user_id,
        days_with_us=days,
        main_balance=round(main_balance, 1),
        bonus_balance=round(bonus_balance, 1),
        withdrawable_balance=round(withdrawable_balance, 1),
        used_requests=user.get("used_requests_today") or 0,
        max_requests=max_requests,
        used_images=user.get("used_images_today") or 0,
        max_images=max_images,
        bot_username=bot_username,
    )

    if edit:
        await message.edit_text(text, reply_markup=kb.profile_kb(), parse_mode=ParseMode.HTML)
    else:
        await message.answer(text, reply_markup=kb.profile_kb(), parse_mode=ParseMode.HTML)


@router.message(F.text == "💎 Тарифы")
@router.callback_query(F.data == "tariffs")
async def tariffs_handler(event: Message | CallbackQuery):
    text = config.TARIFFS_TEXT + "\n\n"
    for key, t in config.TARIFFS.items():
        text += (
            f"<b>{t['name']}</b> — <b>{t['price']} ₽</b>\n"
            f"├ {t['daily_requests']} запросов / день\n"
            f"└ {t['daily_images']} картинок / день\n\n"
        )

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
        "Выбери сумму.\n"
        "После оплаты средства появятся на основном балансе."
    )
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=kb.topup_kb(), parse_mode=ParseMode.HTML)
        await event.answer()
    else:
        await event.answer(text, reply_markup=kb.topup_kb(), parse_mode=ParseMode.HTML)


@router.message(F.text == "🔗 Рефералка")
@router.callback_query(F.data == "referral")
async def referral_handler(event: Message | CallbackQuery):
    user_id = event.from_user.id if isinstance(event, Message) else event.from_user.id
    bot_username = (await event.bot.me()).username

    # Статистика (пока простая)
    invited = 0
    earned = 0.0
    try:
        import aiosqlite
        async with aiosqlite.connect(config.DB_PATH) as conn:
            async with conn.execute(
                "SELECT COUNT(*), COALESCE(SUM(earned), 0) FROM referrals WHERE referrer_id = ?",
                (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    invited = row[0] or 0
                    earned = row[1] or 0.0
    except Exception:
        pass

    text = config.REFERRAL_TEXT.format(
        bot_username=bot_username,
        user_id=user_id,
        invited=invited,
        earned=round(earned, 1),
        percent=config.REFERRAL_PERCENT,
        newbie_bonus=config.REFERRAL_BONUS_FOR_NEWBIE,
        inviter_bonus=config.REFERRAL_BONUS_FOR_INVITER,
    )

    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, parse_mode=ParseMode.HTML)
        await event.answer()
    else:
        await event.answer(text, parse_mode=ParseMode.HTML)


# ================== ВОЗВРАТ В МЕНЮ ==================

@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery):
    await callback.message.delete()
    await callback.message.answer("Главное меню:", reply_markup=kb.main_menu_kb())
    await callback.answer()
