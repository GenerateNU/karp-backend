"""
Service for generating tags for items based on their description.
Uses OpenAI to map item descriptions to tags from a predefined list.
"""

from openai import OpenAI

from app.core.config import settings

# Fixed list of available tags (should match frontend)
AVAILABLE_TAGS = [
    "Sweet",
    "Treat",
    "Candy",
    "Shopping",
    "Clothes",
    "Discounts",
    "Mall",
    "Food",
    "Drink",
    "Restaurant",
    "Coffee",
    "Dessert",
    "Snack",
    "Electronics",
    "Books",
    "Gift",
    "Card",
    "Plant",
    "Health",
    "Beauty",
    "Fashion",
    "Home",
    "Garden",
    "Entertainment",
    "Sports",
]


class TagGenerationService:
    _instance: "TagGenerationService" = None

    def __init__(self):
        if TagGenerationService._instance is not None:
            raise Exception("This class is a singleton!")
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.available_tags = AVAILABLE_TAGS

    @classmethod
    def get_instance(cls) -> "TagGenerationService":
        if TagGenerationService._instance is None:
            TagGenerationService._instance = cls()
        return TagGenerationService._instance

    def generate_tags(self, description: str) -> list[str]:
        """
        Generate tags for an item based on its description.
        Uses OpenAI to map the description to relevant tags from the fixed list.
        """
        try:
            tags_list = ", ".join(self.available_tags)
            prompt = (
                "Given the following item description, "
                "select the most relevant tags from this fixed list:\n"
                f"{tags_list}\n\n"
                f'Item description: "{description}"\n\n'
                "Select 1-4 most relevant tags from the list. "
                "Return only the tag names separated by commas, nothing else. "
                "Tags must be from the provided list exactly as written."
            )

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a helpful assistant that selects "
                            "relevant tags from a fixed list."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=100,
            )

            tags_str = response.choices[0].message.content.strip()
            # Parse the response and validate tags
            suggested_tags = [tag.strip() for tag in tags_str.split(",")]

            # Filter to only include valid tags from our list
            valid_tags = [tag for tag in suggested_tags if tag in self.available_tags]

            # Remove duplicates while preserving order
            seen = set()
            unique_tags = []
            for tag in valid_tags:
                if tag not in seen:
                    seen.add(tag)
                    unique_tags.append(tag)

            return unique_tags[:4]  # Limit to 4 tags max

        except Exception as e:
            print(f"Error generating tags: {e}")
            # Fallback: return empty list if tag generation fails
            return []


tag_generation_service = TagGenerationService.get_instance()
