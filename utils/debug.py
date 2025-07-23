import os
from datetime import datetime
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

# Получаем значение DEBUG из .env (по умолчанию False)
DEBUG = os.getenv('DEBUG', 'False').lower() in ('true', '1', 't')

def dbg(message: str, module: str = ""):
    """
    Выводит отладочное сообщение, если включен режим DEBUG в .env
    
    Args:
        message: Сообщение для вывода
        module: Название модуля или компонента (опционально)
    """
    if DEBUG:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        module_str = f"[{module}]" if module else ""
        print(f"[DEBUG {timestamp}]{module_str} {message}")