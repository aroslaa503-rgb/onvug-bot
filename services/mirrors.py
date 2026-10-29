"""
Сервис работы с зеркалами (white-label).

Два типа:
1. full  — полная копия основного бота
           Партнёр может:
           - менять названия тарифов
           - повышать цены (но не ниже MIN_TARIFF_PRICES)
           Не может:
           - менять реферальную систему (она центральная)
           - отключать Mini App

2. empty — пустой конструктор
           Партнёр сам добавляет:
           - свои API ключи
           - свои способы оплаты
           Может полностью отключить Mini App
           Платит либо фикс в месяц, либо % с оборота.
"""

import json
from datetime import datetime, timedelta
from typing import Optional
import aiosqlite
import config


async def create_full_mirror(owner_id: int, bot_token: str, bot_username: str, title: str = None) -> int:
    """Создаёт full-зеркало. Возвращает bot_id."""
    async with aiosqlite.connect(config.DB_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO bots (owner_id, bot_token, bot_username, type, title, 
                              miniapp_enabled, created_at)
            VALUES (?, ?, ?, 'full', ?, 1, ?)
        """, (owner_id, bot_token, bot_username, title or bot_username, datetime.now().isoformat()))
        await db.commit()
        return cursor.lastrowid


async def create_empty_mirror(
    owner_id: int,
    bot_token: str,
    bot_username: str,
    payment_type: str = "percent",   # 'fixed' или 'percent'
    title: str = None
) -> int:
    """Создаёт empty-зеркало (пустой конструктор)."""
    fixed_price = config.EMPTY_MIRROR_FIXED_PRICE if payment_type == "fixed" else 0
    percent = config.EMPTY_MIRROR_DEFAULT_PERCENT if payment_type == "percent" else 0
    expires = (datetime.now() + timedelta(days=30)).isoformat() if payment_type == "fixed" else None

    async with aiosqlite.connect(config.DB_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO bots (
                owner_id, bot_token, bot_username, type, title,
                payment_type, fixed_price, percent,
                miniapp_enabled, created_at, expires_at
            ) VALUES (?, ?, ?, 'empty', ?, ?, ?, ?, 1, ?, ?)
        """, (
            owner_id, bot_token, bot_username, title or bot_username,
            payment_type, fixed_price, percent,
            datetime.now().isoformat(), expires
        ))
        await db.commit()
        return cursor.lastrowid


async def get_bot(bot_id: int) -> Optional[dict]:
    async with aiosqlite.connect(config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM bots WHERE bot_id = ?", (bot_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def get_bot_by_token(token: str) -> Optional[dict]:
    async with aiosqlite.connect(config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM bots WHERE bot_token = ?", (token,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def get_owner_bots(owner_id: int) -> list[dict]:
    async with aiosqlite.connect(config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM bots WHERE owner_id = ?", (owner_id,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def update_full_mirror_tariffs(bot_id: int, custom_tariffs: dict) -> tuple[bool, str]:
    """
    Обновляет тарифы full-зеркала.
    Проверяет, что цены не ниже минимальных.
    """
    bot = await get_bot(bot_id)
    if not bot or bot["type"] != "full":
        return False, "Это не full-зеркало"

    for key, tariff in custom_tariffs.items():
        min_price = config.MIN_TARIFF_PRICES.get(key)
        if min_price and tariff.get("price", 0) < min_price:
            return False, f"Цена тарифа «{key}» не может быть ниже {min_price} ₽"

    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute("""
            UPDATE bots SET custom_tariffs = ? WHERE bot_id = ?
        """, (json.dumps(custom_tariffs, ensure_ascii=False), bot_id))
        await db.commit()

    return True, "Тарифы обновлены"


async def set_miniapp_status(bot_id: int, enabled: bool) -> tuple[bool, str]:
    """Включить/выключить Mini App. У full-зеркал нельзя отключить."""
    bot = await get_bot(bot_id)
    if not bot:
        return False, "Бот не найден"

    if bot["type"] == "full" and not enabled:
        return False, "В full-зеркале нельзя отключить Mini App"

    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute("""
            UPDATE bots SET miniapp_enabled = ? WHERE bot_id = ?
        """, (1 if enabled else 0, bot_id))
        await db.commit()

    return True, "Настройки Mini App обновлены"


async def add_partner_api(bot_id: int, name: str, api_url: str, api_key: str, model: str = None):
    """Добавляет API партнёру (только empty)."""
    bot = await get_bot(bot_id)
    if not bot or bot["type"] != "empty":
        return False, "Только для empty-зеркал"

    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute("""
            INSERT INTO partner_apis (bot_id, name, api_url, api_key, model)
            VALUES (?, ?, ?, ?, ?)
        """, (bot_id, name, api_url, api_key, model))
        await db.commit()
    return True, "API добавлен"


async def add_partner_payment(bot_id: int, method: str, title: str, details: str, is_manual: bool = True):
    """Добавляет способ оплаты партнёру (только empty)."""
    bot = await get_bot(bot_id)
    if not bot or bot["type"] != "empty":
        return False, "Только для empty-зеркал"

    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute("""
            INSERT INTO partner_payments (bot_id, method, title, details, is_manual)
            VALUES (?, ?, ?, ?, ?)
        """, (bot_id, method, title, details, 1 if is_manual else 0))
        await db.commit()
    return True, "Способ оплаты добавлен"
