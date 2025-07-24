from aiogram import types, Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database.models import User
from keyboards.profile import create_keyboard
from states.ad_broadcast import AdStates
from services.broadcast import broadcast_service
import json

router = Router()

@router.callback_query(F.data == "create_ad")
async def create_ad(callback: types.CallbackQuery, state: FSMContext):
    user = await User.filter(tg_id=callback.from_user.id).first()
    if not user or not user.is_admin:
        await callback.answer("Доступ запрещен")
        return
    
    await callback.message.edit_text(
        "🆕 **Создание рекламного поста**\n\n"
        "Отправьте текст рекламы или медиа-файл с описанием.\n\n"
        "📝 Поддерживаемые форматы:\n"
        "• Текст\n"
        "• Фото + текст\n"
        "• Видео + текст\n"
        "• Несколько фото (album)",
        parse_mode="Markdown"
    )
    
    await state.set_state(AdStates.waiting_content)

@router.message(AdStates.waiting_content)
async def process_ad_content(message: types.Message, state: FSMContext):
    # Сохраняем контент
    ad_data = {
        'text': message.caption or message.text or '',
        'media': []
    }
    
    # Обрабатываем медиа
    if message.photo:
        ad_data['media'].append({
            'type': 'photo',
            'file_id': message.photo[-1].file_id
        })
    elif message.video:
        ad_data['media'].append({
            'type': 'video',
            'file_id': message.video.file_id
        })
    elif message.document:
        ad_data['media'].append({
            'type': 'document',
            'file_id': message.document.file_id
        })
    
    await state.update_data(ad_data=ad_data)
    
    kb = create_keyboard([
        ("➕ Добавить кнопки", "add_buttons"),
        ("⚙️ Настройки", "ad_settings"),
        ("📤 Отправить", "send_ad"),
        ("❌ Отменить", "cancel_ad")
    ])
    
    preview_text = f"**Предварительный просмотр:**\n\n{ad_data['text']}"
    if ad_data['media']:
        preview_text += f"\n\n📎 Медиа: {len(ad_data['media'])} файл(ов)"
    
    await message.answer(preview_text, reply_markup=kb, parse_mode="Markdown")

@router.callback_query(F.data == "add_buttons")
async def add_buttons(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "🔘 **Добавление кнопок**\n\n"
        "Отправьте кнопки в формате:\n"
        "`Текст кнопки 1 | https://example.com`\n"
        "`Текст кнопки 2 | https://example2.com`\n\n"
        "Каждая кнопка с новой строки.\n"
        "Разделитель: ` | `",
        parse_mode="Markdown"
    )
    
    await state.set_state(AdStates.waiting_buttons)

@router.message(AdStates.waiting_buttons)
async def process_buttons(message: types.Message, state: FSMContext):
    buttons = []
    
    for line in message.text.split('\n'):
        if '|' in line:
            parts = line.split('|', 1)
            if len(parts) == 2:
                text = parts[0].strip()
                url = parts[1].strip()
                if text and url:
                    buttons.append({'text': text, 'url': url})
    
    if not buttons:
        await message.answer("❌ Неверный формат кнопок. Попробуйте еще раз.")
        return
    
    await state.update_data(buttons=buttons)
    
    # Показываем финальный предварительный просмотр
    data = await state.get_data()
    ad_data = data['ad_data']
    
    preview_text = f"**Финальный предварительный просмотр:**\n\n{ad_data['text']}"
    if ad_data['media']:
        preview_text += f"\n\n📎 Медиа: {len(ad_data['media'])} файл(ов)"
    
    preview_text += f"\n\n🔘 Кнопки: {len(buttons)}"
    for btn in buttons:
        preview_text += f"\n• {btn['text']}"
    
    kb = create_keyboard([
        ("✅ Отправить рекламу", "confirm_send"),
        ("❌ Отменить", "cancel_ad")
    ])
    
    await message.answer(preview_text, reply_markup=kb, parse_mode="Markdown")
    await state.set_state(AdStates.confirm)

