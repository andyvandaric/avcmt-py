# File: avcmt/ai.py
import os
from importlib import import_module

from jinja2 import Environment, FileSystemLoader


def generate_with_ai(
    prompt, provider="pollinations", api_key=None, model="gemini", **kwargs
):
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
    try:
        provider_module = import_module(f"avcmt.providers.{provider}")
        class_name = "".join([x.capitalize() for x in provider.split("_")]) + "Provider"
        provider_class = getattr(provider_module, class_name)
    except (ModuleNotFoundError, AttributeError) as e:
        raise ImportError(f"Provider `{provider}` not found or invalid: {e}") from e

    if api_key is None:
        # Try to load from env: e.g., POLLINATIONS_API_KEY or OPENAI_API_KEY
        key_env = f"{provider.upper()}_API_KEY"
        api_key = os.getenv(key_env)
        if api_key is None:
            raise RuntimeError(f"{key_env} environment variable not set.")
    provider_instance = provider_class()
    return provider_instance.generate(prompt, api_key=api_key, model=model, **kwargs)


def render_prompt(group_name, diff_text):
    template_dir = os.path.join(os.path.dirname(__file__), "prompt_templates")
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("commit_message.j2")
    return template.render(group_name=group_name, diff_text=diff_text)
