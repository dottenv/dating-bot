import os
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

# Получаем значение DEBUG из .env (по умолчанию False)
DEBUG = os.getenv('DEBUG', 'False').lower() in ('true', '1', 't')
DEBUG_FILE = os.getenv('DEBUG_FILE', 'False').lower() in ('true', '1', 't')
DEBUG_MODULES = os.getenv('DEBUG_MODULES', '').split(',')

# Настройка логирования
logger = logging.getLogger('dating_bot')
if not logger.handlers:
    logger.setLevel(logging.DEBUG if DEBUG else logging.INFO)
    
    # Форматтер для логов
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Обработчик для вывода в консоль
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Обработчик для записи в файл, если включено
    if DEBUG_FILE:
        file_handler = logging.FileHandler('debug.log')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

# Цветовые коды для консоли
COLORS = {
    'RESET': '\033[0m',
    'RED': '\033[91m',
    'GREEN': '\033[92m',
    'YELLOW': '\033[93m',
    'BLUE': '\033[94m',
    'MAGENTA': '\033[95m',
    'CYAN': '\033[96m',
    'WHITE': '\033[97m'
}

# Цвета для разных типов модулей
MODULE_COLORS = {
    'CHAT': COLORS['GREEN'],
    'AI': COLORS['BLUE'],
    'DB': COLORS['CYAN'],
    'HANDLER': COLORS['MAGENTA'],
    'ERROR': COLORS['RED'],
    'CHAT_ERROR': COLORS['RED'],
    'AI_ERROR': COLORS['RED'],
    'DB_ERROR': COLORS['RED'],
    'WARNING': COLORS['YELLOW'],
    'AI_WARNING': COLORS['YELLOW'],
    'CHAT_CACHE': COLORS['CYAN'],
}

def dbg(message: str, module: str = "", data: Optional[Dict[str, Any]] = None):
    """
    Выводит отладочное сообщение, если включен режим DEBUG в .env
    
    Args:
        message: Сообщение для вывода
        module: Название модуля или компонента (опционально)
        data: Дополнительные данные для логирования (опционально)
    """
    # Всегда выводим логи в консоль, независимо от настроек
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    module_str = f"[{module}]" if module else ""
    
    # Добавляем цвет для модуля, если он определен
    if module in MODULE_COLORS:
        colored_module = f"{MODULE_COLORS[module]}{module_str}{COLORS['RESET']}"
    else:
        colored_module = module_str
    
    # Формируем сообщение для вывода в консоль
    console_message = f"[DEBUG {timestamp}] {colored_module} {message}"
    
    # Формируем сообщение для логирования
    log_message = f"{module_str} {message}"
    if data:
        log_message += f" | Data: {data}"
    
    # Выводим в консоль и логируем
    print(console_message, flush=True)
    
    # Также логируем через logger, если включен DEBUG
    if DEBUG:
        logger.debug(log_message)

# Функции для разных уровней логирования
def log_info(message: str, module: str = ""):
    """Логирует информационное сообщение"""
    logger.info(f"[{module}] {message}" if module else message)

def log_warning(message: str, module: str = ""):
    """Логирует предупреждение"""
    logger.warning(f"[{module}] {message}" if module else message)

def log_error(message: str, module: str = "", exc_info=False):
    """Логирует ошибку"""
    logger.error(f"[{module}] {message}" if module else message, exc_info=exc_info)

def log_critical(message: str, module: str = "", exc_info=True):
    """Логирует критическую ошибку"""
    logger.critical(f"[{module}] {message}" if module else message, exc_info=exc_info)