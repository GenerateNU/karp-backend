from fastapi import HTTPException, status

from app.models.event import event_model
from app.schemas.event import Event


class EventService:
    def __init__(self, model=event_model):
        # Inject the model so it’s easy to mock for testing
        self.model = model

    # ensure that only the org who created the event can modify it
    async def authorize_org(self, event_id: str, org_id: str) -> Event | None:
        event = await self.model.get_event_by_id(event_id)
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
