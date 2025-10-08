from __future__ import annotations
from typing import Any


class VolunteerAchievementsService:
    def __init__(self):
        pass

    def create_achievement_request(self, volunteer_id: str, achievement_id: str) -> dict[str, Any]:
        """Helper to create achievement request data"""
        return {"volunteer_id": volunteer_id, "achievement_id": achievement_id}

    def get_level_achievement_id(self, level: int) -> str:
        """Helper to get achievement ID for a level"""
        return f"level_{level}_achievement"

    def should_add_achievement(self, volunteer_id: str, level: int) -> bool:
        """Helper to determine if we should add a level-up achievement"""
        # Business rule: add achievement for level 2 and above
        return level >= 2
