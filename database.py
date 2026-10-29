import aiosqlite
from datetime import datetime, timedelta
from typing import Optional
import config


async def init_db():
    async with aiosqlite.connect(config.DB_PATH) as db:
        # === Основная таблица пользователей ===
        # bot_id = 0 означает главный бот
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER,
                bot_id INTEGER DEFAULT 0,
                username TEXT,
                full_name TEXT,
                registered_at TEXT,
                referrer_id INTEGER,
                
                -- ВСЕ балансы, которые требует код
                free_balance REAL DEFAULT 20.0,
                main_balance REAL DEFAULT 0,          
                bonus_balance REAL DEFAULT 0,         
                withdrawable_balance REAL DEFAULT 0,  
                paid_balance REAL DEFAULT 0,          
                
                subscription TEXT DEFAULT NULL,
                sub_until TEXT DEFAULT NULL,
                used_requests_today INTEGER DEFAULT 0,
                used_images_today INTEGER DEFAULT 0,
                last_reset_date TEXT,
                last_request_at TEXT,
                is_banned INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, bot_id)
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                bot_id INTEGER DEFAULT 0,
                amount REAL,
                type TEXT,
                description TEXT,
                created_at TEXT
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS referrals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id INTEGER,
                referred_id INTEGER,
                bot_id INTEGER DEFAULT 0,
                earned REAL DEFAULT 0,
                created_at TEXT,
                UNIQUE(referred_id, bot_id)
            )
        """)

        # =====================================================
        # ЗЕРКАЛА / WHITE-LABEL
        # =====================================================
        await db.execute("""
            CREATE TABLE IF NOT EXISTS bots (
                bot_id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id INTEGER NOT NULL,
                bot_token TEXT UNIQUE,
                bot_username TEXT,
                type TEXT NOT NULL CHECK(type IN ('full', 'empty')),
                title TEXT,
                is_active INTEGER DEFAULT 1,
                
                custom_tariffs TEXT DEFAULT NULL,   
                
                payment_type TEXT DEFAULT 'percent', 
                fixed_price REAL DEFAULT 0,          
                percent REAL DEFAULT 30,             
                
                miniapp_enabled INTEGER DEFAULT 1,   
                miniapp_url TEXT DEFAULT NULL,
                
                created_at TEXT,
                expires_at TEXT DEFAULT NULL         
            )
        """)

        # =====================================================
        # API-ключи
        # =====================================================
        await db.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bot_id INTEGER DEFAULT 0,          
                provider TEXT NOT NULL,            
                name TEXT NOT NULL,                
                api_key TEXT NOT NULL,
                model TEXT NOT NULL,
                base_url TEXT NOT NULL,            
                is_paid INTEGER DEFAULT 0,         
                daily_limit INTEGER DEFAULT 1000,
                used_today INTEGER DEFAULT 0,
                is_alive INTEGER DEFAULT 1,        
                is_active INTEGER DEFAULT 1,       
                last_error TEXT,
                last_reset_date TEXT,
                created_at TEXT
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS partner_payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bot_id INTEGER,
                method TEXT,                
                title TEXT,
                details TEXT,               
                is_manual INTEGER DEFAULT 1,
                is_active INTEGER DEFAULT 1,
                FOREIGN KEY (bot_id) REFERENCES bots(bot_id)
            )
        """)

        await db.commit()


