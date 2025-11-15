import base64
import io
import json
import secrets
from datetime import timedelta

import qrcode
from fastapi import HTTPException, status

from app.models.event import event_model
from app.schemas.event import Event, UpdateEventStatusRequest
from app.schemas.location import Location
from app.services.ai import ai_service


class EventService:
    _instance: "EventService" = None

    def __init__(self, event_model=event_model):
        if EventService._instance is not None:
            raise Exception("This class is a singleton!")
        self.event_model = event_model

    @classmethod
    def get_instance(cls) -> "EventService":
        if EventService._instance is None:
            EventService._instance = cls()
        return EventService._instance

    # ensure that only the org who created the event can modify it
    async def authorize_org(self, event_id: str, org_id: str) -> Event | None:
        event = await self.event_model.get_event_by_id(event_id)
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
        await self.authorize_org(event_id, user_id)
        updated = await self.event_model.update_event_image(event_id, s3_key)
        return updated

    async def get_events_near(self, lat: float, lng: float, distance_km: float) -> list[Event]:
        location = Location(type="Point", coordinates=[lng, lat])
        max_distance_meters = int(distance_km * 1000)
        return await self.event_model.get_events_by_location(max_distance_meters, location)

    async def get_event_qr_codes(self, event: Event):
        expires_at = event.end_date_time + timedelta(minutes=30)
        check_in_qr_token = secrets.token_hex(16)
        check_out_qr_token = secrets.token_hex(16)

        check_in_payload = json.dumps(
            {
                "event_id": event.id,
                "qr_token": check_in_qr_token,
                "expires_at": expires_at.isoformat(),
            }
        )

        check_out_payload = json.dumps(
            {
                "event_id": event.id,
                "qr_token": check_out_qr_token,
                "expires_at": expires_at.isoformat(),
            }
        )

        check_in_qr_data = json.dumps(check_in_payload)
        check_out_qr_data = json.dumps(check_out_payload)

        check_in_img = qrcode.make(check_in_qr_data)
        check_in_buf = io.BytesIO()
        check_in_img.save(check_in_buf, format="PNG")
        check_in_qr_code = base64.b64encode(
            check_in_buf.getvalue()
        ).decode()  # qr code image for frontend

        check_out_img = qrcode.make(check_out_qr_data)
        check_out_buf = io.BytesIO()
        check_out_img.save(check_out_buf, format="PNG")
        check_out_qr_code = base64.b64encode(
            check_in_buf.getvalue()
        ).decode()  # qr code image for frontend

        update_event_req = UpdateEventStatusRequest(
            check_in_qr_code_image=check_in_qr_code,
            check_in_qr_token=check_in_qr_token,
            check_out_qr_code_image=check_out_qr_code,
            check_out_qr_token=check_out_qr_token,
        )

        return await self.event_model.update_event(event.id, update_event_req)

    async def estimate_event_difficulty(self, description: str) -> float:
        role = (
            "You are an expert event planner. Given an event description,"
            "rate the difficulty of organizing the event on a scale from 0.0 to 2.0,"
            "where 0.0 is very easy and 2.0 is extremely difficult. Provide only the"
            "numeric rating as a decimal."
        )
        prompt = f"Event Description: {description}\n\nPlease provide the difficulty rating:"
        try:
            response = await ai_service.generate_text(role, prompt)
        except Exception:
            return 1
        try:
            difficulty = float(response.strip())
            if 0.0 <= difficulty <= 2.0:
                return difficulty
            else:
                return 1
        except Exception:
            return 1


event_service = EventService.get_instance()
