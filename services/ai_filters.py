import asyncio
from typing import List, Dict, Tuple, Optional, Any
from utils.debug import dbg

# Попытка импорта g4f с обработкой ошибок
try:
    import g4f
    g4f.debug.logging = False
    g4f.check_version = False
    G4F_AVAILABLE = True
except ImportError:
    G4F_AVAILABLE = False
    dbg("g4f не установлен, будет использоваться локальный алгоритм подбора", "AI_WARNING")

def is_gender_orientation_compatible(user1_data: Dict, user2_data: Dict) -> bool:
    """Проверяет совместимость по полу и ориентации"""
    # Для общения и дружбы пол и ориентация не критичны
    goal1 = user1_data.get('dating_goal', '').strip().lower()
    goal2 = user2_data.get('dating_goal', '').strip().lower()
    
    if goal1 in ['общение', 'дружба'] and goal2 in ['общение', 'дружба']:
        return True
    
    gender1 = user1_data.get('gender', '').strip().lower()
    gender2 = user2_data.get('gender', '').strip().lower()
    orientation1 = user1_data.get('orientation', '').strip().lower()
    orientation2 = user2_data.get('orientation', '').strip().lower()
    
    if not all([gender1, gender2, orientation1, orientation2]):
        return False
    
    # Гетеро мужчина совместим только с гетеро/би/пан женщиной
    if gender1 == 'мужской' and orientation1 == 'гетеро':
        return gender2 == 'женский' and orientation2 in ['гетеро', 'би', 'пан']
    
    # Гетеро женщина совместима только с гетеро/би/пан мужчиной
    if gender1 == 'женский' and orientation1 == 'гетеро':
        return gender2 == 'мужской' and orientation2 in ['гетеро', 'би', 'пан']
    
    # Гомо мужчина совместим только с гомо/би/пан мужчиной
    if gender1 == 'мужской' and orientation1 == 'гомо':
        return gender2 == 'мужской' and orientation2 in ['гомо', 'би', 'пан']
    
    # Гомо женщина совместима только с гомо/би/пан женщиной
    if gender1 == 'женский' and orientation1 == 'гомо':
        return gender2 == 'женский' and orientation2 in ['гомо', 'би', 'пан']
    
    # Би/пан люди совместимы с теми, кто может быть заинтересован в их поле
    if orientation1 in ['би', 'пан']:
        if gender1 == 'мужской':
            return orientation2 in ['гетеро', 'би', 'пан'] if gender2 == 'женский' else orientation2 in ['гомо', 'би', 'пан']
        elif gender1 == 'женский':
            return orientation2 in ['гетеро', 'би', 'пан'] if gender2 == 'мужской' else orientation2 in ['гомо', 'би', 'пан']
    
    # Для "другое" - считаем совместимыми с би/пан
    if 'другое' in [gender1, gender2, orientation1, orientation2]:
        return orientation1 in ['би', 'пан', 'другое'] or orientation2 in ['би', 'пан', 'другое']
    
    return False

def is_dating_goal_compatible(user1_data: Dict, user2_data: Dict) -> bool:
    """Проверяет совместимость целей знакомства"""
    goal1 = user1_data.get('dating_goal', '').strip().lower()
    goal2 = user2_data.get('dating_goal', '').strip().lower()
    
    if not goal1 or not goal2:
        return False
    
    # Совместимые комбинации целей
    compatible_goals = {
        'серьезные отношения': ['серьезные отношения'],
        'дружба': ['дружба', 'общение'],
        'общение': ['дружба', 'общение', 'встречи'],
        'встречи': ['встречи', 'общение']
    }
    
    return goal2 in compatible_goals.get(goal1, [])