@router.callback_query(F.data == "send_ad")
async def send_ad_without_buttons(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(buttons=[])
    await confirm_send_ad(callback, state)

@router.callback_query(F.data == "confirm_send")
async def confirm_send_ad(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    ad_data = data['ad_data']
    buttons = data.get('buttons', [])
    
    # Создаем клавиатуру если есть кнопки
    reply_markup = None
    if buttons:
        keyboard = []
        for btn in buttons:
            keyboard.append([InlineKeyboardButton(text=btn['text'], url=btn['url'])])
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    status_msg = await callback.message.edit_text("📤 **Отправка рекламы...**", parse_mode="Markdown")
    
    # Получаем настройки
    settings = data.get('ad_settings', {'audience': 'all', 'rounds': 1, 'frequency': 24})
    
    # Отправляем рекламу
    result = await broadcast_service.send_ad_with_settings(
        callback.bot, 
        ad_data['text'], 
        ad_data['media'], 
        reply_markup,
        settings,
        exclude_ids=[callback.from_user.id]
    )
    
    await status_msg.edit_text(
        f"✅ **Реклама отправлена**\n\n"
        f"Отправлено: `{result['sent']}`\n"
        f"Ошибок: `{result['failed']}`\n"
        f"Всего пользователей: `{result['total']}`",
        parse_mode="Markdown"
    )
    
    await state.clear()

@router.callback_query(F.data == "ad_settings")
async def ad_settings(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "⚙️ **Настройки рекламы**\n\n"
        "Отправьте настройки:\n\n"
        "`Аудитория: all/premium/regular`\n"
        "`Круги: 1-10`\n"
        "`Частота: 1-24`\n\n"
        "**Пример:**\n"
        "`Аудитория: all`\n"
        "`Круги: 3`\n"
        "`Частота: 6`",
        parse_mode="Markdown"
    )
    await state.set_state(AdStates.waiting_settings)

@router.message(AdStates.waiting_settings)
async def process_ad_settings(message: types.Message, state: FSMContext):
    settings = {'audience': 'all', 'rounds': 1, 'frequency': 24}
    
    for line in message.text.split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip().lower()
            value = value.strip()
            
            if 'аудитория' in key:
                if value in ['all', 'premium', 'regular']:
                    settings['audience'] = value
            elif 'круг' in key:
                try:
                    rounds = int(value)
                    if 1 <= rounds <= 10:
                        settings['rounds'] = rounds
                except ValueError:
                    pass
            elif 'частот' in key:
                try:
                    freq = int(value)
                    if 1 <= freq <= 24:
                        settings['frequency'] = freq
                except ValueError:
                    pass
    
    await state.update_data(ad_settings=settings)
    
    data = await state.get_data()
    ad_data = data['ad_data']
    
    audience_text = {'all': 'Всем', 'premium': 'Premium', 'regular': 'Обычным'}
    
    preview_text = f"**Предпросмотр:**\n\n{ad_data['text']}"
    if ad_data['media']:
        preview_text += f"\n\n📁 Медиа: {len(ad_data['media'])}"
    
    preview_text += f"\n\n⚙️ **Настройки:**\n"
    preview_text += f"• Аудитория: {audience_text[settings['audience']]}\n"
    preview_text += f"• Кругов: {settings['rounds']}\n"
    preview_text += f"• Частота: {settings['frequency']}ч"
    
    kb = create_keyboard([
        ("➕ Кнопки", "add_buttons"),
        ("✅ Отправить", "send_ad"),
        ("❌ Отменить", "cancel_ad")
    ])
    
    await message.answer(preview_text, reply_markup=kb, parse_mode="Markdown")

@router.callback_query(F.data == "cancel_ad")
async def cancel_ad(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("❌ **Создание рекламы отменено**", parse_mode="Markdown")
    await state.clear()

@router.callback_query(F.data == "ad_stats")
async def ad_stats(callback: types.CallbackQuery):
    user = await User.filter(tg_id=callback.from_user.id).first()
    if not user or not user.is_admin:
        await callback.answer("Доступ запрещен")
        return
    
    # Простая статистика
    total_users = await User.filter(is_active=True).count()
    premium_users = await User.filter(is_active=True, is_premium=True).count()
    
    stats_text = f"📊 **Статистика для рекламы**\n\n"
    stats_text += f"👥 Активных пользователей: `{total_users}`\n"
    stats_text += f"⭐ Premium пользователей: `{premium_users}`\n"
    stats_text += f"👤 Обычных пользователей: `{total_users - premium_users}`\n\n"
    stats_text += f"📈 Охват рекламы: до `{total_users}` человек"
    
    kb = create_keyboard([("◀️ Назад", "broadcast_ads")])
    
    await callback.message.edit_text(stats_text, reply_markup=kb, parse_mode="Markdown")