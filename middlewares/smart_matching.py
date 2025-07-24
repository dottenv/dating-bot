from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from typing import Callable, Dict, Any, Awaitable
from services.smart_matching import smart_matcher
import time

class SmartMatchingMiddleware(BaseMiddleware):
    """Middleware для обучения системы подбора на основе взаимодействий"""
    
    def __init__(self):
        self.chat_start_times = {}  # Время начала чатов
        self.message_counts = {}    # Количество сообщений в чатах
    
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        # Импортируем здесь чтобы избежать циклических импортов
        from handlers.chat import active_chats
        
        user_id = event.from_user.id
        
        # Отслеживаем начало чата
        if user_id in active_chats and user_id not in self.chat_start_times:
            self.chat_start_times[user_id] = time.time()
            self.message_counts[user_id] = 0
        
        # Считаем сообщения в активных чатах
        if user_id in active_chats and event.text:
            self.message_counts[user_id] = self.message_counts.get(user_id, 0) + 1
        
        # Обрабатываем завершение чата
        if hasattr(event, 'data') and event.data == "end_chat":
            await self._analyze_chat_quality(user_id)
        
        return await handler(event, data)
    
    async def _analyze_chat_quality(self, user_id: int):
        """Анализирует качество чата для обучения системы"""
        from handlers.chat import active_chats
        
        if user_id not in active_chats:
            return
        
        partner_id = active_chats[user_id]
        
        # Получаем статистику чата
        chat_duration = time.time() - self.chat_start_times.get(user_id, time.time())
        message_count = self.message_counts.get(user_id, 0)
        
        # Определяем качество взаимодействия
        quality = "neutral"
        
        if chat_duration > 300 and message_count > 10:  # 5+ минут и 10+ сообщений
            quality = "positive"
        elif chat_duration < 60 or message_count < 3:   # Менее минуты или мало сообщений
            quality = "negative"
        
        # Обучаем систему
        smart_matcher.learn_from_interaction(user_id, partner_id, quality)
        
        # Очищаем статистику
        self.chat_start_times.pop(user_id, None)
        self.message_counts.pop(user_id, None)

# Глобальный экземпляр middleware
smart_matching_middleware = SmartMatchingMiddleware()