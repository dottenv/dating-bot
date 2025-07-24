from aiogram import types, Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.models import User, Profile
from keyboards.profile import create_keyboard
from services.ai_assistant import assistant
from utils.debug import dbg

class AssistantStates(StatesGroup):
    chatting = State()

router = Router()

@router.message(Command("assistant", "help_ai", "ai"))
async def cmd_assistant(message: types.Message):
    """Команда для вызова AI-ассистента"""
    user = await User.filter(tg_id=message.from_user.id).first()
    if not user:
        await message.answer("Пройдите регистрацию /start")
        return
    
    # Создаем клавиатуру с быстрыми вопросами
    kb = create_keyboard([
        ("📊 Как работает рейтинг?", "ask_rating"),
        ("🔍 Как работает поиск?", "ask_search"),
        ("🚨 Система жалоб", "ask_reports"),
        ("🎭 Что такое деанон?", "ask_deanon"),
        ("💬 Просто поболтать", "ask_chat"),
        ("❌ Закрыть", "close_assistant")
    ])
    
    welcome_text = """
🤖 **AI-Ассистент бота знакомств**

Привет! Я знаю все о том, как работает этот бот. Могу объяснить:

• Систему рейтингов и баллов
• Принципы подбора собеседников
• Работу жалоб и модерации  
• Возможности деанона
• Правила безопасности

Выберите тему или просто задайте вопрос! 😊
"""
    
    await message.answer(welcome_text, reply_markup=kb, parse_mode="Markdown")

@router.callback_query(F.data.startswith("ask_"))
async def handle_quick_questions(callback: types.CallbackQuery):
    """Обработка быстрых вопросов"""
    question_type = callback.data.split("_")[1]
    
    user = await User.filter(tg_id=callback.from_user.id).first()
    user_data = {
        'rating': user.raiting,
        'is_premium': user.is_premium,
        'in_chat': False,  # Будем определять из активных чатов
        'in_search': False  # Будем определять из очереди поиска
    }
    
    # Проверяем статус пользователя
    from handlers.chat import active_chats, search_queue
    user_data['in_chat'] = callback.from_user.id in active_chats
    user_data['in_search'] = any(callback.from_user.id in queue for queue in search_queue.values())
    
    questions = {
        'rating': 'Как работает система рейтингов?',
        'search': 'Как работает поиск собеседников?', 
        'reports': 'Расскажи про систему жалоб',
        'deanon': 'Что такое деанон и как он работает?',
        'chat': 'Давай просто поболтаем!'
    }
    
    question = questions.get(question_type, 'Расскажи о боте')
    response = await assistant.get_response(question, user_data)
    
    # Для режима "поболтать" включаем интерактивный режим
    if question_type == 'chat':
        kb = create_keyboard([
            ("💬 Продолжить беседу", "continue_chat"),
            ("❓ Другой вопрос", "ask_another"),
            ("❌ Закрыть", "close_assistant")
        ])
        await callback.message.edit_text(f"{response}\n\n💬 Можете продолжить беседу или задать любой вопрос!", reply_markup=kb, parse_mode="Markdown")
    else:
        # Для остальных вопросов
        kb = create_keyboard([
            ("❓ Другой вопрос", "ask_another"),
            ("❌ Закрыть", "close_assistant")
        ])
        await callback.message.edit_text(response, reply_markup=kb, parse_mode="Markdown")

@router.callback_query(F.data == "continue_chat")
async def continue_chat(callback: types.CallbackQuery, state: FSMContext):
    """Начало интерактивной беседы"""
    await callback.message.edit_text(
        "💬 **Режим беседы активирован!**\n\n"
        "Просто напишите мне что угодно, и я отвечу!\n\n"
        "💡 Можно обсудить:\n"
        "• Ваши увлечения\n"
        "• Планы на будущее\n"
        "• Любые вопросы о боте\n"
        "• Просто поделиться настроением!\n\n"
        "🚫 Для выхода напишите: `/stop`",
        parse_mode="Markdown"
    )
    await state.set_state(AssistantStates.chatting)

