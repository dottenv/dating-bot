import json
import time
from typing import Dict, Optional, Any
from database.models import User, Profile

class ProfileCache:
    def __init__(self, ttl: int = 300):  # 5 минут TTL
        self.cache: Dict[int, Dict] = {}
        self.timestamps: Dict[int, float] = {}
        self.ttl = ttl
    
    def _is_expired(self, user_id: int) -> bool:
        if user_id not in self.timestamps:
            return True
        return time.time() - self.timestamps[user_id] > self.ttl
    
    async def get_profile(self, user_id: int) -> Optional[Dict]:
        if user_id in self.cache and not self._is_expired(user_id):
            return self.cache[user_id]
        
        # Загружаем из БД
        user = await User.filter(tg_id=user_id).first()
        if not user:
            return None
            
        profile = await Profile.filter(user=user).first()
        if not profile:
            return None
        
        profile_data = {
            'user_id': user_id,
            'first_name': profile.first_name,
            'age': profile.age,
            'city': profile.city,
            'about': profile.about,
            'tags': profile.tags,
            'gender': profile.gender,
            'orientation': profile.orientation,
            'dating_goal': profile.dating_goal,
            'rating': user.raiting,
            'is_premium': user.is_premium,
            'is_active': user.is_active,
            'profile_completed': profile.profile_completed
        }
        
        self.cache[user_id] = profile_data
        self.timestamps[user_id] = time.time()
        return profile_data
    
    def invalidate(self, user_id: int):
        self.cache.pop(user_id, None)
        self.timestamps.pop(user_id, None)
    
    def clear_expired(self):
        current_time = time.time()
        expired_keys = [
            user_id for user_id, timestamp in self.timestamps.items()
            if current_time - timestamp > self.ttl
        ]
        for key in expired_keys:
            self.cache.pop(key, None)
            self.timestamps.pop(key, None)

# Глобальный экземпляр кэша
profile_cache = ProfileCache()