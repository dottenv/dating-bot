import logging
import asyncio
import sys
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.exceptions import TelegramAPIError
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError

from config import BOT_TOKEN, DATABASE_URL
from database.models import Base
from handlers import register_all_handlers
from utils.debug import dbg

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Инициализация базы данных с обработкой ошибок
try:
    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    logger.info("База данных успешно инициализирована")
except SQLAlchemyError as e:
    logger.error(f"Ошибка при инициализации базы данных: {e}")
    sys.exit(1)

async def main():
    try:
        # Проверка наличия токена
        if not BOT_TOKEN:
            logger.error("Токен бота не найден. Проверьте файл .env")
            sys.exit(1)
            
        # Инициализация бота и диспетчера
        bot = Bot(token=BOT_TOKEN)
        storage = MemoryStorage()
        dp = Dispatcher(storage=storage)
        
        # Регистрация всех обработчиков
        register_all_handlers(dp)
        logger.info("Все обработчики зарегистрированы")
        
        # Устанавливаем команды бота
        from utils.commands import set_bot_commands
        await set_bot_commands(bot)
        
        # Запуск бота
        logger.info("Бот запущен")
        await dp.start_polling(bot, skip_updates=True)
    except TelegramAPIError as e:
        logger.error(f"Ошибка Telegram API: {e}")
    except Exception as e:
        logger.error(f"Необработанная ошибка: {e}", exc_info=True)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.critical(f"Критическая ошибка: {e}", exc_info=True)