from pydantic import BaseModel


class NotificationRequest(BaseModel):
    title: str
    body: str
    data: dict | None = None
    sound: str = "default"
    badge: int | None = None
    device_token: str
