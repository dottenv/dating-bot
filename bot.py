import logging
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from sqlalchemy import create_engine

from config import BOT_TOKEN, DATABASE_URL
from database.models import Base
from handlers import register_all_handlers

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize database
engine = create_engine(DATABASE_URL)
Base.metadata.create_all(bind=engine)

async def main():
    # Initialize bot and dispatcher
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Register all handlers
    register_all_handlers(dp)
    
    # Start polling
    await dp.start_polling(bot, skip_updates=True)

if __name__ == '__main__':
    asyncio.run(main())