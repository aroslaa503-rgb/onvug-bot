"""
Система балансов по твоей схеме.

Три типа средств:
1. main_balance      — основной (пополняет сам, может вывести обратно)
2. bonus_balance     — бонусный (нельзя вывести, только тратить)
3. withdrawable_balance — то, что пришло с рефералки и можно вывести

При оплате услуги/тарифа все три баланса суммируются.
Списание происходит в порядке: bonus → main → withdrawable
(чтобы бонусные деньги тратились в первую очередь).

Рефералка гибкая:
- Можно отдавать % только на withdrawable
- Можно часть на bonus + часть на withdrawable
- Можно вообще отключить и просто давать фикс-бонус
"""

from datetime import datetime
from typing import Optional
import aiosqlite
import config


async def get_balances(user_id: int, bot_id: int = 0) -> dict:
    async with aiosqlite.connect(config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT main_balance, bonus_balance, withdrawable_balance
            FROM users WHERE user_id = ? AND bot_id = ?
        """, (user_id, bot_id)) as cursor:
            row = await cursor.fetchone()
            if not row:
                return {"main": 0.0, "bonus": 0.0, "withdrawable": 0.0, "total": 0.0}
            return {
                "main": row["main_balance"] or 0.0,
                "bonus": row["bonus_balance"] or 0.0,
                "withdrawable": row["withdrawable_balance"] or 0.0,
                "total": (row["main_balance"] or 0) + (row["bonus_balance"] or 0) + (row["withdrawable_balance"] or 0)
            }


async def add_balance(
    user_id: int,
    amount: float,
    balance_type: str,          # "main" | "bonus" | "withdrawable"
    description: str = "",
    bot_id: int = 0
):
    field_map = {
        "main": "main_balance",
        "bonus": "bonus_balance",
        "withdrawable": "withdrawable_balance",
    }
    field = field_map.get(balance_type)
    if not field:
        raise ValueError("Неизвестный тип баланса")

    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute(f"""
            UPDATE users SET {field} = COALESCE({field}, 0) + ? 
            WHERE user_id = ? AND bot_id = ?
        """, (amount, user_id, bot_id))

        await db.execute("""
            INSERT INTO transactions (user_id, bot_id, amount, type, description, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, bot_id, amount, balance_type, description, datetime.now().isoformat()))

        await db.commit()


async def can_pay(user_id: int, amount: float, bot_id: int = 0) -> bool:
    balances = await get_balances(user_id, bot_id)
    return balances["total"] >= amount


async def pay(
    user_id: int,
    amount: float,
    description: str = "",
    bot_id: int = 0
) -> tuple[bool, str]:
    """
    Списание с объединённых балансов.
    Порядок: bonus → main → withdrawable
    """
    if amount <= 0:
        return False, "Сумма должна быть больше 0"

    balances = await get_balances(user_id, bot_id)
    if balances["total"] < amount:
        return False, f"Недостаточно средств. Нужно {amount} ₽, у вас {balances['total']:.1f} ₽"

    remaining = amount
    take_bonus = min(balances["bonus"], remaining)
    remaining -= take_bonus
    take_main = min(balances["main"], remaining)
    remaining -= take_main
    take_withdrawable = min(balances["withdrawable"], remaining)

    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute("""
            UPDATE users SET
                bonus_balance = COALESCE(bonus_balance, 0) - ?,
                main_balance = COALESCE(main_balance, 0) - ?,
                withdrawable_balance = COALESCE(withdrawable_balance, 0) - ?
            WHERE user_id = ? AND bot_id = ?
        """, (take_bonus, take_main, take_withdrawable, user_id, bot_id))

        await db.execute("""
            INSERT INTO transactions (user_id, bot_id, amount, type, description, created_at)
            VALUES (?, ?, ?, 'payment', ?, ?)
        """, (user_id, bot_id, -amount, description, datetime.now().isoformat()))

        await db.commit()

    return True, "Оплата прошла успешно"


async def process_referral_reward(
    referrer_id: int,
    amount: float,
    bot_id: int = 0
):
    """
    Начисление за реферала.
    Гибкая логика — проценты можно менять в config.
    
    По умолчанию:
    - 50% от реферального % идёт на withdrawable (можно вывести)
    - 50% идёт на bonus (только тратить)
    """
    if amount <= 0:
        return

    total_reward = amount * (config.REFERRAL_PERCENT / 100)

    # Гибкие доли (можно менять)
    withdrawable_share = getattr(config, "REFERRAL_WITHDRAWABLE_SHARE", 0.5)  # 50%
    bonus_share = 1.0 - withdrawable_share

    to_withdrawable = total_reward * withdrawable_share
    to_bonus = total_reward * bonus_share

    if to_withdrawable > 0:
        await add_balance(
            referrer_id, to_withdrawable, "withdrawable",
            f"Реферальное вознаграждение (выводимое) с суммы {amount} ₽",
            bot_id
        )
    if to_bonus > 0:
        await add_balance(
            referrer_id, to_bonus, "bonus",
            f"Реферальное вознаграждение (бонус) с суммы {amount} ₽",
            bot_id
        )

    # Обновляем статистику в referrals
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute("""
            UPDATE referrals SET earned = COALESCE(earned, 0) + ?
            WHERE referrer_id = ? AND bot_id = ?
        """, (total_reward, referrer_id, bot_id))
        await db.commit()
