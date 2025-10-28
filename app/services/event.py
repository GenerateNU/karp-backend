from fastapi import HTTPException, status

from app.schemas.event import Event


class EventService:
    def __init__(self):
        pass

    # ensure that only the org who created the event can modify it
    async def authorize_org(self, event_id: str, org_id: str) -> Event | None:
        from app.models.event import event_model

        event = await event_model.get_event_by_id(event_id)
        print(f"Authorizing org {org_id} for event {event_id}")
        print(f"Event org: {event.organization_id }")
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found",
            )
        if event.organization_id != org_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to modify this event",
            )

    async def update_event_image(self, event_id: str, s3_key: str, user_id: str) -> str:
        from app.models.event import event_model

        await self.authorize_org(event_id, user_id)
        updated = await event_model.update_event_image(event_id, s3_key)
        return updated
