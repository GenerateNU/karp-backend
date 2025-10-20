from pydantic import BaseModel


class GeneratePresignedUrlRequest(BaseModel):
    filename: str


class GeneratePresignedUrlResponse(BaseModel):
    url: str


class UploadResponse(BaseModel):
    message: str
    file_name: str


class PresignedUrlResponse(BaseModel):
    upload_url: str
    file_url: str