async def get_user(user_id: int) -> Optional[dict]:
    async with aiosqlite.connect(config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def create_user(user_id: int, username: str = None, full_name: str = None, referrer_id: int = None):
    now = datetime.now().isoformat()
    today = datetime.now().strftime("%Y-%m-%d")

    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute("""
            INSERT OR IGNORE INTO users 
            (user_id, username, full_name, registered_at, referrer_id, last_reset_date, free_balance)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, username, full_name, now, referrer_id, today, 20.0)) 

        if referrer_id and referrer_id != user_id:
            await db.execute("""
                INSERT OR IGNORE INTO referrals (referrer_id, referred_id, created_at)
                VALUES (?, ?, ?)
            """, (referrer_id, user_id, now))

            await db.execute("""
                UPDATE users SET bonus_balance = bonus_balance + ? WHERE user_id = ?
            """, (config.REFERRAL_BONUS_FOR_INVITER, referrer_id))

            await db.execute("""
                UPDATE users SET bonus_balance = bonus_balance + ? WHERE user_id = ?
            """, (config.REFERRAL_BONUS_FOR_NEWBIE, user_id))

        await db.commit()


async def reset_daily_limits_if_needed(user_id: int):
    user = await get_user(user_id)
    if not user:
        return

    today = datetime.now().strftime("%Y-%m-%d")
    if user["last_reset_date"] != today:
        async with aiosqlite.connect(config.DB_PATH) as db:
            await db.execute("""
                UPDATE users 
                SET used_requests_today = 0, 
                    used_images_today = 0, 
                    last_reset_date = ?,
                    free_balance = 20.0
                WHERE user_id = ?
            """, (today, user_id))
            await db.commit()


async def can_make_request(user_id: int, is_image: bool = False) -> tuple[bool, str]:
    await reset_daily_limits_if_needed(user_id)
    user = await get_user(user_id)
    if not user:
        return False, "Пользователь не найден"

    if user["is_banned"]:
        return False, "Вы заблокированы"

    if user["last_request_at"]:
        last = datetime.fromisoformat(user["last_request_at"])
        if (datetime.now() - last).total_seconds() < config.FREE_COOLDOWN_SECONDS:
            wait = config.FREE_COOLDOWN_SECONDS - int((datetime.now() - last).total_seconds())
            return False, f"Подожди ещё {wait} сек."

    max_requests = config.FREE_DAILY_REQUESTS
    max_images = config.FREE_DAILY_IMAGES

    if user["subscription"] and user["sub_until"]:
        if datetime.fromisoformat(user["sub_until"]) > datetime.now():
            tariff = config.TARIFFS.get(user["subscription"])
            if tariff:
                max_requests = tariff["daily_requests"]
                max_images = tariff["daily_images"]

    if is_image:
        if user["used_images_today"] >= max_images:
            total_balance = user["free_balance"] + user["bonus_balance"] + user["paid_balance"]
            if total_balance < config.PRICES["image_gen"]:
                return False, "Лимит картинок на сегодня исчерпан. Пополни баланс или оформи подписку."
    else:
        if user["used_requests_today"] >= max_requests:
            total_balance = user["free_balance"] + user["bonus_balance"] + user["paid_balance"]
            if total_balance < 1:
                return False, "Лимит запросов на сегодня исчерпан. Пополни баланс или оформи подписку."

    return True, "ok"


async def spend_for_request(user_id: int, is_image: bool = False, cost: float = 0):
    user = await get_user(user_id)
    now = datetime.now().isoformat()

    async with aiosqlite.connect(config.DB_PATH) as db:
        if is_image:
            await db.execute("""
                UPDATE users 
                SET used_images_today = used_images_today + 1,
                    last_request_at = ?
                WHERE user_id = ?
            """, (now, user_id))
        else:
            await db.execute("""
                UPDATE users 
                SET used_requests_today = used_requests_today + 1,
                    last_request_at = ?
                WHERE user_id = ?
            """, (now, user_id))

        if cost > 0:
            remaining = cost
            free = user["free_balance"]
            bonus = user["bonus_balance"]
            paid = user["paid_balance"]

            take_free = min(free, remaining)
            remaining -= take_free
            take_bonus = min(bonus, remaining)
            remaining -= take_bonus
            take_paid = min(paid, remaining)

            await db.execute("""
                UPDATE users 
                SET free_balance = free_balance - ?,
                    bonus_balance = bonus_balance - ?,
                    paid_balance = paid_balance - ?
                WHERE user_id = ?
            """, (take_free, take_bonus, take_paid, user_id))

        await db.commit()


async def add_balance(user_id: int, amount: float, balance_type: str = "paid", description: str = ""):
    field = {
        "free": "free_balance",
        "bonus": "bonus_balance",
        "paid": "paid_balance"
    }.get(balance_type, "paid_balance")

    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute(f"""
            UPDATE users SET {field} = {field} + ? WHERE user_id = ?
        """, (amount, user_id))

        await db.execute("""
            INSERT INTO transactions (user_id, amount, type, description, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, amount, balance_type, description, datetime.now().isoformat()))

        await db.commit()


async def get_referral_stats(user_id: int) -> dict:
    async with aiosqlite.connect(config.DB_PATH) as db:
        async with db.execute("""
            SELECT COUNT(*) as count, COALESCE(SUM(earned), 0) as earned 
            FROM referrals WHERE referrer_id = ?
        """, (user_id,)) as cursor:
            row = await cursor.fetchone()
            return {"count": row[0], "earned": row[1]}
