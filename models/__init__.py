from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from .user import User
from .student import Student
from .classroom import Class, Enrollment
from .attendance import AttendanceSession, AttendanceRecord

__all__ = [
    "db",
    "User",
    "Student",
    "Class",
    "Enrollment",
    "AttendanceSession",
    "AttendanceRecord",
]