@router.message(AssistantStates.chatting)
async def handle_chat_message(message: types.Message, state: FSMContext):
    """Обработка сообщений в режиме беседы"""
    if message.text and message.text.lower() in ['/stop', 'стоп', 'выход', 'закончить']:
        await message.answer("👋 Было приятно пообщаться! Обращайтесь еще! 😊")
        await state.clear()
        return
    
    user = await User.filter(tg_id=message.from_user.id).first()
    user_data = {
        'rating': user.raiting,
        'is_premium': user.is_premium,
        'in_chat': False,
        'in_search': False,
        'chatting_with_ai': True
    }
    
    # Получаем ответ от ИИ
    response = await assistant.get_response(message.text or "Просто поболтаем", user_data)
    
    # Добавляем подсказку о продолжении
    response += "\n\n💬 Продолжайте писать или `/stop` для выхода"
    
    await message.answer(f"🤖 {response}", parse_mode="Markdown")

@router.callback_query(F.data == "ask_another")
async def ask_another_question(callback: types.CallbackQuery, state: FSMContext):
    """Возврат к главному меню ассистента"""
    await state.clear()
    await cmd_assistant(callback.message)

@router.callback_query(F.data == "close_assistant")
async def close_assistant(callback: types.CallbackQuery, state: FSMContext):
    """Закрытие ассистента"""
    await state.clear()
    await callback.message.edit_text("🤖 AI-Ассистент закрыт. Обращайтесь еще! 😊")

# Обработчик для прямых вопросов к ассистенту
@router.message(F.text.startswith(("AI", "ИИ", "Ассистент", "Помощник", "?")))
async def handle_direct_question(message: types.Message):
    """Обработка прямых вопросов к ассистенту"""
    user = await User.filter(tg_id=message.from_user.id).first()
    if not user:
        await message.answer("Пройдите регистрацию /start")
        return
    
    # Убираем обращение из вопроса
    question = message.text
    for prefix in ["AI", "ИИ", "Ассистент", "Помощник"]:
        if question.startswith(prefix):
            question = question[len(prefix):].strip(" ,:!?")
            break
    
    if not question:
        question = "Расскажи о боте"
    
    user_data = {
        'rating': user.raiting,
        'is_premium': user.is_premium,
        'in_chat': False,
        'in_search': False
    }
    
    # Проверяем статус пользователя
    from handlers.chat import active_chats, search_queue
    user_data['in_chat'] = message.from_user.id in active_chats
    user_data['in_search'] = any(message.from_user.id in queue for queue in search_queue.values())
    
    dbg(f"Прямой вопрос к ассистенту: {question}", "AI_ASSISTANT")
    
    response = await assistant.get_response(question, user_data)
    
    # Добавляем кнопку для вызова полного меню ассистента
    kb = create_keyboard([
        ("🤖 Меню ассистента", "open_assistant_menu")
    ])
    
    await message.answer(f"🤖 **AI-Ассистент:**\n\n{response}", reply_markup=kb, parse_mode="Markdown")

@router.callback_query(F.data == "open_assistant_menu")
async def open_assistant_menu(callback: types.CallbackQuery, state: FSMContext):
    """Открытие полного меню ассистента"""
    await state.clear()
    await cmd_assistant(callback.message)

# Интеграция ассистента в поиск собеседника
async def get_search_entertainment(user_id: int) -> str:
    """Получает развлекательное сообщение для пользователя в поиске"""
    user = await User.filter(tg_id=user_id).first()
    user_data = {
        'rating': user.raiting if user else 100,
        'is_premium': user.is_premium if user else False,
        'in_chat': False,
        'in_search': True
    }
    
    entertainment_questions = [
        "Развлеки меня пока идет поиск",
        "Расскажи что-то интересное",
        "Поболтаем?",
        "Какой-нибудь совет?"
    ]
    
    import random
    question = random.choice(entertainment_questions)
    
    return await assistant.get_response(question, user_data)