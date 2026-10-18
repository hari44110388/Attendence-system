import csv
import io
from datetime import date, datetime
from typing import Dict, List, Optional
from sqlalchemy import func
from models import db, AttendanceSession, AttendanceRecord, Student, Class, Enrollment


class ReportService:
    """Service to aggregate metrics, calculate attendance percentages, and generate CSV reports."""

    @staticmethod
    def calculate_attendance_percentage(present_count: int, late_count: int, total_sessions: int, late_weight: float = 1.0) -> float:
        """
        Attendance Percentage formula:
        (Number of Present Sessions + (late_weight * Late Sessions)) / Total Applicable Sessions * 100

        Default late_weight = 1.0: Late arrivals count as present toward total attendance
        while late arrivals are separately enumerated in summary columns.
        If total_sessions == 0, returns 0.0 to prevent division by zero.
        """
        if total_sessions <= 0:
            return 0.0
        effective_present = present_count + (late_count * late_weight)
        percentage = (effective_present / total_sessions) * 100.0
        return round(min(100.0, max(0.0, percentage)), 1)

    @staticmethod
    def get_dashboard_stats() -> Dict[str, any]:
        """Aggregate high-level metrics for dashboard cards."""
        today = date.today()
        total_students = Student.query.filter_by(status="active").count()
        total_classes = Class.query.count()
        total_sessions = AttendanceSession.query.filter_by(status="completed").count()

        # Today's attendance percentage
        today_sessions = AttendanceSession.query.filter_by(
            session_date=today, status="completed"
        ).all()

        today_present = 0
        today_late = 0
        today_total_records = 0

        for s in today_sessions:
            for r in s.records:
                today_total_records += 1
                if r.status == "present":
                    today_present += 1
                elif r.status == "late":
                    today_late += 1

        today_pct = ReportService.calculate_attendance_percentage(
            today_present, today_late, today_total_records
        )

        # Recent 5 sessions
        recent_sessions = (
            AttendanceSession.query.order_by(
                AttendanceSession.session_date.desc(), AttendanceSession.id.desc()
            )
            .limit(5)
            .all()
        )

        return {
            "total_students": total_students,
            "total_classes": total_classes,
            "total_sessions": total_sessions,
            "today_percentage": today_pct,
            "today_records_count": today_total_records,
            "recent_sessions": recent_sessions,
        }

    @staticmethod
    def get_daily_report(report_date: date, class_id: Optional[int] = None) -> Dict[str, any]:
        """Aggregate all attendance records for a specific date."""
        query = AttendanceSession.query.filter(
            AttendanceSession.session_date == report_date,
            AttendanceSession.status == "completed",
        )
        if class_id:
            query = query.filter(AttendanceSession.class_id == class_id)

        sessions = query.all()
        session_ids = [s.id for s in sessions]

        records = []
        if session_ids:
            records = (
                AttendanceRecord.query.filter(AttendanceRecord.attendance_session_id.in_(session_ids))
                .join(Student)
                .order_by(Student.name.asc())
                .all()
            )

        total_present = sum(1 for r in records if r.status == "present")
        total_absent = sum(1 for r in records if r.status == "absent")
        total_late = sum(1 for r in records if r.status == "late")
        total_records = len(records)
        overall_pct = ReportService.calculate_attendance_percentage(
            total_present, total_late, total_records
        )

        return {
            "date": report_date,
            "sessions": sessions,
            "records": records,
            "total_records": total_records,
            "present_count": total_present,
            "absent_count": total_absent,
            "late_count": total_late,
            "attendance_percentage": overall_pct,
        }

    @staticmethod
    def get_class_report(
        class_id: int, from_date: Optional[date] = None, to_date: Optional[date] = None
    ) -> Dict[str, any]:
        """Aggregate attendance for each student enrolled in a class over a date range."""
        classroom = db.session.get(Class, class_id)
        if not classroom:
            return {}

        query = AttendanceSession.query.filter(
            AttendanceSession.class_id == class_id,
            AttendanceSession.status == "completed",
        )
        if from_date:
            query = query.filter(AttendanceSession.session_date >= from_date)
        if to_date:
            query = query.filter(AttendanceSession.session_date <= to_date)

        sessions = query.order_by(AttendanceSession.session_date.asc()).all()
        session_ids = [s.id for s in sessions]
        total_sessions_count = len(sessions)

        # Get all actively enrolled students in this class
        enrolled_students = classroom.enrolled_students

        # Map student_id -> {present, absent, late}
        student_stats = []
        for stu in enrolled_students:
            if not session_ids:
                records = []
            else:
                records = AttendanceRecord.query.filter(
                    AttendanceRecord.attendance_session_id.in_(session_ids),
                    AttendanceRecord.student_id == stu.id,
                ).all()

            p_count = sum(1 for r in records if r.status == "present")
            a_count = sum(1 for r in records if r.status == "absent")
            l_count = sum(1 for r in records if r.status == "late")
            applicable_sessions = len(records)

            pct = ReportService.calculate_attendance_percentage(
                p_count, l_count, applicable_sessions
            )

            student_stats.append({
                "student": stu,
                "present": p_count,
                "absent": a_count,
                "late": l_count,
                "total_sessions": applicable_sessions,
                "percentage": pct,
            })

        return {
            "class": classroom,
            "sessions_count": total_sessions_count,
            "students": student_stats,
            "from_date": from_date,
            "to_date": to_date,
        }

    @staticmethod
    def get_student_report(
        student_id: int, from_date: Optional[date] = None, to_date: Optional[date] = None
    ) -> Dict[str, any]:
        """Aggregate detailed session-by-session attendance history for an individual student."""
        student = db.session.get(Student, student_id)
        if not student:
            return {}

        query = (
            AttendanceRecord.query.filter(AttendanceRecord.student_id == student_id)
            .join(AttendanceSession)
            .filter(AttendanceSession.status == "completed")
        )
        if from_date:
            query = query.filter(AttendanceSession.session_date >= from_date)
        if to_date:
            query = query.filter(AttendanceSession.session_date <= to_date)

        records = query.order_by(AttendanceSession.session_date.desc()).all()

        p_count = sum(1 for r in records if r.status == "present")
        a_count = sum(1 for r in records if r.status == "absent")
        l_count = sum(1 for r in records if r.status == "late")
        total_sessions = len(records)
        pct = ReportService.calculate_attendance_percentage(p_count, l_count, total_sessions)

        return {
            "student": student,
            "records": records,
            "present_count": p_count,
            "absent_count": a_count,
            "late_count": l_count,
            "total_sessions": total_sessions,
            "attendance_percentage": pct,
            "from_date": from_date,
            "to_date": to_date,
        }

    @staticmethod
    def generate_csv(headers: List[str], rows: List[List[any]]) -> str:
        """Render a clean UTF-8 CSV string."""
        output = io.StringIO()
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(headers)
        for row in rows:
            writer.writerow(row)
        return output.getvalue()
