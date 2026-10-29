import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

import config
import database as db
from handlers import all_routers

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    # Инициализация базы
    await db.init_db()
    logger.info("База данных готова")

    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Подключаем все роутеры
    for router in all_routers:
        dp.include_router(router)

    # ОЧИСТКА СТАРЫХ ПОДКЛЮЧЕНИЙ (чтобы не было ошибки Conflict)
    await bot.delete_webhook(drop_pending_updates=True)

    logger.info("Бот запускается...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен")
