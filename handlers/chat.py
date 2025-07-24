from aiogram import types, Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import asyncio
import random
import time

from database.models import User, Profile
from services.smart_matching import smart_matcher
from keyboards.profile import create_keyboard

router = Router()

class ChatStates(StatesGroup):
    searching = State()
    chatting = State()

# Активные чаты: {user_id: partner_id}
active_chats = {}
# Очередь поиска: {rating_tier: [user_ids]}
search_queue = {"high": [], "medium": [], "low": []}

async def background_partner_search(user_id: int, user_profile: dict, user_tier: str, bot):
    """Фоновый поиск партнеров каждые 3 секунды"""
    for i in range(200):  # 10 минут максимум
        await asyncio.sleep(3)
        
        # ИСПРАВЛЕНИЕ: Проверяем, не нашел ли уже партнера или не в очереди
        if user_id in active_chats:
            break
            
        user_in_queue = any(user_id in queue for queue in search_queue.values())
        if not user_in_queue:
            break
            
        # Ищем партнера с постепенным ослаблением правил
        print(f"Background search for {user_id}, tier: {user_tier}, queue: {search_queue}")
        # Определяем уровень ослабления правил на основе времени поиска
        relaxed_level = min(i // 20, 4)  # Каждую минуту увеличиваем уровень ослабления (0-4)
        partner_id = await find_compatible_partner(user_id, user_profile, user_tier, relaxed_level)
        print(f"Found partner: {partner_id} (relaxed_level: {relaxed_level})")
        
        if partner_id:
            # Убираем обоих из очереди
            for tier_queue in search_queue.values():
                if user_id in tier_queue:
                    tier_queue.remove(user_id)
                if partner_id in tier_queue:
                    tier_queue.remove(partner_id)
            
            # Создаем чат
            active_chats[user_id] = partner_id
            active_chats[partner_id] = user_id
            
            kb = create_keyboard([
                ("Завершить чат", "end_chat"),
                ("Пожаловаться", "report_user")
            ])
            
            try:
                # Получаем информацию о качестве подбора
                matches = await smart_matcher.find_best_matches(user_id, [partner_id], relaxed_level)
                match_info = ""
                if matches:
                    score, reasons = matches[0][1], matches[0][2]
                    if relaxed_level > 0:
                        match_info = f"\n🔄 Подбор с расширенными критериями: {', '.join(reasons)}"
                    elif score > 0.6:
                        match_info = f"\n✨ Отличный подбор: {', '.join(reasons)}"
                    elif reasons:
                        match_info = f"\n🔍 Подбор по: {', '.join(reasons)}"
                
                # Отправляем уведомления обоим пользователям
                await bot.send_message(user_id, f"**Собеседник найден**{match_info}\n\nМожете начинать общение.", reply_markup=kb, parse_mode="Markdown")
                await bot.send_message(partner_id, f"**Собеседник найден**{match_info}\n\nМожете начинать общение.", reply_markup=kb, parse_mode="Markdown")
                
                # Устанавливаем состояние чата для обоих (нужно для FSM)
                from aiogram.fsm.storage.memory import MemoryStorage
                # Пока просто отмечаем в логах
                print(f"Chat created: {user_id} <-> {partner_id}")
            except Exception as e:
                print(f"Error sending messages: {e}")
            break

async def update_search_progress_simple(user_id: int, message, user_tier: str):
    """Упрощенное обновление прогресса поиска без AI-ассистента"""
    for i in range(120):  # 10 минут максимум
        await asyncio.sleep(5)
        
        # Проверяем, не найден ли партнер или пользователь не в очереди
        if user_id in active_chats:
            break
            
        user_in_queue = any(user_id in queue for queue in search_queue.values())
        if not user_in_queue:
            break
            
        total_in_queue = sum(len(queue) for queue in search_queue.values())
        tier_count = len(search_queue[user_tier])
        progress_text = f"В очереди: {total_in_queue} | Ваш уровень: {tier_count} чел."
        
        # Советы с информацией о новой ИИ-системе
        tips = [
            "🤖 ИИ анализирует ваши интересы и личность для идеального подбора",
            "🎯 Система учитывает совместимость личностей по описаниям",
            "✨ Качество подбора улучшается с каждым вашим чатом",
            "🔍 Подробно заполните профиль - это помогает ИИ найти вам лучших собеседников",
            "💬 Общайтесь качественно - система запоминает успешные матчи",
            "🔄 Постепенно расширяем критерии для поиска наиболее подходящих людей",
            "⏰ Максимальное время поиска - 10 минут, ИИ найдет кого-то подходящего!"
        ]
        
        kb = create_keyboard([("Отменить поиск", "cancel_search")])
        
        # Показываем совет каждые 15 секунд и информацию об ослаблении правил
        relaxed_level = min(i // 12, 4)  # Каждую минуту увеличиваем уровень
        relaxed_info = ""
        if relaxed_level == 1:
            relaxed_info = "\n🔄 Расширяем возрастные рамки (до 15 лет разницы)"
        elif relaxed_level == 2:
            relaxed_info = "\n🔄 Расширяем возраст + разрешаем разные города"
        elif relaxed_level == 3:
            relaxed_info = "\n🔄 Расширяем возраст + город + цели знакомства"
        elif relaxed_level >= 4:
            relaxed_info = "\n🔄 Максимальное ослабление критериев (кроме пола/ориентации)"
        
        if i % 3 == 0 and i > 0:
            tip = tips[(i // 3 - 1) % len(tips)]
            try:
                await message.edit_text(f"**Поиск активен** `({i*5+5}с)`\n\n{progress_text}{relaxed_info}\n\n{tip}", reply_markup=kb, parse_mode="Markdown")
            except:
                pass
        else:
            try:
                await message.edit_text(f"**Поиск активен** `({i*5+5}с)`\n\n{progress_text}{relaxed_info}", reply_markup=kb, parse_mode="Markdown")
            except:
                break

def get_rating_tier(rating: int) -> str:
    if rating >= 700:
        return "high"
    elif rating >= 300:
        return "medium"
    else:
        return "low"

def get_search_tiers(user_tier: str) -> list:
    # Для тестирования - разрешаем всем искать друг друга
    return ["high", "medium", "low"]

async def find_compatible_partner(user_id: int, user_profile: dict, user_tier: str, relaxed_level: int = 0):
    search_tiers = get_search_tiers(user_tier)
    candidates = []
    
    for tier in search_tiers:
        if tier in search_queue:
            candidates.extend(search_queue[tier])
    
    if not candidates:
        return None
    
    # Используем новую интеллектуальную систему подбора
    matches = await smart_matcher.find_best_matches(user_id, candidates, relaxed_level)
    
    if not matches:
        print(f"No AI matches found for {user_profile['first_name']} (relaxed_level: {relaxed_level})")
        return None
    
    best_match = matches[0]
    best_match_id, score, reasons = best_match
    
    print(f"AI match for {user_profile['first_name']}: score {score:.2f}, reasons: {', '.join(reasons)}")
    return best_match_id

@router.message(F.text == "Найти собеседника")
async def start_search(message: types.Message, state: FSMContext):
    user = await User.filter(tg_id=message.from_user.id).first()
    if not user:
        await message.answer("Сначала пройдите регистрацию /start")
        return
    
    profile = await Profile.filter(user=user).first()
    if not profile or not profile.profile_completed:
        await message.answer("Завершите заполнение профиля")
        return
    
    # Проверяем, не в чате ли уже
    if message.from_user.id in active_chats:
        await message.answer("Вы уже в чате! Завершите текущий разговор.")
        return
    
    user_tier = get_rating_tier(user.raiting)
    # Используем кэшированные данные
    from services.cache import profile_cache
    user_profile = await profile_cache.get_profile(message.from_user.id)
    if not user_profile or not user_profile['profile_completed']:
        await message.answer("Завершите заполнение профиля")
        return
    
    # Показываем прогресс поиска
    total_in_queue = sum(len(queue) for queue in search_queue.values())
    tier_count = len(search_queue[user_tier])
    
    # Ищем партнера
    print(f"Initial search for {message.from_user.id}, tier: {user_tier}, queue: {search_queue}")
    partner_id = await find_compatible_partner(message.from_user.id, user_profile, user_tier, 0)
    print(f"Initial found partner: {partner_id}")
    
    if partner_id:
        # Создаем чат сначала
        active_chats[message.from_user.id] = partner_id
        active_chats[partner_id] = message.from_user.id
        print(f"Chat created between {message.from_user.id} and {partner_id}")
        
        # Теперь убираем обоих из очереди
        for tier_queue in search_queue.values():
            if message.from_user.id in tier_queue:
                tier_queue.remove(message.from_user.id)
            if partner_id in tier_queue:
                tier_queue.remove(partner_id)
        
        kb = create_keyboard([
            ("Завершить чат", "end_chat"),
            ("Пожаловаться", "report_user")
        ])
        
        # Получаем информацию о качестве подбора
        matches = await smart_matcher.find_best_matches(message.from_user.id, [partner_id], 0)
        match_info = ""
        if matches:
            score, reasons = matches[0][1], matches[0][2]
            if score > 0.7:
                match_info = f"\n🎆 Отличная совместимость: {', '.join(reasons)}"
            elif score > 0.5:
                match_info = f"\n✨ Хорошая совместимость: {', '.join(reasons)}"
            elif reasons:
                match_info = f"\n🔍 Подбор по: {', '.join(reasons)}"
        
        await message.answer(f"**Собеседник найден**{match_info}\n\nМожете начинать общение.", reply_markup=kb, parse_mode="Markdown")
        await message.bot.send_message(partner_id, f"**Собеседник найден**{match_info}\n\nМожете начинать общение.", reply_markup=kb, parse_mode="Markdown")
        
        await state.set_state(ChatStates.chatting)
        print(f"Set chatting state for {message.from_user.id}")
    else:
        # Добавляем в очередь поиска
        if message.from_user.id not in search_queue[user_tier]:
            search_queue[user_tier].append(message.from_user.id)
            print(f"Added {message.from_user.id} to queue {user_tier}. Queue now: {search_queue}")
        
        # Запускаем фоновый поиск партнеров
        asyncio.create_task(background_partner_search(message.from_user.id, user_profile, user_tier, message.bot))
        
        # Показываем критерии подбора
        search_criteria = f"🎯 **Критерии подбора:**\n"
        search_criteria += f"• Город: {user_profile.get('city', 'Не указан')}\n"
        search_criteria += f"• Цель: {user_profile.get('dating_goal', 'Не указана')}\n"
        search_criteria += f"• Возраст: {user_profile.get('age', 'Не указан')} лет\n"
        search_criteria += f"• Пол/ориентация: {user_profile.get('gender', 'Не указан')}/{user_profile.get('orientation', 'Не указана')}\n\n"
        
        kb = create_keyboard([("Отменить поиск", "cancel_search")])
        search_msg = await message.answer(f"**Поиск собеседника**\n\n{search_criteria}Пожалуйста, ожидайте...", reply_markup=kb, parse_mode="Markdown")
        
        # Показываем прогресс в callback
        progress_text = f"В очереди: {total_in_queue + 1} | Ваш уровень: {tier_count + 1} чел.\nОжидание: до 10 минут"
        try:
            await search_msg.edit_text(f"**Поиск активен**\n\n{search_criteria}{progress_text}", reply_markup=kb, parse_mode="Markdown")
        except:
            pass
        
        await state.set_state(ChatStates.searching)
        
        # Запускаем периодическое обновление прогресса (без AI-ассистента)
        asyncio.create_task(update_search_progress_simple(message.from_user.id, search_msg, user_tier))

@router.callback_query(F.data == "cancel_search")
async def cancel_search(callback: types.CallbackQuery, state: FSMContext):
    for tier_queue in search_queue.values():
        if callback.from_user.id in tier_queue:
            tier_queue.remove(callback.from_user.id)
    
    await callback.message.edit_text("**Поиск отменен**", parse_mode="Markdown")
    await state.clear()

@router.callback_query(F.data.startswith("relaxed_search_"))
async def relaxed_search(callback: types.CallbackQuery):
    user_id = int(callback.data.split("_")[2])
    
    if user_id != callback.from_user.id:
        await callback.answer("Ошибка авторизации")
        return
    
    from services.cache import profile_cache
    user_profile = await profile_cache.get_profile(user_id)
    user_tier = get_rating_tier((await User.filter(tg_id=user_id).first()).raiting)
    
    # Поиск в расслабленном режиме (максимальное ослабление)
    partner_id = await find_compatible_partner(user_id, user_profile, user_tier, 4)
    
    if partner_id:
        # Создаем чат
        active_chats[user_id] = partner_id
        active_chats[partner_id] = user_id
        
        # Убираем из очереди
        for tier_queue in search_queue.values():
            if user_id in tier_queue:
                tier_queue.remove(user_id)
            if partner_id in tier_queue:
                tier_queue.remove(partner_id)
        
        kb = create_keyboard([
            ("Завершить чат", "end_chat"),
            ("Пожаловаться", "report_user")
        ])
        
        await callback.message.edit_text(
            "**🎉 Собеседник найден!**\n\n"
            "💡 Подбор по расширенным критериям\n"
            "Можете начинать общение!",
            reply_markup=kb,
            parse_mode="Markdown"
        )
        
        await callback.bot.send_message(
            partner_id,
            "**🎉 Собеседник найден!**\n\n"
            "💡 Подбор по расширенным критериям\n"
            "Можете начинать общение!",
            reply_markup=kb,
            parse_mode="Markdown"
        )
    else:
        await callback.message.edit_text(
            "**😔 К сожалению, никого не нашлось**\n\n"
            "Попробуйте позже или обновите свой профиль.",
            parse_mode="Markdown"
        )
    
    await callback.answer()

@router.callback_query(F.data == "end_chat")
async def end_chat(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    partner_id = active_chats.get(user_id)
    
    if partner_id:
        # Завершаем чат для обоих
        del active_chats[user_id]
        del active_chats[partner_id]
        
        await callback.message.edit_text("**Чат завершен**\n\nСпасибо за общение.", parse_mode="Markdown")
        await callback.bot.send_message(partner_id, "**Чат завершен**\n\nСпасибо за общение.", parse_mode="Markdown")
    
    await state.clear()

@router.callback_query(F.data == "report_user")
async def report_user(callback: types.CallbackQuery):
    try:
        print(f"Report button clicked by {callback.from_user.id}")
        user_id = callback.from_user.id
        partner_id = active_chats.get(user_id)
        
        print(f"Reporter: {user_id}, Reported: {partner_id}")
        
        if not partner_id:
            await callback.answer("Нет активного чата")
            return
        
        if partner_id:
            # Получаем информацию о пользователях
            reporter_user = await User.filter(tg_id=user_id).first()
            reported_user = await User.filter(tg_id=partner_id).first()
            
            reporter_profile = await Profile.filter(user=reporter_user).first()
            reported_profile = await Profile.filter(user=reported_user).first()
        
            # Получаем реальный лог переписки
            from bot import chat_logger
            chat_log = chat_logger.get_chat_log(user_id, partner_id)
            print(f"Chat log for report: {len(chat_log)} messages")
        
            # AI-анализ обоснованности жалобы
            try:
                from services.ai_filters import analyze_report_validity
                
                reporter_data = {
                    'user_id': user_id,
                    'first_name': reporter_profile.first_name
                }
                reported_data = {
                    'user_id': partner_id,
                    'first_name': reported_profile.first_name
                }
                
                validity = await analyze_report_validity(chat_log, reporter_data, reported_data)
                print(f"AI analysis result: {validity}")
            except Exception as e:
                print(f"AI analysis failed: {e}")
                # Fallback - стандартное наказание
                validity = {
                    'is_valid': True,
                    'confidence': 0.5,
                    'reason': 'Ошибка AI-анализа, стандартное наказание',
                    'action': 'warning'
                }
        
        # Создаем сообщение для админов с AI-анализом
        status_emoji = "✅" if validity['is_valid'] else "❌"
        report_text = f"{status_emoji} ЖАЛОБА ({validity['action'].upper()})\n\n"
        report_text += f"👤 Отправитель: {reporter_profile.first_name} (ID: {user_id})\n"
        report_text += f"🎯 На кого: {reported_profile.first_name} (ID: {partner_id})\n"
        report_text += f"📅 Время: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        report_text += f"🤖 AI-анализ:\n"
        report_text += f"• Обоснованность: {validity['confidence']:.0%}\n"
        report_text += f"• Причина: {validity['reason']}\n"
        report_text += f"• Действие: {validity['action']}\n\n"
        report_text += f"📊 Рейтинг обвиняемого: {reported_user.raiting}\n"
        
        # Создаем кнопки для админов
        admin_kb = create_keyboard([
            ("Бан 1ч", f"admin_ban_1h_{partner_id}_{user_id}"), ("Бан 1д", f"admin_ban_1d_{partner_id}_{user_id}"),
            ("Бан навсегда", f"admin_ban_perm_{partner_id}_{user_id}"),
            ("-50 рейтинг", f"admin_rating_{partner_id}_-50_{user_id}"), ("+20 рейтинг", f"admin_rating_{partner_id}_20_{user_id}"),
            ("Амнистия", f"admin_amnesty_{partner_id}_{user_id}"), ("Отклонить", f"admin_dismiss_{user_id}_{partner_id}")
        ])
        
        # Отправляем всем админам
        admins = await User.filter(is_admin=True).all()
        print(f"Found {len(admins)} admins")
        
        for admin in admins:
            try:
                print(f"Sending report to admin {admin.tg_id}")
                await callback.bot.send_message(admin.tg_id, report_text, reply_markup=admin_kb)
                print(f"Report sent to admin {admin.tg_id}")
            except Exception as e:
                print(f"Failed to send to admin {admin.tg_id}: {e}")
        
        # Применяем действие на основе AI-анализа
        from middlewares.notifications import notification_service
        
        response_text = "Жалоба отправлена админам."
        
        if validity['action'] == 'penalize':
            # Сильное наказание
            penalty = int(20 * validity['confidence'])
            old_rating = reported_user.raiting
            new_rating = max(0, reported_user.raiting - penalty)
            await User.filter(id=reported_user.id).update(raiting=new_rating)
            
            # Уведомляем пользователя о наказании
            await notification_service.notify_rating_change(
                partner_id, old_rating, new_rating, 
                f"Нарушение: {validity['reason']}"
            )
            response_text += f" Рейтинг снижен на {penalty}."
            
        elif validity['action'] == 'warning':
            # Легкое наказание
            penalty = 5
            old_rating = reported_user.raiting
            new_rating = max(0, reported_user.raiting - penalty)
            await User.filter(id=reported_user.id).update(raiting=new_rating)
            
            # Уведомляем о предупреждении
            await notification_service.notify_violation_warning(
                partner_id, "Нарушение правил", validity['reason']
            )
            await notification_service.notify_rating_change(
                partner_id, old_rating, new_rating, "Предупреждение"
            )
            response_text += f" Предупреждение (-{penalty} рейтинга)."
            
        elif validity['action'] == 'penalize_reporter':
            # Наказываем жалобщика за ложную жалобу
            penalty = 15
            old_rating = reporter_user.raiting
            new_rating = max(0, reporter_user.raiting - penalty)
            await User.filter(id=reporter_user.id).update(raiting=new_rating)
            
            # Уведомляем жалобщика
            await notification_service.notify_rating_change(
                user_id, old_rating, new_rating, "Ложная жалоба"
            )
            response_text = f"Ложная жалоба! Ваш рейтинг снижен на {penalty}."
            
        else:  # ignore
            response_text += " Нарушений не обнаружено."
            # Уведомляем жалобщика о результате
            await notification_service.notify_complaint_processed(
                user_id, "Жалоба рассмотрена. Нарушений не обнаружено."
            )
        
        await callback.answer(response_text)
        
    except Exception as e:
        print(f"Error in report_user: {e}")
        await callback.answer("Ошибка обработки жалобы")   
    except Exception as e:
        print(f"Error in report_user: {e}")
        await callback.answer("Ошибка обработки жалобы")

# Обработчик сообщений во время поиска - простые ответы без AI
@router.message(ChatStates.searching)
async def handle_search_message(message: types.Message, state: FSMContext):
    """Обработка сообщений во время поиска - простые ответы"""
    # Проверяем, не найден ли уже партнер
    if message.from_user.id in active_chats:
        await state.set_state(ChatStates.chatting)
        return
    
    # Проверяем, что пользователь все еще в очереди поиска
    user_in_queue = any(message.from_user.id in queue for queue in search_queue.values())
    if not user_in_queue:
        await state.clear()
        return
    
    # Простые ответы на популярные вопросы
    text_lower = message.text.lower() if message.text else ""
    
    if any(word in text_lower for word in ['сколько', 'долго', 'время']):
        response = "⏱️ Поиск до 10 минут. ИИ анализирует совместимость по многим параметрам для идеального подбора!"
    elif any(word in text_lower for word in ['как', 'работает', 'алгоритм', 'ии']):
        response = "🤖 ИИ анализирует: возраст, город, цели, интересы, личность по описанию. Система учится на ваших успешных чатах!"
    elif any(word in text_lower for word in ['отменить', 'стоп', 'хватит']):
        response = "❌ Для отмены поиска нажмите кнопку 'Отменить поиск' ниже."
    elif any(word in text_lower for word in ['привет', 'здравствуй', 'добро']):
        response = "👋 Привет! Ищем для вас подходящего собеседника..."
    else:
        responses = [
            "🤖 ИИ анализирует совместимость кандидатов...",
            "✨ Подбираем наиболее подходящую личность...",
            "🎯 Анализируем интересы и совместимость...",
            "💫 ИИ найдет вам идеального собеседника!"
        ]
        import random
        response = random.choice(responses)
    
    kb = create_keyboard([("Отменить поиск", "cancel_search")])
    await message.answer(response, reply_markup=kb)

# Универсальный обработчик для всех сообщений в активных чатах
@router.message(lambda message: message.from_user.id in active_chats)
async def handle_chat_message(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    partner_id = active_chats.get(user_id)
    
    print(f"Chat message from {user_id}, partner: {partner_id}, active_chats: {active_chats}")
    
    if not partner_id:
        await message.answer("Чат не активен.")
        await state.clear()
        return
    
    # Принудительно логируем сообщение
    from bot import chat_logger
    if message.text:
        chat_logger.chat_logs.setdefault(chat_logger._get_chat_key(user_id, partner_id), []).append({
            'user_id': user_id,
            'message': message.text,
            'timestamp': time.time(),
            'type': 'text'
        })
        print(f"Force logged message from {user_id}: {message.text[:30]}...")
    
    # Добавляем ID партнера в контекст для middleware через data
    # Не можем изменять замороженный объект Message - используем только data
    
    # Проверяем возможность деанона и 18+ чата (пока отключено)
    # conversation_stats = data.get('conversation_stats', {})
    conversation_stats = {}
    
    if conversation_stats.get('can_deanon'):
        kb = create_keyboard([
            ("Предложить деанон", "offer_deanon"),
            ("Завершить чат", "end_chat")
        ])
        await message.bot.send_message(user_id, "💡 Вы можете предложить взаимный деанон!", reply_markup=kb)
    
    if conversation_stats.get('can_adult_chat'):
        kb = create_keyboard([
            ("Перейти в 18+ режим", "adult_mode"),
            ("Завершить чат", "end_chat")
        ])
        await message.bot.send_message(user_id, "🔞 Доступен 18+ режим общения!", reply_markup=kb)
    
    # Пересылаем сообщение партнеру
    try:
        if message.text:
            await message.bot.send_message(partner_id, message.text)
        elif message.photo:
            await message.bot.send_photo(partner_id, message.photo[-1].file_id, caption=message.caption or "📷 Фото")
        elif message.video:
            await message.bot.send_video(partner_id, message.video.file_id, caption=message.caption or "🎥 Видео")
        elif message.voice:
            await message.bot.send_voice(partner_id, message.voice.file_id)
        elif message.video_note:
            await message.bot.send_video_note(partner_id, message.video_note.file_id)
        elif message.audio:
            await message.bot.send_audio(partner_id, message.audio.file_id, caption=message.caption or "🎵 Аудио")
        elif message.document:
            await message.bot.send_document(partner_id, message.document.file_id, caption=message.caption or "📄 Документ")
        elif message.sticker:
            await message.bot.send_sticker(partner_id, message.sticker.file_id)
        elif message.animation:
            await message.bot.send_animation(partner_id, message.animation.file_id, caption=message.caption or "🎬 GIF")
        elif message.location:
            await message.bot.send_location(partner_id, message.location.latitude, message.location.longitude)
        elif message.contact:
            await message.bot.send_contact(partner_id, message.contact.phone_number, message.contact.first_name, message.contact.last_name)
        else:
            await message.answer("Этот тип сообщения не поддерживается")
    except Exception as e:
        print(f"Error sending message: {e}")
        await message.answer("Ошибка отправки сообщения.")

@router.callback_query(F.data == "offer_deanon")
async def offer_deanon(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    partner_id = active_chats.get(user_id)
    
    if partner_id:
        kb = create_keyboard([
            ("Согласиться", f"accept_deanon_{user_id}"),
            ("Отказаться", "decline_deanon")
        ])
        
        await callback.bot.send_message(
            partner_id, 
            "Предложение взаимного деанона. Вы узнаете имена и сможете обмениваться контактами.",
            reply_markup=kb
        )
        await callback.answer("Предложение отправлено!")

@router.callback_query(F.data.startswith("accept_deanon_"))
async def accept_deanon(callback: types.CallbackQuery):
    requester_id = int(callback.data.split("_")[2])
    accepter_id = callback.from_user.id
    
    # Получаем профили пользователей
    requester = await User.filter(tg_id=requester_id).first()
    accepter = await User.filter(tg_id=accepter_id).first()
    
    if requester and accepter:
        # Отправляем информацию друг другу
        await callback.bot.send_message(
            requester_id,
            f"🎉 Деанон принят!\n👤 Имя: {accepter.first_name}\n🆔 ID: @{accepter.username or 'скрыт'}"
        )
        await callback.bot.send_message(
            accepter_id,
            f"🎉 Деанон состоялся!\n👤 Имя: {requester.first_name}\n🆔 ID: @{requester.username or 'скрыт'}"
        )
        
    await callback.answer("Деанон принят!")

@router.callback_query(F.data == "decline_deanon")
async def decline_deanon(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    partner_id = active_chats.get(user_id)
    
    if partner_id:
        await callback.bot.send_message(partner_id, "❌ Предложение деанона отклонено")
    
    await callback.answer("Предложение отклонено")

@router.callback_query(F.data == "adult_mode")
async def adult_mode(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    partner_id = active_chats.get(user_id)
    
    if partner_id:
        kb = create_keyboard([
            ("Согласиться на 18+", f"accept_adult_{user_id}"),
            ("Отказаться", "decline_adult")
        ])
        
        await callback.bot.send_message(
            partner_id,
            "🔞 Предложение перейти в режим 18+ общения",
            reply_markup=kb
        )
        await callback.answer("Предложение отправлено!")

@router.callback_query(F.data.startswith("accept_adult_"))
async def accept_adult(callback: types.CallbackQuery):
    requester_id = int(callback.data.split("_")[2])
    accepter_id = callback.from_user.id
    
    # Уведомляем обоих пользователей
    await callback.bot.send_message(requester_id, "🔞 Режим 18+ активирован")
    await callback.bot.send_message(accepter_id, "🔞 Режим 18+ активирован")
    
    await callback.answer("Режим 18+ активирован!")

@router.callback_query(F.data == "decline_adult")
async def decline_adult(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    partner_id = active_chats.get(user_id)
    
    if partner_id:
        await callback.bot.send_message(partner_id, "❌ Предложение 18+ отклонено")
    
    await callback.answer("Предложение отклонено")

