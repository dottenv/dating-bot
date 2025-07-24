from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command

from services.update_service import update_service
from keyboards.profile import create_keyboard
from database.models import User

router = Router()

@router.callback_query(F.data == "admin_updates")
async def updates_menu(callback: CallbackQuery):
    user = await User.filter(tg_id=callback.from_user.id).first()
    if not user or not user.is_admin:
        await callback.answer("Access denied")
        return
    
    kb = create_keyboard([
        ("🔍 Check Updates", "check_updates"),
        ("⬇️ Apply Updates", "apply_updates"),
        ("🔄 Restart Bot", "restart_bot"),
        ("⚙️ Git Settings", "git_settings"),
        ("◀️ Back", "admin_panel")
    ])
    
    await callback.message.edit_text("🔧 **Update Management**", reply_markup=kb, parse_mode="Markdown")

@router.callback_query(F.data == "check_updates")
async def check_updates(callback: CallbackQuery):
    user = await User.filter(tg_id=callback.from_user.id).first()
    if not user or not user.is_admin:
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
async def apply_updates(callback: CallbackQuery):
    user = await User.filter(tg_id=callback.from_user.id).first()
    if not user or not user.is_admin:
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
async def restart_bot(callback: CallbackQuery):
    user = await User.filter(tg_id=callback.from_user.id).first()
    if not user or not user.is_admin:
        await callback.answer("Access denied")
        return
    
    await callback.message.edit_text("🔄 **Restarting bot...**")
    await update_service.restart_bot()

@router.callback_query(F.data == "git_settings")
async def git_settings(callback: CallbackQuery):
    user = await User.filter(tg_id=callback.from_user.id).first()
    if not user or not user.is_admin:
        await callback.answer("Access denied")
        return
    
    from config import GIT_REPO_URL, GIT_BRANCH
    
    text = f"⚙️ **Git Settings**\n\n"
    text += f"Repository: `{GIT_REPO_URL or 'Not set'}`\n"
    text += f"Branch: `{GIT_BRANCH}`\n\n"
    text += "Commands:\n"
    text += "`/set_git_url <url>` - set repository URL\n"
    text += "`/set_git_branch <branch>` - set branch"
    
    kb = create_keyboard([("◀️ Back", "admin_updates")])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")

@router.message(Command("set_git_url"))
async def set_git_url(message: Message):
    user = await User.filter(tg_id=message.from_user.id).first()
    if not user or not user.is_admin:
        return
    
    try:
        url = message.text.split(maxsplit=1)[1]
        
        # Update .env file
        import os
        env_path = ".env"
        
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                lines = f.readlines()
            
            updated = False
            for i, line in enumerate(lines):
                if line.startswith('GIT_REPO_URL='):
                    lines[i] = f'GIT_REPO_URL={url}\n'
                    updated = True
                    break
            
            if not updated:
                lines.append(f'GIT_REPO_URL={url}\n')
            
            with open(env_path, 'w') as f:
                f.writelines(lines)
        else:
            with open(env_path, 'w') as f:
                f.write(f'GIT_REPO_URL={url}\n')
        
        await message.answer(f"✅ **Git URL updated**\n\nNew URL: `{url}`", parse_mode="Markdown")
        
    except IndexError:
        await message.answer("**Usage:** `/set_git_url <repository_url>`", parse_mode="Markdown")

@router.message(Command("set_git_branch"))
async def set_git_branch(message: Message):
    user = await User.filter(tg_id=message.from_user.id).first()
    if not user or not user.is_admin:
        return
    
    try:
        branch = message.text.split(maxsplit=1)[1]
        
        # Update .env file
        import os
        env_path = ".env"
        
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                lines = f.readlines()
            
            updated = False
            for i, line in enumerate(lines):
                if line.startswith('GIT_BRANCH='):
                    lines[i] = f'GIT_BRANCH={branch}\n'
                    updated = True
                    break
            
            if not updated:
                lines.append(f'GIT_BRANCH={branch}\n')
            
            with open(env_path, 'w') as f:
                f.writelines(lines)
        else:
            with open(env_path, 'w') as f:
                f.write(f'GIT_BRANCH={branch}\n')
        
        await message.answer(f"✅ **Git branch updated**\n\nNew branch: `{branch}`", parse_mode="Markdown")
        
    except IndexError:
        await message.answer("**Usage:** `/set_git_branch <branch_name>`", parse_mode="Markdown")