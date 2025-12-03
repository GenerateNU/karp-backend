from pydantic import BaseModel


class Address(BaseModel):
    """Structured address information from Google Maps Geocoding API"""

    street_number: str | None = None
    street_name: str | None = None
    city: str | None = None
    state: str | None = None
    zipcode: str | None = None
    country: str | None = None
    formatted_address: str | None = None

    def to_string(self) -> str:
        """Convert structured address to a formatted string"""
        parts = []
        if self.street_number and self.street_name:
            parts.append(f"{self.street_number} {self.street_name}")
        elif self.street_name:
            parts.append(self.street_name)
        if self.city:
            parts.append(self.city)
        if self.state:
            parts.append(self.state)
        if self.zipcode:
            parts.append(self.zipcode)
        if self.country and self.country != "United States":
            parts.append(self.country)

        return ", ".join(parts) if parts else self.formatted_address or ""
