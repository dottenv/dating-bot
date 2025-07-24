from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from database.models import User

class UserCounterMiddleware(BaseMiddleware):
    def __init__(self):
        self.last_count = 0
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        result = await handler(event, data)
        
        # Обновляем счетчик после обработки события
        if hasattr(event, 'from_user'):
            current_count = await User.all().count()
            if current_count != self.last_count:
                bot = data.get('bot')
                if bot:
                    try:
                        await bot.set_my_description(f"Бот для знакомств в слепую. Пользователей: {current_count}")
                        self.last_count = current_count
                    except:
                        pass
        
        return result