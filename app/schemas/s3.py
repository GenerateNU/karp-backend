from pydantic import BaseModel


class PresignedUrlResponse(BaseModel):
    upload_url: str
    file_url: str
