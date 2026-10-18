# AWS Lambda Automated Attendance Export

This component provides a serverless cron job that automatically exports completed attendance records from **Amazon RDS (MySQL)** into a private, encrypted **Amazon S3** bucket on the 1st of every month.

---

## 1. Architecture Overview

```
+-----------------------------------+
|  Amazon EventBridge Scheduler     |  (Cron: 0 0 1 * ? * - 1st of month)
+-----------------+-----------------+
                  | (Invoke)
                  v
+-----------------+-----------------+
|     AWS Lambda Function           |
| (Python 3.12/3.13 Runtime in VPC) |
+--------+-------------------+------+
         | (1. Read Secrets) | (2. Query Data)
         v                   v
+--------+---------+  +------+------+
| Secrets Manager  |  | Amazon RDS  |
| (DB Credentials) |  |   (MySQL)   |
+------------------+  +------+------+
                             |
                   (3. Put Encrypted CSV)
                             v
                      +------+------+
                      |  Amazon S3  |
                      |   Bucket    |
                      +-------------+
```

---

## 2. Prerequisites & Environment Variables

| Variable | Description | Example Value |
|---|---|---|
| `S3_BUCKET_NAME` | Destination S3 Bucket | `attendancesystem-exports-bucket` |
| `DB_SECRET_NAME` | AWS Secrets Manager secret ID | `production/attendance-system/db` |
| `AWS_REGION` | AWS Region | `us-east-1` |
| `DB_HOST` | RDS Endpoint (if not using Secrets Manager) | `attendance-db.c123.rds.amazonaws.com` |
| `DB_USER` | RDS MySQL Master Username | `admin` |
| `DB_PASSWORD` | RDS MySQL Password | `YourSecurePassword` |
| `DB_NAME` | Database Name | `attendance_system` |
| `DB_PORT` | MySQL Port | `3306` |

---

## 3. VPC & Network Setup

When Amazon RDS resides in private subnets, configure the Lambda function with **VPC Connectivity**:

1. **VPC:** Select the same VPC where Amazon RDS is deployed.
2. **Subnets:** Select at least 2 Private Subnets with DB access.
3. **Security Groups:** 
   - Assign a Lambda Security Group (`sg-lambda-export`).
   - Add an Inbound Rule in the RDS Security Group (`sg-rds-mysql`):
     - **Type:** MySQL/Aurora (Port 3306)
     - **Source:** Security group ID of Lambda (`sg-lambda-export`).
4. **S3 Access:** Add an **S3 VPC Gateway Endpoint** (`com.amazonaws.<region>.s3`) attached to your VPC route tables so Lambda can communicate with Amazon S3 directly without requiring a NAT Gateway!

---

## 4. Least-Privilege IAM Execution Role

Create an IAM Role named `AttendanceExportLambdaRole` with the following policy attachments:

1. **AWSLambdaVPCAccessExecutionRole** (Allows ENI creation in your VPC).
2. **Inline Policy: `AttendanceS3AndSecretsPolicy`**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowS3ExportUpload",
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:PutObjectAcl"
      ],
      "Resource": "arn:aws:s3:::attendancesystem-exports-bucket/attendance-exports/*"
    },
    {
      "Sid": "AllowSecretsManagerRead",
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:*:*:secret:production/attendance-system/db*"
    }
  ]
}
```

---

## 5. Build & Packaging Instructions

### Option A: Create a Deployment Package (Zip)

```bash
# On your local Linux terminal or EC2:
mkdir -p package
pip install -r requirements.txt -t package/
cp lambda_function.py package/
cd package
zip -r ../attendance_export_lambda.zip .
cd ..
```

### Option B: Deploy via AWS CLI

```bash
aws lambda create-function \
  --function-name AttendanceMonthlyExport \
  --runtime python3.12 \
  --role arn:aws:iam::123456789012:role/AttendanceExportLambdaRole \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://attendance_export_lambda.zip \
  --timeout 60 \
  --memory-size 256 \
  --environment "Variables={S3_BUCKET_NAME=attendancesystem-exports-bucket,DB_SECRET_NAME=production/attendance-system/db}"
```

---

## 6. Configuring Amazon EventBridge Scheduler

1. In the AWS Management Console, open **Amazon EventBridge** &rarr; **Schedules**.
2. Click **Create Schedule**:
   - **Name:** `MonthlyAttendanceExportSchedule`
   - **Schedule pattern:** Recurring schedule
   - **Cron expression:** `0 0 1 * ? *` (Midnight on the 1st day of every month, UTC)
   - **Flexible time window:** Off (or 15 minutes)
3. **Target:** AWS Lambda &rarr; Choose `AttendanceMonthlyExport`.
4. Save schedule.

---

## 7. Manual Testing & Verification

### Test in AWS Lambda Console

Create a manual test event:

**Default Previous Month Export Test Event:**
```json
{}
```

**Custom Date Range Test Event:**
```json
{
  "start_date": "2026-09-01",
  "end_date": "2026-09-30"
}
```

### Verification in Amazon S3
1. Open the Amazon S3 Console.
2. Navigate to bucket: `attendancesystem-exports-bucket`.
3. Check the folder: `attendance-exports/2026/09/`.
4. Verify file name: `monthly_attendance_export_2026-09_<timestamp>.csv`.
5. Check file properties: Server-Side Encryption must show `SSE-S3 (AES-256)`.
