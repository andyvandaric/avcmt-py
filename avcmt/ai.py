# File: avcmt/ai.py
import os
from importlib import import_module


def generate_with_ai(prompt, provider="pollinations", api_key=None, model="gemini", **kwargs):
    """
    Universal AI commit message generator, routed to provider class.

    Args:
        prompt (str): Prompt string.
        provider (str): Provider name, must match file/class in avcmt/providers/.
        api_key (str): API key for the provider.
        model (str): Model name (if provider supports).
        **kwargs: Extra args for provider.

    Returns:
        str: AI-generated content.
    """
    provider_module = import_module(f"avcmt.providers.{provider}")
    class_name = "".join([x.capitalize() for x in provider.split("_")]) + "Provider"
    ProviderClass = getattr(provider_module, class_name)
    if api_key is None:
        # Try to load from env: e.g., POLLINATIONS_API_KEY or OPENAI_API_KEY
        key_env = f"{provider.upper()}_API_KEY"
        api_key = os.getenv(key_env)
        if api_key is None:
            raise RuntimeError(f"{key_env} environment variable not set.")
    provider_instance = ProviderClass()
    return provider_instance.generate(prompt, api_key=api_key, model=model, **kwargs)
