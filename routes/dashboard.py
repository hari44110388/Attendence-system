from datetime import date, datetime
from flask import Blueprint, render_template
from .auth import login_required
from services import ReportService
from models import Class, Student, AttendanceSession, AttendanceRecord

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@dashboard_bp.route("/dashboard")
@login_required
def index():
    """Main administrative and teacher dashboard overview."""
    stats = ReportService.get_dashboard_stats()

    # Monthly breakdown for charts / metric cards
    today = date.today()
    first_of_month = date(today.year, today.month, 1)

    monthly_sessions = AttendanceSession.query.filter(
        AttendanceSession.session_date >= first_of_month,
        AttendanceSession.session_date <= today,
        AttendanceSession.status == "completed",
    ).all()

    monthly_records_count = 0
    monthly_present = 0
    monthly_late = 0
    monthly_absent = 0

    for s in monthly_sessions:
        for r in s.records:
            monthly_records_count += 1
            if r.status == "present":
                monthly_present += 1
            elif r.status == "late":
                monthly_late += 1
            elif r.status == "absent":
                monthly_absent += 1

    monthly_pct = ReportService.calculate_attendance_percentage(
        monthly_present, monthly_late, monthly_records_count
    )

    monthly_summary = {
        "month_name": today.strftime("%B %Y"),
        "session_count": len(monthly_sessions),
        "total_records": monthly_records_count,
        "present": monthly_present,
        "late": monthly_late,
        "absent": monthly_absent,
        "percentage": monthly_pct,
    }

    # Fetch classes for quick-action dropdown
    classes = Class.query.order_by(Class.name.asc()).all()

    return render_template(
        "dashboard.html",
        stats=stats,
        monthly_summary=monthly_summary,
        classes=classes,
    )
