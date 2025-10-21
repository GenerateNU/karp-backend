import os
import uuid

import boto3
from botocore.exceptions import ClientError

from app.core.config import settings


class S3Service:
    def __init__(self):
        pass

    AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
    BUCKET_NAME = settings.AWS_S3_BUCKET_NAME

    s3_client = boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION,
    )

    # Create a safe filename with a UUID to avoid unsafe characters such as :, ?, &
    def make_safe_filename(self, original_url: str) -> str:
        ext = os.path.splitext(original_url)[1]  # try to keep file extension
        return f"uploads/{uuid.uuid4()}{ext or '.png'}"

    # Generate a pre-signed URL to upload to S3 (to upload directly to S3 from the frontend)
    def generate_presigned_url(
        self, filename: str, content_type: str | None = None, expires_in: int = 3600
    ) -> str:
        mod_filename = self.make_safe_filename(filename)
        params = {"Bucket": self.BUCKET_NAME, "Key": mod_filename}
        params["ContentType"] = content_type
        print(params["ContentType"])
        try:
            url = self.s3_client.generate_presigned_url(
                "put_object", Params=params, ExpiresIn=expires_in
            )
            return url
        except ClientError as e:
            raise RuntimeError(f"Failed to generate pre-signed URL: {e}") from e

    # Directly upload a file object to S3
    def upload_file_to_s3(self, file, filename: str):
        try:
            self.s3_client.upload_fileobj(file, self.BUCKET_NAME, filename)
            return {"message": "File uploaded successfully!", "file_name": filename}
        except ClientError as e:
            raise RuntimeError(f"Failed to upload file: {e}") from e


s3_service = S3Service()
