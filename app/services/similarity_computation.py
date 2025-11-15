import logging
from datetime import datetime

from app.models.event import event_model
from app.models.event_similarity import event_similarity_model
from app.schemas.event import EventStatus
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
            events = await event_model.search_events(statuses=[EventStatus.PUBLISHED], limit=200)

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

    async def compute_similarities_for_event(self, event_id: str) -> None:
        """
        Compute similarities for a single event against all other published events.

        This is triggered when a new event is published or updated.

        Args:
            event_id: The ID of the event to compute similarities for
        """
        logger.info(f"Computing similarities for event {event_id}")

        try:
            target_event = await event_model.get_event_by_id(event_id)

            if not target_event or target_event.status != EventStatus.PUBLISHED:
                logger.warning(
                    f"Event {event_id} is not published, skipping similarity computation"
                )
                return

            all_events = await event_model.search_events(
                statuses=[EventStatus.PUBLISHED], limit=200
            )

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

        except Exception as e:
            logger.error(f"Error computing similarities for event {event_id}: {e}", exc_info=True)


similarity_computation_service = SimilarityComputationService.get_instance()
