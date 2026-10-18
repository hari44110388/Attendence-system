from datetime import date
from services import ReportService
from models import db, Enrollment, AttendanceSession, AttendanceRecord


def test_attendance_percentage_zero_sessions():
    """Verify zero sessions returns 0.0 without ZeroDivisionError."""
    pct = ReportService.calculate_attendance_percentage(
        present_count=0, late_count=0, total_sessions=0
    )
    assert pct == 0.0


def test_attendance_percentage_calculation():
    """Verify standard percentage formula."""
    # 8 present out of 10 sessions -> 80.0%
    pct = ReportService.calculate_attendance_percentage(
        present_count=8, late_count=0, total_sessions=10
    )
    assert pct == 80.0

    # 7 present, 1 late (late counts as present) out of 10 sessions -> 80.0%
    pct_with_late = ReportService.calculate_attendance_percentage(
        present_count=7, late_count=1, total_sessions=10
    )
    assert pct_with_late == 80.0


def test_generate_csv_string():
    """Verify CSV string generation formats correctly."""
    headers = ["ID", "Name", "Score"]
    rows = [["1", "Alice", "95%"], ["2", "Bob", "80%"]]
    csv_str = ReportService.generate_csv(headers, rows)
    assert "ID,Name,Score" in csv_str
    assert "1,Alice,95%" in csv_str
    assert "2,Bob,80%" in csv_str


def test_export_csv_browser_download(auth_teacher, sample_class, sample_student, app):
    """Verify CSV export route returns downloadable attachment."""
    with app.app_context():
        # Create an attendance session
        sess = AttendanceSession(
            class_id=sample_class,
            session_date=date.today(),
            session_name="Lecture 1",
            status="completed",
        )
        db.session.add(sess)
        db.session.flush()

        rec = AttendanceRecord(
            attendance_session_id=sess.id,
            student_id=sample_student,
            status="present",
            remarks="Present",
        )
        db.session.add(rec)
        db.session.commit()

    today_str = date.today().isoformat()
    response = auth_teacher.get(
        f"/reports/export/csv?type=daily&destination=browser&date={today_str}&class_id={sample_class}"
    )
    assert response.status_code == 200
    assert "text/csv" in response.headers.get("Content-Type", "")
    assert "attachment" in response.headers.get("Content-Disposition", "")
    assert b"PRESENT" in response.data
