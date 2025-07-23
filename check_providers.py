import g4f
from g4f.Provider import ProviderUtils

# Получаем список провайдеров, которые не требуют браузера
no_browser_providers = []
for provider in ProviderUtils.get_providers():
    if not getattr(provider, 'needs_auth', False) and not getattr(provider, 'supports_stream', False):
        no_browser_providers.append(provider.__name__)

print("Провайдеры без браузера:")
for provider in no_browser_providers:
    print(f"- {provider}")