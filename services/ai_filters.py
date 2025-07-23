import g4f
import asyncio
from typing import List, Dict, Tuple
from utils.debug import dbg

# Настройка g4f для работы без браузера
g4f.debug.logging = False  # Отключаем логирование
g4f.check_version = False  # Отключаем проверку версии

async def analyze_compatibility(user1_data: Dict, user2_data: Dict) -> float:
    """
    Анализирует совместимость между двумя пользователями на основе их данных.
    Возвращает коэффициент совместимости от 0 до 1.
    """
    dbg(f"Анализ совместимости между {user1_data['first_name']} и {user2_data['first_name']}", "AI")

    prompt = f"""
    Оцени совместимость двух пользователей по шкале от 0 до 1, где 1 - идеальная совместимость, а 0 - полное не совпадение.
    Учитывай их интересы, возраст, город, пол, ориентацию и другие факторы.


    Пользователь 1:
    - Имя: {user1_data['first_name']}
    - Возраст: {user1_data['age']}
    - Город: {user1_data['city']}
    - О себе: {user1_data['about']}
    - Интересы: {user1_data['tags']}
    - Пол: {user1_data.get('gender', 'Не указан')}
    - Ориентация: {user1_data.get('orientation', 'Не указана')}

    Пользователь 2:
    - Имя: {user2_data['first_name']}
    - Возраст: {user2_data['age']}
    - Город: {user2_data['city']}
    - О себе: {user2_data['about']}
    - Интересы: {user2_data['tags']}
    - Пол: {user2_data.get('gender', 'Не указан')}
    - Ориентация: {user2_data.get('orientation', 'Не указана')}


    Верни только число от 0 до 1, без пояснений или дополнительного текста.
    Если пользователи несовместимы по полу и ориентации, верни 0.
    """
    

    dbg(f"Отправка запроса к ИИ", "AI")
    
    try:
        # Используем провайдер, который не требует браузера
        response = await g4f.ChatCompletion.create_async(
            model="gpt-3.5-turbo",  # Указываем конкретную модель
            messages=[{"role": "user", "content": prompt}],
            provider=g4f.Provider.DeepAi  # Используем провайдер без браузера
        )

        dbg(f"Ответ от ИИ: {response}", "AI")
        
        score = float(response.strip())
        score = max(0, min(score, 1))  # Ограничиваем значение от 0 до 1
        dbg(f"Итоговая оценка совместимости: {score}", "AI")
        return score
    except Exception as e:
        dbg(f"Ошибка при анализе совместимости: {e}", "AI_ERROR")
        return 0.5


async def find_best_match(user_data: Dict, candidates: List[Dict]) -> Tuple[Dict, float]:
    """
    Находит лучшего кандидата для пользователя на основе совместимости.
    Возвращает словарь с данными лучшего кандидата и коэффициент совместимости.
    """
    dbg(f"Поиск лучшего совпадения для {user_data['first_name']} среди {len(candidates)} кандидатов", "AI")

    best_candidate = None
    best_score = 0.0

    for candidate in candidates:
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
