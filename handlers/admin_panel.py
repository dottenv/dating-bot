from aiogram import types, Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from database.models import User, Profile, Ban
from keyboards.profile import create_keyboard
from services.ai_moderation import ai_moderator
from services.cache import profile_cache
from utils.admin_helpers import safe_edit_message
import time

router = Router()

@router.message(Command("admin"))
async def admin_panel(message: types.Message):
    user = await User.filter(tg_id=message.from_user.id).first()
    if not user or not user.is_admin:
        await message.answer("**Доступ запрещен**")
        return
    
    kb = create_keyboard([
        ("📊 Статистика", "admin_stats"),
        ("👥 Пользователи", "admin_users"),
        ("🚫 Модерация", "admin_moderation"),
        ("📢 Рассылка", "admin_broadcast"),
        ("🔧 Updates", "admin_updates"),
        ("⚙️ Настройки", "admin_settings")
    ])
    
    await message.answer("**Панель администратора**", reply_markup=kb, parse_mode="Markdown")

@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: types.CallbackQuery):
    user = await User.filter(tg_id=callback.from_user.id).first()
    if not user or not user.is_admin:
        await callback.answer("Доступ запрещен")
        return
    from handlers.chat import active_chats, search_queue
    
    total_users = await User.all().count()
    active_users = await User.filter(is_active=True).count()
    premium_users = await User.filter(is_premium=True).count()
    banned_users = await Ban.filter(is_active=True).count()
    
    in_chat = len(active_chats) // 2
    in_queue = sum(len(queue) for queue in search_queue.values())
    
    stats_text = f"""**📊 Статистика системы**

**Пользователи:**
• Всего: `{total_users}`
• Активных: `{active_users}`
• Premium: `{premium_users}`
• Заблокированных: `{banned_users}`

**Активность:**
• В чате: `{in_chat}`
• В поиске: `{in_queue}`
• Онлайн: `{active_users}`

**Система:**
• Кэш профилей: `{len(profile_cache.cache)}`
• Нарушения: `{len(ai_moderator.violation_history)}`"""
    
    kb = create_keyboard([("🔄 Обновить", "admin_stats"), ("◀️ Назад", "admin_back")])
    try:
        await callback.message.edit_text(stats_text, reply_markup=kb, parse_mode="Markdown")
    except:
        pass

@router.callback_query(F.data == "admin_users")
async def admin_users(callback: types.CallbackQuery):
    user = await User.filter(tg_id=callback.from_user.id).first()
    if not user or not user.is_admin:
        await callback.answer("Доступ запрещен")
        return
    kb = create_keyboard([
        ("📋 Список пользователей", "users_list_0"),
        ("📋 Топ по рейтингу", "admin_top_rating"),
        ("⚠️ Проблемные", "admin_problem_users"),
        ("🚫 Заблокированные", "admin_banned_users"),
        ("◀️ Назад", "admin_back")
    ])
    
    try:
        await callback.message.edit_text("**👥 Управление пользователями**", reply_markup=kb, parse_mode="Markdown")
    except:
        pass

@router.callback_query(F.data == "admin_user_search")
async def admin_user_search(callback: types.CallbackQuery):
    try:
        await callback.message.edit_text(
            "**🔍 Поиск пользователя**\n\n"
            "Команды:\n"
            "`/find_user <ID>` - по ID\n"
            "`/user_info <ID>` - полная инфо\n"
            "`/ban_user <ID> [1h|1d|perm]` - забанить\n"
            "`/set_rating <ID> <рейтинг>` - изменить рейтинг\n"
            "`/make_premium <ID>` - дать Premium",
            parse_mode="Markdown"
        )
    except:
        pass

@router.callback_query(F.data == "admin_problem_users")
async def admin_problem_users(callback: types.CallbackQuery):
    problem_users = await User.filter(raiting__lt=50, is_active=True).order_by('raiting').limit(10)
    
    text = "**⚠️ Проблемные пользователи:**\n\n"
    
    for user in problem_users:
        profile = await Profile.filter(user=user).first()
        name = profile.first_name if profile else "Неизвестно"
        text += f"`{user.tg_id}` {name} - {user.raiting} баллов\n"
    
    if not problem_users:
        text += "Проблемных пользователей нет"
    
    kb = create_keyboard([("◀️ Назад", "admin_users")])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")

@router.callback_query(F.data == "admin_banned_users")
async def admin_banned_users(callback: types.CallbackQuery):
    banned = await Ban.filter(is_active=True).limit(10).prefetch_related('user')
    
    text = "**🚫 Заблокированные пользователи:**\n\n"
    
    for ban in banned:
        text += f"`{ban.user.tg_id}` - {ban.ban_type}\n"
        if ban.expires_at:
            text += f"До: {ban.expires_at.strftime('%d.%m %H:%M')}\n"
        text += f"Причина: {ban.reason}\n\n"
    
    if not banned:
        text += "Заблокированных пользователей нет"
    
    kb = create_keyboard([("◀️ Назад", "admin_users")])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")

