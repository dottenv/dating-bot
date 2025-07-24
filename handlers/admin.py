from aiogram import types, Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import time

from database.models import User, Profile, Ban
from datetime import datetime, timedelta
from keyboards.profile import create_keyboard

router = Router()

class AdminStates(StatesGroup):
    confirming_action = State()

# Удаляем словарь - теперь все в базе

@router.callback_query(F.data.startswith("admin_ban_"))
async def admin_ban_user(callback: types.CallbackQuery, state: FSMContext):
    if not callback.data.startswith("admin_ban_"):
        return
    
    parts = callback.data.split("_")
    duration = parts[2]  # 1h, 1d, perm
    user_id = int(parts[3])
    
    user = await User.filter(tg_id=user_id).first()
    profile = await Profile.filter(user=user).first()
    
    if duration == "1h":
        ban_text = "на 1 час"
    elif duration == "1d":
        ban_text = "на 1 день"
    elif duration == "perm":
        ban_text = "навсегда"
    
    # Запрос подтверждения
    confirm_kb = create_keyboard([
        ("✅ Подтвердить", f"confirm_ban_{user_id}_{duration}"),
        ("❌ Отмена", "cancel_action")
    ])
    
    await callback.message.edit_text(
        f"🚫 Подтвердите бан пользователя {profile.first_name} (ID: {user_id}) {ban_text}",
        reply_markup=confirm_kb
    )

