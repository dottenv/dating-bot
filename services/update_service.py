import subprocess
import os
import sys
import shutil
from datetime import datetime
from config import GIT_BRANCH, BACKUP_BEFORE_UPDATE

class UpdateService:
    def __init__(self):
        self.repo_path = os.getcwd()
    
    async def check_updates(self) -> dict:
        """Проверка наличия обновлений"""
        try:
            # Получаем текущий коммит
            current = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], 
                cwd=self.repo_path
            ).decode().strip()
            
            # Получаем последний коммит с удаленного репозитория
            subprocess.run(["git", "fetch", "origin"], cwd=self.repo_path, check=True)
            remote = subprocess.check_output(
                ["git", "rev-parse", f"origin/{GIT_BRANCH}"], 
                cwd=self.repo_path
            ).decode().strip()
            
            has_updates = current != remote
            
            return {
                "has_updates": has_updates,
                "current_commit": current[:8],
                "remote_commit": remote[:8],
                "status": "Updates available" if has_updates else "Up to date"
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def create_backup(self) -> bool:
        """Создание резервной копии"""
        if not BACKUP_BEFORE_UPDATE:
            return True
            
        try:
            backup_dir = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copytree(".", backup_dir, ignore=shutil.ignore_patterns('.git', '__pycache__', '*.pyc'))
            return True
        except Exception as e:
            print(f"Backup failed: {e}")
            return False
    
    async def apply_update(self) -> dict:
        """Применение обновления"""
        try:
            # Создаем бэкап
            if not await self.create_backup():
                return {"error": "Backup failed"}
            
            # Применяем обновления
            subprocess.run(["git", "pull", "origin", GIT_BRANCH], cwd=self.repo_path, check=True)
            
            # Выполняем миграции
            subprocess.run(["aerich", "migrate"], cwd=self.repo_path, check=True)
            subprocess.run(["aerich", "upgrade"], cwd=self.repo_path, check=True)
            
            return {"success": True, "message": "Update applied successfully"}
        except Exception as e:
            return {"error": str(e)}
    
    async def restart_bot(self):
        """Перезапуск бота"""
        os.execv(sys.executable, ['python'] + sys.argv)

update_service = UpdateService()