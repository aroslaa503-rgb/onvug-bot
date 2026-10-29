"""
Сервис ИИ с ротацией API (бутерброд).

Ключи хранятся в базе и добавляются через бота (админка / кабинет партнёра).
"""

import aiohttp
import asyncio
import logging
import random
from typing import Optional
from dataclasses import dataclass
from datetime import datetime
import aiosqlite
import config

logger = logging.getLogger(__name__)


@dataclass
class APIKey:
    id: int
    bot_id: int
    provider: str
    name: str
    api_key: str
    model: str
    base_url: str
    is_paid: bool
    daily_limit: int
    used_today: int
    is_alive: bool
    last_error: str
    last_reset_date: str


class AIService:
    def __init__(self):
        self._lock = asyncio.Lock()
        self._cache: dict[int, list[APIKey]] = {}
        self._cache_time: dict[int, float] = {}

    async def _load_keys(self, bot_id: int = 0, force: bool = False) -> list[APIKey]:
        now = datetime.now().timestamp()
        if not force and bot_id in self._cache:
            if now - self._cache_time.get(bot_id, 0) < 30:
                return self._cache[bot_id]

        keys = []
        async with aiosqlite.connect(config.DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM api_keys 
                WHERE bot_id = ? AND is_active = 1
                ORDER BY is_paid ASC, id ASC
            """, (bot_id,)) as cursor:
                rows = await cursor.fetchall()
                for r in rows:
                    keys.append(APIKey(
                        id=r["id"],
                        bot_id=r["bot_id"],
                        provider=r["provider"],
                        name=r["name"],
                        api_key=r["api_key"],
                        model=r["model"],
                        base_url=r["base_url"],
                        is_paid=bool(r["is_paid"]),
                        daily_limit=r["daily_limit"],
                        used_today=r["used_today"],
                        is_alive=bool(r["is_alive"]),
                        last_error=r["last_error"] or "",
                        last_reset_date=r["last_reset_date"] or "",
                    ))

        self._cache[bot_id] = keys
        self._cache_time[bot_id] = now
        return keys

    async def _reset_daily_if_needed(self, key: APIKey):
        today = datetime.now().strftime("%Y-%m-%d")
        if key.last_reset_date != today:
            async with aiosqlite.connect(config.DB_PATH) as db:
                await db.execute("""
                    UPDATE api_keys 
                    SET used_today = 0, last_reset_date = ?, is_alive = 1
                    WHERE id = ?
                """, (today, key.id))
                await db.commit()
            key.used_today = 0
            key.last_reset_date = today
            key.is_alive = True

    async def _mark_key_error(self, key_id: int, error: str, kill: bool = False):
        async with aiosqlite.connect(config.DB_PATH) as db:
            if kill:
                await db.execute("""
                    UPDATE api_keys SET is_alive = 0, last_error = ? WHERE id = ?
                """, (error[:300], key_id))
            else:
                await db.execute("""
                    UPDATE api_keys SET last_error = ? WHERE id = ?
                """, (error[:300], key_id))
            await db.commit()
        self._cache.clear()

    async def _increment_usage(self, key_id: int):
        async with aiosqlite.connect(config.DB_PATH) as db:
            await db.execute("""
                UPDATE api_keys SET used_today = used_today + 1 WHERE id = ?
            """, (key_id,))
            await db.commit()

    def _estimate_complexity(self, prompt: str) -> str:
        prompt_lower = prompt.lower()
        complex_markers = [
            "реши", "докажи", "напиши сочинение", "код", "программ",
            "анализ", "сравни", "диплом", "реферат", "по шагам",
            "математич", "физик", "химич", "уравнен", "интеграл",
            "составь план", "разверни", "подробно", "объясни подробно"
        ]
        if any(m in prompt_lower for m in complex_markers) or len(prompt) > 400:
            return "complex"
        return "simple"

    async def _call_openai_compatible(self, key: APIKey, messages: list[dict]) -> str:
        headers = {
            "Authorization": f"Bearer {key.api_key}",
            "Content-Type": "application/json",
        }
        if key.provider == "openrouter":
            headers["HTTP-Referer"] = "https://t.me"
            headers["X-Title"] = "ONVUG Bot"

        payload = {
            "model": key.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 2048,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{key.base_url.rstrip('/')}/chat/completions",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as resp:
                if resp.status == 429:
                    await self._mark_key_error(key.id, "rate_limit", kill=True)
                    raise Exception("Rate limit")
                if resp.status == 401:
                    await self._mark_key_error(key.id, "invalid_key", kill=True)
                    raise Exception("Invalid API key")
                if resp.status >= 400:
                    text = await resp.text()
                    await self._mark_key_error(key.id, text[:200])
                    raise Exception(f"API error {resp.status}")

                data = await resp.json()
                await self._increment_usage(key.id)
                return data["choices"][0]["message"]["content"]

    async def ask(self, prompt: str, system: str = None, bot_id: int = 0) -> str:
        keys = await self._load_keys(bot_id)

        if not keys:
            return (
                "⚠️ Пока не добавлено ни одного API-ключа.\n\n"
                "Админ может добавить ключи через /admin → API ключи."
            )

        for k in keys:
            await self._reset_daily_if_needed(k)

        complexity = self._estimate_complexity(prompt)
        prefer_paid = complexity == "complex"

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        else:
            messages.append({
                "role": "system",
                "content": (
                    "Ты полезный русскоязычный ассистент. "
                    "Отвечай чётко, по делу и дружелюбно. "
                    "Если решаешь задачу — показывай решение по шагам."
                )
            })
        messages.append({"role": "user", "content": prompt})

        def sort_key(k: APIKey):
            type_penalty = 0 if (k.is_paid == prefer_paid) else 1
            return (type_penalty, k.used_today, not k.is_alive)

        candidates = sorted(
            [k for k in keys if k.is_alive and k.used_today < k.daily_limit],
            key=sort_key
        )

        if not candidates:
            for k in keys:
                k.is_alive = True
            candidates = [k for k in keys if k.used_today < k.daily_limit]

        if not candidates:
            return "Сейчас все лимиты API временно закончились. Попробуй через несколько минут."

        last_error = None
        for key in candidates[:6]:
            try:
                result = await self._call_openai_compatible(key, messages)
                return result
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Key {key.name} ({key.provider}) failed: {e}")
                continue

        return f"Не удалось получить ответ. Попробуй позже.\n({last_error})" if last_error else "Ошибка API."

    async def solve_photo(self, image_bytes: bytes, caption: str = "", bot_id: int = 0) -> str:
        if caption:
            return await self.ask(
                f"Реши эту задачу по шагам:\n\n{caption}",
                system="Ты опытный репетитор. Решай задачи подробно, шаг за шагом, с объяснениями.",
                bot_id=bot_id
            )
        return (
            "📸 Фото получил.\n\n"
            "Пока лучше всего работает так:\n"
            "1. Пришли фото\n"
            "2. В подписи напиши условие задачи\n\n"
            "Я решу её по шагам.\n"
            "Скоро подключу полноценное распознавание с фото."
        )

    async def generate_image(self, prompt: str) -> Optional[str]:
        try:
            from urllib.parse import quote
            encoded = quote(prompt)
            return f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=1024&nologo=true"
        except Exception as e:
            logger.error(f"Image gen error: {e}")
            return None


ai_service = AIService()


async def add_api_key(
    bot_id: int,
    provider: str,
    name: str,
    api_key: str,
    model: str,
    base_url: str,
    is_paid: bool = False,
    daily_limit: int = 1000
) -> int:
    async with aiosqlite.connect(config.DB_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO api_keys (
                bot_id, provider, name, api_key, model, base_url,
                is_paid, daily_limit, used_today, is_alive, is_active,
                last_reset_date, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 1, 1, ?, ?)
        """, (
            bot_id, provider, name, api_key, model, base_url,
            1 if is_paid else 0, daily_limit,
            datetime.now().strftime("%Y-%m-%d"),
            datetime.now().isoformat()
        ))
        await db.commit()
        return cursor.lastrowid


async def list_api_keys(bot_id: int = 0) -> list[dict]:
    async with aiosqlite.connect(config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT id, provider, name, model, is_paid, daily_limit, used_today, is_alive, is_active
            FROM api_keys WHERE bot_id = ? ORDER BY id
        """, (bot_id,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def delete_api_key(key_id: int, bot_id: int = 0) -> bool:
    async with aiosqlite.connect(config.DB_PATH) as db:
        cursor = await db.execute("""
            DELETE FROM api_keys WHERE id = ? AND bot_id = ?
        """, (key_id, bot_id))
        await db.commit()
        return cursor.rowcount > 0


async def toggle_api_key(key_id: int, bot_id: int = 0) -> bool:
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute("""
            UPDATE api_keys SET is_active = 1 - is_active WHERE id = ? AND bot_id = ?
        """, (key_id, bot_id))
        await db.commit()
        return True
