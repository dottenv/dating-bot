from typing import Dict, Any
from utils.debug import dbg

def analyze_user_message(message_text: str) -> Dict[str, Any]:
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
    
    # Проверка на попытки деанона
    found_deanon_phrases = []
    for phrase in deanon_phrases:
        if phrase in lower_text:
            is_toxic = True
            toxicity_score += 0.3
            rating_change -= 5  # Сильно уменьшаем рейтинг за попытки деанона
            found_deanon_phrases.append(phrase)
    
    if found_deanon_phrases:
        dbg(f"Найдены попытки деанона: {found_deanon_phrases}", "AI")
        block_message = True
        replacement_text = "Сообщение заблокировано. Попытки деанона запрещены. Ваш рейтинг снижен."
    
    # Проверка на попытки получить обнаженку
    found_nude_phrases = []
    for phrase in nude_phrases:
        if phrase in lower_text:
            is_toxic = True
            toxicity_score += 0.4
            rating_change -= 10  # Очень сильно уменьшаем рейтинг за попытки получить обнаженку
            found_nude_phrases.append(phrase)
    
    if found_nude_phrases:
        dbg(f"Найдены попытки получить обнаженку: {found_nude_phrases}", "AI")
        block_message = True
        replacement_text = "Сообщение заблокировано. Запросы интимных фото или видео запрещены. Ваш рейтинг значительно снижен."
    
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