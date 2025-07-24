from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message

class BanMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user = data.get('user')
        if user:
            # Проверяем постоянный бан
            if hasattr(user, 'is_banned') and user.is_banned:
                if isinstance(event, Message):
                    await event.answer("Вы заблокированы навсегда.")
                return
            
            # Проверяем временные баны
            from handlers.admin import is_banned
            if await is_banned(user.tg_id):
                if isinstance(event, Message):
                    await event.answer("Вы заблокированы.")
                return
        
        return await handler(event, data)