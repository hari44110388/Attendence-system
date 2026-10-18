from .auth import auth_bp
from .dashboard import dashboard_bp
from .students import students_bp
from .classes import classes_bp
from .attendance import attendance_bp
from .reports import reports_bp

__all__ = [
    "auth_bp",
    "dashboard_bp",
    "students_bp",
    "classes_bp",
    "attendance_bp",
    "reports_bp",
]
