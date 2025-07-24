from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message
from database.models import User, Profile

class RegistrationCheckMiddleware(BaseMiddleware):
    def __init__(self):
        self.allowed_commands = ['/start', '/help']
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        if isinstance(event, Message) and event.from_user:
            # Пропускаем разрешенные команды
            if event.text and any(event.text.startswith(cmd) for cmd in self.allowed_commands):
                return await handler(event, data)
            
            # Пропускаем, если пользователь в процессе регистрации
            state = data.get('state')
            if state:
                current_state = await state.get_state()
                if current_state and 'registration' in current_state.lower():
                    return await handler(event, data)
            
            user = await User.filter(tg_id=event.from_user.id).first()
            if not user:
                await event.answer("Для использования бота необходимо пройти регистрацию. Нажмите /start")
                return
            
            profile = await Profile.filter(user=user).first()
            if not profile or not profile.profile_completed:
                await event.answer("Завершите заполнение профиля. Нажмите /start")
                return
        
        return await handler(event, data)