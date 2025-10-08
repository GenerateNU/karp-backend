from __future__ import annotations
from typing import Any
from datetime import datetime, timezone


class RegistrationService:
    async def bulk_checkout_missing(self, regs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Helper to identify and prepare checkout updates for volunteers who haven't checked out"""
        now = datetime.now(timezone.utc)
        out = []
        for r in regs:
            if r.get("clocked_out") is None:
                out.append({**r, "clocked_out": now})
        return out

    async def should_level_up(self, reg: dict[str, Any]) -> str | None:
        """Business rule: return volunteer_id if we should check level-up"""
        return reg.get("volunteer_id")