@router.callback_query(F.data == "admin_settings")
async def admin_settings(callback: types.CallbackQuery):
    kb = create_keyboard([
        ("📊 Лимиты системы", "admin_limits"),
        ("🤖 Настройки ИИ", "admin_ai_settings"),
        ("📝 Логи", "admin_logs"),
        ("👑 Управление правами", "admin_permissions"),
        ("🗑️ Очистка", "admin_cleanup"),
        ("◀️ Назад", "admin_back")
    ])
    
    await callback.message.edit_text("**⚙️ Настройки системы**", reply_markup=kb, parse_mode="Markdown")

@router.callback_query(F.data == "admin_limits")
async def admin_limits(callback: types.CallbackQuery):
    from handlers.chat import active_chats, search_queue
    
    max_users_in_chat = 1000
    max_queue_size = 500
    current_chats = len(active_chats) // 2
    current_queue = sum(len(queue) for queue in search_queue.values())
    
    text = f"**📊 Лимиты системы**\n\n"
    text += f"**Текущая нагрузка:**\n"
    text += f"• Активных чатов: `{current_chats}/{max_users_in_chat}`\n"
    text += f"• В очереди поиска: `{current_queue}/{max_queue_size}`\n\n"
    
    text += f"**Лимиты:**\n"
    text += f"• Макс. одновременных чатов: `{max_users_in_chat}`\n"
    text += f"• Макс. размер очереди: `{max_queue_size}`\n"
    text += f"• Поиск партнера: `60 сек`\n"
    text += f"• Антифлуд: `3 сек`\n\n"
    
    if current_chats > max_users_in_chat * 0.8:
        status = "🔴 Высокая нагрузка"
    elif current_chats > max_users_in_chat * 0.5:
        status = "🟡 Средняя нагрузка"
    else:
        status = "🟢 Нормальная нагрузка"
    
    text += f"**Статус:** {status}"
    
    kb = create_keyboard([
        ("🔄 Обновить", "admin_limits"),
        ("◀️ Назад", "admin_settings")
    ])
    
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")

@router.callback_query(F.data == "admin_ai_settings")
async def admin_ai_settings(callback: types.CallbackQuery):
    text = f"**🤖 Настройки ИИ**\n\n"
    text += f"**Модерация контента:**\n"
    text += f"• Токсичность: `Включена`\n"
    text += f"• Попытки деанона: `Включена`\n"
    text += f"• Спам: `Включена`\n"
    text += f"• 18+ контент: `Включена`\n\n"
    
    text += f"**Подбор собеседников:**\n"
    text += f"• Совместимость по городу: `+100 баллов`\n"
    text += f"• Совместимость по цели: `+50 баллов`\n"
    text += f"• Близкий возраст: `+10-30 баллов`\n"
    text += f"• Общие интересы: `+5-20 баллов`\n\n"
    
    text += f"**Провайдеры ИИ:**\n"
    text += f"• You.com: `Активен`\n"
    text += f"• Bing: `Резерв`\n"
    text += f"• ChatgptAi: `Резерв`"
    
    kb = create_keyboard([
        ("⚙️ Настройки модерации", "admin_mod_settings"),
        ("◀️ Назад", "admin_settings")
    ])
    
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")

@router.callback_query(F.data == "admin_logs")
async def admin_logs(callback: types.CallbackQuery):
    import os
    
    log_file = "bot.log"
    if os.path.exists(log_file):
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()[-20:]
        
        text = f"**📝 Системные логи**\n\n**Последние записи:**\n"
        
        for line in lines:
            if line.strip():
                short_line = line.strip()[:80] + "..." if len(line.strip()) > 80 else line.strip()
                text += f"`{short_line}`\n"
    else:
        text = "**📝 Системные логи**\n\nФайл логов не найден"
    
    kb = create_keyboard([
        ("🔄 Обновить", "admin_logs"),
        ("🗑️ Очистить логи", "admin_clear_logs"),
        ("◀️ Назад", "admin_settings")
    ])
    
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")

@router.callback_query(F.data == "admin_permissions")
async def admin_permissions(callback: types.CallbackQuery):
    admins = await User.filter(is_admin=True).all()
    premium_users = await User.filter(is_premium=True).count()
    
    text = f"**👑 Управление правами**\n\n"
    text += f"**Администраторы ({len(admins)}):**\n"
    
    for admin in admins:
        profile = await Profile.filter(user=admin).first()
        name = profile.first_name if profile else "Неизвестно"
        text += f"• `{admin.tg_id}` {name}\n"
    
    text += f"\n**Premium пользователей:** `{premium_users}`\n\n"
    text += f"**Команды:**\n"
    text += f"`/make_admin <ID>` - дать права админа\n"
    text += f"`/remove_admin <ID>` - убрать права админа\n"
    text += f"`/make_premium <ID>` - дать Premium\n"
    text += f"`/remove_premium <ID>` - убрать Premium"
    
    kb = create_keyboard([
        ("🔄 Обновить", "admin_permissions"),
        ("◀️ Назад", "admin_settings")
    ])
    
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")

@router.callback_query(F.data == "admin_clear_logs")
async def admin_clear_logs(callback: types.CallbackQuery):
    import os
    
    log_file = "bot.log"
    if os.path.exists(log_file):
        open(log_file, 'w').close()
        await callback.answer("Логи очищены")
    else:
        await callback.answer("Файл логов не найден")
    
    await admin_logs(callback)

