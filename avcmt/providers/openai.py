import openai


class OpenaiProvider:
    def generate(self, prompt, api_key, model="gpt-4o", **kwargs):
        openai.api_key = api_key
        completion = openai.ChatCompletion.create(
            model=model, messages=[{"role": "user", "content": prompt}], **kwargs
        )
        return completion.choices[0].message.content.strip()
