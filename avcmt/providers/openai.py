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

# File: avcmt/providers/openai.py
# Revision v2 - Updated to use modern OpenAI v1.x client API.

# --- IMPORT CHANGE ---
# Import the main OpenAI class, not the entire module.
from openai import OpenAI


class OpenaiProvider:
    """Generates a response string using the OpenAI ChatCompletion API based on the provided prompt and parameters. This method initializes an OpenAI client with the given API key, sends a chat completion request with specified model and additional parameters, and returns the content of the generated message.

    Args:
        prompt (str): The input prompt to generate a response for.
        api_key (str): The API key used to authenticate with the OpenAI service.
        model (str, optional): The model to use for generation; defaults to "gpt-4o".
        **kwargs: Additional keyword arguments to customize the API request (e.g., temperature).

    Returns:
        str: The content of the generated response message.
    """

    DEFAULT_MODEL = "gpt-4o"

    def generate(
        self, prompt: str, api_key: str, model: str | None = None, **kwargs
    ) -> str:
        """Generates a response from the OpenAI ChatCompletion API based on the provided prompt and parameters.

        Creates a client instance with the specified API key, sends a chat completion request using the selected model and additional parameters, and returns the generated message content as a string.

        Args:
            prompt (str): Prompt input.
            api_key (str): OpenAI API key.
            model (str, optional): Model to use (default: gpt-4o).
            **kwargs: Additional OpenAI ChatCompletion parameters (e.g., temperature).

        Returns:
            str: Generated response content.
        """
        # --- LOGIC CHANGE ---
        # 1. Create a client instance with the API key.
        try:
            client = OpenAI(api_key=api_key)
        except Exception as e:
            # Add error handling if the client fails to initialize
            raise RuntimeError(f"Failed to initialize OpenAI client: {e}")

        # 2. Use the modern API syntax: client.chat.completions.create
        response = client.chat.completions.create(
            model=model or self.DEFAULT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            **kwargs,
        )
        return response.choices[0].message.content.strip()

    # The old _send_request method is no longer needed and has been removed.