@router.callback_query(F.data == "admin_mod_settings")
async def admin_mod_settings(callback: types.CallbackQuery):
    from services.ai_moderation import ai_moderator
    
    text = f"**⚙️ Настройки модерации**\n\n"
    text += f"Пороги автобанов:\n"
    for violation_type, threshold in ai_moderator.auto_ban_thresholds.items():
        text += f"• {violation_type}: `{threshold}` нарушений\n"
    
    text += f"\nВсего нарушителей: `{len(ai_moderator.violation_history)}`"
    
    kb = create_keyboard([
        ("🗑️ Очистить историю", "admin_clear_violations"),
        ("◀️ Назад", "admin_moderation")
    ])
    
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")

@router.callback_query(F.data == "admin_clear_violations")
async def admin_clear_violations(callback: types.CallbackQuery):
    from services.ai_moderation import ai_moderator
    
    count = len(ai_moderator.violation_history)
    ai_moderator.violation_history.clear()
    
    await callback.answer(f"Очищено {count} записей")
    await admin_mod_settings(callback)

@router.callback_query(F.data == "admin_cleanup")
async def admin_cleanup(callback: types.CallbackQuery):
    from services.cache import profile_cache
    
    # Очистка кэша
    cache_count = len(profile_cache.cache)
    profile_cache.cache.clear()
    profile_cache.timestamps.clear()
    
    # Очистка неактивных банов
    from datetime import datetime
    expired_bans = await Ban.filter(expires_at__lt=datetime.now(), is_active=True).update(is_active=False)
    
    text = f"**🗑️ Очистка выполнена**\n\n"
    text += f"Очищен кэш: `{cache_count}` записей\n"
    text += f"Деактивировано банов: `{expired_bans}`"
    
    kb = create_keyboard([("◀️ Назад", "admin_settings")])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")

@router.callback_query(F.data == "admin_moderation")
async def admin_moderation(callback: types.CallbackQuery):
    user = await User.filter(tg_id=callback.from_user.id).first()
    if not user or not user.is_admin:
        await callback.answer("Доступ запрещен")
        return
    # Последние нарушения
    recent_violations = []
    for user_id, violations in ai_moderator.violation_history.items():
        for violation in violations[-3:]:  # Последние 3
            recent_violations.append((user_id, violation))
    
    recent_violations.sort(key=lambda x: x[1]['timestamp'], reverse=True)
    
    text = "**🚫 Модерация**\n\n**Последние нарушения:**\n"
    
    for user_id, violation in recent_violations[:10]:
        user_profile = await profile_cache.get_profile(user_id)
        name = user_profile['first_name'] if user_profile else f"ID{user_id}"
        violation_time = time.strftime("%H:%M", time.localtime(violation['timestamp']))
        text += f"• `{violation_time}` {name}: {violation['type']} - {violation['reason']}\n"
    
    kb = create_keyboard([
        ("🔄 Обновить", "admin_moderation"),
        ("⚙️ Настройки модерации", "admin_mod_settings"),
        ("◀️ Назад", "admin_back")
    ])
    
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")

@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast(callback: types.CallbackQuery):
    user = await User.filter(tg_id=callback.from_user.id).first()
    if not user or not user.is_admin:
        await callback.answer("Доступ запрещен")
        return
    kb = create_keyboard([
        ("📢 Всем пользователям", "broadcast_all"),
        ("⭐ Только Premium", "broadcast_premium"),
        ("🎯 По городам", "broadcast_cities"),
        ("📺 Реклама", "broadcast_ads"),
        ("◀️ Назад", "admin_back")
    ])
    
    await callback.message.edit_text("**📢 Рассылка сообщений**", reply_markup=kb, parse_mode="Markdown")

@router.callback_query(F.data == "admin_back")
async def admin_back(callback: types.CallbackQuery):
    user = await User.filter(tg_id=callback.from_user.id).first()
    if not user or not user.is_admin:
        await callback.answer("Доступ запрещен")
        return
    
    kb = create_keyboard([
        ("📊 Статистика", "admin_stats"),
        ("👥 Пользователи", "admin_users"),
        ("🚫 Модерация", "admin_moderation"),
        ("📢 Рассылка", "admin_broadcast"),
        ("🔧 Updates", "admin_updates"),
        ("⚙️ Настройки", "admin_settings")
    ])
    
    await callback.message.edit_text("**Панель администратора**", reply_markup=kb, parse_mode="Markdown")

# Команды поиска и управления
@router.message(Command("find_user"))
async def find_user_by_id(message: types.Message):
    user = await User.filter(tg_id=message.from_user.id).first()
    if not user or not user.is_admin:
        return
    
    try:
        user_id = int(message.text.split()[1])
        target_user = await User.filter(tg_id=user_id).first()
        
        if not target_user:
            await message.answer("**Пользователь не найден**", parse_mode="Markdown")
            return
        
        profile = await Profile.filter(user=target_user).first()
        name = profile.first_name if profile else "Неизвестно"
        
        text = f"**👤 Пользователь {name}**\n\n"
        text += f"ID: `{target_user.tg_id}`\n"
        text += f"Рейтинг: `{target_user.raiting}`\n"
        text += f"Статус: {'Premium' if target_user.is_premium else 'Обычный'}\n"
        text += f"Активен: {'✅' if target_user.is_active else '❌'}\n"
        
        if profile:
            text += f"Возраст: `{profile.age}`\n"
            text += f"Город: `{profile.city or 'Не указан'}`\n"
        
        await message.answer(text, parse_mode="Markdown")
        
    except (IndexError, ValueError):
        await message.answer("**Использование:** `/find_user <ID>`", parse_mode="Markdown")