# Локальный алгоритм для расчета совместимости
def calculate_local_compatibility(user1_data: Dict, user2_data: Dict) -> float:
    """Локальный алгоритм расчета совместимости без использования внешних API"""
    # КРИТИЧЕСКАЯ ПРОВЕРКА: Совместимость по полу и ориентации
    if not is_gender_orientation_compatible(user1_data, user2_data):
        return 0.0  # Полная несовместимость
    
    # КРИТИЧЕСКАЯ ПРОВЕРКА: Совместимость целей знакомства
    if not is_dating_goal_compatible(user1_data, user2_data):
        return 0.0  # Полная несовместимость
    
    score = 0.4  # Базовая оценка для совместимых пар
    matches = 0
    total_factors = 0
    
    # Проверка заполненности профилей
    required_fields = ['first_name', 'age', 'city', 'about', 'tags', 'gender', 'orientation', 'dating_goal']
    for field in required_fields:
        if not user1_data.get(field) or not user2_data.get(field):
            return 0.1  # Неполный профиль получает очень низкую оценку
    
    # Совпадение по городу
    if user1_data.get('city') and user2_data.get('city'):
        total_factors += 1
        if user1_data['city'].lower() == user2_data['city'].lower():
            matches += 1
            score += 0.1
    
    # Близость по возрасту
    if user1_data.get('age') and user2_data.get('age'):
        total_factors += 1
        age_diff = abs(int(user1_data['age']) - int(user2_data['age']))
        if age_diff <= 5:
            matches += 1
            score += 0.1
        elif age_diff <= 10:
            matches += 0.5
            score += 0.05
    
    # Совпадение интересов
    if user1_data.get('tags') and user2_data.get('tags'):
        total_factors += 1
        user1_tags = [tag.strip().lower() for tag in user1_data['tags'].split(',')]
        user2_tags = [tag.strip().lower() for tag in user2_data['tags'].split(',')]
        
        common_tags = set(user1_tags) & set(user2_tags)
        if common_tags:
            tag_score = min(len(common_tags) / max(len(user1_tags), len(user2_tags)), 1.0)
            matches += tag_score
            score += tag_score * 0.2
    
    # Нормализация оценки
    if total_factors > 0:
        match_ratio = matches / total_factors
        score = min(max(0.3 + match_ratio * 0.5, 0), 1)  # От 0.3 до 0.8 на основе совпадений
    
    return score

async def analyze_compatibility(user1_data: Dict, user2_data: Dict) -> float:
    """Анализирует совместимость между двумя пользователями на основе их данных."""
    dbg(f"Анализ совместимости между {user1_data['first_name']} и {user2_data['first_name']}", "AI")
    
    # Если g4f недоступен, используем локальный алгоритм
    if not G4F_AVAILABLE:
        score = calculate_local_compatibility(user1_data, user2_data)
        dbg(f"Локальная оценка совместимости: {score}", "AI")
        return score
    
    # Используем g4f, если доступен
    prompt = f"""
    Оцени совместимость двух пользователей по шкале от 0 до 1, где 1 - идеальная совместимость, а 0 - полное не совпадение.
    Учитывай их интересы, возраст, город, пол, ориентацию, цель знакомства и другие факторы.
    Оценивай только тех пользователей, у которых полностью заполнен профиль, иначе возвращай 0.0

    Пользователь 1:
    - Имя: {user1_data['first_name']}
    - Возраст: {user1_data['age']}
    - Город: {user1_data['city']}
    - О себе: {user1_data['about']}
    - Интересы: {user1_data['tags']}
    - Пол: {user1_data.get('gender', 'Не указан')}
    - Ориентация: {user1_data.get('orientation', 'Не указана')}
    - Цель знакомства: {user1_data.get('dating_goal', 'Не указана')}

    Пользователь 2:
    - Имя: {user2_data['first_name']}
    - Возраст: {user2_data['age']}
    - Город: {user2_data['city']}
    - О себе: {user2_data['about']}
    - Интересы: {user2_data['tags']}
    - Пол: {user2_data.get('gender', 'Не указан')}
    - Ориентация: {user2_data.get('orientation', 'Не указана')}
    - Цель знакомства: {user2_data.get('dating_goal', 'Не указана')}

    Верни только число от 0 до 1, без пояснений или дополнительного текста.
    Если пользователи несовместимы по полу и ориентации, верни 0.
    Если цели знакомства противоречат друг другу (например, один ищет отношения, а другой только дружбу), снизь оценку.
    """

    dbg(f"Отправка запроса к ИИ", "AI")

    try:
        # Пробуем несколько провайдеров, если один не работает
        providers = [g4f.Provider.You, g4f.Provider.Bing, g4f.Provider.ChatgptAi]
        
        for provider in providers:
            try:
                response = await g4f.ChatCompletion.create_async(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    provider=provider,
                    timeout=10  # Добавляем таймаут
                )
                
                # Проверяем, что ответ содержит число
                response = response.strip()
                if response and any(char.isdigit() for char in response):
                    # Извлекаем первое число из ответа
                    import re
                    numbers = re.findall(r"[0-9]*\.?[0-9]+", response)
                    if numbers:
                        score = float(numbers[0])
                        score = max(0, min(score, 1))  # Ограничиваем значение от 0 до 1
                        dbg(f"Оценка совместимости от {provider.__name__}: {score}", "AI")
                        return score
            except Exception as e:
                dbg(f"Ошибка при использовании {provider.__name__}: {e}", "AI_ERROR")
                continue
        
        # Если все провайдеры не сработали, используем локальный алгоритм
        dbg("Все провайдеры ИИ не сработали, используем локальный алгоритм", "AI_WARNING")
        return calculate_local_compatibility(user1_data, user2_data)
    except Exception as e:
        dbg(f"Общая ошибка при анализе совместимости: {e}", "AI_ERROR")
        return calculate_local_compatibility(user1_data, user2_data)

