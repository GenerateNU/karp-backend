import logging
from datetime import datetime

from bson import ObjectId

from app.models.event import event_model
from app.models.event_similarity import event_similarity_model
from app.models.registration import registration_model
from app.models.volunteer import volunteer_model
from app.schemas.event import EventStatus as Status
from app.schemas.registration import RegistrationStatus
from app.services.recommendation import recommendation_service

logger = logging.getLogger(__name__)


class SimilarityComputationService:
    _instance: "SimilarityComputationService | None" = None

    def __init__(self) -> None:
        pass

    @classmethod
    def get_instance(cls) -> "SimilarityComputationService":
        if SimilarityComputationService._instance is None:
            SimilarityComputationService._instance = cls()
        return SimilarityComputationService._instance

    async def compute_all_event_similarities(self) -> dict[str, int | float]:
        """
        Batch job: Compute and store similarities for all published events.

        This should be run nightly at 2 AM via cron.

        Returns:
            Dict with statistics about the computation
        """
        logger.info("Starting batch event similarity computation")
        start_time = datetime.now()

        try:
            events = await event_model.search_events(statuses=[Status.PUBLISHED], limit=200)

            if len(events) < 2:
                logger.info("Not enough published events to compute similarities")
                return {
                    "total_events": len(events),
                    "similarities_computed": 0,
                    "duration_seconds": 0,
                }

            logger.info(f"Computing similarities for {len(events)} published events")

            similarities = await recommendation_service.compute_event_similarities(events)

            stored_count = 0
            for event_id, similar_events in similarities.items():
                if similar_events:
                    await event_similarity_model.upsert_similarities(event_id, similar_events)
                    stored_count += 1

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            logger.info(
                f"Batch computation complete. "
                f"Processed {len(events)} events, "
                f"stored {stored_count} similarity records in {duration:.2f} seconds"
            )

            return {
                "total_events": len(events),
                "similarities_computed": stored_count,
                "duration_seconds": duration,
            }

        except Exception as e:
            logger.error(f"Error during batch similarity computation: {e}", exc_info=True)
            raise

    async def get_relevant_volunteers(self, event_id: str) -> set[str]:
        """
        Get volunteers who are most likely to care about this event.

        Criteria:
        - Have matching event type preferences
        - Have volunteered frequently at this organization

        Args:
            event_id: The event ID to find relevant volunteers for

        Returns:
            Set of volunteer IDs
        """
        relevant_volunteer_ids: set[str] = set()

        try:
            event = await event_model.get_event_by_id(event_id)
            if not event or not event.id:
                return relevant_volunteer_ids

            all_volunteers = await volunteer_model.get_all_volunteers()

            for volunteer in all_volunteers:
                if volunteer.id:
                    if any(pref in event.tags for pref in volunteer.preferences):
                        relevant_volunteer_ids.add(volunteer.id)

            org_events = await event_model.get_events_by_organization(event.organization_id)

            for org_event in org_events:
                if org_event.id:
                    registrations = await registration_model.registrations.find(
                        {
                            "event_id": ObjectId(org_event.id),
                            "registration_status": RegistrationStatus.COMPLETED,
                        }
                    ).to_list(length=None)

                    for reg in registrations:
                        volunteer_id = reg.get("volunteer_id")
                        if volunteer_id:
                            relevant_volunteer_ids.add(str(volunteer_id))

            logger.info(
                f"Found {len(relevant_volunteer_ids)} relevant volunteers for event {event_id}"
            )

            return relevant_volunteer_ids

        except Exception as e:
            logger.error(f"Error getting relevant volunteers for event {event_id}: {e}")
            return relevant_volunteer_ids

    async def compute_similarities_for_event(self, event_id: str) -> None:
        """
        Compute similarities for a single event against all other published events.

        This is triggered when a new event is published or updated.
        Uses selective recomputation - only affects volunteers who are likely to care.

        Args:
            event_id: The ID of the event to compute similarities for
        """
        logger.info(f"Computing similarities for event {event_id}")

        try:
            target_event = await event_model.get_event_by_id(event_id)

            if not target_event or target_event.status != Status.PUBLISHED:
                logger.warning(
                    f"Event {event_id} is not published, skipping similarity computation"
                )
                return

            all_events = await event_model.search_events(statuses=[Status.PUBLISHED], limit=200)

            if len(all_events) < 2:
                logger.info("Not enough events to compute similarities")
                return

            similarities = await recommendation_service.compute_event_similarities(all_events)

            if event_id in similarities and similarities[event_id]:
                await event_similarity_model.upsert_similarities(event_id, similarities[event_id])
                logger.info(
                    f"Stored {len(similarities[event_id])} similar events for event {event_id}"
                )
            else:
                logger.info(f"No similar events found for event {event_id}")

            for other_event_id, similar_events in similarities.items():
                if other_event_id != event_id and similar_events:
                    if any(se["event_id"] == event_id for se in similar_events):
                        await event_similarity_model.upsert_similarities(
                            other_event_id, similar_events
                        )

            relevant_volunteer_ids = await self.get_relevant_volunteers(event_id)

            if relevant_volunteer_ids:
                logger.info(
                    f"Event {event_id} affects {len(relevant_volunteer_ids)} volunteers. "
                    f"Their recommendations will be updated on next request."
                )
            else:
                logger.info(f"No relevant volunteers found for event {event_id}")

        except Exception as e:
            logger.error(f"Error computing similarities for event {event_id}: {e}", exc_info=True)


similarity_computation_service = SimilarityComputationService.get_instance()