@router.message(Command("ban_user"))
async def ban_user_command(message: types.Message):
    user = await User.filter(tg_id=message.from_user.id).first()
    if not user or not user.is_admin:
        return
    
    try:
        parts = message.text.split()
        user_id = int(parts[1])
        duration = parts[2] if len(parts) > 2 else "1d"
        
        target_user = await User.filter(tg_id=user_id).first()
        if not target_user:
            await message.answer("**Пользователь не найден**", parse_mode="Markdown")
            return
        
        from datetime import datetime, timedelta
        from middlewares.notifications import notification_service
        
        if duration == "perm":
            expires_at = None
            ban_type = "permanent"
            hours = None
        else:
            hours = int(duration.replace("h", "").replace("d", "")) * (24 if "d" in duration else 1)
            expires_at = datetime.now() + timedelta(hours=hours)
            ban_type = "temp"
        
        await Ban.create(
            user=target_user,
            banned_by=user,
            ban_type=ban_type,
            duration_hours=hours,
            reason=f"Ручной бан от админа",
            expires_at=expires_at
        )
        
        # Уведомляем пользователя о бане
        await notification_service.notify_ban(user_id, ban_type, "Ручной бан от админа", expires_at)
        
        await message.answer(f"**Пользователь {user_id} заблокирован**", parse_mode="Markdown")
        
    except (IndexError, ValueError):
        await message.answer("**Использование:** `/ban_user <ID> [1h|1d|perm]`", parse_mode="Markdown")

@router.message(Command("set_rating"))
async def set_rating_command(message: types.Message):
    user = await User.filter(tg_id=message.from_user.id).first()
    if not user or not user.is_admin:
        return
    
    try:
        parts = message.text.split()
        user_id = int(parts[1])
        new_rating = int(parts[2])
        
        target_user = await User.filter(tg_id=user_id).first()
        if not target_user:
            await message.answer("**Пользователь не найден**", parse_mode="Markdown")
            return
        
        old_rating = target_user.raiting
        await User.filter(id=target_user.id).update(raiting=max(0, min(1000, new_rating)))
        
        from services.cache import profile_cache
        from middlewares.notifications import notification_service
        
        profile_cache.invalidate(user_id)
        
        # Уведомляем пользователя об изменении рейтинга
        await notification_service.notify_rating_change(user_id, old_rating, new_rating, "Изменение администратором")
        
        await message.answer(
            f"**Рейтинг изменен**\n\n"
            f"Пользователь: `{user_id}`\n"
            f"Было: `{old_rating}`\n"
            f"Стало: `{new_rating}`",
            parse_mode="Markdown"
        )
        
    except (IndexError, ValueError):
        await message.answer("**Использование:** `/set_rating <ID> <рейтинг>`", parse_mode="Markdown")

@router.message(Command("make_premium"))
async def make_premium_command(message: types.Message):
    user = await User.filter(tg_id=message.from_user.id).first()
    if not user or not user.is_admin:
        return
    
    try:
        user_id = int(message.text.split()[1])
        target_user = await User.filter(tg_id=user_id).first()
        
        if not target_user:
            await message.answer("**Пользователь не найден**", parse_mode="Markdown")
            return
        
        await User.filter(id=target_user.id).update(is_premium=True)
        
        from services.cache import profile_cache
        from middlewares.notifications import notification_service
        
        profile_cache.invalidate(user_id)
        
        await message.answer(f"**Пользователь {user_id} получил Premium**", parse_mode="Markdown")
        
        # Уведомляем пользователя о получении Premium
        await notification_service.notify_premium_granted(user_id)
            
    except (IndexError, ValueError):
        await message.answer("**Использование:** `/make_premium <ID>`", parse_mode="Markdown")



@router.message(Command("make_admin"))
async def make_admin_command(message: types.Message):
    user = await User.filter(tg_id=message.from_user.id).first()
    if not user or not user.is_admin:
        return
    
    try:
        user_id = int(message.text.split()[1])
        target_user = await User.filter(tg_id=user_id).first()
        
        if not target_user:
            await message.answer("**Пользователь не найден**", parse_mode="Markdown")
            return
        
        if target_user.is_admin:
            await message.answer("**Пользователь уже админ**", parse_mode="Markdown")
            return
        
        await User.filter(id=target_user.id).update(is_admin=True)
        
        await message.answer(f"**Пользователь {user_id} получил права админа**", parse_mode="Markdown")
        
        from middlewares.notifications import notification_service
        
        # Уведомляем пользователя о получении прав админа
        await notification_service.notify_admin_granted(user_id)
            
    except (IndexError, ValueError):
        await message.answer("**Использование:** `/make_admin <ID>`", parse_mode="Markdown")

