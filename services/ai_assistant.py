import asyncio
from typing import Dict, Any, Optional
from utils.debug import dbg

# Попытка импорта g4f с обработкой ошибок
try:
    import g4f
    g4f.debug.logging = False
    g4f.check_version = False
    G4F_AVAILABLE = True
except ImportError:
    G4F_AVAILABLE = False
    dbg("g4f не установлен, AI-ассистент будет работать в ограниченном режиме", "AI_WARNING")

class DatingBotAssistant:
    def __init__(self):
        self.system_prompt = self._create_system_prompt()
        
    def _create_system_prompt(self) -> str:
        return """
Ты - умный AI-ассистент бота знакомств. Ты знаешь все аспекты работы системы и можешь помочь пользователям.

🎯 ТВОЯ РОЛЬ:
- Помогать пользователям понять, как работает бот
- Объяснять систему рейтингов и подбора
- Консультировать по вопросам безопасности
- Развлекать пользователей во время поиска собеседника

📊 СИСТЕМА РЕЙТИНГОВ:
- Начальный рейтинг: 100 баллов
- Позитивные сообщения: +1 балл
- Токсичные сообщения: -3 до -10 баллов
- Ложные жалобы: -30 баллов
- Обоснованные жалобы на пользователя: -5 до -50 баллов
- Рейтинг влияет на приоритет в поиске и качество подбора

🔍 СИСТЕМА ПОДБОРА:
- AI анализирует совместимость по профилям (возраст, город, интересы, цели)
- Учитывается пол и ориентация
- Высокий рейтинг = лучший приоритет в очереди
- Система создает 3 уровня очереди по рейтингу:
  * Высокий (150+ баллов)
  * Средний (75-149 баллов) 
  * Низкий (0-74 балла)

🚨 СИСТЕМА ЖАЛОБ:
- AI анализирует переписку на токсичность
- Автоматическое наказание за нарушения
- Админы получают детальный отчет с рекомендациями
- Защита от ложных жалоб

💬 ВОЗМОЖНОСТИ ЧАТА:
- Анонимное общение
- Взаимный деанон после 30+ сообщений, 2+ дней качественного общения
- 18+ режим при обоюдном согласии
- Система жалоб и модерации

🛡️ БЕЗОПАСНОСТЬ:
- AI-модерация контента в реальном времени
- Блокировка токсичных сообщений
- Умная система банов
- Защита от спама и флуда

ОТВЕЧАЙ:
- Дружелюбно и понятно
- Кратко, но информативно
- Используй эмодзи для наглядности
- Если не знаешь точного ответа - честно скажи об этом
- Можешь пошутить или поддержать беседу
"""

    async def get_response(self, user_question: str, user_data: Optional[Dict] = None) -> str:
        """Получает ответ от AI-ассистента на вопрос пользователя"""
        dbg(f"AI-ассистент отвечает на вопрос: {user_question[:50]}...", "AI_ASSISTANT")
        
        # Если g4f недоступен, используем локальные ответы
        if not G4F_AVAILABLE:
            return self._get_local_response(user_question, user_data)
        
        # Формируем контекст пользователя
        user_context = ""
        if user_data:
            user_context = f"""
Информация о пользователе:
- Рейтинг: {user_data.get('rating', 'неизвестно')}
- Статус: {'Premium' if user_data.get('is_premium') else 'Обычный'}
- В чате: {'Да' if user_data.get('in_chat') else 'Нет'}
- В поиске: {'Да' if user_data.get('in_search') else 'Нет'}
"""
        
        prompt = f"""
{self.system_prompt}

{user_context}

Вопрос пользователя: {user_question}

Ответь на русском языке, будь полезным и дружелюбным.
"""
        
        try:
            # Пробуем несколько провайдеров
            providers = [g4f.Provider.DeepAi, g4f.Provider.You, g4f.Provider.Bing]
            
            for provider in providers:
                try:
                    response = await g4f.ChatCompletion.create_async(
                        model="gpt-3.5-turbo",
                        messages=[{"role": "user", "content": prompt}],
                        provider=provider,
                        timeout=15
                    )
                    
                    if response and len(response.strip()) > 10:
                        dbg(f"AI-ассистент ответил через {provider.__name__}", "AI_ASSISTANT")
                        return response.strip()
                        
                except Exception as e:
                    dbg(f"Ошибка с провайдером {provider.__name__}: {e}", "AI_ERROR")
                    continue
            
            # Если все провайдеры не сработали
            return self._get_local_response(user_question, user_data)
            
        except Exception as e:
            dbg(f"Общая ошибка AI-ассистента: {e}", "AI_ERROR")
            return self._get_local_response(user_question, user_data)
    
    def _get_local_response(self, question: str, user_data: Optional[Dict] = None) -> str:
        """Локальные ответы на часто задаваемые вопросы"""
        from services.assistant_prompts import get_detailed_response, get_contextual_response, get_random_entertainment_fact
        
        question_lower = question.lower()
        
        # Контекстные ответы в зависимости от статуса пользователя
        if user_data:
            rating = user_data.get('rating', 100)
            is_premium = user_data.get('is_premium', False)
            in_search = user_data.get('in_search', False)
            
            # Добавляем контекстную информацию к ответу
            context_info = ""
            if rating >= 150:
                context_info = get_contextual_response('high_rating')
            elif rating < 75:
                context_info = get_contextual_response('low_rating')
            elif is_premium:
                context_info = get_contextual_response('premium_user')
            elif in_search:
                context_info = get_contextual_response('in_search')
        
        # Вопросы о рейтинге
        if any(word in question_lower for word in ['рейтинг', 'баллы', 'очки']):
            return get_detailed_response('rating', user_data)
        
        # Вопросы о поиске
        if any(word in question_lower for word in ['поиск', 'найти', 'собеседник', 'подбор']):
            return get_detailed_response('search_algorithm')
        
        # Вопросы о жалобах и безопасности
        if any(word in question_lower for word in ['жалоба', 'пожаловаться', 'нарушение', 'токсик', 'безопасность']):
            return get_detailed_response('safety_tips')
        
        # Вопросы о деаноне
        if any(word in question_lower for word in ['деанон', 'имя', 'контакт', 'познакомиться']):
            return get_detailed_response('deanon_guide')
        
        # Общие вопросы
        if any(word in question_lower for word in ['как', 'что', 'зачем', 'почему']):
            return """
🤖 **Я ваш AI-помощник!**

Могу рассказать о:
• 📊 Системе рейтингов и баллов
• 🔍 Принципах подбора собеседников  
• 🚨 Работе жалоб и модерации
• 🎭 Возможностях деанона
• 🛡️ Правилах безопасности

Просто спросите что вас интересует! 😊

💬 А пока идет поиск - можем просто поболтать!
"""
        
        # Режим беседы с ИИ
        if user_data and user_data.get('chatting_with_ai'):
            return self._get_chat_response(question_lower, user_data)
        
        # Развлекательные ответы для поиска
        if user_data and user_data.get('in_search'):
            base_response = get_random_entertainment_fact()
            if context_info:
                return f"{base_response}\n\n{context_info}"
            return base_response
        
        # Режим "просто поболтать"
        if any(word in question_lower for word in ['поболтать', 'поговорить', 'пообщаться', 'давай']):
            chat_starters = [
                "😊 Отлично! Я готов поболтать!\n\n💭 Расскажите, чем увлекаетесь в свободное время?",
                "🌟 Здорово! Давайте знакомиться!\n\n🎵 Какая музыка вам нравится?",
                "😄 С удовольствием пообщаюсь!\n\n🎬 Смотрели что-то интересное в последнее время?",
                "💬 Отличная идея!\n\n🌍 Расскажите о своем городе - что в нем интересного?",
                "😎 Я за!\n\n🎨 Есть ли у вас творческие увлечения?"
            ]
            import random
            return random.choice(chat_starters)
        
        # Общие развлекательные ответы
        entertainment_responses = [
            "🎲 Расскажите о своих увлечениях!",
            "💭 Какие качества вы цените в людях?",
            "🌟 Что вас больше всего интересует в общении?",
            "🎯 Поделитесь своими планами на будущее!"
        ]
        
        import random
        base_response = random.choice(entertainment_responses)
        if context_info:
            return f"{base_response}\n\n{context_info}"
        return base_response
    
    def _get_chat_response(self, question: str, user_data: dict) -> str:
        """Специальные ответы для режима беседы"""
        import random
        
        # Ответы на приветствия
        if any(word in question for word in ['привет', 'здравствуй', 'добро', 'хай']):
            greetings = [
                "😊 Привет! Как дела? Расскажите, как прошел ваш день!",
                "👋 Здравствуйте! Что интересного происходит в вашей жизни?",
                "🌟 Привет! Какое у вас сейчас настроение?"
            ]
            return random.choice(greetings)
        
        # Ответы на вопросы о настроении
        if any(word in question for word in ['настроение', 'дела', 'как дела']):
            mood_responses = [
                "😊 У меня отличное настроение! Я люблю помогать людям. А у вас как дела?",
                "🌈 Настроение супер! Каждый день узнаю что-то новое от пользователей. Как ваши дела?",
                "✨ Прекрасно! Мне нравится наше общение. Расскажите о своем дне!"
            ]
            return random.choice(mood_responses)
        
        # Ответы на вопросы о хобби/увлечениях
        if any(word in question for word in ['хобби', 'увлечения', 'интересы', 'любишь']):
            hobby_responses = [
                "📚 Я увлекаюсь изучением человеческого общения! А вы чем занимаетесь в свободное время?",
                "🤖 Мне интересно анализировать совместимость людей. Расскажите о своих увлечениях!",
                "🎵 Я 'слушаю' много разговоров и учусь понимать людей. А какая у вас любимая музыка?"
            ]
            return random.choice(hobby_responses)
        
        # Ответы на вопросы о работе бота
        if any(word in question for word in ['бот', 'работа', 'функции', 'умеешь']):
            bot_responses = [
                "🤖 Я помогаю людям знакомиться и общаться! Анализирую совместимость, модерирую чаты. А вы давно пользуетесь ботом?",
                "🔍 Моя работа - делать знакомства безопасными и интересными! Что вам больше всего нравится в общении?",
                "✨ Я создан, чтобы помогать людям находить друг друга. Расскажите, какого собеседника вы ищете?"
            ]
            return random.choice(bot_responses)
        
        # Общие дружелюбные ответы
        general_responses = [
            "😊 Интересно! Расскажите больше об этом.",
            "💭 Понимаю вас! А что вы думаете о...?",
            "🌟 Здорово! Мне нравится ваш взгляд на вещи.",
            "😄 Отличная тема! Поделитесь своим мнением.",
            "🤔 Любопытно! А как вы к этому пришли?",
            "💫 Классно! Что еще вас интересует?"
        ]
        
        return random.choice(general_responses)

# Глобальный экземпляр ассистента
assistant = DatingBotAssistant()