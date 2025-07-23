import logging
from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeDefault

logger = logging.getLogger(__name__)

async def set_bot_commands(bot: Bot):
    """Устанавливает команды бота"""
    commands = [
        BotCommand(command="start", description="Начать работу с ботом"),
        BotCommand(command="help", description="Показать справку"),
        BotCommand(command="profile", description="Просмотреть свой профиль"),
        BotCommand(command="find", description="Найти собеседника"),
        BotCommand(command="cancel", description="Отменить поиск собеседника"),
        BotCommand(command="end", description="Завершить текущий чат"),
        BotCommand(command="info", description="Информация о текущем чате"),
        BotCommand(command="report", description="Пожаловаться на собеседника"),
    ]
    
    try:
        await bot.set_my_commands(commands, scope=BotCommandScopeDefault())
        logger.info("Команды бота успешно установлены")
    except Exception as e:
        logger.error(f"Ошибка при установке команд бота: {e}")