"""
AWS Lambda Scheduled Export Function
Automates monthly attendance reporting by extracting records from Amazon RDS (MySQL),
generating encrypted CSV files, and uploading them to Amazon S3.

Trigger: Amazon EventBridge Rule (Cron: '0 0 1 * ? *' - 1st of every month at midnight UTC)
Architecture: Lambda in VPC with RDS access & S3 VPC Gateway Endpoint (or NAT Gateway).
"""

import os
import io
import csv
import json
import logging
from datetime import datetime, date, timedelta
from typing import Dict, Any, Tuple, Optional
import boto3
from botocore.exceptions import ClientError
import pymysql

# Setup structured logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def get_db_credentials() -> Dict[str, Any]:
    """
    Fetch RDS MySQL database credentials.
    Priority 1: AWS Secrets Manager (Production Best Practice)
    Priority 2: Environment Variables (Testing / Alternative Setup)
    NOTE: Passwords and sensitive tokens are NEVER logged!
    """
    secret_name = os.environ.get("DB_SECRET_NAME")
    region_name = os.environ.get("AWS_REGION", "us-east-1")

    if secret_name:
        logger.info(f"Retrieving DB credentials from AWS Secrets Manager: {secret_name}")
        client = boto3.client("secretsmanager", region_name=region_name)
        try:
            get_secret_value_response = client.get_secret_value(SecretId=secret_name)
            if "SecretString" in get_secret_value_response:
                return json.loads(get_secret_value_response["SecretString"])
        except ClientError as e:
            logger.error(f"Failed to retrieve secret from Secrets Manager: {e.response['Error']['Code']}")
            raise

    # Fallback to Lambda environment variables
    logger.info("Using database configuration from Lambda environment variables.")
    return {
        "host": os.environ.get("DB_HOST", "localhost"),
        "user": os.environ.get("DB_USER", "admin"),
        "password": os.environ.get("DB_PASSWORD", ""),
        "database": os.environ.get("DB_NAME", "attendance_system"),
        "port": int(os.environ.get("DB_PORT", 3306)),
    }


