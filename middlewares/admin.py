from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message

class AdminMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Проверяем команды только для админов
        if isinstance(event, Message) and event.text:
            admin_commands = ['/admin', '/ban', '/unban', '/stats', '/broadcast']
            
            if any(event.text.startswith(cmd) for cmd in admin_commands):
                is_admin = data.get('is_admin', False)
                if not is_admin:
                    await event.answer("У вас нет прав администратора.")
                    return
        
        return await handler(event, data)