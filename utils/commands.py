import logging
from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeDefault

logger = logging.getLogger(__name__)

async def set_bot_commands(bot: Bot):
    """Устанавливает команды бота"""
    commands = [
        BotCommand(command="start", description="🚀 Начать работу с ботом"),
        BotCommand(command="profile", description="👤 Мой профиль"),
        BotCommand(command="find", description="🔍 Найти собеседника"),
        BotCommand(command="cancel", description="❌ Отменить поиск"),
        BotCommand(command="end", description="🔚 Завершить чат"),
        BotCommand(command="report", description="🚨 Пожаловаться"),
        # BotCommand(command="assistant", description="🤖 AI-Ассистент"),
        BotCommand(command="stats", description="📊 Статистика"),
        BotCommand(command="settings", description="⚙️ Настройки"),
    ]
    
    # Команды для админов
    admin_commands = commands + [
        BotCommand(command="admin", description="🛡️ Админ-панель"),
        BotCommand(command="ban", description="🚫 Забанить пользователя"),
        BotCommand(command="unban", description="✅ Разбанить пользователя"),
        BotCommand(command="broadcast", description="📢 Рассылка"),
        BotCommand(command="users", description="👥 Список пользователей"),
    ]
    
    try:
        await bot.set_my_commands(commands, scope=BotCommandScopeDefault())
        logger.info("Команды бота успешно установлены")
    except Exception as e:
        logger.error(f"Ошибка при установке команд бота: {e}")