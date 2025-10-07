import numpy as np

from app.schemas.data_types import EventType
from app.schemas.event import Event


class EventVector:
    """Converts events into feature vectors for similarity calculations"""

    def __init__(self):
        self.event_types = [e.value for e in EventType]
        self.num_event_types = len(self.event_types)

        self.org_id_to_index = {}
        self.num_orgs = 0

    def _build_org_mapping(self, events: list[Event]):
        unique_orgs = list(set(event.organization_id for event in events))
        self.org_id_to_index = {org_id: idx for idx, org_id in enumerate(unique_orgs)}
        self.num_orgs = len(unique_orgs)

    def _encode_tags(self, tags: list[str]) -> np.ndarray:
        encoding = np.zeros(self.num_event_types)
        for tag in tags:
            if tag in self.event_types:
                idx = self.event_types.index(tag)
                encoding[idx] = 1

        return encoding

    def _encode_org(self, org_id: str) -> np.ndarray:
        encoding = np.zeros(self.num_orgs)
        if org_id in self.org_id_to_index:
            idx = self.org_id_to_index[org_id]
            encoding[idx] = 1

        return encoding

    def vectorize_event(self, event: Event) -> np.ndarray:
        tags_vector = self._encode_tags(event.tags) * 0.8
        org_vector = self._encode_org(event.organization_id) * 0.2
        vector = np.concatenate([tags_vector, org_vector])
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm

        return vector

    def vectorize_events(self, events: list[Event]) -> dict[str, np.ndarray]:
        self._build_org_mapping(events)
        vectors = {}
        for event in events:
            vectors[event.id] = self.vectorize_event(event)

        return vectors
