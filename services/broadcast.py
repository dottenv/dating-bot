import asyncio
from typing import List, Dict, Optional
from database.models import User, Profile
from services.cache import profile_cache

class BroadcastService:
    def __init__(self):
        self.active_broadcasts = {}
    
    async def send_to_all(self, bot, message: str, exclude_ids: List[int] = None) -> Dict:
        users = await User.filter(is_active=True).all()
        if exclude_ids:
            users = [u for u in users if u.tg_id not in exclude_ids]
        
        return await self._send_broadcast(bot, users, message)
    
    async def send_to_premium(self, bot, message: str) -> Dict:
        users = await User.filter(is_active=True, is_premium=True).all()
        return await self._send_broadcast(bot, users, message)
    
    async def send_to_city(self, bot, city: str, message: str) -> Dict:
        users = await User.filter(is_active=True).all()
        city_users = []
        
        for user in users:
            profile = await profile_cache.get_profile(user.tg_id)
            if profile and profile.get('city', '').lower() == city.lower():
                city_users.append(user)
        
        return await self._send_broadcast(bot, city_users, message)
    
    async def send_to_gender(self, bot, gender: str, message: str) -> Dict:
        users = await User.filter(is_active=True).all()
        gender_users = []
        
        for user in users:
            profile = await profile_cache.get_profile(user.tg_id)
            if profile and profile.get('gender', '').lower() == gender.lower():
                gender_users.append(user)
        
        return await self._send_broadcast(bot, gender_users, message)
    
    async def send_ad_to_all(self, bot, text: str, media: list, reply_markup=None, exclude_ids: List[int] = None) -> Dict:
        users = await User.filter(is_active=True).all()
        if exclude_ids:
            users = [u for u in users if u.tg_id not in exclude_ids]
        
        return await self._send_ad_broadcast(bot, users, text, media, reply_markup)
    
    async def send_ad_with_settings(self, bot, text: str, media: list, reply_markup=None, settings: dict = None, exclude_ids: List[int] = None) -> Dict:
        if not settings:
            settings = {'audience': 'all', 'rounds': 1, 'frequency': 24}
        
        # Фильтруем аудиторию
        if settings['audience'] == 'premium':
            users = await User.filter(is_active=True, is_premium=True).all()
        elif settings['audience'] == 'regular':
            users = await User.filter(is_active=True, is_premium=False).all()
        else:
            users = await User.filter(is_active=True).all()
        
        if exclude_ids:
            users = [u for u in users if u.tg_id not in exclude_ids]
        
        total_sent = 0
        total_failed = 0
        
        # Отправляем нужное количество кругов
        for round_num in range(settings['rounds']):
            result = await self._send_ad_broadcast(bot, users, text, media, reply_markup)
            total_sent += result['sent']
            total_failed += result['failed']
            
            # Если не последний круг, ждем
            if round_num < settings['rounds'] - 1:
                await asyncio.sleep(settings['frequency'] * 3600)  # Часы в секунды
        
        return {
            'total': len(users),
            'sent': total_sent,
            'failed': total_failed,
            'rounds': settings['rounds'],
            'errors': []
        }
    
    async def _send_ad_broadcast(self, bot, users: List[User], text: str, media: list, reply_markup=None) -> Dict:
        sent = 0
        failed = 0
        errors = []
        
        for user in users:
            try:
                if media:
                    media_item = media[0]
                    if media_item['type'] == 'photo':
                        await bot.send_photo(
                            user.tg_id, 
                            media_item['file_id'], 
                            caption=text, 
                            reply_markup=reply_markup,
                            parse_mode="Markdown"
                        )
                    elif media_item['type'] == 'video':
                        await bot.send_video(
                            user.tg_id, 
                            media_item['file_id'], 
                            caption=text, 
                            reply_markup=reply_markup,
                            parse_mode="Markdown"
                        )
                    elif media_item['type'] == 'document':
                        await bot.send_document(
                            user.tg_id, 
                            media_item['file_id'], 
                            caption=text, 
                            reply_markup=reply_markup,
                            parse_mode="Markdown"
                        )
                else:
                    await bot.send_message(
                        user.tg_id, 
                        text, 
                        reply_markup=reply_markup,
                        parse_mode="Markdown"
                    )
                
                sent += 1
                await asyncio.sleep(0.05)  # Защита от rate limit
            except Exception as e:
                failed += 1
                errors.append(f"User {user.tg_id}: {str(e)}")
        
        return {
            'total': len(users),
            'sent': sent,
            'failed': failed,
            'errors': errors[:10]  # Первые 10 ошибок
        }
    
    async def _send_broadcast(self, bot, users: List[User], message: str) -> Dict:
        sent = 0
        failed = 0
        errors = []
        
        for user in users:
            try:
                await bot.send_message(user.tg_id, message, parse_mode="Markdown")
                sent += 1
                await asyncio.sleep(0.05)  # Защита от rate limit
            except Exception as e:
                failed += 1
                errors.append(f"User {user.tg_id}: {str(e)}")
        
        return {
            'total': len(users),
            'sent': sent,
            'failed': failed,
            'errors': errors[:10]  # Первые 10 ошибок
        }

# Глобальный экземпляр
broadcast_service = BroadcastService()