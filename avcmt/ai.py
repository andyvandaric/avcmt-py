# Copyright 2025 Andy Vandaric
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# File: avcmt/ai.py
# Revision: render_prompt function removed, all Jinja2 loading centralized via avcmt.utils.get_jinja_env.

import os
from importlib import import_module

# REMOVED: from pathlib import Path
# REMOVED: from jinja2 import Environment, FileSystemLoader


def generate_with_ai(
    prompt, provider="pollinations", api_key=None, model="gemini", **kwargs
):
    """Generates AI-based content such as commit messages using the specified provider and model.
    This function dynamically loads and initializes the provider class, sets the API key, and invokes the provider's generate method with the provided prompt and additional parameters.

    Args:
        prompt (str): The input prompt used to generate content.
        provider (str): The name of the provider module and class to use; defaults to "pollinations".
        api_key (str, optional): The API key for authenticating with the provider; if not provided, attempts to load from environment variables.
        model (str): The name of the model to use with the provider; defaults to "gemini".
        **kwargs: Additional keyword arguments to pass to the provider's generate method.

    Returns:
        str: The generated content produced by the AI provider.
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


# REMOVED: render_prompt function as requested.
# Its functionality is now expected to be handled directly by modules that need it,
# using avcmt.utils.get_jinja_env.
