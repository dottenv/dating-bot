import asyncio
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message
from database.models import User
from services.ai_moderation import ai_moderator

class AIContentModerationMiddleware(BaseMiddleware):
    async def _apply_auto_ban(self, user_id: int, action: str, bot):
        from database.models import Ban
        import datetime
        
        user = await User.filter(tg_id=user_id).first()
        if not user:
            return
        
        if action == 'ban_1h':
            expires_at = datetime.datetime.now() + datetime.timedelta(hours=1)
            duration = 1
        elif action == 'ban_1d':
            expires_at = datetime.datetime.now() + datetime.timedelta(days=1)
            duration = 24
        elif action == 'ban_permanent':
            expires_at = None
            duration = None
        else:
            return
        
        await Ban.create(
            user=user,
            ban_type='temp' if expires_at else 'permanent',
            duration_hours=duration,
            reason=f'Автобан за нарушения',
            expires_at=expires_at
        )
        
        try:
            if action == 'ban_permanent':
                await bot.send_message(user_id, "**Вы заблокированы навсегда**\n\nПричина: системные нарушения", parse_mode="Markdown")
            else:
                time_str = '1 час' if duration == 1 else f'{duration} часов'
                await bot.send_message(user_id, f"**Вы заблокированы на {time_str}**\n\nПричина: множественные нарушения", parse_mode="Markdown")
        except:
            pass
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        if isinstance(event, Message) and event.text and event.from_user:
            user = data.get('user')
            if not user:
                return await handler(event, data)
            
            # Новая ИИ модерация
            moderation = await ai_moderator.moderate_message(event.from_user.id, event.text)
            
            # Блокируем сообщение если нужно
            if not moderation['allow']:
                await event.answer(f"**Сообщение заблокировано**\n\nПричина: {moderation['reason']}", parse_mode="Markdown")
                return
            
            # Применяем автобан если нужно
            if moderation.get('action'):
                await self._apply_auto_ban(event.from_user.id, moderation['action'], event.bot)
            
            data['moderation'] = moderation
        
        return await handler(event, data)