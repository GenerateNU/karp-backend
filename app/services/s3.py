import os
import uuid

import boto3
from botocore.exceptions import ClientError

from app.core.config import settings


class S3Service:
    _instance: "S3Service" = None

    def __init__(self):
        if S3Service._instance is not None:
            raise Exception("This class is a singleton!")
        self.AWS_REGION = settings.AWS_REGION
        self.BUCKET_NAME = settings.AWS_S3_BUCKET_NAME

        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=self.AWS_REGION,
        )

    @classmethod
    def get_instance(cls) -> "S3Service":
        if S3Service._instance is None:
            S3Service._instance = cls()
        return S3Service._instance

    # Create a safe filename with a UUID to avoid unsafe characters such as :, ?, &
    def make_safe_filename(self, original_url: str, dir_prefix: str) -> str:
        ext = os.path.splitext(original_url)[1]  # try to keep file extension
        return f"{dir_prefix}/{uuid.uuid4()}{ext or '.png'}"

    # Generate a pre-signed URL to upload image to S3 bucket
    def generate_presigned_url(
        self, filename: str, content_type: str, dir_prefix: str, expires_in: int = 3600
    ) -> str:
        mod_filename = self.make_safe_filename(filename, dir_prefix)
        params = {"Bucket": self.BUCKET_NAME, "Key": mod_filename}
        params["ContentType"] = content_type
        try:
            url = self.s3_client.generate_presigned_url(
                "put_object", Params=params, ExpiresIn=expires_in
            )
            return url, mod_filename
        except ClientError as e:
            raise RuntimeError(f"Failed to generate pre-signed URL: {e}") from e

    # Get a pre-signed URL to retrieve an image from S3 bucket
    def get_presigned_url(
        self, filename: str, content_type: str | None = None, expires_in: int = 3600
    ) -> str:
        params = {"Bucket": self.BUCKET_NAME, "Key": filename}
        try:
            url = self.s3_client.generate_presigned_url(
                "get_object", Params=params, ExpiresIn=expires_in
            )
            return url
        except ClientError as e:
            raise RuntimeError(f"Failed to get pre-signed URL: {e}") from e


s3_service = S3Service.get_instance()