@router.message(Command("remove_admin"))
async def remove_admin_command(message: types.Message):
    user = await User.filter(tg_id=message.from_user.id).first()
    if not user or not user.is_admin:
        return
    
    try:
        user_id = int(message.text.split()[1])
        target_user = await User.filter(tg_id=user_id).first()
        
        if not target_user:
            await message.answer("**Пользователь не найден**", parse_mode="Markdown")
            return
        
        if user_id == message.from_user.id:
            await message.answer("**Нельзя убрать права у самого себя**", parse_mode="Markdown")
            return
        
        await User.filter(id=target_user.id).update(is_admin=False)
        
        from middlewares.notifications import notification_service
        
        # Уведомляем пользователя об удалении прав админа
        await notification_service.notify_admin_removed(user_id)
        
        await message.answer(f"**Права админа убраны у {user_id}**", parse_mode="Markdown")
        
    except (IndexError, ValueError):
        await message.answer("**Использование:** `/remove_admin <ID>`", parse_mode="Markdown")

@router.message(Command("remove_premium"))
async def remove_premium_command(message: types.Message):
    user = await User.filter(tg_id=message.from_user.id).first()
    if not user or not user.is_admin:
        return
    
    try:
        user_id = int(message.text.split()[1])
        target_user = await User.filter(tg_id=user_id).first()
        
        if not target_user:
            await message.answer("**Пользователь не найден**", parse_mode="Markdown")
            return
        
        await User.filter(id=target_user.id).update(is_premium=False)
        
        from services.cache import profile_cache
        from middlewares.notifications import notification_service
        
        profile_cache.invalidate(user_id)
        
        # Уведомляем пользователя об удалении Premium
        await notification_service.notify_premium_removed(user_id)
        
        await message.answer(f"**Premium статус убран у {user_id}**", parse_mode="Markdown")
        
    except (IndexError, ValueError):
        await message.answer("**Использование:** `/remove_premium <ID>`", parse_mode="Markdown")

# Обработчики для конкретных действий
@router.callback_query(F.data == "admin_top_rating")
async def admin_top_rating(callback: types.CallbackQuery):
    top_users = await User.all().order_by('-raiting').limit(15)
    
    text = "**📋 Топ-15 по рейтингу:**\n\n"
    for i, user in enumerate(top_users, 1):
        profile = await Profile.filter(user=user).first()
        name = profile.first_name if profile else "Неизвестно"
        status = "⭐" if user.is_premium else ""
        text += f"`{i}.` {name} {status} - `{user.raiting}` баллов\n"
    
    kb = create_keyboard([("◀️ Назад", "admin_users")])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")

@router.callback_query(F.data == "broadcast_all")
async def broadcast_all(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "**Рассылка всем пользователям**\n\n"
        "Команды:\n"
        "`/send_all <текст>` - всем\n"
        "`/send_premium <текст>` - только Premium",
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "broadcast_premium")
async def broadcast_premium(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "**Рассылка Premium пользователям**\n\n"
        "Используйте: `/send_premium <текст>`",
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "broadcast_cities")
async def broadcast_cities(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "**Рассылка по городам**\n\n"
        "Используйте: `/send_city <город> <текст>`",
        parse_mode="Markdown"
    )

# Перенаправляем на новую систему рекламы
# broadcast_ads теперь в ad_manager.py

@router.callback_query(F.data == "create_ad")
async def create_ad(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "🆕 **Создание рекламного поста**\n\n"
        "Отправьте текст рекламы или медиа-файл с описанием.\n\n"
        "📝 Поддерживаемые форматы:\n"
        "• Текст\n"
        "• Фото + текст\n"
        "• Видео + текст",
        parse_mode="Markdown"
    )
    
    from states.ad_broadcast import AdStates
    await state.set_state(AdStates.waiting_content)

@router.callback_query(F.data == "ad_stats")
async def ad_stats(callback: types.CallbackQuery):
    total_users = await User.filter(is_active=True).count()
    premium_users = await User.filter(is_active=True, is_premium=True).count()
    
    stats_text = f"📊 **Статистика для рекламы**\n\n"
    stats_text += f"👥 Активных пользователей: `{total_users}`\n"
    stats_text += f"⭐ Premium пользователей: `{premium_users}`\n"
    stats_text += f"👤 Обычных пользователей: `{total_users - premium_users}`\n\n"
    stats_text += f"📈 Охват рекламы: до `{total_users}` человек"
    
    kb = create_keyboard([("◀️ Назад", "broadcast_ads")])
    await callback.message.edit_text(stats_text, reply_markup=kb, parse_mode="Markdown")

@router.message(Command("send_all"))
async def send_broadcast_all(message: types.Message):
    from services.broadcast import broadcast_service
    
    user = await User.filter(tg_id=message.from_user.id).first()
    if not user or not user.is_admin:
        return
    
    text = message.text.replace("/send_all", "").strip()
    if not text:
        await message.answer("**Укажите текст сообщения**", parse_mode="Markdown")
        return
    
    status_msg = await message.answer("**Рассылка запущена...**", parse_mode="Markdown")
    
    result = await broadcast_service.send_to_all(message.bot, text, exclude_ids=[message.from_user.id])
    
    await status_msg.edit_text(
        f"**Рассылка завершена**\n\n"
        f"Отправлено: `{result['sent']}`\n"
        f"Ошибок: `{result['failed']}`",
        parse_mode="Markdown"
    )

