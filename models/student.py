from datetime import datetime, date
from . import db


class Student(db.Model):
    """Student entity storing personal info, enrollment, and attendance records."""
    __tablename__ = "students"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(32), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(20), nullable=True)
    status = db.Column(db.String(20), default="active", nullable=False)  # 'active', 'inactive'
    enrollment_date = db.Column(db.Date, default=date.today, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    enrollments = db.relationship(
        "Enrollment",
        back_populates="student",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    attendance_records = db.relationship(
        "AttendanceRecord",
        back_populates="student",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    @property
    def active_classes(self):
        """Returns list of Class instances where student is actively enrolled."""
        return [
            enrollment.classroom
            for enrollment in self.enrollments
            if enrollment.status == "active" and enrollment.classroom
        ]

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "student_id": self.student_id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "status": self.status,
            "enrollment_date": self.enrollment_date.isoformat() if self.enrollment_date else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "classes": [c.name for c in self.active_classes],
        }

    def __repr__(self) -> str:
        return f"<Student {self.student_id} - {self.name}>"
