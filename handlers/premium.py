from aiogram import types, Router, F
from aiogram.types import LabeledPrice, PreCheckoutQuery
from database.models import User, PremiumPurchase
from keyboards.profile import create_keyboard
from middlewares.notifications import notification_service

router = Router()

PREMIUM_PRICES = {
    30: 50,   # 30 дней за 50 звезд
    90: 120,  # 90 дней за 120 звезд
    365: 400  # 365 дней за 400 звезд
}

@router.message(F.text == "⭐ Premium")
async def premium_menu(message: types.Message):
    user = await User.filter(tg_id=message.from_user.id).first()
    if not user:
        return
    
    if user.is_premium:
        text = "⭐ **Вы уже Premium пользователь!**\n\n**Ваши преимущества:**\n• Нет рекламы\n• Приоритет в поиске\n• Расширенные фильтры"
        kb = create_keyboard([("◀️ Назад", "main_menu")])
    else:
        text = "⭐ **Premium статус**\n\n**Преимущества:**\n• Нет рекламы\n• Приоритет в поиске\n• Расширенные фильтры\n\n**Тарифы:**"
        
        buttons = []
        for days, stars in PREMIUM_PRICES.items():
            if days == 30:
                period = "1 месяц"
            elif days == 90:
                period = "3 месяца"
            else:
                period = "1 год"
            buttons.append((f"{period} - {stars} ⭐", f"buy_premium_{days}"))
        
        buttons.append(("◀️ Назад", "main_menu"))
        kb = create_keyboard(buttons)
    
    await message.answer(text, reply_markup=kb, parse_mode="Markdown")

@router.callback_query(F.data.startswith("buy_premium_"))
async def buy_premium(callback: types.CallbackQuery):
    days = int(callback.data.split("_")[2])
    stars = PREMIUM_PRICES[days]
    
    if days == 30:
        period = "1 месяц"
    elif days == 90:
        period = "3 месяца"
    else:
        period = "1 год"
    
    prices = [LabeledPrice(label=f"Premium {period}", amount=stars)]
    
    await callback.bot.send_invoice(
        chat_id=callback.from_user.id,
        title="Premium статус",
        description=f"Premium на {period}\n• Нет рекламы\n• Приоритет в поиске\n• Расширенные фильтры",
        payload=f"premium_{days}_{callback.from_user.id}",
        provider_token="",  # Для Telegram Stars не нужен
        currency="XTR",  # Telegram Stars
        prices=prices,
        start_parameter="premium"
    )
    
    await callback.answer()

@router.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)

@router.message(F.successful_payment)
async def successful_payment(message: types.Message):
    payment = message.successful_payment
    payload_parts = payment.invoice_payload.split("_")
    
    if payload_parts[0] == "premium":
        days = int(payload_parts[1])
        user_id = int(payload_parts[2])
        
        user = await User.filter(tg_id=user_id).first()
        if user:
            # Записываем покупку
            await PremiumPurchase.create(
                user=user,
                stars_amount=payment.total_amount,
                duration_days=days,
                telegram_payment_id=payment.telegram_payment_charge_id
            )
            
            # Выдаем Premium
            await User.filter(id=user.id).update(is_premium=True)
            
            # Уведомляем пользователя
            await notification_service.notify_premium_granted(user_id)
            
            period = "1 месяц" if days == 30 else "3 месяца" if days == 90 else "1 год"
            await message.answer(
                f"✅ **Оплата прошла успешно!**\n\nPremium статус активирован на {period}",
                parse_mode="Markdown"
            )

@router.callback_query(F.data == "main_menu")
async def main_menu(callback: types.CallbackQuery):
    from keyboards.main import main_keyboard
    await callback.message.edit_text("Главное меню", reply_markup=main_keyboard)