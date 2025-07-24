import time
from typing import Dict, List, Any
from database.models import User
from services.cache import profile_cache

class AIModerationService:
    def __init__(self):
        self.violation_history: Dict[int, List[Dict]] = {}
        self.auto_ban_thresholds = {
            'spam': 5,      # 5 спам сообщений = бан на час
            'toxic': 3,     # 3 токсичных сообщения = бан на день
            'harassment': 1 # 1 харассмент = бан навсегда
        }
    
    async def moderate_message(self, user_id: int, message: str) -> Dict[str, Any]:
        # Базовая проверка
        result = {
            'allow': True,
            'violation_type': None,
            'severity': 0,
            'action': None,
            'reason': '',
            'rating_change': 0
        }
        
        message_lower = message.lower().strip()
        
        # Проверка на спам
        if self._is_spam(message_lower):
            result.update({
                'allow': False,
                'violation_type': 'spam',
                'severity': 2,
                'reason': 'Обнаружен спам',
                'rating_change': -10
            })
        
        # Проверка на токсичность
        elif self._is_toxic(message_lower):
            result.update({
                'allow': False,
                'violation_type': 'toxic',
                'severity': 3,
                'reason': 'Токсичное сообщение',
                'rating_change': -20
            })
        
        # Проверка на харассмент
        elif self._is_harassment(message_lower):
            result.update({
                'allow': False,
                'violation_type': 'harassment',
                'severity': 5,
                'reason': 'Харассмент',
                'rating_change': -50
            })
        
        # Проверка на попытки деанона
        elif self._is_deanon_attempt(message_lower):
            result.update({
                'allow': True,  # Не блокируем, но предупреждаем
                'violation_type': 'deanon',
                'severity': 1,
                'reason': 'Попытка деанона',
                'rating_change': -5
            })
        
        # Записываем нарушение
        if result['violation_type']:
            await self._record_violation(user_id, result)
            
            # Проверяем на автобан
            ban_action = await self._check_auto_ban(user_id, result['violation_type'])
            if ban_action:
                result['action'] = ban_action
        
        return result
    
    def _is_spam(self, message: str) -> bool:
        spam_patterns = [
            'купить', 'продать', 'заработок', 'деньги быстро',
            'телеграм канал', 'подписывайся', 'реклама',
            'http://', 'https://', 'www.', '.com', '.ru'
        ]
        return any(pattern in message for pattern in spam_patterns)
    
    def _is_toxic(self, message: str) -> bool:
        toxic_words = [
            'дурак', 'идиот', 'тупой', 'урод', 'сука', 'блять',
            'пиздец', 'нахуй', 'ебать', 'гондон', 'шлюха'
        ]
        return any(word in message for word in toxic_words)
    
    def _is_harassment(self, message: str) -> bool:
        harassment_patterns = [
            'убью', 'найду тебя', 'адрес знаю', 'приеду к тебе',
            'изнасилую', 'покончи с собой', 'умри'
        ]
        return any(pattern in message for pattern in harassment_patterns)
    
    def _is_deanon_attempt(self, message: str) -> bool:
        deanon_patterns = [
            'как тебя зовут', 'номер телефона', 'где живешь',
            'инстаграм', 'вконтакте', 'телеграм', 'встретимся'
        ]
        return any(pattern in message for pattern in deanon_patterns)
    
    async def _record_violation(self, user_id: int, violation: Dict):
        if user_id not in self.violation_history:
            self.violation_history[user_id] = []
        
        self.violation_history[user_id].append({
            'type': violation['violation_type'],
            'severity': violation['severity'],
            'timestamp': time.time(),
            'reason': violation['reason']
        })
        
        # Обновляем рейтинг
        user = await User.filter(tg_id=user_id).first()
        if user:
            new_rating = max(0, user.raiting + violation['rating_change'])
            await User.filter(id=user.id).update(raiting=new_rating)
            profile_cache.invalidate(user_id)
    
    async def _check_auto_ban(self, user_id: int, violation_type: str) -> str:
        if user_id not in self.violation_history:
            return None
        
        # Считаем нарушения за последние 24 часа
        recent_violations = [
            v for v in self.violation_history[user_id]
            if time.time() - v['timestamp'] < 86400 and v['type'] == violation_type
        ]
        
        threshold = self.auto_ban_thresholds.get(violation_type, 999)
        
        if len(recent_violations) >= threshold:
            if violation_type == 'spam':
                return 'ban_1h'
            elif violation_type == 'toxic':
                return 'ban_1d'
            elif violation_type == 'harassment':
                return 'ban_permanent'
        
        return None
    
    async def get_user_violations(self, user_id: int) -> List[Dict]:
        return self.violation_history.get(user_id, [])

# Глобальный экземпляр
ai_moderator = AIModerationService()