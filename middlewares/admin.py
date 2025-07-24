from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

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
        
        # Проверяем админские callback_query
        elif isinstance(event, CallbackQuery) and event.data:
            admin_callbacks = [
                'admin_panel', 'admin_updates', 'check_updates', 'apply_updates', 'restart_bot',
                'admin_broadcast', 'admin_stats', 'admin_users', 'admin_ads', 'admin_settings'
            ]
            
            if event.data in admin_callbacks:
                is_admin = data.get('is_admin', False)
                if not is_admin:
                    await event.answer("Access denied", show_alert=True)
                    return
        
        return await handler(event, data)