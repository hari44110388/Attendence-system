# AttendanceSystem - Student Attendance Management System

[![Python Version](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/framework-Flask%203.x-lightgrey.svg)](https://palletsprojects.com/p/flask/)
[![Frontend](https://img.shields.io/badge/frontend-Bootstrap%205.3-purple.svg)](https://getbootstrap.com/)
[![Database](https://img.shields.io/badge/database-MySQL%208.0%20%7C%20Amazon%20RDS-orange.svg)](https://aws.amazon.com/rds/)
[![Cloud](https://img.shields.io/badge/cloud-AWS%20(EC2%20%7C%20RDS%20%7C%20S3%20%7C%20Lambda)-232f3e.svg)](https://aws.amazon.com/)
[![Tests](https://img.shields.io/badge/tests-22%20passed-success.svg)](https://docs.pytest.org/)

An enterprise-ready, beginner-friendly web application for managing academic classes, student enrollments, daily roll-calls, and attendance compliance reporting, featuring native integration with **Amazon Web Services (EC2, RDS, S3, Lambda, EventBridge)**.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Key Features](#2-key-features)
3. [System Architecture](#3-system-architecture)
4. [Technology Stack](#4-technology-stack)
5. [Local Development & Setup](#5-local-development--setup)
6. [Initial Accounts & Seeding](#6-initial-accounts--seeding)
7. [Running Tests](#7-running-tests)
8. [AWS Production Deployment](#8-aws-production-deployment)
   - [Amazon EC2 Setup](#amazon-ec2-setup)
   - [Amazon RDS (MySQL) Integration](#amazon-rds-mysql-integration)
   - [Amazon S3 Private Bucket Exports](#amazon-s3-private-bucket-exports)
   - [AWS Lambda Scheduled Exporter](#aws-lambda-scheduled-exporter)
9. [Configuration & Environment Variables](#9-configuration--environment-variables)
10. [Attendance Calculation Formula & Policies](#10-attendance-calculation-formula--policies)
11. [AWS Cost Estimation](#11-aws-cost-estimation)
12. [Troubleshooting](#12-troubleshooting)

---

## 1. Project Overview

**AttendanceSystem** addresses the administrative inefficiencies and data inaccuracies of traditional paper-based roll-calls in universities and colleges. Built with a modular Flask backend and responsive Bootstrap 5 interface, it empowers academic administrators and teachers to:
- Organize classes and multi-course enrollments.
- Log daily attendance sessions (Present, Absent, Late) with atomic database transactions.
- Prevent duplicate records and accidental or invalid deletions.
- Generate daily, class-level, and student-level compliance reports.
- Automatically export encrypted CSV reports to Amazon S3 via serverless cron jobs.

---

## 2. Key Features

- **Role-Based Access Control (RBAC):** Distinct permissions for `Admin` (full system configuration, user/class/student CRUD) and `Teacher` (attendance marking, class roster viewing, student reports).
- **Interactive Attendance Sheet:** Single-click batch toggles (*All Present*, *All Late*, *All Absent*) with individual remarks per student.
- **Dynamic Analytics Dashboard:** Live calculation of active students, courses, total sessions conducted, today's attendance percentage, and monthly compliance metrics.
- **Data Integrity & Relational Safety:** Database foreign key constraints, composite unique constraints (`uq_class_date_session`, `uq_session_student`), and deletion guardrails preventing removal of classes containing recorded attendance sessions.
- **Dual Export Strategy:** Direct in-browser streaming download or secure upload to private Amazon S3 with expiring presigned download URLs.
- **Serverless Monthly Automation:** AWS Lambda function triggered by Amazon EventBridge queries RDS and auto-archives monthly attendance to S3 without human intervention.
- **Security-First Architecture:** Passwords hashed with `Werkzeug` (Scrypt/PBKDF2), CSRF tokens enforced on all POST actions, rate limiting against brute-force login attempts, and strict separation of secrets.

---

## 3. System Architecture

```
[ Web Browser ]
      |
      | HTTPS (Port 443)
      v
+-----------------------------------------------------------+
| Amazon EC2 Instance (Ubuntu 24.04 LTS)                    |
|                                                           |
|   [ Nginx Reverse Proxy ]                                 |
|          | (Port 8000 Unix Socket / HTTP)                 |
|          v                                                |
|   [ Gunicorn WSGI Server ]                                |
|          |                                                |
|   [ Flask Application (AttendanceSystem) ]                |
|      - Blueprints: auth, dashboard, students,             |
|                    classes, attendance, reports           |
|      - Services: AttendanceService, ReportService,        |
|                  S3ExportService                          |
+-----------------------------+-----------------------------+
                              |
                              | Port 3306 (Private VPC Subnet)
                              v
             +---------------------------------+
             | Amazon RDS (MySQL 8.0)          |
             | Tables: users, classes,         |
             |         students, enrollments,  |
             |         attendance_sessions,    |
             |         attendance_records      |
             +----------------+----------------+
                              ^
                              | Queries via VPC
                              |
             +----------------+----------------+
             | AWS Lambda Scheduled Exporter   |
             | (Triggered Monthly by           |
             |  Amazon EventBridge Scheduler)  |
             +----------------+----------------+
                              |
                              | AES-256 Server-Side Encryption
                              v
             +---------------------------------+
             | Amazon S3 Private Bucket        |
             | Prefix: attendance-exports/     |
             +---------------------------------+
```

---

## 4. Technology Stack

| Layer | Technologies Used |
|---|---|
| **Frontend** | HTML5, CSS3, JavaScript (ES6+), Bootstrap 5.3, Bootstrap Icons, Google Fonts (Plus Jakarta Sans) |
| **Backend** | Python 3.11+, Flask 3.x, Flask-WTF, WTForms, Werkzeug Security |
| **ORM & DB Library**| Flask-SQLAlchemy 3.x, SQLAlchemy 2.x, PyMySQL |
| **Database** | MySQL 8.0 (Production Amazon RDS) / SQLite (Local Out-of-the-Box Development) |
| **Cloud Hosting** | Amazon EC2 (Ubuntu 24.04 LTS), Nginx, Gunicorn, Systemd |
| **Object Storage**| Amazon S3, Boto3 SDK, Server-Side Encryption (`AES256`), Presigned URLs |
| **Serverless Cron**| AWS Lambda, Amazon EventBridge Scheduler, AWS Secrets Manager |
| **Testing** | Pytest, Pytest-Flask |

---

## 5. Local Development & Setup

### 5.1 Prerequisites
- Python 3.10+ (Python 3.11, 3.12, or 3.13 supported)
- Git

### 5.2 Step-by-Step Installation

1. **Clone or navigate to the repository:**
   ```bash
   cd "c:\attendence system"
   ```

2. **Create and activate a virtual environment:**
   - **Windows (PowerShell):**
     ```powershell
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```
   - **Linux / macOS:**
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables:**
   A development `.env` is pre-configured for local instant running with SQLite. To customize or switch to local MySQL:
   ```bash
   cp .env.example .env
   ```

5. **Initialize Database Tables & Seed Sample Data:**
   ```bash
   flask init-db
   flask seed-db
   ```

6. **Start the local server:**
   ```bash
   python app.py
   ```
   Open your browser at `http://127.0.0.1:5000`.

---

## 6. Initial Accounts & Seeding

The application comes with pre-configured demo credentials generated during `flask seed-db`:

| Role | Username | Password | Email |
|---|---|---|---|
| **System Admin** | `admin` | `Admin@123` | `admin@attendance.edu` |
| **Teacher 1** | `prof.sharma` | `Teacher@123` | `sharma@attendance.edu` |
| **Teacher 2** | `dr.anita` | `Teacher@123` | `anita@attendance.edu` |

> [!NOTE]
> On the login page, you can click the **Demo Credentials** buttons for one-click autofill!

### Securely Creating Additional Administrators via CLI
To create a new administrator account without exposing credentials:
```bash
flask create-admin
```
Follow the interactive prompts (username, email, full name, hidden password confirmation).

---

## 7. Running Tests

The test suite validates authentication, role-based authorization, student CRUD, class CRUD, attendance marking, duplicate prevention constraints, percentage calculation formulas, and CSV downloads across 22 tests.

Run pytest using:
```bash
pytest -v
```

All tests execute against an isolated in-memory SQLite database (`TestingConfig`) to guarantee that development and production data are never affected.

---

## 8. AWS Production Deployment

### Amazon EC2 Setup

1. **Launch Instance:** Ubuntu Server 24.04 LTS on a `t3.micro` or `t3.small` instance in a public subnet.
2. **Security Group (`attendance-ec2-sg`):**
   - Inbound: Port 80 (HTTP), Port 443 (HTTPS), Port 22 (SSH from admin IP).
   - Outbound: All traffic (`0.0.0.0/0`).
3. **IAM Instance Profile:** Attach `AttendanceEC2Role` allowing `s3:PutObject` and `s3:GetObject` on your bucket (eliminates storing access keys in files).
4. **Deploy Application:**
   Run the automated deployment script provided in `deployment/deploy.sh`:
   ```bash
   chmod +x deployment/deploy.sh
   sudo ./deployment/deploy.sh
   ```
5. **Issue Free SSL/TLS Certificate via Certbot:**
   ```bash
   sudo apt-get install -y certbot python3-certbot-nginx
   sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
   ```

### Amazon RDS (MySQL) Integration

1. Create a MySQL 8.0 instance in private subnets with **Public Access: Disabled**.
2. **Security Group (`attendance-rds-sg`):**
   - Inbound: Port 3306 **only from `attendance-ec2-sg`** and `attendance-lambda-sg`.
3. In production `/var/www/AttendanceSystem/.env`:
   ```ini
   DB_ENGINE=mysql
   DB_USER=admin
   DB_PASSWORD=YourSecureRDSMasterPassword
   DB_HOST=attendance-db-prod.c1234567890.us-east-1.rds.amazonaws.com
   DB_PORT=3306
   DB_NAME=attendance_system
   ```
4. Run migrations/initialization on EC2:
   ```bash
   flask init-db
   ```

### Amazon S3 Private Bucket Exports

1. Create a private bucket: `attendancesystem-exports-prod-<account_id>`.
2. Enable **Block All Public Access** and **AES-256 Default Server-Side Encryption**.
3. Set `S3_BUCKET_NAME` in `.env`.
4. The application automatically stores CSV exports under the timestamped directory prefix:
   `attendance-exports/YYYY/MM/attendance_report_YYYYMMDD_HHMMSS.csv`
5. Reports can be downloaded via secure, temporary **presigned URLs** valid for 60 minutes.

### AWS Lambda Scheduled Exporter

The serverless exporter function is located in `lambda_function/`:
- **Code:** `lambda_function/lambda_function.py`
- **Dependencies:** `lambda_function/requirements.txt`
- **Trigger:** Amazon EventBridge Scheduler running recurring cron:
  `0 0 1 * ? *` (Midnight UTC on the 1st day of every month).
- **VPC Configuration:** Deploy Lambda into the VPC private subnets with an S3 VPC Gateway Endpoint to reach both RDS and S3 securely.

---

## 9. Configuration & Environment Variables

| Variable | Description | Default / Example |
|---|---|---|
| `FLASK_APP` | Application entry point | `app.py` |
| `FLASK_ENV` | Environment (`development` or `production`) | `development` |
| `SECRET_KEY` | Cryptographic secret for sessions & CSRF | 32+ byte random hex string |
| `PORT` | Local application port | `5000` |
| `DB_ENGINE` | Database type (`sqlite` or `mysql`) | `sqlite` |
| `DB_USER` | MySQL username | `admin` |
| `DB_PASSWORD` | MySQL password | Secret |
| `DB_HOST` | MySQL hostname or RDS endpoint | `localhost` / RDS endpoint |
| `DB_PORT` | MySQL port | `3306` |
| `DB_NAME` | MySQL database name | `attendance_system` |
| `AWS_REGION` | AWS Region for S3 and Lambda | `us-east-1` |
| `S3_BUCKET_NAME` | Target S3 bucket for exported reports | `attendancesystem-exports-bucket` |
| `S3_PRESIGNED_EXPIRATION`| Expiration seconds for S3 presigned links | `3600` (1 hour) |

---

## 10. Attendance Calculation Formula & Policies

### Standard Calculation
$$\text{Attendance Percentage} = \left( \frac{\text{Number of Present Sessions}}{\text{Total Applicable Sessions}} \right) \times 100$$

### Institutional Rules Implemented:
1. **Late Arrival Policy:** Late arrivals count as present toward total session attendance compliance, but late arrival frequency is tracked and reported distinctly in summary tables.
2. **Cancelled Sessions:** Sessions marked with status `cancelled` are strictly excluded from the calculation denominator.
3. **Enrollment Boundary:** Only sessions occurring during active student enrollment are counted as applicable.
4. **Division by Zero Protection:** When a class or student has 0 applicable sessions, the system safely returns `0.0%` without runtime errors.

---

## 11. AWS Cost Estimation

### Free Tier Eligible Configuration (Initial 12 Months)
- **EC2:** `t3.micro` or `t2.micro` (750 hours/month free) = **$0.00**
- **RDS:** `db.t3.micro` Single-AZ MySQL (750 hours/month, 20GB storage free) = **$0.00**
- **S3:** Standard Storage (5 GB, 20,000 GET, 2,000 PUT requests free) = **$0.00**
- **Lambda:** 1 million free invocations and 3.2 million seconds of compute time = **$0.00**
- **Estimated Total:** **$0.00 / month**

### Production Paid Estimate (After Free Tier or Scaled Usage)
- **EC2 `t3.small` (2 vCPU, 2GB RAM):** ~$15.00 / month
- **RDS `db.t3.small` Multi-AZ MySQL:** ~$30.00 / month
- **S3 Storage & Presigned Requests (10GB):** ~$0.25 / month
- **AWS Lambda & EventBridge:** ~$0.05 / month
- **Estimated Total:** **~$45.30 / month**

---

## 12. Troubleshooting

### 1. Database Connection Failure
- **Symptom:** `pymysql.err.OperationalError: Can't connect to MySQL server`
- **Fix:** Verify security group rules in `attendance-rds-sg`. Ensure port 3306 is open to `attendance-ec2-sg`. Test connectivity on EC2 via:
  ```bash
  nc -zv <RDS_ENDPOINT> 3306
  ```

### 2. S3 Access Denied
- **Symptom:** `botocore.exceptions.ClientError: An error occurred (AccessDenied) when calling the PutObject operation`
- **Fix:** Check that the EC2 instance has the `AttendanceEC2Role` IAM role attached and that the role policy explicitly allows `s3:PutObject` on `arn:aws:s3:::<your-bucket-name>/*`.

### 3. Service Fails to Start on EC2
- **Check service status and logs:**
  ```bash
  sudo systemctl status attendance.service
  sudo journalctl -u attendance.service -n 50 --no-pager
  tail -n 50 /var/log/attendance_system/gunicorn_error.log
  ```

---

## License

Developed for academic and institutional student attendance management. Licensed under the MIT License.
