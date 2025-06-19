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
    """
    Provider for OpenAI and compatible APIs using the modern v1.x client.
    """

    DEFAULT_MODEL = "gpt-4o"

    def generate(
        self, prompt: str, api_key: str, model: str | None = None, **kwargs
    ) -> str:
        """
        Generate response using the modern OpenAI ChatCompletion API.

        Args:
            prompt (str): Prompt input.
            api_key (str): OpenAI API key.
            model (str): Model to use (default: gpt-4o).
            **kwargs: Additional OpenAI ChatCompletion params (e.g., temperature).

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
