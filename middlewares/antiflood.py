import time
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message

class AntiFloodMiddleware(BaseMiddleware):
    def __init__(self, rate_limit: int = 1):
        self.rate_limit = rate_limit
        self.user_timestamps = {}
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        if isinstance(event, Message) and event.from_user:
            user_id = event.from_user.id
            current_time = time.time()
            
            if user_id in self.user_timestamps:
                if current_time - self.user_timestamps[user_id] < self.rate_limit:
                    return  # Игнорируем сообщение
            
            self.user_timestamps[user_id] = current_time
        
        return await handler(event, data)