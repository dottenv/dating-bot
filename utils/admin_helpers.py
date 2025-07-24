async def safe_edit_message(callback, text, reply_markup=None, parse_mode="Markdown"):
    """Безопасное редактирование сообщения с обработкой ошибок"""
    try:
        await callback.message.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    except:
        pass