@router.callback_query(F.data.startswith("admin_rating_"))
async def admin_change_rating(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    user_id = int(parts[2])
    change = int(parts[3])
    
    user = await User.filter(tg_id=user_id).first()
    profile = await Profile.filter(user=user).first()
    
    # Запрос подтверждения
    action_text = f"{'повысить' if change > 0 else 'понизить'} рейтинг на {abs(change)}"
    confirm_kb = create_keyboard([
        ("✅ Подтвердить", f"confirm_rating_{user_id}_{change}"),
        ("❌ Отмена", "cancel_action")
    ])
    
    await callback.message.edit_text(
        f"📊 Подтвердите: {action_text} пользователю {profile.first_name} (ID: {user_id})\nТекущий рейтинг: {user.raiting}",
        reply_markup=confirm_kb
    )

@router.callback_query(F.data.startswith("admin_amnesty_"))
async def admin_amnesty(callback: types.CallbackQuery):
    user_id = int(callback.data.split("_")[2])
    
    user = await User.filter(tg_id=user_id).first()
    profile = await Profile.filter(user=user).first()
    
    # Запрос подтверждения
    confirm_kb = create_keyboard([
        ("✅ Подтвердить", f"confirm_amnesty_{user_id}"),
        ("❌ Отмена", "cancel_action")
    ])
    
    await callback.message.edit_text(
        f"🕊️ Подтвердите амнистию для {profile.first_name} (ID: {user_id})\n• Снятие бана\n• Восстановление рейтинга до 100",
        reply_markup=confirm_kb
    )

@router.callback_query(F.data.startswith("admin_dismiss_"))
async def admin_dismiss_report(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    reporter_id = int(parts[2])
    reported_id = int(parts[3])
    
    reporter = await User.filter(tg_id=reporter_id).first()
    reporter_profile = await Profile.filter(user=reporter).first()
    
    # Запрос подтверждения
    confirm_kb = create_keyboard([
        ("✅ Подтвердить", f"confirm_dismiss_{reporter_id}"),
        ("❌ Отмена", "cancel_action")
    ])
    
    await callback.message.edit_text(
        f"❌ Подтвердите отклонение жалобы и наказание {reporter_profile.first_name} (ID: {reporter_id}) за ложную жалобу (-30 рейтинга)",
        reply_markup=confirm_kb
    )

# Обработчики подтверждений
@router.callback_query(F.data.startswith("confirm_ban_"))
async def confirm_ban(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    user_id = int(parts[2])
    duration = parts[3]
    
    user = await User.filter(tg_id=user_id).first()
    profile = await Profile.filter(user=user).first()
    admin = await User.filter(tg_id=callback.from_user.id).first()
    
    # Деактивируем старые баны
    await Ban.filter(user=user, is_active=True).update(is_active=False)
    
    if duration == "perm":
        # Постоянный бан
        await Ban.create(
            user=user,
            banned_by=admin,
            ban_type="permanent",
            reason="Постоянный бан по жалобе"
        )
        await User.filter(id=user.id).update(is_banned=True)
        result_text = f"🚫 Пользователь {profile.first_name} заблокирован навсегда"
    else:
        # Временный бан
        ban_hours = 1 if duration == "1h" else 24
        expires_at = datetime.now() + timedelta(hours=ban_hours)
        
        await Ban.create(
            user=user,
            banned_by=admin,
            ban_type="temp",
            duration_hours=ban_hours,
            expires_at=expires_at,
            reason=f"Временный бан на {ban_hours} час(ов)"
        )
        result_text = f"🚫 Пользователь {profile.first_name} заблокирован на {ban_hours} час(ов)"
    
    await callback.message.edit_text(f"✅ {result_text}")

@router.callback_query(F.data.startswith("confirm_rating_"))
async def confirm_rating(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    user_id = int(parts[2])
    change = int(parts[3])
    
    user = await User.filter(tg_id=user_id).first()
    profile = await Profile.filter(user=user).first()
    
    old_rating = user.raiting
    new_rating = max(0, min(1000, old_rating + change))
    await User.filter(id=user.id).update(raiting=new_rating)
    
    await callback.message.edit_text(
        f"✅ Рейтинг {profile.first_name} изменен: {old_rating} → {new_rating} ({change:+d})"
    )

@router.callback_query(F.data.startswith("confirm_amnesty_"))
async def confirm_amnesty(callback: types.CallbackQuery):
    user_id = int(callback.data.split("_")[2])
    
    user = await User.filter(tg_id=user_id).first()
    profile = await Profile.filter(user=user).first()
    
    # Снимаем все баны и восстанавливаем рейтинг
    await Ban.filter(user=user, is_active=True).update(is_active=False)
    await User.filter(id=user.id).update(is_banned=False, raiting=100)
    
    await callback.message.edit_text(f"✅ Амнистия для {profile.first_name}: бан снят, рейтинг восстановлен до 100")

@router.callback_query(F.data.startswith("confirm_dismiss_"))
async def confirm_dismiss(callback: types.CallbackQuery):
    reporter_id = int(callback.data.split("_")[2])
    
    reporter = await User.filter(tg_id=reporter_id).first()
    reporter_profile = await Profile.filter(user=reporter).first()
    
    # Наказываем за ложную жалобу
    new_rating = max(0, reporter.raiting - 30)
    await User.filter(id=reporter.id).update(raiting=new_rating)
    
    await callback.message.edit_text(f"✅ Жалоба отклонена. {reporter_profile.first_name} наказан за ложную жалобу (-30 рейтинга)")

@router.callback_query(F.data == "cancel_action")
async def cancel_action(callback: types.CallbackQuery):
    await callback.message.edit_text("❌ Действие отменено")

# Проверка банов в базе данных
async def is_banned(user_id: int) -> bool:
    user = await User.filter(tg_id=user_id).first()
    if not user:
        return False
    
    # Проверяем постоянный бан
    if user.is_banned:
        return True
    
    # Проверяем активные временные баны
    active_ban = await Ban.filter(
        user=user, 
        is_active=True, 
        ban_type="temp",
        expires_at__gt=datetime.now()
    ).first()
    
    if active_ban:
        return True
    
    # Деактивируем просроченные баны
    await Ban.filter(
        user=user,
        is_active=True,
        ban_type="temp",
        expires_at__lt=datetime.now()
    ).update(is_active=False)
    
    return False