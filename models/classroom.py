from datetime import datetime
from . import db


class Class(db.Model):
    """Classroom/Course model representing academic groups."""
    __tablename__ = "classes"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(32), unique=True, nullable=False, index=True)
    academic_year = db.Column(db.String(20), nullable=False)  # e.g. '2025-2026'
    teacher_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    teacher = db.relationship("User", back_populates="classes_taught")
    enrollments = db.relationship(
        "Enrollment",
        back_populates="classroom",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    attendance_sessions = db.relationship(
        "AttendanceSession",
        back_populates="classroom",
        lazy="dynamic",
    )

    @property
    def student_count(self) -> int:
        """Count of active students enrolled in this class."""
        return sum(1 for e in self.enrollments if e.status == "active")

    @property
    def enrolled_students(self):
        """List of active Student objects in this class."""
        return [
            e.student
            for e in self.enrollments
            if e.status == "active" and e.student
        ]

    def has_attendance_sessions(self) -> bool:
        """Check if any attendance sessions have been logged for this class."""
        return self.attendance_sessions.count() > 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "code": self.code,
            "academic_year": self.academic_year,
            "teacher_id": self.teacher_id,
            "teacher_name": self.teacher.full_name if self.teacher else "Unassigned",
            "student_count": self.student_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<Class {self.code} - {self.name}>"


class Enrollment(db.Model):
    """Association model linking Students to Classes with enrollment metadata."""
    __tablename__ = "enrollments"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    class_id = db.Column(db.Integer, db.ForeignKey("classes.id", ondelete="CASCADE"), nullable=False, index=True)
    enrolled_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    status = db.Column(db.String(20), default="active", nullable=False)  # 'active', 'dropped'

    __table_args__ = (
        db.UniqueConstraint("student_id", "class_id", name="uq_student_class"),
    )

    # Relationships
    student = db.relationship("Student", back_populates="enrollments")
    classroom = db.relationship("Class", back_populates="enrollments")

    def __repr__(self) -> str:
        return f"<Enrollment student={self.student_id} class={self.class_id}>"
