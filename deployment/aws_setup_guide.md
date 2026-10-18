# Complete AWS Cloud Setup & Deployment Guide: AttendanceSystem

This guide walks you through deploying **AttendanceSystem** into a production AWS environment utilizing **Amazon EC2**, **Amazon RDS (MySQL)**, **Amazon S3**, and **AWS Lambda**.

---

## Architecture Diagram

```
Internet Users (Admins & Teachers)
          |
          | HTTPS (Port 443)
          v
   +--------------+
   |  Amazon EC2  | (Public Subnet)
   |  (Nginx +    |
   |   Gunicorn + |
   |   Flask App) |
   +-------+------+
           |
           | Port 3306 (Private VPC traffic only)
           v
   +--------------+
   |  Amazon RDS  | (Private DB Subnet)
   |  (MySQL 8.0) |
   +-------+------+
           ^
           | Query via VPC
           |
   +-------+------+       Upload Encrypted CSV       +----------------+
   |  AWS Lambda  | -------------------------------> |   Amazon S3    |
   |  (Scheduled  |                                  | (Private Bucket|
   |   Exporter)  |                                  |   AES-256)     |
   +-------+------+                                  +----------------+
           ^
           | Monthly Trigger (Cron)
   +-------+------+
   | EventBridge  |
   +--------------+
```

---

## Step 1: Virtual Private Cloud (VPC) & Security Groups

### 1.1 VPC Architecture
- Create a VPC `10.0.0.0/16` with:
  - 2 Public Subnets: `10.0.1.0/24` (AZ-a), `10.0.2.0/24` (AZ-b)
  - 2 Private Subnets: `10.0.11.0/24` (AZ-a), `10.0.12.0/24` (AZ-b)
  - Internet Gateway (IGW) attached to Public Subnets.

### 1.2 Security Groups (Least-Privilege Isolation)
1. **EC2 Security Group (`attendance-ec2-sg`)**:
   - Inbound:
     - `HTTP` (TCP 80) from `0.0.0.0/0`
     - `HTTPS` (TCP 443) from `0.0.0.0/0`
     - `SSH` (TCP 22) from your administrative IP only (`x.x.x.x/32`)
   - Outbound: All traffic (`0.0.0.0/0`).

2. **RDS Security Group (`attendance-rds-sg`)**:
   - Inbound:
     - `MySQL/Aurora` (TCP 3306) with source set to **`attendance-ec2-sg`** (and `attendance-lambda-sg` if Lambda is in VPC).
     - **CRITICAL:** Do NOT allow `0.0.0.0/0`. MySQL is never exposed to the internet.
   - Outbound: None needed.

3. **Lambda Security Group (`attendance-lambda-sg`)**:
   - Inbound: None.
   - Outbound: All traffic (or VPC Endpoint for S3).

---

## Step 2: Amazon RDS (MySQL) Provisioning

1. Navigate to **RDS** &rarr; **Databases** &rarr; **Create database**.
2. **Engine:** MySQL (Community Edition 8.0 or later).
3. **Template:** Free tier or Production (Multi-AZ for high availability).
4. **Settings:**
   - DB instance identifier: `attendance-db-prod`
   - Master username: `admin`
   - Master password: `Use_A_Strong_Generated_Password_32_chars`
5. **Instance Configuration:** `db.t3.micro` or `db.t4g.micro`.
6. **Connectivity:**
   - VPC: Select your custom VPC.
   - Subnet group: Private Subnets.
   - Public access: **No** (Private).
   - VPC security group: Choose `attendance-rds-sg`.
7. **Initial Database Name:** `attendance_system`.
8. Once created, copy the **RDS Endpoint**:
   `attendance-db-prod.c1234567890.us-east-1.rds.amazonaws.com`

---

## Step 3: Amazon S3 Bucket Configuration

