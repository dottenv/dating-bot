import os
from dotenv import load_dotenv

load_dotenv()

# Bot settings
BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite://dating_bot.db")

# Update system
GIT_REPO_URL = os.getenv("GIT_REPO_URL", "")
GIT_BRANCH = os.getenv("GIT_BRANCH", "main")
AUTO_RESTART = os.getenv("AUTO_RESTART", "true").lower() == "true"
BACKUP_BEFORE_UPDATE = os.getenv("BACKUP_BEFORE_UPDATE", "true").lower() == "true"

# Admin settings
ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]