import time
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message
from database.models import User

class SmartBanMiddleware(BaseMiddleware):
    def __init__(self):
        # Структура: {user_id: {'warnings': count, 'temp_ban_until': timestamp}}
        self.user_violations = {}
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        if isinstance(event, Message) and event.from_user:
            user_id = event.from_user.id
            user = data.get('user')
            
            if not user:
                return await handler(event, data)
            
            # Проверяем временный бан
            if user_id in self.user_violations:
                temp_ban_until = self.user_violations[user_id].get('temp_ban_until', 0)
                if temp_ban_until > time.time():
                    ban_hours = int((temp_ban_until - time.time()) / 3600)
                    await event.answer(f"Вы временно заблокированы на {ban_hours} часов за нарушения.")
                    return
            
            # Анализируем нарушения
            content_analysis = data.get('content_analysis', {})
            if content_analysis.get('is_toxic') or content_analysis.get('block_message'):
                if user_id not in self.user_violations:
                    self.user_violations[user_id] = {'warnings': 0, 'temp_ban_until': 0}
                
                violations = self.user_violations[user_id]
                violations['warnings'] += 1
                
                # Градация наказаний
                if violations['warnings'] == 1:
                    await event.answer("⚠️ Предупреждение! Соблюдайте правила общения.")
                elif violations['warnings'] == 2:
                    await event.answer("⚠️ Второе предупреждение! При следующем нарушении будет временная блокировка.")
                elif violations['warnings'] == 3:
                    # Временный бан на 1 час
                    violations['temp_ban_until'] = time.time() + 3600
                    await event.answer("🚫 Вы заблокированы на 1 час за нарушения.")
                    return
                elif violations['warnings'] >= 5:
                    # Постоянный бан
                    await User.filter(id=user.id).update(is_banned=True)
                    await event.answer("🚫 Вы заблокированы навсегда за множественные нарушения.")
                    return
        
        return await handler(event, data)