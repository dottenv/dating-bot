from aiogram import types, Router, F
from aiogram.fsm.context import FSMContext
from database.models import User, Advertisement, AdClick
from keyboards.profile import create_keyboard
from states.ad_broadcast import AdStates
import json

router = Router()

@router.callback_query(F.data == "broadcast_ads")
async def ads_menu(callback: types.CallbackQuery):
    kb = create_keyboard([
        ("🆕 Создать", "create_ad_new"),
        ("📋 Список", "ads_list"),
        ("📊 Аналитика", "ads_analytics"),
        ("◀️ Назад", "admin_broadcast")
    ])
    
    await callback.message.edit_text("📺 **Управление рекламой**", reply_markup=kb, parse_mode="Markdown")

@router.callback_query(F.data == "create_ad_new")
async def create_ad_step1(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(step="title", ad_data={
        "title": "", "text": "", "media": None, "buttons": [],
        "audience": "all", "rounds": 1, "frequency": 24
    })
    
    kb = create_keyboard([("❌ Отмена", "ads_cancel")])
    await callback.message.edit_text("📝 **Введите название рекламы:**", reply_markup=kb, parse_mode="Markdown")
    await state.set_state(AdStates.creating)

@router.message(AdStates.creating)
async def process_ad_input(message: types.Message, state: FSMContext):
    data = await state.get_data()
    step = data.get("step")
    ad_data = data["ad_data"]
    
    if step == "title":
        ad_data["title"] = message.text
        await state.update_data(ad_data=ad_data, step="text")
        kb = create_keyboard([("❌ Отмена", "ads_cancel")])
        await message.answer("📄 **Введите текст рекламы:**", reply_markup=kb, parse_mode="Markdown")
    
    elif step == "text":
        ad_data["text"] = message.text
        if message.photo:
            ad_data["media"] = {"type": "photo", "file_id": message.photo[-1].file_id}
        elif message.video:
            ad_data["media"] = {"type": "video", "file_id": message.video.file_id}
        
        await state.update_data(ad_data=ad_data)
        await show_ad_settings(message, state)
    
    elif step == "rounds_input":
        try:
            rounds = int(message.text)
            if 1 <= rounds <= 10:
                ad_data["rounds"] = rounds
                await state.update_data(ad_data=ad_data)
                await show_ad_settings(message, state)
            else:
                await message.answer("❌ **Количество кругов должно быть от 1 до 10**", parse_mode="Markdown")
        except ValueError:
            await message.answer("❌ **Введите число**", parse_mode="Markdown")
    
    elif step == "freq_input":
        try:
            freq = int(message.text)
            if 1 <= freq <= 72:
                ad_data["frequency"] = freq
                await state.update_data(ad_data=ad_data)
                await show_ad_settings(message, state)
            else:
                await message.answer("❌ **Частота должна быть от 1 до 72 часов**", parse_mode="Markdown")
        except ValueError:
            await message.answer("❌ **Введите число**", parse_mode="Markdown")
    
    elif step == "edit_text":
        data = await state.get_data()
        edit_ad_id = data.get("edit_ad_id")
        
        await Advertisement.filter(id=edit_ad_id).update(text=message.text)
        
        kb = create_keyboard([("◀️ Назад", "ads_list")])
        await message.answer(
            "✅ **Текст рекламы обновлен**",
            reply_markup=kb,
            parse_mode="Markdown"
        )
        await state.clear()

async def show_ad_settings(message, state):
    data = await state.get_data()
    if "ad_data" not in data:
        await message.answer("❌ **Ошибка данных**", parse_mode="Markdown")
        return
    ad = data["ad_data"]
    
    audience_text = {"all": "Всем", "premium": "Premium", "regular": "Обычным"}
    
    text = f"⚙️ **Настройки рекламы**\n\n"
    text += f"📝 Название: {ad['title']}\n"
    text += f"👥 Аудитория: {audience_text[ad['audience']]}\n"
    text += f"🔄 Кругов: {ad['rounds']}\n"
    text += f"⏰ Частота: {ad['frequency']}ч\n"
    text += f"🔘 Кнопок: {len(ad['buttons'])}"
    
    kb = create_keyboard([
        ("👥 Аудитория", "set_audience"), ("🔄 Круги", "set_rounds"),
        ("⏰ Частота", "set_frequency"), ("🔘 Кнопки", "set_buttons"),
        ("✅ Сохранить", "save_ad"), ("❌ Отмена", "ads_cancel")
    ])
    
    await message.answer(text, reply_markup=kb, parse_mode="Markdown")

@router.callback_query(F.data == "set_audience")
async def set_audience(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    current = data["ad_data"]["audience"]
    
    kb = create_keyboard([
        ("👥 Всем" + (" ✅" if current == "all" else ""), "audience_all"),
        ("⭐ Premium" + (" ✅" if current == "premium" else ""), "audience_premium"),
        ("👤 Обычным" + (" ✅" if current == "regular" else ""), "audience_regular"),
        ("◀️ Назад", "back_settings")
    ])
    
    await callback.message.edit_text("👥 **Выберите аудиторию:**", reply_markup=kb, parse_mode="Markdown")

@router.callback_query(F.data.startswith("audience_"))
async def select_audience(callback: types.CallbackQuery, state: FSMContext):
    audience = callback.data.split("_")[1]
    data = await state.get_data()
    data["ad_data"]["audience"] = audience
    await state.update_data(ad_data=data["ad_data"])
    await callback.message.delete()
    await show_ad_settings(callback.message, state)

@router.callback_query(F.data == "set_rounds")
async def set_rounds(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    current = data["ad_data"]["rounds"]
    
    buttons = []
    for i in range(1, 6):
        text = f"{i}" + (" ✅" if current == i else "")
        buttons.append((text, f"rounds_{i}"))
    
    buttons.extend([
        ("✏️ Свой вариант", "rounds_custom"),
        ("◀️ Назад", "back_settings")
    ])
    kb = create_keyboard(buttons)
    
    await callback.message.edit_text("🔄 **Количество кругов:**", reply_markup=kb, parse_mode="Markdown")

@router.callback_query(F.data.startswith("rounds_"))
async def select_rounds(callback: types.CallbackQuery, state: FSMContext):
    rounds = int(callback.data.split("_")[1])
    data = await state.get_data()
    data["ad_data"]["rounds"] = rounds
    await state.update_data(ad_data=data["ad_data"])
    await callback.message.delete()
    await show_ad_settings(callback.message, state)

@router.callback_query(F.data == "set_frequency")
async def set_frequency(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    current = data["ad_data"]["frequency"]
    
    buttons = []
    for h in [1, 6, 12, 24]:
        text = f"{h}ч" + (" ✅" if current == h else "")
        buttons.append((text, f"freq_{h}"))
    
    buttons.extend([
        ("✏️ Свой вариант", "freq_custom"),
        ("◀️ Назад", "back_settings")
    ])
    kb = create_keyboard(buttons)
    
    await callback.message.edit_text("⏰ **Частота отправки:**", reply_markup=kb, parse_mode="Markdown")

@router.callback_query(F.data.startswith("freq_"))
async def select_frequency(callback: types.CallbackQuery, state: FSMContext):
    freq = int(callback.data.split("_")[1])
    data = await state.get_data()
    data["ad_data"]["frequency"] = freq
    await state.update_data(ad_data=data["ad_data"])
    await callback.message.delete()
    await show_ad_settings(callback.message, state)

@router.callback_query(F.data == "back_settings")
async def back_to_settings(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if "ad_data" not in data:
        await ads_menu(callback)
        return
    await callback.message.delete()
    await show_ad_settings(callback.message, state)

@router.callback_query(F.data == "rounds_custom")
async def rounds_custom(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(step="rounds_input")
    kb = create_keyboard([("❌ Отмена", "back_settings")])
    await callback.message.edit_text("🔄 **Введите количество кругов (1-10):**", reply_markup=kb, parse_mode="Markdown")
    await state.set_state(AdStates.creating)

@router.callback_query(F.data == "freq_custom")
async def freq_custom(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(step="freq_input")
    kb = create_keyboard([("❌ Отмена", "back_settings")])
    await callback.message.edit_text("⏰ **Введите частоту в часах (1-72):**", reply_markup=kb, parse_mode="Markdown")
    await state.set_state(AdStates.creating)

@router.callback_query(F.data == "save_ad")
async def save_advertisement(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    ad_data = data["ad_data"]
    
    user = await User.filter(tg_id=callback.from_user.id).first()
    
    ad = await Advertisement.create(
        title=ad_data["title"],
        text=ad_data["text"],
        media_type=ad_data["media"]["type"] if ad_data["media"] else None,
        media_file_id=ad_data["media"]["file_id"] if ad_data["media"] else None,
        buttons=ad_data["buttons"],
        audience=ad_data["audience"],
        rounds=ad_data["rounds"],
        frequency_hours=ad_data["frequency"],
        created_by=user
    )
    
    await callback.message.edit_text(f"✅ **Реклама '{ad.title}' сохранена**", parse_mode="Markdown")
    await state.clear()

@router.callback_query(F.data == "ads_list")
async def ads_list(callback: types.CallbackQuery):
    ads = await Advertisement.filter(is_active=True).order_by("-created_at").limit(10)
    
    if not ads:
        kb = create_keyboard([("◀️ Назад", "broadcast_ads")])
        await callback.message.edit_text("📋 **Нет активных реклам**", reply_markup=kb, parse_mode="Markdown")
        return
    
    buttons = []
    for ad in ads:
        status = "🟢" if ad.is_active else "🔴"
        buttons.append((f"{status} {ad.title}", f"ad_view_{ad.id}"))
    
    buttons.append(("◀️ Назад", "broadcast_ads"))
    kb = create_keyboard(buttons)
    
    await callback.message.edit_text("📋 **Список реклам:**", reply_markup=kb, parse_mode="Markdown")

@router.callback_query(F.data.startswith("ad_view_"))
async def view_ad(callback: types.CallbackQuery):
    ad_id = int(callback.data.split("_")[2])
    ad = await Advertisement.get(id=ad_id)
    
    audience_text = {"all": "Всем", "premium": "Premium", "regular": "Обычным"}
    
    text = f"📺 **{ad.title}**\n\n"
    text += f"📄 Текст: {ad.text[:100]}...\n"
    text += f"👥 Аудитория: {audience_text[ad.audience]}\n"
    text += f"📊 Отправлено: {ad.total_sent}\n"
    text += f"👆 Кликов: {ad.total_clicks}\n"
    text += f"📅 Создано: {ad.created_at.strftime('%d.%m %H:%M')}"
    
    kb = create_keyboard([
        ("📤 Отправить", f"send_ad_{ad.id}"),
        ("✏️ Изменить", f"edit_ad_{ad.id}"),
        ("🗑️ Удалить", f"delete_ad_{ad.id}"),
        ("◀️ Назад", "ads_list")
    ])
    
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")

@router.callback_query(F.data.startswith("send_ad_"))
async def send_ad(callback: types.CallbackQuery):
    ad_id = int(callback.data.split("_")[2])
    ad = await Advertisement.get(id=ad_id)
    
    from services.broadcast import broadcast_service
    
    # Создаем кнопки с отслеживанием кликов
    reply_markup = None
    if ad.buttons:
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = []
        for btn in ad.buttons:
            keyboard.append([InlineKeyboardButton(
                text=btn["text"], 
                callback_data=f"track_click_{ad.id}_{btn['text']}"
            )])
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    settings = {
        "audience": ad.audience,
        "rounds": ad.rounds,
        "frequency": ad.frequency_hours
    }
    
    media = [{"type": ad.media_type, "file_id": ad.media_file_id}] if ad.media_file_id else []
    
    result = await broadcast_service.send_ad_with_settings(
        callback.bot, ad.text, media, reply_markup, settings, [callback.from_user.id]
    )
    
    # Обновляем статистику
    await Advertisement.filter(id=ad.id).update(total_sent=ad.total_sent + result["sent"])
    
    await callback.message.edit_text(
        f"✅ **Реклама отправлена**\n\nОтправлено: {result['sent']}\nОшибок: {result['failed']}",
        parse_mode="Markdown"
    )

@router.callback_query(F.data.startswith("track_click_"))
async def track_click(callback: types.CallbackQuery):
    parts = callback.data.split("_", 3)
    ad_id = int(parts[2])
    button_text = parts[3]
    
    user = await User.filter(tg_id=callback.from_user.id).first()
    ad = await Advertisement.get(id=ad_id)
    
    # Записываем клик
    await AdClick.create(ad=ad, user=user, button_text=button_text)
    
    # Обновляем счетчик
    await Advertisement.filter(id=ad.id).update(total_clicks=ad.total_clicks + 1)
    
    await callback.answer("Переход зарегистрирован!")

@router.callback_query(F.data == "ads_analytics")
async def ads_analytics(callback: types.CallbackQuery):
    total_ads = await Advertisement.all().count()
    active_ads = await Advertisement.filter(is_active=True).count()
    total_sent = sum([ad.total_sent for ad in await Advertisement.all()])
    total_clicks = sum([ad.total_clicks for ad in await Advertisement.all()])
    
    ctr = (total_clicks / total_sent * 100) if total_sent > 0 else 0
    
    text = f"📊 **Аналитика рекламы**\n\n"
    text += f"📺 Всего реклам: {total_ads}\n"
    text += f"🟢 Активных: {active_ads}\n"
    text += f"📤 Отправлено: {total_sent}\n"
    text += f"👆 Кликов: {total_clicks}\n"
    text += f"📈 CTR: {ctr:.1f}%"
    
    kb = create_keyboard([("◀️ Назад", "broadcast_ads")])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")

@router.callback_query(F.data == "ads_cancel")
async def cancel_ad_creation(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await ads_menu(callback)

@router.callback_query(F.data.startswith("delete_ad_"))
async def delete_ad(callback: types.CallbackQuery):
    ad_id = int(callback.data.split("_")[2])
    ad = await Advertisement.get(id=ad_id)
    
    await Advertisement.filter(id=ad.id).update(is_active=False)
    
    kb = create_keyboard([("◀️ Назад", "ads_list")])
    await callback.message.edit_text(
        f"🗑️ **Реклама '{ad.title}' удалена**",
        reply_markup=kb,
        parse_mode="Markdown"
    )

@router.callback_query(F.data.startswith("edit_ad_"))
async def edit_ad(callback: types.CallbackQuery, state: FSMContext):
    ad_id = int(callback.data.split("_")[2])
    ad = await Advertisement.get(id=ad_id)
    
    await state.update_data(edit_ad_id=ad_id, step="edit_text", ad_data={
        "title": ad.title,
        "text": ad.text,
        "media": {"type": ad.media_type, "file_id": ad.media_file_id} if ad.media_file_id else None,
        "buttons": ad.buttons,
        "audience": ad.audience,
        "rounds": ad.rounds,
        "frequency": ad.frequency_hours
    })
    
    kb = create_keyboard([("❌ Отмена", "ads_cancel")])
    await callback.message.edit_text(
        f"✏️ **Редактирование '{ad.title}'**\n\nВведите новый текст:",
        reply_markup=kb,
        parse_mode="Markdown"
    )
    await state.set_state(AdStates.creating)