def calculate_reporting_period(event: Dict[str, Any]) -> Tuple[date, date, str]:
    """
    Determine start date, end date, and period label.
    Supports manual overrides passed via test event JSON:
    {"start_date": "2026-09-01", "end_date": "2026-09-30"}
    Default: Previous calendar month.
    """
    if "start_date" in event and "end_date" in event:
        start_date = datetime.strptime(event["start_date"], "%Y-%m-%d").date()
        end_date = datetime.strptime(event["end_date"], "%Y-%m-%d").date()
        period_label = f"{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"
        return start_date, end_date, period_label

    today = date.today()
    # First day of current month
    first_current_month = date(today.year, today.month, 1)
    # Last day of previous month
    end_date = first_current_month - timedelta(days=1)
    # First day of previous month
    start_date = date(end_date.year, end_date.month, 1)
    period_label = start_date.strftime("%Y-%m")
    return start_date, end_date, period_label


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda entry point invoked by EventBridge Scheduler.
    """
    logger.info("Starting automated attendance export job...")
    logger.info(f"Event payload received: {json.dumps(event)}")

    start_date, end_date, period_label = calculate_reporting_period(event)
    logger.info(f"Processing attendance data for period: {start_date} to {end_date} ({period_label})")

    s3_bucket = os.environ.get("S3_BUCKET_NAME")
    if not s3_bucket:
        err_msg = "Configuration error: S3_BUCKET_NAME environment variable is required."
        logger.error(err_msg)
        return {"statusCode": 500, "body": json.dumps({"error": err_msg})}

    # Connect to RDS MySQL
    db_config = get_db_credentials()
    connection = None

    try:
        connection = pymysql.connect(
            host=db_config["host"],
            user=db_config["user"],
            password=db_config["password"],
            database=db_config["database"],
            port=int(db_config.get("port", 3306)),
            connect_timeout=10,
            cursorclass=pymysql.cursors.DictCursor,
        )
        logger.info(f"Successfully connected to RDS MySQL at {db_config['host']}")

        # Query all attendance records for the reporting period
        query = """
            SELECT 
                s.session_date,
                c.code AS class_code,
                c.name AS class_name,
                s.session_name,
                st.student_id,
                st.name AS student_name,
                st.email AS student_email,
                ar.status,
                COALESCE(ar.remarks, '') AS remarks,
                ar.recorded_at
            FROM attendance_records ar
            INNER JOIN attendance_sessions s ON ar.attendance_session_id = s.id
            INNER JOIN classes c ON s.class_id = c.id
            INNER JOIN students st ON ar.student_id = st.id
            WHERE s.session_date >= %s AND s.session_date <= %s
              AND s.status = 'completed'
            ORDER BY s.session_date ASC, c.code ASC, st.name ASC;
        """

        with connection.cursor() as cursor:
            cursor.execute(query, (start_date, end_date))
            rows = cursor.fetchall()

        record_count = len(rows)
        logger.info(f"Retrieved {record_count} attendance records from database for period {period_label}.")

        # Generate CSV payload
        csv_buffer = io.StringIO()
        fieldnames = [
            "Session Date",
            "Class Code",
            "Class Name",
            "Session Name",
            "Student ID",
            "Student Name",
            "Student Email",
            "Status",
            "Remarks",
            "Recorded At",
        ]
        writer = csv.writer(csv_buffer, lineterminator="\n")
        writer.writerow(fieldnames)

        for row in rows:
            writer.writerow([
                row["session_date"].isoformat(),
                row["class_code"],
                row["class_name"],
                row["session_name"],
                row["student_id"],
                row["student_name"],
                row["student_email"],
                row["status"].upper(),
                row["remarks"],
                row["recorded_at"].strftime("%Y-%m-%d %H:%M:%S") if row["recorded_at"] else "",
            ])

        csv_content = csv_buffer.getvalue().encode("utf-8")

        # Construct S3 Object Key: attendance-exports/YYYY/MM/monthly_attendance_export_YYYY_MM.csv
        timestamp_str = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        s3_key = f"attendance-exports/{start_date.strftime('%Y/%m')}/monthly_attendance_export_{period_label}_{timestamp_str}.csv"

        # Check for duplicate prevention if idempotent flag set
        s3_client = boto3.client("s3")
        
        # Upload with Server-Side Encryption (AES256)
        logger.info(f"Uploading export to s3://{s3_bucket}/{s3_key}")
        s3_client.put_object(
            Bucket=s3_bucket,
            Key=s3_key,
            Body=csv_content,
            ContentType="text/csv",
            ServerSideEncryption="AES256",
            Metadata={
                "ReportingPeriod": period_label,
                "StartDate": start_date.isoformat(),
                "EndDate": end_date.isoformat(),
                "RecordCount": str(record_count),
                "GeneratedBy": "AWS-Lambda-Scheduled-Export",
            },
        )

        success_response = {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Monthly attendance export completed successfully.",
                "bucket": s3_bucket,
                "s3_key": s3_key,
                "reporting_period": period_label,
                "record_count": record_count,
                "size_bytes": len(csv_content),
            }),
        }
        logger.info(f"Scheduled export execution succeeded: {success_response}")
        return success_response

    except pymysql.MySQLError as db_err:
        logger.error(f"Database error executing export query: {db_err}")
        return {"statusCode": 500, "body": json.dumps({"error": f"Database failure: {str(db_err)}"})}
    except ClientError as s3_err:
        logger.error(f"Amazon S3 error uploading export: {s3_err}")
        return {"statusCode": 500, "body": json.dumps({"error": f"S3 upload failure: {str(s3_err)}"})}
    except Exception as general_err:
        logger.error(f"Unexpected error in lambda execution: {general_err}")
        return {"statusCode": 500, "body": json.dumps({"error": str(general_err)})}
    finally:
        if connection and connection.open:
            connection.close()
            logger.info("Database connection closed.")
