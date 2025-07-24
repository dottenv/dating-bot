import asyncio
from typing import List, Dict, Optional, Tuple
from services.cache import profile_cache
from services.ai_filters import is_gender_orientation_compatible, is_dating_goal_compatible
import time

class SmartMatchingService:
    def __init__(self):
        self.blacklist: Dict[int, List[int]] = {}
        self.match_history: Dict[int, List[int]] = {}  # История матчей пользователя
        self.user_preferences: Dict[int, Dict] = {}  # Изученные предпочтения
    
    def add_to_blacklist(self, user_id: int, blocked_user_id: int):
        if user_id not in self.blacklist:
            self.blacklist[user_id] = []
        if blocked_user_id not in self.blacklist[user_id]:
            self.blacklist[user_id].append(blocked_user_id)
    
    def is_blacklisted(self, user_id: int, candidate_id: int) -> bool:
        return candidate_id in self.blacklist.get(user_id, [])
    
    def learn_from_interaction(self, user_id: int, partner_id: int, interaction_quality: str):
        """Обучение на основе качества взаимодействия"""
        if user_id not in self.user_preferences:
            self.user_preferences[user_id] = {'positive_traits': {}, 'negative_traits': {}}
        
        # Получаем профиль партнера для анализа
        # Здесь можно добавить логику обучения на основе успешных/неуспешных матчей
    
    async def calculate_ai_compatibility(self, user_profile: Dict, candidate_profile: Dict, relaxed_level: int = 0) -> float:
        """Интеллектуальный расчет совместимости с учетом ослабления правил"""
        
        # Базовые проверки (всегда обязательны)
        if not is_gender_orientation_compatible(user_profile, candidate_profile):
            return 0.0
        
        score = 0.0
        factors = []
        
        # 1. Совместимость целей (критично для уровней 0-2)
        goal_compatible = is_dating_goal_compatible(user_profile, candidate_profile)
        if relaxed_level < 3 and not goal_compatible:
            return 0.0
        
        if goal_compatible:
            score += 0.3
            factors.append("цели совпадают")
        elif relaxed_level >= 3:
            score += 0.1
            factors.append("цели частично совместимы")
        
        # 2. Возрастная совместимость (с постепенным ослаблением)
        if user_profile.get('age') and candidate_profile.get('age'):
            age_diff = abs(int(user_profile['age']) - int(candidate_profile['age']))
            
            if age_diff <= 3:
                score += 0.25
                factors.append("идеальный возраст")
            elif age_diff <= 7:
                score += 0.2
                factors.append("хороший возраст")
            elif age_diff <= 12:
                score += 0.15
                factors.append("приемлемый возраст")
            elif relaxed_level >= 1 and age_diff <= 15:
                score += 0.1
                factors.append("расширенный возраст")
            elif relaxed_level >= 2 and age_diff <= 20:
                score += 0.05
                factors.append("широкий возрастной диапазон")
            elif relaxed_level >= 4:
                score += 0.02
                factors.append("любой возраст")
        
        # 3. Географическая близость
        same_city = user_profile.get('city', '').lower() == candidate_profile.get('city', '').lower()
        if same_city:
            score += 0.2
            factors.append("тот же город")
        elif relaxed_level >= 2:
            score += 0.05
            factors.append("разные города")
        
        # 4. Общие интересы (ИИ-анализ)
        interest_score = await self._analyze_interests_compatibility(
            user_profile.get('tags', ''), 
            candidate_profile.get('tags', ''),
            user_profile.get('about', ''),
            candidate_profile.get('about', '')
        )
        score += interest_score * 0.15
        if interest_score > 0.5:
            factors.append("много общих интересов")
        elif interest_score > 0.2:
            factors.append("есть общие интересы")
        
        # 5. Анализ описаний профилей
        description_score = await self._analyze_personality_compatibility(
            user_profile.get('about', ''),
            candidate_profile.get('about', '')
        )
        score += description_score * 0.1
        if description_score > 0.6:
            factors.append("совместимые личности")
        
        print(f"AI compatibility: {score:.2f} - {', '.join(factors)}")
        return min(score, 1.0)
    
    async def _analyze_interests_compatibility(self, tags1: str, tags2: str, about1: str, about2: str) -> float:
        """ИИ-анализ совместимости интересов"""
        if not tags1 or not tags2:
            return 0.0
        
        # Простой анализ пересечения тегов
        tags1_set = set(tag.strip().lower() for tag in tags1.split(','))
        tags2_set = set(tag.strip().lower() for tag in tags2.split(','))
        
        common_tags = tags1_set & tags2_set
        total_tags = tags1_set | tags2_set
        
        if not total_tags:
            return 0.0
        
        base_score = len(common_tags) / len(total_tags)
        
        # Бонус за качественные совпадения
        quality_bonus = 0.0
        high_value_interests = {'спорт', 'музыка', 'кино', 'путешествия', 'книги', 'искусство', 'наука'}
        quality_matches = common_tags & high_value_interests
        if quality_matches:
            quality_bonus = len(quality_matches) * 0.1
        
        return min(base_score + quality_bonus, 1.0)
    
    async def _analyze_personality_compatibility(self, about1: str, about2: str) -> float:
        """ИИ-анализ совместимости личностей по описаниям"""
        if not about1 or not about2:
            return 0.3  # Нейтральная оценка при отсутствии данных
        
        # Простой анализ тональности и ключевых слов
        positive_words = ['добрый', 'веселый', 'активный', 'позитивный', 'открытый', 'дружелюбный']
        negative_words = ['грустный', 'замкнутый', 'серьезный', 'интроверт']
        
        about1_lower = about1.lower()
        about2_lower = about2.lower()
        
        # Анализ тональности
        pos1 = sum(1 for word in positive_words if word in about1_lower)
        pos2 = sum(1 for word in positive_words if word in about2_lower)
        neg1 = sum(1 for word in negative_words if word in about1_lower)
        neg2 = sum(1 for word in negative_words if word in about2_lower)
        
        # Совместимость по тональности
        if (pos1 > neg1 and pos2 > neg2) or (neg1 >= pos1 and neg2 >= pos2):
            return 0.7  # Схожая тональность
        else:
            return 0.4  # Разная тональность может быть дополняющей
    
    async def find_best_matches(self, user_id: int, candidate_ids: List[int], relaxed_level: int = 0) -> List[Tuple[int, float, List[str]]]:
        """Находит лучших кандидатов с ИИ-анализом"""
        user_profile = await profile_cache.get_profile(user_id)
        if not user_profile:
            return []
        
        matches = []
        
        for candidate_id in candidate_ids:
            if candidate_id == user_id or self.is_blacklisted(user_id, candidate_id):
                continue
            
            candidate_profile = await profile_cache.get_profile(candidate_id)
            if not candidate_profile or not candidate_profile.get('profile_completed'):
                continue
            
            # ИИ-анализ совместимости
            score = await self.calculate_ai_compatibility(user_profile, candidate_profile, relaxed_level)
            
            if score > 0.1:  # Минимальный порог
                # Генерируем объяснение совместимости
                explanation = await self._generate_match_explanation(user_profile, candidate_profile, score)
                matches.append((candidate_id, score, explanation))
        
        # Сортируем по убыванию совместимости
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches[:10]  # Топ-10
    
    async def _generate_match_explanation(self, user_profile: Dict, candidate_profile: Dict, score: float) -> List[str]:
        """Генерирует объяснение почему пользователи совместимы"""
        reasons = []
        
        # Возраст
        if user_profile.get('age') and candidate_profile.get('age'):
            age_diff = abs(int(user_profile['age']) - int(candidate_profile['age']))
            if age_diff <= 3:
                reasons.append("очень близкий возраст")
            elif age_diff <= 7:
                reasons.append("подходящий возраст")
        
        # Город
        if user_profile.get('city', '').lower() == candidate_profile.get('city', '').lower():
            reasons.append("из одного города")
        
        # Цели
        if user_profile.get('dating_goal', '').lower() == candidate_profile.get('dating_goal', '').lower():
            reasons.append("одинаковые цели знакомства")
        
        # Интересы
        if user_profile.get('tags') and candidate_profile.get('tags'):
            user_tags = set(tag.strip().lower() for tag in user_profile['tags'].split(','))
            candidate_tags = set(tag.strip().lower() for tag in candidate_profile['tags'].split(','))
            common = user_tags & candidate_tags
            if len(common) >= 2:
                reasons.append(f"общие интересы: {', '.join(list(common)[:3])}")
            elif len(common) == 1:
                reasons.append(f"общий интерес: {list(common)[0]}")
        
        if score > 0.7:
            reasons.append("высокая совместимость")
        elif score > 0.5:
            reasons.append("хорошая совместимость")
        
        return reasons[:3]  # Максимум 3 причины

# Глобальный экземпляр
smart_matcher = SmartMatchingService()