@router.message(Command("send_premium"))
async def send_broadcast_premium(message: types.Message):
    from services.broadcast import broadcast_service
    
    user = await User.filter(tg_id=message.from_user.id).first()
    if not user or not user.is_admin:
        return
    
    text = message.text.replace("/send_premium", "").strip()
    if not text:
        await message.answer("**Укажите текст сообщения**", parse_mode="Markdown")
        return
    
    status_msg = await message.answer("**Рассылка Premium пользователям...**", parse_mode="Markdown")
    
    result = await broadcast_service.send_to_premium(message.bot, text)
    
    await status_msg.edit_text(
        f"**Рассылка Premium завершена**\n\n"
        f"Отправлено: `{result['sent']}`\n"
        f"Ошибок: `{result['failed']}`",
        parse_mode="Markdown"
    )

@router.message(Command("send_city"))
async def send_broadcast_city(message: types.Message):
    from services.broadcast import broadcast_service
    
    user = await User.filter(tg_id=message.from_user.id).first()
    if not user or not user.is_admin:
        return
    
    try:
        parts = message.text.split(maxsplit=2)
        city = parts[1]
        text = parts[2]
        
        status_msg = await message.answer(f"**Рассылка в {city}...**", parse_mode="Markdown")
        
        result = await broadcast_service.send_to_city(message.bot, city, text)
        
        await status_msg.edit_text(
            f"**Рассылка в {city} завершена**\n\n"
            f"Отправлено: `{result['sent']}`\n"
            f"Ошибок: `{result['failed']}`",
            parse_mode="Markdown"
        )
        
    except (IndexError, ValueError):
        await message.answer("**Использование:** `/send_city <город> <текст>`", parse_mode="Markdown")

@router.message(Command("system_stats"))
async def system_stats_command(message: types.Message):
    user = await User.filter(tg_id=message.from_user.id).first()
    if not user or not user.is_admin:
        return
    
    from handlers.chat import active_chats, search_queue
    from services.cache import profile_cache
    from services.ai_moderation import ai_moderator
    
    total_users = await User.all().count()
    active_users = await User.filter(is_active=True).count()
    premium_users = await User.filter(is_premium=True).count()
    banned_users = await Ban.filter(is_active=True).count()
    
    in_chat = len(active_chats) // 2
    in_queue = sum(len(queue) for queue in search_queue.values())
    
    text = f"**📊 Полная статистика системы**\n\n"
    text += f"👥 **Пользователи:**\n"
    text += f"• Всего: `{total_users}`\n"
    text += f"• Активных: `{active_users}`\n"
    text += f"• Premium: `{premium_users}`\n"
    text += f"• Заблокированных: `{banned_users}`\n\n"
    
    text += f"💬 **Активность:**\n"
    text += f"• В чате: `{in_chat}`\n"
    text += f"• В поиске: `{in_queue}`\n\n"
    
    text += f"⚙️ **Система:**\n"
    text += f"• Кэш профилей: `{len(profile_cache.cache)}`\n"
    text += f"• Нарушителей: `{len(ai_moderator.violation_history)}`"
    
    await message.answer(text, parse_mode="Markdown")

@router.callback_query(F.data.startswith("users_list_"))
async def users_list(callback: types.CallbackQuery):
    page = int(callback.data.split("_")[2])
    per_page = 8
    offset = page * per_page
    
    users = await User.all().order_by('-raiting').offset(offset).limit(per_page)
    total_users = await User.all().count()
    total_pages = (total_users + per_page - 1) // per_page
    
    text = f"📋 **Список пользователей** (стр. {page + 1}/{total_pages})\n\n"
    
    buttons = []
    for user in users:
        profile = await Profile.filter(user=user).first()
        name = profile.first_name if profile else "Неизвестно"
        status = "⭐" if user.is_premium else ""
        banned = "🚫" if await Ban.filter(user=user, is_active=True).exists() else ""
        
        text += f"`{user.tg_id}` {name} {status}{banned} - {user.raiting} б.\n"
        buttons.append((f"{name[:12]}... ({user.raiting})", f"user_{user.tg_id}"))
    
    nav_buttons = []
    if page > 0:
        nav_buttons.append(("⬅️", f"users_list_{page-1}"))
    if page < total_pages - 1:
        nav_buttons.append(("➡️", f"users_list_{page+1}"))
    
    all_buttons = buttons[:]
    if nav_buttons:
        all_buttons.extend(nav_buttons)
    all_buttons.append(("◀️ Назад", "admin_users"))
    
    kb = create_keyboard(all_buttons)
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")

