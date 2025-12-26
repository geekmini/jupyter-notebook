"""S3/MinIO client for file operations."""

import logging
import os
from pathlib import Path

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError


logger = logging.getLogger(__name__)


class S3Client:
    """Client for interacting with S3/MinIO storage."""

    def __init__(
        self,
        endpoint_url: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
    ):
        """Initialize S3 client.

        Args:
            endpoint_url: S3/MinIO endpoint URL. Defaults to AWS_ENDPOINT_URL env var.
            access_key: Access key. Defaults to AWS_ACCESS_KEY_ID env var.
            secret_key: Secret key. Defaults to AWS_SECRET_ACCESS_KEY env var.

        Raises:
            ValueError: If required credentials are not provided.
        """
        self.endpoint_url = endpoint_url or os.getenv("AWS_ENDPOINT_URL")
        self.access_key = access_key or os.getenv("AWS_ACCESS_KEY_ID")
        self.secret_key = secret_key or os.getenv("AWS_SECRET_ACCESS_KEY")

        # Fail fast if credentials are not configured
        if not self.endpoint_url:
            raise ValueError("AWS_ENDPOINT_URL environment variable is required")
        if not self.access_key:
            raise ValueError("AWS_ACCESS_KEY_ID environment variable is required")
        if not self.secret_key:
            raise ValueError("AWS_SECRET_ACCESS_KEY environment variable is required")

        self.client = boto3.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            config=Config(signature_version="s3v4"),
        )

    def download_file(self, bucket: str, key: str, local_path: Path) -> Path:
        """Download file from S3 to local path.

        Args:
            bucket: S3 bucket name
            key: S3 object key
            local_path: Local file path to save to

        Returns:
            Path to downloaded file
        """
        local_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"Downloading s3://{bucket}/{key} to {local_path}")
        self.client.download_file(bucket, key, str(local_path))
        return local_path

    def upload_file(self, local_path: Path, bucket: str, key: str) -> str:
        """Upload local file to S3.

        Args:
            local_path: Local file path
            bucket: S3 bucket name
            key: S3 object key

        Returns:
            S3 URI of uploaded file
        """
        logger.info(f"Uploading {local_path} to s3://{bucket}/{key}")
        self.client.upload_file(str(local_path), bucket, key)
        return f"s3://{bucket}/{key}"

    def upload_bytes(self, data: bytes, bucket: str, key: str) -> str:
        """Upload bytes directly to S3.

        Args:
            data: Bytes to upload
            bucket: S3 bucket name
            key: S3 object key

        Returns:
            S3 URI of uploaded object
        """
        logger.info(f"Uploading bytes to s3://{bucket}/{key}")
        self.client.put_object(Bucket=bucket, Key=key, Body=data)
        return f"s3://{bucket}/{key}"

    def upload_text(self, text: str, bucket: str, key: str) -> str:
        """Upload text content to S3.

        Args:
            text: Text content to upload
            bucket: S3 bucket name
            key: S3 object key

        Returns:
            S3 URI of uploaded object
        """
        return self.upload_bytes(text.encode("utf-8"), bucket, key)

    def download_bytes(self, bucket: str, key: str) -> bytes:
        """Download file content as bytes.

        Args:
            bucket: S3 bucket name
            key: S3 object key

        Returns:
            File content as bytes
        """
        response = self.client.get_object(Bucket=bucket, Key=key)
        try:
            return response["Body"].read()
        finally:
            response["Body"].close()

    def list_objects(self, bucket: str, prefix: str = "") -> list[str]:
        """List objects in bucket with optional prefix.

        Args:
            bucket: S3 bucket name
            prefix: Key prefix to filter by

        Returns:
            List of object keys
        """
        paginator = self.client.get_paginator("list_objects_v2")
        keys = []
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                keys.append(obj["Key"])
        return keys

    def delete_objects(self, bucket: str, keys: list[str]) -> None:
        """Delete multiple objects from bucket.

        Args:
            bucket: S3 bucket name
            keys: List of object keys to delete
        """
        if not keys:
            return

        # S3 delete_objects has a limit of 1000 keys per request
        for i in range(0, len(keys), 1000):
            batch = keys[i : i + 1000]
            delete_request = {"Objects": [{"Key": k} for k in batch]}
            logger.info(f"Deleting {len(batch)} objects from s3://{bucket}")
            self.client.delete_objects(Bucket=bucket, Delete=delete_request)

    def object_exists(self, bucket: str, key: str) -> bool:
        """Check if object exists in bucket.

        Args:
            bucket: S3 bucket name
            key: S3 object key

        Returns:
            True if object exists
        """
        try:
            self.client.head_object(Bucket=bucket, Key=key)
            return True
        except ClientError:
            return False
