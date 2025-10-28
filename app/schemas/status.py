from enum import Enum


class Status(str, Enum):
    PUBLISHED = "PUBLISHED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    DRAFT = "DRAFT"
    DELETED = "DELETED"
