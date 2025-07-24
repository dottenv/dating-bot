import time
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message
from database.models import User

class ConversationTrackerMiddleware(BaseMiddleware):
    def __init__(self):
        # Структура: {(user1_id, user2_id): {'messages': count, 'start_time': timestamp, 'quality_score': float, 'adult_consent': {'user1': bool, 'user2': bool}}}
        self.conversations = {}
    
    def _get_conversation_key(self, user1_id: int, user2_id: int):
        return tuple(sorted([user1_id, user2_id]))
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        if isinstance(event, Message) and event.text and event.from_user:
            # Получаем ID собеседника из активных чатов
            from handlers.chat import active_chats
            chat_partner_id = active_chats.get(event.from_user.id)
            if chat_partner_id:
                conv_key = self._get_conversation_key(event.from_user.id, chat_partner_id)
                current_time = time.time()
                
                if conv_key not in self.conversations:
                    self.conversations[conv_key] = {
                        'messages': 0,
                        'start_time': current_time,
                        'quality_score': 0.0,
                        'adult_consent': {'user1': False, 'user2': False},
                        'last_activity': current_time
                    }
                
                conv = self.conversations[conv_key]
                conv['messages'] += 1
                conv['last_activity'] = current_time
                
                # Анализируем качество сообщения
                content_analysis = data.get('content_analysis', {})
                if content_analysis.get('sentiment') == 'positive':
                    conv['quality_score'] += 0.1
                elif content_analysis.get('is_toxic'):
                    conv['quality_score'] -= 0.2
                
                # Проверяем согласие на 18+ контент
                message_lower = event.text.lower()
                adult_keywords = ['согласен на 18+', 'хочу 18+', 'можно интим', 'давай 18+']
                if any(keyword in message_lower for keyword in adult_keywords):
                    user_key = 'user1' if event.from_user.id == min(conv_key) else 'user2'
                    conv['adult_consent'][user_key] = True
                
                # Проверяем критерии для деанона
                days_chatting = (current_time - conv['start_time']) / 86400
                can_deanon = (
                    conv['messages'] >= 30 and
                    days_chatting >= 2 and
                    conv['quality_score'] > 2.0
                )
                
                # Проверяем возможность 18+ чата
                can_adult_chat = (
                    conv['adult_consent']['user1'] and 
                    conv['adult_consent']['user2'] and
                    conv['quality_score'] > 1.0
                )
                
                conversation_stats = {
                    'messages_count': conv['messages'],
                    'days_chatting': days_chatting,
                    'quality_score': conv['quality_score'],
                    'can_deanon': can_deanon,
                    'can_adult_chat': can_adult_chat,
                    'adult_consent': conv['adult_consent']
                }
                
                data['conversation_stats'] = conversation_stats
        
        return await handler(event, data)