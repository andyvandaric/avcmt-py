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

# File: avcmt/providers/pollinations.py

import time

import requests


class PollinationsProvider:
    """Generates a response from Pollinations AI by sending a prompt with specified credentials, handling retries and errors to ensure reliable communication.

    Args:
        prompt (str): The input prompt text for the AI model.
        api_key (str): The API token used for authentication with Pollinations.
        model (str): The name of the AI model to use (default is "gemini").
        retries (int): The number of times to retry the request upon failure (default is 3).
        **kwargs: Additional optional arguments for future extensions.

    Returns:
        str: The generated response content from Pollinations AI.

    Raises:
        RuntimeError: If all retry attempts fail to obtain a successful response.
    """

    API_URL = "https://text.pollinations.ai/openai"
    RETRY_DELAY = 2  # seconds
    TIMEOUT = 60  # seconds

    def generate(self, prompt, api_key, model="gemini", retries=3, **kwargs):
        """Generates a response from Pollinations AI based on the input prompt and specified parameters, handling retries upon failure.

        This method sends a request to the AI service with the provided prompt, API key, and model configuration, attempting multiple retries if errors occur.

        Args:
            prompt (str): The input prompt to send to the AI model.
            api_key (str): The API key used for authentication with the AI service.
            model (str, optional): The name of the AI model to use. Defaults to "gemini".
            retries (int, optional): The number of retry attempts upon failure. Defaults to 3.
            **kwargs: Additional keyword arguments for extended configuration (not used in this implementation).

        Returns:
            The response from the Pollinations AI service, as returned by self._send_request.

        Raises:
            RuntimeError: If all retry attempts fail due to exceptions during request processing.
        """
        for attempt in range(1, retries + 1):
            try:
                return self._send_request(prompt, api_key, model)
            except Exception as e:
                if attempt < retries:
                    print(f"[Pollinations] Error (attempt {attempt}): {e}. Retrying...")
                    time.sleep(self.RETRY_DELAY)
                else:
                    raise RuntimeError(
                        f"[Pollinations] Failed after {retries} attempts: {e}"
                    )

    def _send_request(self, prompt, api_key, model):
        """Performs an HTTP POST request to send a prompt to a specified API endpoint using the provided API key and model, then processes and returns the response content.

        Args:
            prompt (str): The input prompt message to send to the API.
            api_key (str): The API key used for authorization.
            model (str): The identifier of the model to be used for generating the response.

        Returns:
            str: The content of the API's response message, with leading and trailing whitespace removed.
        """
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        response = requests.post(
            self.API_URL, json=payload, headers=headers, timeout=self.TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
