from datetime import datetime, date
from . import db


class AttendanceSession(db.Model):
    """Represents a specific attendance event/session for a class on a date."""
    __tablename__ = "attendance_sessions"

    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey("classes.id", ondelete="RESTRICT"), nullable=False, index=True)
    session_date = db.Column(db.Date, nullable=False, index=True, default=date.today)
    session_name = db.Column(db.String(50), nullable=False, default="Regular Session")
    status = db.Column(db.String(20), default="completed", nullable=False)  # 'completed', 'cancelled'
    created_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("class_id", "session_date", "session_name", name="uq_class_date_session"),
    )

    # Relationships
    classroom = db.relationship("Class", back_populates="attendance_sessions")
    creator = db.relationship("User", back_populates="attendance_sessions")
    records = db.relationship(
        "AttendanceRecord",
        back_populates="session",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    @property
    def summary(self):
        """Returns counts of present, absent, late records."""
        counts = {"present": 0, "absent": 0, "late": 0, "total": len(self.records)}
        for r in self.records:
            if r.status in counts:
                counts[r.status] += 1
        return counts

    @property
    def attendance_percentage(self) -> float:
        """Percentage of present (+ optionally late counted per policy)."""
        total = len(self.records)
        if total == 0:
            return 0.0
        # Standard: Present = 1.0, Late = 1.0 or 0.5 (configurable, defaults to Present count)
        present = sum(1 for r in self.records if r.status in ("present", "late"))
        return round((present / total) * 100, 1)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "class_id": self.class_id,
            "class_name": self.classroom.name if self.classroom else None,
            "session_date": self.session_date.isoformat() if self.session_date else None,
            "session_name": self.session_name,
            "status": self.status,
            "created_by": self.creator.full_name if self.creator else None,
            "summary": self.summary,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<AttendanceSession class_id={self.class_id} date={self.session_date} name={self.session_name}>"


class AttendanceRecord(db.Model):
    """Individual student status for a specific attendance session."""
    __tablename__ = "attendance_records"

    id = db.Column(db.Integer, primary_key=True)
    attendance_session_id = db.Column(
        db.Integer,
        db.ForeignKey("attendance_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_id = db.Column(
        db.Integer,
        db.ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status = db.Column(db.String(20), nullable=False, default="present")  # 'present', 'absent', 'late'
    remarks = db.Column(db.String(255), nullable=True)
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("attendance_session_id", "student_id", name="uq_session_student"),
    )

    # Relationships
    session = db.relationship("AttendanceSession", back_populates="records")
    student = db.relationship("Student", back_populates="attendance_records")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "session_id": self.attendance_session_id,
            "student_id": self.student_id,
            "student_name": self.student.name if self.student else None,
            "student_code": self.student.student_id if self.student else None,
            "status": self.status,
            "remarks": self.remarks,
            "recorded_at": self.recorded_at.isoformat() if self.recorded_at else None,
        }

    def __repr__(self) -> str:
        return f"<AttendanceRecord session={self.attendance_session_id} student={self.student_id} status={self.status}>"
