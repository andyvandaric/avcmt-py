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
