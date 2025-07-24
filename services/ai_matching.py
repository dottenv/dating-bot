import asyncio
from typing import List, Dict, Optional, Tuple
from services.cache import profile_cache
from services.ai_filters import is_gender_orientation_compatible, is_dating_goal_compatible
from utils.debug import dbg

class AIMatchingService:
    def __init__(self):
        self.blacklist: Dict[int, List[int]] = {}  # {user_id: [blocked_user_ids]}
    
    def add_to_blacklist(self, user_id: int, blocked_user_id: int):
        if user_id not in self.blacklist:
            self.blacklist[user_id] = []
        if blocked_user_id not in self.blacklist[user_id]:
            self.blacklist[user_id].append(blocked_user_id)
    
    def is_blacklisted(self, user_id: int, candidate_id: int) -> bool:
        return candidate_id in self.blacklist.get(user_id, [])
    
    async def find_best_matches(self, user_id: int, candidate_ids: List[int], filters: Dict = None) -> List[Tuple[int, float]]:
        user_profile = await profile_cache.get_profile(user_id)
        if not user_profile:
            return []
        
        matches = []
        for candidate_id in candidate_ids:
            if candidate_id == user_id:
                continue
                
            if self.is_blacklisted(user_id, candidate_id):
                continue
            
            candidate_profile = await profile_cache.get_profile(candidate_id)
            if not candidate_profile:
                continue
            
            # Применяем фильтры
            if not self._apply_filters(user_profile, candidate_profile, filters):
                continue
            
            # Базовая проверка совместимости
            if not (is_gender_orientation_compatible(user_profile, candidate_profile) and 
                    is_dating_goal_compatible(user_profile, candidate_profile)):
                continue
            
            # ИИ оценка совместимости
            score = await self._calculate_ai_compatibility(user_profile, candidate_profile)
            if score > 0.1:
                matches.append((candidate_id, score))
        
        # Сортируем по убыванию совместимости
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches[:10]  # Топ-10 кандидатов
    
    def _apply_filters(self, user_profile: Dict, candidate_profile: Dict, filters: Dict = None) -> bool:
        if not filters:
            return True
        
        # Фильтр по возрасту
        if 'age_min' in filters or 'age_max' in filters:
            age = candidate_profile.get('age')
            if not age:
                return False
            if filters.get('age_min', 0) > age or age > filters.get('age_max', 100):
                return False
        
        # Фильтр по городу
        if 'city' in filters and filters['city']:
            if candidate_profile.get('city', '').lower() != filters['city'].lower():
                return False
        
        # Фильтр по рейтингу
        if 'min_rating' in filters:
            if candidate_profile.get('rating', 0) < filters['min_rating']:
                return False
        
        return True
    
    async def _calculate_ai_compatibility(self, user1: Dict, user2: Dict) -> float:
        # Базовая оценка
        score = 0.4
        
        # Город (+0.2)
        if user1.get('city', '').lower() == user2.get('city', '').lower():
            score += 0.2
        
        # Возраст (+0.1-0.2)
        age_diff = abs(user1.get('age', 25) - user2.get('age', 25))
        if age_diff <= 3:
            score += 0.2
        elif age_diff <= 7:
            score += 0.1
        
        # Интересы (+0.1-0.3)
        if user1.get('tags') and user2.get('tags'):
            tags1 = set(tag.strip().lower() for tag in user1['tags'].split(','))
            tags2 = set(tag.strip().lower() for tag in user2['tags'].split(','))
            common = len(tags1 & tags2)
            if common > 0:
                score += min(common * 0.1, 0.3)
        
        # Рейтинг (+0.1)
        rating_diff = abs(user1.get('rating', 100) - user2.get('rating', 100))
        if rating_diff <= 50:
            score += 0.1
        
        return min(score, 1.0)

# Глобальный экземпляр
ai_matcher = AIMatchingService()