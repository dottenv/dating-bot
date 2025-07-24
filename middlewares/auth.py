from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from database.models import User

class AuthMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        if hasattr(event, 'from_user') and event.from_user:
            user = await User.filter(tg_id=event.from_user.id).first()
            if user:
                data['user'] = user
                data['is_premium'] = user.is_premium
                data['is_admin'] = user.is_admin
                data['is_active'] = user.is_active
            else:
                data['user'] = None
                data['is_premium'] = False
                data['is_admin'] = False
                data['is_active'] = False
        
        return await handler(event, data)