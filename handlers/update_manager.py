from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.filters import Command

from services.update_service import update_service
from keyboards.profile import create_keyboard
from database.models import User

router = Router()

@router.callback_query(F.data == "admin_updates")
async def updates_menu(callback: CallbackQuery, is_admin: bool = False):
    if not is_admin:
        await callback.answer("Access denied")
        return
    
    kb = create_keyboard([
        ("🔍 Check Updates", "check_updates"),
        ("⬇️ Apply Updates", "apply_updates"),
        ("🔄 Restart Bot", "restart_bot"),
        ("◀️ Back", "admin_panel")
    ])
    
    await callback.message.edit_text("🔧 **Update Management**", reply_markup=kb, parse_mode="Markdown")

@router.callback_query(F.data == "check_updates")
async def check_updates(callback: CallbackQuery, is_admin: bool = False):
    if not is_admin:
        await callback.answer("Access denied")
        return
    
    result = await update_service.check_updates()
    
    if "error" in result:
        text = f"❌ **Error:** {result['error']}"
    else:
        text = f"📊 **Update Status**\n\n"
        text += f"Current: `{result['current_commit']}`\n"
        text += f"Remote: `{result['remote_commit']}`\n"
        text += f"Status: {result['status']}"
    
    kb = create_keyboard([("◀️ Back", "admin_updates")])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")

@router.callback_query(F.data == "apply_updates")
async def apply_updates(callback: CallbackQuery, is_admin: bool = False):
    if not is_admin:
        await callback.answer("Access denied")
        return
    
    await callback.message.edit_text("⏳ Applying updates...")
    
    result = await update_service.apply_update()
    
    if "error" in result:
        text = f"❌ **Update Failed:** {result['error']}"
        kb = create_keyboard([("◀️ Back", "admin_updates")])
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    else:
        await callback.message.edit_text("✅ **Update completed!** Restarting bot...")
        await update_service.restart_bot()

@router.callback_query(F.data == "restart_bot")
async def restart_bot(callback: CallbackQuery, is_admin: bool = False):
    if not is_admin:
        await callback.answer("Access denied")
        return
    
    await callback.message.edit_text("🔄 **Restarting bot...**")
    await update_service.restart_bot()