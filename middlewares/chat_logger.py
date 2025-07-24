import time
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message

class ChatLoggerMiddleware(BaseMiddleware):
    def __init__(self):
        # Структура: {(user1_id, user2_id): [{'user_id': int, 'message': str, 'timestamp': float, 'type': str}]}
        self.chat_logs = {}
    
    def _get_chat_key(self, user1_id: int, user2_id: int):
        return tuple(sorted([user1_id, user2_id]))
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        if isinstance(event, Message) and event.from_user:
            # Получаем ID партнера из активных чатов
            from handlers.chat import active_chats
            partner_id = active_chats.get(event.from_user.id)
            
            print(f"ChatLogger: user {event.from_user.id}, partner: {partner_id}, active_chats: {active_chats}")
            
            if partner_id:
                chat_key = self._get_chat_key(event.from_user.id, partner_id)
                
                if chat_key not in self.chat_logs:
                    self.chat_logs[chat_key] = []
                
                # Определяем тип сообщения
                msg_type = "text"
                msg_content = event.text or ""
                
                if event.photo:
                    msg_type = "photo"
                    msg_content = event.caption or "📷 Фото"
                elif event.video:
                    msg_type = "video"
                    msg_content = event.caption or "🎥 Видео"
                elif event.voice:
                    msg_type = "voice"
                    msg_content = "🎤 Голосовое сообщение"
                elif event.sticker:
                    msg_type = "sticker"
                    msg_content = "🎭 Стикер"
                elif event.document:
                    msg_type = "document"
                    msg_content = event.caption or "📄 Документ"
                
                # Логируем сообщение
                log_entry = {
                    'user_id': event.from_user.id,
                    'message': msg_content,
                    'timestamp': time.time(),
                    'type': msg_type
                }
                self.chat_logs[chat_key].append(log_entry)
                print(f"Logged message: {event.from_user.id} -> {partner_id}: {msg_content[:50]}..., total logs: {len(self.chat_logs[chat_key])}")
                print(f"Chat key: {chat_key}, all chat keys: {list(self.chat_logs.keys())}")
                
                # Ограничиваем размер лога (последние 100 сообщений)
                if len(self.chat_logs[chat_key]) > 100:
                    self.chat_logs[chat_key] = self.chat_logs[chat_key][-100:]
        
        return await handler(event, data)
    
    def get_chat_log(self, user1_id: int, user2_id: int):
        chat_key = self._get_chat_key(user1_id, user2_id)
        log = self.chat_logs.get(chat_key, [])
        print(f"Retrieved chat log for {user1_id}-{user2_id}, key: {chat_key}: {len(log)} messages")
        print(f"Available chat keys: {list(self.chat_logs.keys())}")
        if log:
            print(f"Sample messages: {[msg['message'][:30] for msg in log[:3]]}")
        return log