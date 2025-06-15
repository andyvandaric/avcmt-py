# File: avcmt/providers/pollinations.py 
import requests
import time

class PollinationsProvider:
    API_URL = "https://text.pollinations.ai/openai"

    def generate(self, prompt, api_key, model="gemini", retries=3, **kwargs):
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        for attempt in range(1, retries + 1):
            try:
                response = requests.post(
                    self.API_URL, json=payload, headers=headers, timeout=60
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"].strip()
            except Exception as e:
                if attempt < retries:
                    print(f"[Pollinations] Error (attempt {attempt}): {e}. Retrying...")
                    time.sleep(2)
                    continue
                raise RuntimeError(
                    f"[Pollinations] Failed after {retries} attempts: {e}"
                )