import logging
from datetime import UTC, datetime, timedelta

from app.models.event import event_model
from app.schemas.event import Event
from app.schemas.notification import NotificationRequest
from app.services.device_token import device_token_service
from app.services.notification import notification_service
from app.services.scheduler import scheduler_service

logger = logging.getLogger(__name__)


def format_time_delta(time_delta: timedelta) -> str:
    total_seconds = int(time_delta.total_seconds())

    weeks = total_seconds // (7 * 24 * 3600)
    days = (total_seconds % (7 * 24 * 3600)) // (24 * 3600)
    hours = (total_seconds % (24 * 3600)) // 3600
    minutes = (total_seconds % 3600) // 60

    if weeks > 0:
        return f"{weeks} week{'s' if weeks != 1 else ''}"
    elif days > 0:
        return f"{days} day{'s' if days != 1 else ''}"
    elif hours > 0:
        return f"{hours} hour{'s' if hours != 1 else ''}"
    elif minutes > 0:
        return f"{minutes} minute{'s' if minutes != 1 else ''}"
    else:
        return "less than a minute"


def _get_event_notification_job_key(event_id: str, time_delta: timedelta) -> str:
    return f"event-notification-{event_id}-{time_delta.total_seconds()}"


def _ensure_timezone_aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


async def schedule_event_notifications(event: Event) -> None:
    scheduler = scheduler_service.get_scheduler()
    start_date_time = _ensure_timezone_aware(event.start_date_time)
    now = datetime.now(UTC)

    if start_date_time > now + timedelta(minutes=2):
        scheduler.add_job(
            id=_get_event_notification_job_key(event.id, timedelta(minutes=2)),
            func=_schedule_event_notification,
            trigger="date",
            run_date=start_date_time - timedelta(minutes=2),
            args=[event, timedelta(minutes=2)],
        )
        logger.info(
            f"Scheduled event notification for event {event.name} "
            f"starting in {timedelta(minutes=2)}"
        )


async def _schedule_event_notification(event: Event, time_delta: timedelta) -> None:
    volunteers = await event_model.get_registered_volunteers_for_event(event.id)

    device_tokens = await device_token_service.get_device_tokens_by_volunteer_ids(
        volunteer_ids=[volunteer.id for volunteer in volunteers]
    )

    device_token_map = {
        device_token.volunteer_id: device_token.device_token for device_token in device_tokens
    }

    time_str = format_time_delta(time_delta)

    notifications = [
        NotificationRequest(
            title=f"Upcoming Event: {event.name}",
            body=f"{event.name} is starting in {time_str}",
            device_token=device_token_map.get(volunteer.id),
        )
        for volunteer in volunteers
    ]
    await notification_service.send_batch_notifications(notifications)


async def update_event_notifications(event: Event) -> None:
    scheduler = scheduler_service.get_scheduler()
    start_date_time = _ensure_timezone_aware(event.start_date_time)
    now = datetime.now(UTC)

    if scheduler.get_job(
        _get_event_notification_job_key(event.id, timedelta(days=1))
    ) and start_date_time > now + timedelta(days=1):
        scheduler.modify_job(
            _get_event_notification_job_key(event.id, timedelta(days=1)),
            run_date=start_date_time - timedelta(days=1),
        )


async def cancel_event_notifications(event: Event) -> None:
    scheduler = scheduler_service.get_scheduler()

    if scheduler.get_job(_get_event_notification_job_key(event.id, timedelta(days=1))):
        scheduler_service.get_scheduler().remove_job(
            _get_event_notification_job_key(event.id, timedelta(days=1))
        )
