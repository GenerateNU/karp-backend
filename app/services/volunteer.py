from __future__ import annotations
from typing import Any


class VolunteerService:
    def __init__(self):
        self.base_xp = 100
        self.growth_factor = 1.15

    def compute_level_from_exp(self, total_exp: int) -> int:
        """Helper to compute level from total EXP using exponential growth"""
        level = 1
        required_for_next = self.base_xp
        remaining = int(total_exp)
        while remaining >= required_for_next:
            remaining -= required_for_next
            level += 1
            required_for_next = int(required_for_next * self.growth_factor)
            if required_for_next <= 0:
                required_for_next = self.base_xp
        return level

    def should_level_up(self, volunteer: dict[str, Any]) -> bool:
        """Helper to determine if volunteer should level up"""
        current_exp = volunteer.get("exp", 0)
        current_level = volunteer.get("level", 1)
        new_level = self.compute_level_from_exp(current_exp)
        return new_level != current_level

    def get_new_level(self, volunteer: dict[str, Any]) -> int:
        """Helper to get the new level for a volunteer"""
        current_exp = volunteer.get("exp", 0)
        return self.compute_level_from_exp(current_exp)
