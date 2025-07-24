import time
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message

class RateLimitMiddleware(BaseMiddleware):
    def __init__(self, daily_limit: int = 50, premium_limit: int = 200):
        self.daily_limit = daily_limit
        self.premium_limit = premium_limit
        self.user_actions = {}
    
    def _get_today_key(self):
        return int(time.time() // 86400)  # Дни с эпохи
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        if isinstance(event, Message) and event.from_user:
            user_id = event.from_user.id
            today = self._get_today_key()
            is_premium = data.get('is_premium', False)
            
            if user_id not in self.user_actions:
                self.user_actions[user_id] = {}
            
            if today not in self.user_actions[user_id]:
                self.user_actions[user_id][today] = 0
            
            current_actions = self.user_actions[user_id][today]
            limit = self.premium_limit if is_premium else self.daily_limit
            
            if current_actions >= limit:
                await event.answer(f"Достигнут дневной лимит действий ({limit}). {'Попробуйте завтра.' if not is_premium else ''}")
                return
            
            self.user_actions[user_id][today] += 1
        
        return await handler(event, data)