@router.callback_query(F.data.startswith("user_") & ~F.data.contains("_history_") & ~F.data.contains("_actions_"))
async def user_details(callback: types.CallbackQuery):
    user_id = int(callback.data.split("_")[1])
    user = await User.filter(tg_id=user_id).first()
    
    if not user:
        await callback.answer("Пользователь не найден")
        return
    
    profile = await Profile.filter(user=user).first()
    name = profile.first_name if profile else "Неизвестно"
    
    text = f"👤 **{name}** (ID: `{user.tg_id}`)\n\n"
    text += f"📈 Рейтинг: `{user.raiting}`\n"
    text += f"⭐ Статус: {'Premium' if user.is_premium else 'Обычный'}\n"
    text += f"✅ Активен: {'Да' if user.is_active else 'Нет'}\n"
    
    if profile:
        text += f"🎂 Возраст: `{profile.age or 'Не указан'}`\n"
        text += f"🏠 Город: `{profile.city or 'Не указан'}`\n"
    
    active_ban = await Ban.filter(user=user, is_active=True).first()
    if active_ban:
        text += f"\n🚫 **Заблокирован**\n"
        text += f"• Тип: {active_ban.ban_type}\n"
        if active_ban.expires_at:
            text += f"• До: {active_ban.expires_at.strftime('%d.%m.%Y %H:%M')}\n"
    
    kb = create_keyboard([
        ("📈 История", f"user_history_{user_id}"),
        ("⚙️ Действия", f"user_actions_{user_id}"),
        ("◀️ Назад", "users_list_0")
    ])
    
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")

@router.callback_query(F.data.startswith("user_actions_"))
async def user_actions(callback: types.CallbackQuery):
    user_id = int(callback.data.split("_")[2])
    user = await User.filter(tg_id=user_id).first()
    
    active_ban = await Ban.filter(user=user, is_active=True).first()
    
    buttons = []
    if active_ban:
        buttons.append(("✅ Разбанить", f"unban_{user_id}"))
    else:
        buttons.extend([
            ("🚫 Бан 1ч", f"ban_{user_id}_1h"),
            ("🚫 Бан 1д", f"ban_{user_id}_1d"),
            ("🚫 Навсегда", f"ban_{user_id}_perm")
        ])
    
    buttons.extend([
        ("📈 +50", f"rating_{user_id}_+50"),
        ("📉 -50", f"rating_{user_id}_-50"),
        ("⭐ Premium", f"premium_{user_id}") if not user.is_premium else ("❌ Убрать Premium", f"unpremium_{user_id}"),
        ("◀️ Назад", f"user_{user_id}")
    ])
    
    kb = create_keyboard(buttons)
    await callback.message.edit_text(f"⚙️ **Действия с пользователем** `{user_id}`", reply_markup=kb, parse_mode="Markdown")

@router.callback_query(F.data.startswith("user_history_"))
async def user_history(callback: types.CallbackQuery):
    user_id = int(callback.data.split("_")[2])
    user = await User.filter(tg_id=user_id).first()
    
    text = f"📈 **История пользователя** `{user_id}`\n\n"
    
    bans = await Ban.filter(user=user).order_by('-created_at').limit(5)
    if bans:
        text += "🚫 **Баны:**\n"
        for ban in bans:
            status = "✅" if ban.is_active else "❌"
            text += f"{status} {ban.created_at.strftime('%d.%m %H:%M')} - {ban.ban_type}\n"
    
    from services.ai_moderation import ai_moderator
    violations = ai_moderator.violation_history.get(user_id, [])
    if violations:
        text += f"\n⚠️ **Нарушения ({len(violations)}):**\n"
        for violation in violations[-3:]:
            import time
            vtime = time.strftime('%d.%m %H:%M', time.localtime(violation['timestamp']))
            text += f"• {vtime} - {violation['type']}\n"
    
    if not bans and not violations:
        text += "✅ Нарушений не обнаружено"
    
    kb = create_keyboard([("◀️ Назад", f"user_{user_id}")])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")

