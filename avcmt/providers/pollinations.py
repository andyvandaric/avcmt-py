# File: avcmt/providers/pollinations.py

import time

import requests


class PollinationsProvider:
    API_URL = "https://text.pollinations.ai/openai"
    RETRY_DELAY = 2  # seconds
    TIMEOUT = 60  # seconds

    def generate(self, prompt, api_key, model="gemini", retries=3, **kwargs):
        """
        Generate a response from Pollinations AI using OpenAI-compatible API.

        Args:
            prompt (str): Prompt text for the model.
            api_key (str): Pollinations API token.
            model (str): Model name (e.g., "gemini").
            retries (int): Number of retry attempts.
            **kwargs: Reserved for future arguments.

        Returns:
            str: The generated response content.

        Raises:
            RuntimeError: If all attempts fail.
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
