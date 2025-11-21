import logging

from fastapi import HTTPException, status
from httpx import AsyncClient

from app.schemas.notification import NotificationRequest

logger = logging.getLogger(__name__)

EXPO_PUSH_API_URL = "https://api.expo.dev/v2/push/send"


class NotificationService:
    _instance: "NotificationService" = None

    def __init__(self):
        if NotificationService._instance is not None:
            raise Exception("This class is a singleton!")

    @classmethod
    def get_instance(cls) -> "NotificationService":
        if NotificationService._instance is None:
            NotificationService._instance = cls()
        return NotificationService._instance

    async def _send_to_expo(
        self, payload: dict | list[dict], timeout: float = 10.0
    ) -> dict | list[dict]:
        async with AsyncClient(timeout=timeout) as client:
            try:
                response = await client.post(
                    EXPO_PUSH_API_URL,
                    json=payload,
                    headers={"Content-Type": "application/json", "Accept": "application/json"},
                )
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.error(f"Error sending notification to Expo API: {e}")
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Notification service error: {str(e)}",
                ) from e

    async def send_notification(
        self,
        notification_request: NotificationRequest,
    ) -> dict:

        payload = {
            "to": notification_request.device_token,
            "title": notification_request.title,
            "body": notification_request.body,
            "sound": notification_request.sound,
        }

        if notification_request.data:
            payload["data"] = notification_request.data

        result = await self._send_to_expo(payload, timeout=10.0)

        if isinstance(result, list) and len(result) > 0:
            notification_result = result[0]
            if notification_result.get("status") == "error":
                error_message = notification_result.get("message", "Unknown error")
                logger.error(f"Failed to send notification: {error_message}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to send notification: {error_message}",
                )
            return notification_result
        return result

    async def send_batch_notifications(
        self,
        notifications: list[NotificationRequest],
    ) -> list[dict]:
        if not notifications:
            return []

        payload = []
        for notif in notifications:
            payload = {
                "to": notif.device_token,
                "title": notif.title,
                "body": notif.body,
                "sound": notif.sound,
            }

            if notif.data:
                payload["data"] = notif.data

        results = await self._send_to_expo(payload, timeout=30.0)

        if isinstance(results, list):
            for i, result in enumerate(results):
                if result.get("status") == "error":
                    logger.warning(
                        f"Notification {i} failed: {result.get('message', 'Unknown error')}"
                    )
            return results

        return [results] if results else []


notification_service = NotificationService.get_instance()
