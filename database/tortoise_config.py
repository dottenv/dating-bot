TORTOISE_ORM = {
    "connections": {"default": "sqlite://dating_bot.db"},  # или ваша строка подключения
    "apps": {
        "models": {
            "models": ["database.models", "aerich.models"],
            "default_connection": "default",
        },
    },
}