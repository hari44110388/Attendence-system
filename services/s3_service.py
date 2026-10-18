import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from flask import current_app

logger = logging.getLogger(__name__)


class S3ExportService:
    """Manages secure uploading of generated reports to Amazon S3 or local fallback."""

    @staticmethod
    def get_s3_client():
        """
        Instantiate boto3 S3 client.
        Supports both explicit environment credentials and AWS EC2 IAM Roles.
        """
        region = current_app.config.get("AWS_REGION", "us-east-1")
        access_key = current_app.config.get("AWS_ACCESS_KEY_ID")
        secret_key = current_app.config.get("AWS_SECRET_ACCESS_KEY")

        if access_key and secret_key:
            return boto3.client(
                "s3",
                region_name=region,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
            )
        else:
            # Uses EC2 IAM Role or default AWS CLI credentials profile
            return boto3.client("s3", region_name=region)

    @staticmethod
    def upload_report_csv(csv_content: str, filename_prefix: str = "attendance_report") -> Dict[str, Any]:
        """
        Upload CSV string to S3 under structured prefix: attendance-exports/YYYY/MM/
        Returns dictionary with storage mode, object key, and download URL.
        """
        now = datetime.utcnow()
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        safe_prefix = filename_prefix.replace(" ", "_").lower()
        filename = f"{safe_prefix}_{timestamp}.csv"
        s3_key = f"attendance-exports/{now.strftime('%Y/%m')}/{filename}"

        bucket_name = current_app.config.get("S3_BUCKET_NAME")

        # Try AWS S3 upload if bucket is specified
        if bucket_name:
            try:
                s3_client = S3ExportService.get_s3_client()
                
                # Upload with AES256 server-side encryption to enforce private & encrypted data
                s3_client.put_object(
                    Bucket=bucket_name,
                    Key=s3_key,
                    Body=csv_content.encode("utf-8"),
                    ContentType="text/csv",
                    ServerSideEncryption="AES256",
                )

                # Generate temporary presigned URL for authorized download
                expiration = current_app.config.get("S3_PRESIGNED_EXPIRATION", 3600)
                presigned_url = s3_client.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": bucket_name, "Key": s3_key},
                    ExpiresIn=expiration,
                )

                logger.info(f"Successfully uploaded {filename} to s3://{bucket_name}/{s3_key}")
                return {
                    "success": True,
                    "mode": "s3",
                    "bucket": bucket_name,
                    "key": s3_key,
                    "filename": filename,
                    "download_url": presigned_url,
                    "message": "Report uploaded to Amazon S3 securely with encryption.",
                }
            except (ClientError, NoCredentialsError, Exception) as err:
                logger.warning(
                    f"S3 upload failed or AWS credentials unavailable: {err}. Falling back to local storage."
                )

        # Local Fallback when S3 is unconfigured or credentials missing
        try:
            local_dir = Path(current_app.config.get("LOCAL_EXPORTS_DIR", "exports"))
            local_dir.mkdir(parents=True, exist_ok=True)
            local_path = local_dir / filename
            with open(local_path, "w", encoding="utf-8") as f:
                f.write(csv_content)

            return {
                "success": True,
                "mode": "local",
                "filename": filename,
                "local_path": str(local_path),
                "download_url": f"/reports/download-local/{filename}",
                "message": "Saved to local export storage (S3 not configured or in local development mode).",
            }
        except Exception as local_err:
            logger.error(f"Failed to save report locally: {local_err}")
            return {
                "success": False,
                "mode": "none",
                "filename": filename,
                "error": str(local_err),
                "message": "Failed to save exported report.",
            }
