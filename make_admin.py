import asyncio
from tortoise import Tortoise
from database.models import User
from database.tortoise_config import TORTOISE_ORM

async def make_admin():
    await Tortoise.init(config=TORTOISE_ORM)
    
    admin_id = 6658529992  # Ваш ID из .env
    
    user = await User.filter(tg_id=admin_id).first()
    if user:
        await User.filter(id=user.id).update(is_admin=True)
        print(f"User {admin_id} is now admin")
    else:
        # Создаем пользователя-админа
        user = await User.create(tg_id=admin_id, is_admin=True)
        print(f"Created admin user {admin_id}")
    
    await Tortoise.close_connections()

if __name__ == "__main__":
    asyncio.run(make_admin())