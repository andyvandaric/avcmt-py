# File: avcmt/providers/openai.py

import openai


class OpenaiProvider:
    DEFAULT_MODEL = "gpt-4o"

    def generate(self, prompt, api_key, model=None, **kwargs):
        """
        Generate response using OpenAI-compatible API.

        Args:
            prompt (str): Prompt input.
            api_key (str): OpenAI API key.
            model (str): Model to use (default: gpt-4o).
            **kwargs: Additional OpenAI ChatCompletion params (e.g., temperature).

        Returns:
            str: Generated response content.
        """
        openai.api_key = api_key
        response = self._send_request(prompt, model or self.DEFAULT_MODEL, **kwargs)
        return response.choices[0].message.content.strip()

    @staticmethod
    def _send_request(prompt, model, **kwargs):  # <--- fix: no "self"
        return openai.ChatCompletion.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            **kwargs,
        )
