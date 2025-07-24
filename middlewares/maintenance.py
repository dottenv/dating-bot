from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message

class MaintenanceMiddleware(BaseMiddleware):
    def __init__(self, maintenance_mode: bool = False):
        self.maintenance_mode = maintenance_mode
    
    def set_maintenance(self, status: bool):
        self.maintenance_mode = status
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        if self.maintenance_mode:
            is_admin = data.get('is_admin', False)
            if not is_admin and isinstance(event, Message):
                await event.answer("Бот находится на техническом обслуживании. Попробуйте позже.")
                return
        
        return await handler(event, data)