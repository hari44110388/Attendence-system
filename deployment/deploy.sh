#!/usr/bin/env bash
# ==============================================================================
# AttendanceSystem - Automated EC2 Ubuntu Deployment & Update Script
# ==============================================================================

set -euo pipefail

APP_DIR="/var/www/AttendanceSystem"
LOG_DIR="/var/log/attendance_system"
SERVICE_NAME="attendance.service"

echo "=========================================================="
echo " Starting AttendanceSystem EC2 Deployment Process"
echo "=========================================================="

# 1. Update OS Packages
echo "[1/7] Updating system packages..."
sudo apt-get update -y
sudo apt-get install -y python3 python3-pip python3-venv nginx git curl ufw

# 2. Setup Application Directory & Logs
echo "[2/7] Preparing directories..."
sudo mkdir -p "${APP_DIR}"
sudo mkdir -p "${LOG_DIR}"
sudo chown -R ubuntu:www-data "${APP_DIR}"
sudo chown -R ubuntu:www-data "${LOG_DIR}"

# 3. Setup Python Virtual Environment
echo "[3/7] Setting up Python virtual environment..."
cd "${APP_DIR}"
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi

# 4. Install Dependencies
echo "[4/7] Installing application dependencies..."
"${APP_DIR}/.venv/bin/pip" install --upgrade pip
"${APP_DIR}/.venv/bin/pip" install -r requirements.txt

# 5. Initialize Database Schema
echo "[5/7] Initializing database tables..."
"${APP_DIR}/.venv/bin/flask" init-db
"${APP_DIR}/.venv/bin/flask" seed-db || true

# 6. Configure Systemd Service
echo "[6/7] Configuring systemd attendance service..."
sudo cp deployment/attendance.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable "${SERVICE_NAME}"
sudo systemctl restart "${SERVICE_NAME}"

# 7. Configure Nginx Reverse Proxy
echo "[7/7] Configuring Nginx reverse proxy..."
sudo cp deployment/nginx.conf /etc/nginx/sites-available/attendance
sudo ln -sf /etc/nginx/sites-available/attendance /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx

echo "=========================================================="
echo " AttendanceSystem Deployment Finished Successfully!"
echo " Check service status with: sudo systemctl status ${SERVICE_NAME}"
echo " Check logs: sudo tail -f ${LOG_DIR}/gunicorn_error.log"
echo "=========================================================="
