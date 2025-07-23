import os
from dotenv import load_dotenv

load_dotenv()

# Bot settings
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Database settings
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./dating_bot.db")

# Application settings
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(","))) if os.getenv("ADMIN_IDS") else []