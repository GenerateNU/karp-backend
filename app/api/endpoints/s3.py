from fastapi import APIRouter, HTTPException

from app.schemas.s3 import GeneratePresignedUrlRequest, GeneratePresignedUrlResponse
from app.services.s3 import s3_service

router = APIRouter()


# need to add permissions on what users can upload what files later
@router.post("/generate-presigned-url", response_model=GeneratePresignedUrlResponse)
def create_presigned_url(request: GeneratePresignedUrlRequest):
    try:
        url = s3_service.generate_presigned_url(request.filename)
        print(f"Generated presigned URL: {url}")
        return GeneratePresignedUrlResponse(url=url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# @router.post("/upload", response_model=UploadResponse)
# async def upload_image(file: UploadFile = File(...)):
#     try:
#         result = s3_service.upload_file_to_s3(file.file, file.filename)
#         return UploadResponse(**result)
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e)) from e
