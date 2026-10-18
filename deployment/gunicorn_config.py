import multiprocessing

# Gunicorn WSGI Server Production Configuration

bind = "127.0.0.1:8000"
workers = multiprocessing.cpu_count() * 2 + 1
threads = 2
worker_class = "gthread"
timeout = 120
keepalive = 5
max_requests = 1000
max_requests_jitter = 50

# Security
limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8190

# Logging
accesslog = "/var/log/attendance_system/gunicorn_access.log"
errorlog = "/var/log/attendance_system/gunicorn_error.log"
loglevel = "info"
