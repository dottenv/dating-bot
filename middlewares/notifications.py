from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from typing import Callable, Dict, Any, Awaitable
from database.models import User, Profile, Ban
import asyncio

class NotificationService:
    def __init__(self):
        self.bot = None
    
    def set_bot(self, bot):
        self.bot = bot
    
    async def send_notification(self, user_id: int, message: str, parse_mode: str = "Markdown"):
        """Отправка уведомления пользователю"""
        if not self.bot:
            return
        try:
            await self.bot.send_message(user_id, message, parse_mode=parse_mode)
        except:
            pass
    
    async def notify_ban(self, user_id: int, ban_type: str, reason: str, expires_at=None):
        """Уведомление о бане"""
        if ban_type == "permanent":
            text = f"🚫 **Вы заблокированы навсегда**\n\n📝 Причина: {reason}"
        else:
            expire_text = expires_at.strftime('%d.%m.%Y %H:%M') if expires_at else "неизвестно"
            text = f"🚫 **Вы временно заблокированы**\n\n📝 Причина: {reason}\n⏰ До: {expire_text}"
        
        await self.send_notification(user_id, text, "Markdown")
    
    async def notify_unban(self, user_id: int):
        """Уведомление о разбане"""
        text = "✅ **Блокировка снята**\n\nВы можете продолжить пользоваться ботом."
        await self.send_notification(user_id, text, "Markdown")
    
    async def notify_premium_granted(self, user_id: int):
        """Уведомление о получении Premium"""
        text = ("🎉 **Поздравляем!**\n\nВы получили Premium статус!\n\n"
                "**Ваши преимущества:**\n"
                "• Приоритет в поиске\n"
                "• Расширенные фильтры\n"
                "• Больше возможностей")
        await self.send_notification(user_id, text, "Markdown")
    
    async def notify_premium_removed(self, user_id: int):
        """Уведомление об удалении Premium"""
        text = "❌ **Premium статус отозван**\n\nВы вернулись к обычному статусу пользователя."
        await self.send_notification(user_id, text, "Markdown")
    
    async def notify_admin_granted(self, user_id: int):
        """Уведомление о получении прав админа"""
        text = "👑 **Поздравляем!**\n\nВы получили права администратора.\n\nИспользуйте /admin для доступа к панели."
        await self.send_notification(user_id, text, "Markdown")
    
    async def notify_admin_removed(self, user_id: int):
        """Уведомление об удалении прав админа"""
        text = "❌ **Права администратора отозваны**\n\nВы больше не являетесь администратором."
        await self.send_notification(user_id, text, "Markdown")
    
    async def notify_rating_change(self, user_id: int, old_rating: int, new_rating: int, reason: str = ""):
        """Уведомление об изменении рейтинга"""
        change = new_rating - old_rating
        emoji = "📈" if change > 0 else "📉"
        sign = "+" if change > 0 else ""
        
        text = f"{emoji} **Рейтинг изменен**\n\n"
        text += f"Было: `{old_rating}`\n"
        text += f"Стало: `{new_rating}` ({sign}{change})\n"
        if reason:
            text += f"\n📝 Причина: {reason}"
        
        await self.send_notification(user_id, text, "Markdown")
    
    async def notify_complaint_processed(self, user_id: int, result: str):
        """Уведомление о рассмотрении жалобы"""
        text = f"📋 **Ваша жалоба рассмотрена**\n\n{result}"
        await self.send_notification(user_id, text, "Markdown")
    
    async def notify_violation_warning(self, user_id: int, violation_type: str, reason: str):
        """Уведомление о предупреждении за нарушение"""
        text = f"⚠️ **Предупреждение**\n\n"
        text += f"Тип нарушения: {violation_type}\n"
        text += f"Причина: {reason}\n\n"
        text += "Соблюдайте правила сообщества."
        
        await self.send_notification(user_id, text, "Markdown")

# Глобальный экземпляр сервиса уведомлений
notification_service = NotificationService()

class NotificationMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Устанавливаем бот в сервис уведомлений
        if 'bot' in data and not notification_service.bot:
            notification_service.set_bot(data['bot'])
        
        # Добавляем сервис уведомлений в данные
        data['notification_service'] = notification_service
        
        return await handler(event, data)