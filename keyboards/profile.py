from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

def create_keyboard(buttons, row_width=2):
    kb = []
    i = 0
    while i < len(buttons):
        # Если элемент - это список кнопок для одной строки
        if isinstance(buttons[i], list) and all(isinstance(btn, tuple) for btn in buttons[i]):
            row = []
            for btn in buttons[i]:
                text, callback_data = btn
                row.append(InlineKeyboardButton(text=text, callback_data=callback_data))
            kb.append(row)
            i += 1
        else:
            # Обычная обработка с row_width
            row = []
            for j in range(row_width):
                if i + j >= len(buttons):
                    break
                btn = buttons[i + j]
                if isinstance(btn, tuple):
                    text, callback_data = btn
                else:
                    text = callback_data = btn
                row.append(InlineKeyboardButton(text=text, callback_data=callback_data))
            kb.append(row)
            i += row_width
    return InlineKeyboardMarkup(inline_keyboard=kb)