1. Navigate to **S3** &rarr; **Create bucket**.
2. **Bucket name:** `attendancesystem-exports-prod-<your-account-id>` (Must be globally unique).
3. **Region:** Same as EC2/RDS (`us-east-1`).
4. **Block Public Access:** **Enable "Block ALL public access"** (Keep bucket strictly private).
5. **Default Encryption:** Enable Server-Side Encryption (`SSE-S3` or `SSE-KMS`).
6. **Object Ownership:** Bucket owner preferred.
7. Click **Create bucket**.

---

## Step 4: IAM Role for Amazon EC2 Instance

Avoid hardcoding AWS keys inside `.env` on EC2! Instead, use an IAM Instance Profile:

1. Navigate to **IAM** &rarr; **Roles** &rarr; **Create role**.
2. Trusted entity type: **AWS Service** &rarr; Use case: **EC2**.
3. Attach Policy: Create an inline policy named `EC2AttendanceS3Policy`:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowS3ExportOperations",
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject"
      ],
      "Resource": "arn:aws:s3:::attendancesystem-exports-prod-*/*"
    }
  ]
}
```
4. Role Name: `AttendanceEC2Role`.
5. Attach this role to your EC2 instance: **EC2 Console** &rarr; **Actions** &rarr; **Security** &rarr; **Modify IAM role**.

---

## Step 5: EC2 Server Provisioning & Application Deployment

1. Launch an EC2 Instance:
   - AMI: **Ubuntu Server 24.04 LTS (HVM)**
   - Instance Type: `t3.micro` or `t3.small`
   - Key pair: Choose or create your `.pem` key
   - Network settings: Select your VPC, a **Public Subnet**, and assign `attendance-ec2-sg`.
   - Auto-assign public IP: **Enable**.

2. Connect via SSH:
```bash
ssh -i "your-key.pem" ubuntu@<EC2_PUBLIC_IP>
```

3. Clone or copy the application code into `/var/www/AttendanceSystem`:
```bash
sudo mkdir -p /var/www/AttendanceSystem
sudo chown -R ubuntu:ubuntu /var/www/AttendanceSystem
cd /var/www/AttendanceSystem
# Copy project files here using git or scp
```

4. Create the Production `.env` file:
```bash
nano /var/www/AttendanceSystem/.env
```
Populate with production values:
```ini
FLASK_APP=app.py
FLASK_ENV=production
SECRET_KEY=9f8c3a1b2d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0
PORT=8000

DB_ENGINE=mysql
DB_USER=admin
DB_PASSWORD=YourRDSMasterPassword
DB_HOST=attendance-db-prod.c1234567890.us-east-1.rds.amazonaws.com
DB_PORT=3306
DB_NAME=attendance_system

AWS_REGION=us-east-1
S3_BUCKET_NAME=attendancesystem-exports-prod-<your-account-id>
S3_PRESIGNED_EXPIRATION=3600
```

5. Run the automated deployment script:
```bash
chmod +x deployment/deploy.sh
./deployment/deploy.sh
```

---

## Step 6: HTTPS Setup with Let's Encrypt (Certbot)

1. Ensure your domain name has an **A Record** pointing to your EC2 Public IP address.
2. Install Certbot:
```bash
sudo apt-get install -y certbot python3-certbot-nginx
```
3. Issue TLS Certificate:
```bash
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```
4. Test automated renewal:
```bash
sudo certbot renew --dry-run
```

---

## Step 7: Application Logs & Troubleshooting

- **Check systemd service status:**
  ```bash
  sudo systemctl status attendance.service
  ```
- **Inspect live application logs:**
  ```bash
  sudo journalctl -u attendance.service -f
  ```
- **Inspect Gunicorn error logs:**
  ```bash
  tail -f /var/log/attendance_system/gunicorn_error.log
  ```
- **Inspect Nginx logs:**
  ```bash
  tail -f /var/log/nginx/error.log
  ```
- **Test Database Connectivity from EC2:**
  ```bash
  python3 -c "import pymysql; conn = pymysql.connect(host='<RDS_ENDPOINT>', user='admin', password='<PASSWORD>'); print('RDS Connected Successfully!')"
  ```