@router.callback_query(F.data.startswith("ban_"))
async def ban_user_action(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    user_id = int(parts[1])
    duration = parts[2]
    
    user = await User.filter(tg_id=user_id).first()
    admin = await User.filter(tg_id=callback.from_user.id).first()
    
    from datetime import datetime, timedelta
    from middlewares.notifications import notification_service
    
    if duration == "perm":
        expires_at = None
        ban_type = "permanent"
        hours = None
    else:
        hours = int(duration.replace("h", "").replace("d", "")) * (24 if "d" in duration else 1)
        expires_at = datetime.now() + timedelta(hours=hours)
        ban_type = "temp"
    
    await Ban.create(
        user=user,
        banned_by=admin,
        ban_type=ban_type,
        duration_hours=hours,
        reason="Бан через админку",
        expires_at=expires_at
    )
    
    # Уведомляем пользователя о бане
    await notification_service.notify_ban(user_id, ban_type, "Бан через админку", expires_at)
    
    await callback.answer(f"Пользователь {user_id} заблокирован")
    await user_details(callback)

@router.callback_query(F.data.startswith("unban_"))
async def unban_user_action(callback: types.CallbackQuery):
    user_id = int(callback.data.split("_")[1])
    user = await User.filter(tg_id=user_id).first()
    
    from middlewares.notifications import notification_service
    
    await Ban.filter(user=user, is_active=True).update(is_active=False)
    
    # Уведомляем пользователя о разбане
    await notification_service.notify_unban(user_id)
    
    await callback.answer(f"Пользователь {user_id} разбанен")
    await user_details(callback)

@router.callback_query(F.data.startswith("rating_"))
async def rating_action(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    user_id = int(parts[1])
    change = int(parts[2])
    
    user = await User.filter(tg_id=user_id).first()
    old_rating = user.raiting
    new_rating = max(0, min(1000, user.raiting + change))
    await User.filter(id=user.id).update(raiting=new_rating)
    
    from services.cache import profile_cache
    from middlewares.notifications import notification_service
    
    profile_cache.invalidate(user_id)
    
    # Уведомляем пользователя об изменении рейтинга
    await notification_service.notify_rating_change(user_id, old_rating, new_rating, "Изменение администратором")
    
    await callback.answer(f"Рейтинг изменен на {change:+d}")
    await user_details(callback)

@router.callback_query(F.data.startswith("premium_"))
async def premium_action(callback: types.CallbackQuery):
    user_id = int(callback.data.split("_")[1])
    await User.filter(tg_id=user_id).update(is_premium=True)
    
    from services.cache import profile_cache
    from middlewares.notifications import notification_service
    
    profile_cache.invalidate(user_id)
    
    # Уведомляем пользователя о получении Premium
    await notification_service.notify_premium_granted(user_id)
    
    await callback.answer(f"Пользователь {user_id} получил Premium")
    await user_details(callback)

@router.callback_query(F.data.startswith("unpremium_"))
async def unpremium_action(callback: types.CallbackQuery):
    user_id = int(callback.data.split("_")[1])
    await User.filter(tg_id=user_id).update(is_premium=False)
    
    from services.cache import profile_cache
    from middlewares.notifications import notification_service
    
    profile_cache.invalidate(user_id)
    
    # Уведомляем пользователя об удалении Premium
    await notification_service.notify_premium_removed(user_id)
    
    await callback.answer(f"Premium статус убран у {user_id}")
    await user_details(callback)

# Обработчики для кнопок админов в жалобах
@router.callback_query(F.data.startswith("admin_ban_"))
async def admin_ban_from_report(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    duration = parts[2]
    reported_id = int(parts[3])
    reporter_id = int(parts[4])
    
    from datetime import datetime, timedelta
    from middlewares.notifications import notification_service
    
    reported_user = await User.filter(tg_id=reported_id).first()
    admin = await User.filter(tg_id=callback.from_user.id).first()
    
    if duration == "perm":
        expires_at = None
        ban_type = "permanent"
        hours = None
    else:
        hours = int(duration.replace("h", "").replace("d", "")) * (24 if "d" in duration else 1)
        expires_at = datetime.now() + timedelta(hours=hours)
        ban_type = "temp"
    
    await Ban.create(
        user=reported_user,
        banned_by=admin,
        ban_type=ban_type,
        duration_hours=hours,
        reason="Бан по жалобе",
        expires_at=expires_at
    )
    
    # Уведомляем пользователя о бане
    await notification_service.notify_ban(reported_id, ban_type, "Бан по жалобе", expires_at)
    
    # Уведомляем жалобщика
    await notification_service.notify_complaint_processed(
        reporter_id, f"Жалоба удовлетворена. Пользователь заблокирован."
    )
    
    await callback.message.edit_text(
        callback.message.text + f"\n\n✅ **Обработано:** Бан {duration}",
        parse_mode="Markdown"
    )

@router.callback_query(F.data.startswith("admin_rating_"))
async def admin_rating_from_report(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    reported_id = int(parts[2])
    change = int(parts[3])
    reporter_id = int(parts[4])
    
    from middlewares.notifications import notification_service
    
    reported_user = await User.filter(tg_id=reported_id).first()
    old_rating = reported_user.raiting
    new_rating = max(0, min(1000, reported_user.raiting + change))
    await User.filter(id=reported_user.id).update(raiting=new_rating)
    
    # Уведомляем пользователя
    await notification_service.notify_rating_change(
        reported_id, old_rating, new_rating, "Изменение по жалобе"
    )
    
    # Уведомляем жалобщика
    await notification_service.notify_complaint_processed(
        reporter_id, f"Жалоба удовлетворена. Рейтинг изменен на {change:+d}."
    )
    
    await callback.message.edit_text(
        callback.message.text + f"\n\n✅ **Обработано:** Рейтинг {change:+d}",
        parse_mode="Markdown"
    )

@router.callback_query(F.data.startswith("admin_amnesty_"))
async def admin_amnesty_from_report(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    reported_id = int(parts[2])
    reporter_id = int(parts[3])
    
    from middlewares.notifications import notification_service
    
    # Уведомляем жалобщика
    await notification_service.notify_complaint_processed(
        reporter_id, "Жалоба рассмотрена. Пользователь помилован."
    )
    
    await callback.message.edit_text(
        callback.message.text + "\n\n✅ **Обработано:** Амнистия",
        parse_mode="Markdown"
    )

@router.callback_query(F.data.startswith("admin_dismiss_"))
async def admin_dismiss_report(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    reporter_id = int(parts[2])
    reported_id = int(parts[3])
    
    from middlewares.notifications import notification_service
    
    # Уведомляем жалобщика
    await notification_service.notify_complaint_processed(
        reporter_id, "Жалоба отклонена. Нарушений не обнаружено."
    )
    
    await callback.message.edit_text(
        callback.message.text + "\n\n❌ **Обработано:** Отклонено",
        parse_mode="Markdown"
    )