async def analyze_user_message(message_text: str) -> Dict[str, Any]:
    """Анализирует сообщение пользователя и возвращает оценку его содержания.
    
    Args:
        message_text: Текст сообщения для анализа
        
    Returns:
        Словарь с результатами анализа:
        {
            'is_toxic': bool,
            'toxicity_score': float,  # от 0 до 1
            'sentiment': str,  # 'positive', 'neutral', 'negative'
            'rating_change': int,  # рекомендуемое изменение рейтинга
            'block_message': bool,  # блокировать ли сообщение
            'replacement_text': str  # текст замены, если сообщение блокируется
        }
    """
    dbg(f"Анализ сообщения: '{message_text}'", "AI")
    
    # Расширенный список токсичных слов и фраз
    toxic_words = [
        'дурак', 'идиот', 'тупой', 'урод', 'ненавижу', 'заткнись', 'отвали',
        'сука', 'блять', 'хуй', 'пиздец', 'ебать', 'нахуй', 'пидор', 'гондон', 'шлюха'
    ]
    
    # Список слов и фраз, связанных с деаноном
    deanon_phrases = [
        'давай познакомимся', 'как тебя зовут', 'скинь фото', 'фото скинь',
        'давай встретимся', 'где живешь', 'номер телефона', 'телеграм', 'инстаграм',
        'вконтакте', 'вк', 'тг', 'фейсбук', 'фб', 'ватсап', 'вайбер', 'скайп'
    ]
    
    # Список слов и фраз, связанных с обнаженкой
    nude_phrases = [
        'голое фото', 'нюдсы', 'разденься', 'покажи сиськи', 'покажи грудь',
        'покажи попу', 'покажи тело', 'интим фото', 'интимное фото', 'секс фото',
        'секс видео', 'порно', 'порнуха', 'вирт', 'виртуал', 'мастурб', 'дроч', 'минет'
    ]
    
    positive_words = ['спасибо', 'пожалуйста', 'приятно', 'здорово', 'отлично', 'круто', 'классно']
    
    lower_text = message_text.lower()
    
    is_toxic = False
    toxicity_score = 0.0
    sentiment = 'neutral'
    rating_change = 0
    block_message = False
    replacement_text = ""
    
    # Проверка на токсичность
    found_toxic_words = []
    for word in toxic_words:
        if word in lower_text:
            is_toxic = True
            toxicity_score += 0.2  # Увеличиваем оценку токсичности
            rating_change -= 3  # Уменьшаем рейтинг сильнее
            found_toxic_words.append(word)
    
    if found_toxic_words:
        dbg(f"Найдены токсичные слова: {found_toxic_words}", "AI")
        # Если найдено более одного токсичного слова, блокируем сообщение
        if len(found_toxic_words) > 1:
            block_message = True
            replacement_text = "Сообщение заблокировано из-за нарушения правил. Ваш рейтинг снижен."
    
    # Проверка на попытки деанона (менее строгая для качественного общения)
    found_deanon_phrases = []
    for phrase in deanon_phrases:
        if phrase in lower_text:
            # Не блокируем сразу, только помечаем как потенциальный деанон
            toxicity_score += 0.1
            rating_change -= 2  # Меньше штрафа
            found_deanon_phrases.append(phrase)
    
    if found_deanon_phrases:
        dbg(f"Найдены попытки деанона: {found_deanon_phrases}", "AI")
        # Не блокируем автоматически - пусть система сама решает на основе качества общения
    
    # Проверка на попытки получить обнаженку (с учетом контекста)
    found_nude_phrases = []
    consent_phrases = ['согласен на 18+', 'хочу 18+', 'можно интим', 'давай 18+']
    is_consent_message = any(phrase in lower_text for phrase in consent_phrases)
    
    for phrase in nude_phrases:
        if phrase in lower_text and not is_consent_message:
            is_toxic = True
            toxicity_score += 0.4
            rating_change -= 10
            found_nude_phrases.append(phrase)
    
    if found_nude_phrases:
        dbg(f"Найдены попытки получить обнаженку: {found_nude_phrases}", "AI")
        block_message = True
        replacement_text = "Сообщение заблокировано. Запросы интимных фото или видео запрещены без взаимного согласия. Ваш рейтинг значительно снижен."
    
    # Проверка на позитив
    found_positive_words = []
    for word in positive_words:
        if word in lower_text:
            sentiment = 'positive'
            rating_change += 1  # Увеличиваем рейтинг
            found_positive_words.append(word)
    
    if found_positive_words:
        dbg(f"Найдены позитивные слова: {found_positive_words}", "AI")
    
    # Ограничиваем значения
    toxicity_score = min(1.0, toxicity_score)
    
    if toxicity_score > 0.5:
        sentiment = 'negative'
    
    result = {
        'is_toxic': is_toxic,
        'toxicity_score': toxicity_score,
        'sentiment': sentiment,
        'rating_change': rating_change,
        'block_message': block_message,
        'replacement_text': replacement_text
    }
    
    dbg(f"Результат анализа сообщения: {result}", "AI")
    return result
    
