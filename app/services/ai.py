from openai import AsyncOpenAI

from app.core.config import settings


class AIService:
    _instance: "AIService" = None

    def __init__(self):
        if AIService._instance is not None:
            raise Exception("This class is a singleton!")
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    @classmethod
    def get_instance(cls) -> "AIService":
        if AIService._instance is None:
            AIService._instance = cls()
        return AIService._instance

    async def generate_text(self, role: str, prompt: str) -> str:
        response = await self.client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": role},
                {"role": "user", "content": prompt},
            ],
        )
        return response.choices[0].message.content


ai_service = AIService.get_instance()
