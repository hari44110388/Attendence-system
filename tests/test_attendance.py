from datetime import date
from models import db, Enrollment, AttendanceSession, AttendanceRecord
from services import AttendanceService


def test_record_attendance_service(app, sample_class, sample_student):
    """Test AttendanceService transactionally logging attendance."""
    with app.app_context():
        # Enroll student in class
        e = Enrollment(student_id=sample_student, class_id=sample_class, status="active")
        db.session.add(e)
        db.session.commit()

        student_records = [
            {"student_id": sample_student, "status": "present", "remarks": "On time"}
        ]
        success, msg, session = AttendanceService.record_attendance(
            class_id=sample_class,
            session_date=date.today(),
            session_name="Lecture 1",
            student_records=student_records,
        )

        assert success is True
        assert session is not None
        assert len(session.records) == 1
        assert session.records[0].status == "present"
        assert session.records[0].remarks == "On time"


def test_update_existing_attendance_session(app, sample_class, sample_student):
    """Test modifying existing attendance record without creating duplicate session."""
    with app.app_context():
        e = Enrollment(student_id=sample_student, class_id=sample_class, status="active")
        db.session.add(e)
        db.session.commit()

        # Initial record: Present
        AttendanceService.record_attendance(
            class_id=sample_class,
            session_date=date.today(),
            session_name="Lecture 1",
            student_records=[{"student_id": sample_student, "status": "present", "remarks": ""}],
        )

        # Update record to: Late
        success, msg, session = AttendanceService.record_attendance(
            class_id=sample_class,
            session_date=date.today(),
            session_name="Lecture 1",
            student_records=[{"student_id": sample_student, "status": "late", "remarks": "Traffic delay"}],
        )

        assert success is True
        # Total sessions for class and date must still be exactly 1
        sessions = AttendanceSession.query.filter_by(
            class_id=sample_class, session_date=date.today()
        ).all()
        assert len(sessions) == 1
        assert session.records[0].status == "late"
        assert session.records[0].remarks == "Traffic delay"


def test_take_attendance_route(auth_teacher, sample_class, sample_student, app):
    """Verify HTTP POST route marks student attendance."""
    with app.app_context():
        e = Enrollment(student_id=sample_student, class_id=sample_class, status="active")
        db.session.add(e)
        db.session.commit()

    today_str = date.today().isoformat()
    response = auth_teacher.post(
        "/attendance/take",
        data={
            "class_id": sample_class,
            "session_date": today_str,
            "session_name": "Period 1",
            f"status_{sample_student}": "present",
            f"remarks_{sample_student}": "Participated well",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Attendance logged successfully" in response.data or b"Attendance History" in response.data
