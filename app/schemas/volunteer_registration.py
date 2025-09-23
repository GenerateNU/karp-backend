from pydantic import BaseModel


class VolunteerRegistration(BaseModel):
    id: str
    first_name: str
    last_name: str
    username: str
    volunteer_id: str

    class Config:
        from_attributes = True
