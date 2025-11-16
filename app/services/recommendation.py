from datetime import datetime
from typing import Any

import numpy as np
from bson import ObjectId
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import normalize

from app.models.event import event_model
from app.models.event_similarity import event_similarity_model
from app.models.registration import registration_model
from app.models.volunteer import volunteer_model
from app.schemas.event import Event
from app.schemas.event import EventStatus as Status
from app.schemas.registration import RegistrationStatus
from app.schemas.volunteer import EventType


class RecommendationService:
    _instance: "RecommendationService | None" = None
    SIMILARITY_THRESHOLD = 0.7
    COLLAB_WEIGHT = 0.7
    CONTENT_WEIGHT = 0.3

    def __init__(self) -> None:
        pass

    @classmethod
    def get_instance(cls) -> "RecommendationService":
        if RecommendationService._instance is None:
            RecommendationService._instance = cls()
        return RecommendationService._instance

    def vectorize_event(self, event: Event, all_org_ids: list[str]) -> np.ndarray:
        """Create feature vector for an event with 80% tag weight, 20% org weight"""
        all_event_types = [et.value for et in EventType]
        tag_vector = np.array([1.0 if tag in event.tags else 0.0 for tag in all_event_types])
        tag_vector = tag_vector * 0.8

        org_vector = np.array(
            [1.0 if event.organization_id == org_id else 0.0 for org_id in all_org_ids]
        )
        org_vector = org_vector * 0.2

        full_vector = np.concatenate([tag_vector, org_vector])
        normalized = normalize(full_vector.reshape(1, -1))[0]
        return normalized

    async def compute_event_similarities(
        self, events: list[Event]
    ) -> dict[str, list[dict[str, Any]]]:
        """Compute pairwise similarities for a list of events

        Returns:
            Dict mapping event_id to list of similar events with scores
        """
        if len(events) < 2:
            return {}

        all_org_ids = list(set(e.organization_id for e in events))

        event_vectors = []
        event_ids: list[str] = []
        for event in events:
            if event.id:
                vector = self.vectorize_event(event, all_org_ids)
                event_vectors.append(vector)
                event_ids.append(event.id)

        similarity_matrix = cosine_similarity(np.array(event_vectors))

        similarities: dict[str, list[dict[str, Any]]] = {}
        for i, event_id in enumerate(event_ids):
            similar_events: list[dict[str, Any]] = []
            for j, other_event_id in enumerate(event_ids):
                if i != j:
                    score = float(similarity_matrix[i][j])
                    if score >= self.SIMILARITY_THRESHOLD:
                        similar_events.append(
                            {"event_id": other_event_id, "similarity_score": score}
                        )

            similar_events.sort(key=lambda x: float(x["similarity_score"]), reverse=True)
            similarities[event_id] = similar_events

        return similarities

    async def get_volunteer_completed_events(self, volunteer_id: str) -> list[str]:
        """Get list of event IDs the volunteer has completed"""
        completed_events = await registration_model.get_events_by_volunteer(
            volunteer_id, RegistrationStatus.COMPLETED
        )
        return [event.id for event in completed_events if event.id]

    async def get_volunteer_registered_events(self, volunteer_id: str) -> set[str]:
        """Get set of event IDs the volunteer is registered for (any status except unregistered)"""
        all_registrations = await registration_model.registrations.find(
            {"volunteer_id": ObjectId(volunteer_id)}
        ).to_list(length=None)

        registered_event_ids: set[str] = set()
        for reg in all_registrations:
            if reg.get("registration_status") != RegistrationStatus.UNREGISTERED:
                event_id = reg.get("event_id")
                if event_id:
                    registered_event_ids.add(str(event_id))

        return registered_event_ids

    async def compute_collaborative_score(
        self, candidate_event_id: str, completed_event_ids: list[str]
    ) -> float:
        """Compute collaborative filtering score for a candidate event"""
        if not completed_event_ids:
            return 0.0

        similarity_scores: list[float] = []

        for completed_event_id in completed_event_ids:
            similarity_doc = await event_similarity_model.get_similar_events(completed_event_id)

            if similarity_doc:
                for similar_event in similarity_doc.similar_events:
                    if similar_event.event_id == candidate_event_id:
                        similarity_scores.append(similar_event.similarity_score)
                        break

        if similarity_scores:
            return sum(similarity_scores) / len(similarity_scores)
        return 0.0

    def compute_content_score(self, event: Event, volunteer_preferences: list[EventType]) -> float:
        """Compute content-based filtering score"""
        if not volunteer_preferences:
            return 0.0

        matching_tags = sum(1 for tag in event.tags if tag in volunteer_preferences)
        return matching_tags / len(volunteer_preferences)

    async def is_event_available(self, event: Event, registered_event_ids: set[str]) -> bool:
        """Check if event is available for registration"""
        if not event.id:
            return False

        if event.id in registered_event_ids:
            return False

        if event.start_date_time <= datetime.now():
            return False

        if event.status != Status.PUBLISHED:
            return False

        registrations = await registration_model.registrations.find(
            {"event_id": ObjectId(event.id)}
        ).to_list(length=None)

        active_registrations = [
            r
            for r in registrations
            if r.get("registration_status") != RegistrationStatus.UNREGISTERED
        ]

        if len(active_registrations) >= event.max_volunteers:
            return False

        return True

    async def get_recommendations_for_volunteer(self, volunteer_id: str) -> list[dict[str, Any]]:
        """Get event recommendations for a volunteer

        Returns:
            List of dicts with 'event' and 'score' keys, sorted by score descending
        """
        volunteer = await volunteer_model.get_volunteer_by_id(volunteer_id)
        if not volunteer:
            return []

        completed_event_ids = await self.get_volunteer_completed_events(volunteer_id)
        registered_event_ids = await self.get_volunteer_registered_events(volunteer_id)

        all_events = await event_model.search_events(statuses=[Status.PUBLISHED], limit=200)

        recommendations: list[dict[str, Any]] = []

        if completed_event_ids:
            for event in all_events:
                if not event.id:
                    continue

                if not await self.is_event_available(event, registered_event_ids):
                    continue

                collab_score = await self.compute_collaborative_score(event.id, completed_event_ids)

                content_score = self.compute_content_score(event, volunteer.preferences)

                final_score = (collab_score * self.COLLAB_WEIGHT) + (
                    content_score * self.CONTENT_WEIGHT
                )

                recommendations.append({"event": event, "score": final_score})

        else:
            if volunteer.preferences:
                for event in all_events:
                    if not event.id:
                        continue

                    if not await self.is_event_available(event, registered_event_ids):
                        continue

                    if any(tag in volunteer.preferences for tag in event.tags):
                        score = self.compute_content_score(event, volunteer.preferences)
                        recommendations.append({"event": event, "score": score})

            else:
                for event in all_events:
                    if not event.id:
                        continue

                    if not await self.is_event_available(event, registered_event_ids):
                        continue

                    registrations = await registration_model.registrations.find(
                        {"event_id": ObjectId(event.id)}
                    ).to_list(length=None)

                    active_registrations = [
                        r
                        for r in registrations
                        if r.get("registration_status") != RegistrationStatus.UNREGISTERED
                    ]

                    popularity_score = (
                        len(active_registrations) / event.max_volunteers
                        if event.max_volunteers > 0
                        else 0
                    )

                    recommendations.append({"event": event, "score": popularity_score})

        recommendations.sort(key=lambda x: float(x["score"]), reverse=True)

        return recommendations


recommendation_service = RecommendationService.get_instance()
