import logging
import asyncio
import sys
import subprocess
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.exceptions import TelegramAPIError

from config import BOT_TOKEN, DATABASE_URL
from handlers.start import router as start_router
from handlers.profile import router as profile_router
from handlers.chat import router as chat_router
from handlers.admin import router as admin_router
from handlers.assistant import router as assistant_router
from handlers.admin_panel import router as admin_panel_router
from handlers.ad_broadcast import router as ad_broadcast_router
from handlers.ad_manager import router as ad_manager_router
from handlers.premium import router as premium_router
from handlers.update_manager import router as update_router
from utils.debug import dbg
from tortoise import Tortoise

from middlewares.user_counter import UserCounterMiddleware
from middlewares.auth import AuthMiddleware
from middlewares.antiflood import AntiFloodMiddleware
from middlewares.logging import LoggingMiddleware
from middlewares.maintenance import MaintenanceMiddleware
from middlewares.registration_check import RegistrationCheckMiddleware
from middlewares.ban import BanMiddleware
from middlewares.rate_limit import RateLimitMiddleware
from middlewares.ai_content_moderation import AIContentModerationMiddleware
from middlewares.conversation_tracker import ConversationTrackerMiddleware
from middlewares.smart_ban import SmartBanMiddleware
from middlewares.admin import AdminMiddleware
from middlewares.chat_logger import ChatLoggerMiddleware
from middlewares.notifications import NotificationMiddleware

# Глобальный экземпляр для доступа к логам
chat_logger = ChatLoggerMiddleware()

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

async def main():
    try:
        # Проверка наличия токена
        if not BOT_TOKEN:
            logger.error("Токен бота не найден. Проверьте файл .env")
            sys.exit(1)
            
        # Выполняем миграции при старте
        try:
            subprocess.run(["aerich", "migrate"], check=True)
            subprocess.run(["aerich", "upgrade"], check=True)
            logger.info("Database migrations completed")
        except Exception as e:
            logger.warning(f"Migration error: {e}")
        
        # Инициализация Tortoise-ORM
        await Tortoise.init(config=__import__('database.tortoise_config', fromlist=['TORTOISE_ORM']).TORTOISE_ORM)
        logger.info("Tortoise-ORM инициализирована")
        
        # Инициализация бота и диспетчера
        bot = Bot(token=BOT_TOKEN)
        storage = MemoryStorage()
        dp = Dispatcher(storage=storage)
        
        # Регистрируем middleware (порядок важен!)
        dp.message.middleware(UserCounterMiddleware())
        dp.message.middleware(AuthMiddleware())
        dp.message.middleware(BanMiddleware())
        dp.message.middleware(MaintenanceMiddleware())
        dp.message.middleware(RegistrationCheckMiddleware())
        dp.message.middleware(AntiFloodMiddleware())
        dp.message.middleware(AIContentModerationMiddleware())
        dp.message.middleware(ConversationTrackerMiddleware())
        dp.message.middleware(chat_logger)
        dp.message.middleware(SmartBanMiddleware())
        dp.message.middleware(AdminMiddleware())
        dp.message.middleware(NotificationMiddleware())
        dp.message.middleware(RateLimitMiddleware())
        dp.message.middleware(LoggingMiddleware())
        
        dp.callback_query.middleware(AuthMiddleware())
        dp.callback_query.middleware(BanMiddleware())
        dp.callback_query.middleware(NotificationMiddleware())
        dp.callback_query.middleware(LoggingMiddleware())
        
        dp.include_router(start_router)
        dp.include_router(profile_router)
        dp.include_router(chat_router)
        dp.include_router(admin_router)
        dp.include_router(admin_panel_router)
        dp.include_router(ad_broadcast_router)
        dp.include_router(ad_manager_router)
        dp.include_router(premium_router)
        dp.include_router(update_router)
        dp.include_router(assistant_router)
        logger.info("Обработчики и middleware зарегистрированы")
        
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