async def analyze_report_validity(chat_log: list, reporter_profile: dict, reported_profile: dict) -> dict:
    """Анализирует обоснованность жалобы на основе переписки"""
    dbg(f"Анализ обоснованности жалобы от {reporter_profile['first_name']} на {reported_profile['first_name']}", "AI")
    
    if not chat_log:
        return {
            'is_valid': False,
            'confidence': 0.0,
            'reason': 'Нет переписки для анализа',
            'action': 'ignore'
        }
    
    # Локальный анализ переписки
    toxic_count = 0
    total_messages = len(chat_log)
    reported_messages = [msg for msg in chat_log if msg['user_id'] == reported_profile.get('user_id')]
    
    if not reported_messages:
        return {
            'is_valid': False,
            'confidence': 0.0,
            'reason': 'Нет сообщений от обвиняемого',
            'action': 'ignore'
        }
    
    # Проверяем сообщения обвиняемого на токсичность
    for msg in reported_messages:
        analysis = await analyze_user_message(msg['message'])
        if analysis['is_toxic'] or analysis['block_message']:
            toxic_count += 1
    
    toxicity_ratio = toxic_count / len(reported_messages) if reported_messages else 0
    
    # Определяем обоснованность
    if toxicity_ratio >= 0.3:  # 30% токсичных сообщений
        return {
            'is_valid': True,
            'confidence': min(toxicity_ratio * 2, 1.0),
            'reason': f'Обнаружено {toxic_count} токсичных сообщений из {len(reported_messages)}',
            'action': 'penalize'
        }
    elif toxicity_ratio > 0:
        return {
            'is_valid': True,
            'confidence': toxicity_ratio,
            'reason': f'Обнаружено {toxic_count} нарушений, но мало',
            'action': 'warning'
        }
    else:
        # Проверяем, не троллит ли жалобщик
        reporter_messages = [msg for msg in chat_log if msg['user_id'] == reporter_profile.get('user_id')]
        reporter_toxic = 0
        
        for msg in reporter_messages:
            analysis = await analyze_user_message(msg['message'])
            if analysis['is_toxic']:
                reporter_toxic += 1
        
        if reporter_toxic > toxic_count:
            return {
                'is_valid': False,
                'confidence': 0.8,
                'reason': f'Жалобщик сам более токсичен ({reporter_toxic} против {toxic_count})',
                'action': 'penalize_reporter'
            }
        
        return {
            'is_valid': False,
            'confidence': 0.6,
            'reason': 'Не обнаружено нарушений',
            'action': 'ignore'
        }

    # Использование G4F временно отключено для стабильности

async def find_best_match(user_data: Dict, candidates: List[Dict]) -> Tuple[Optional[Dict], float]:
    """Находит лучшего кандидата для пользователя на основе совместимости."""
    dbg(f"Поиск лучшего совпадения для {user_data['first_name']} среди {len(candidates)} кандидатов", "AI")

    if not candidates:
        return None, 0.0

    best_candidate = None
    best_score = 0.0

    # Ограничиваем количество кандидатов для анализа, чтобы не перегружать систему
    max_candidates = min(len(candidates), 10)
    candidates_to_check = candidates[:max_candidates]
    
    for candidate in candidates_to_check:
        dbg(f"Проверка кандидата: {candidate['first_name']}", "AI")
        score = await analyze_compatibility(user_data, candidate)
        dbg(f"Оценка совместимости с {candidate['first_name']}: {score}", "AI")

        if score > best_score:
            best_score = score
            best_candidate = candidate
            dbg(f"Новый лучший кандидат: {candidate['first_name']} с оценкой {score}", "AI")

    if best_candidate:
        dbg(f"Итоговый выбор: {best_candidate['first_name']} с оценкой {best_score}", "AI")
    else:
        dbg("Подходящих кандидатов не найдено", "AI")

    return best_candidate, best_score
