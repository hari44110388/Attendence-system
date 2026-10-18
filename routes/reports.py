from datetime import date, datetime
from flask import (
    Blueprint,
    render_template,
    request,
    Response,
    flash,
    redirect,
    url_for,
    send_from_directory,
    current_app,
)
from models import Class, Student
from services import ReportService, S3ExportService
from .auth import login_required

reports_bp = Blueprint("reports", __name__, url_prefix="/reports")


@reports_bp.route("/")
@login_required
def index():
    """Report hub with links to Daily, Class-wise, and Student-wise reports."""
    classes = Class.query.order_by(Class.name.asc()).all()
    students = Student.query.filter_by(status="active").order_by(Student.name.asc()).all()
    return render_template("reports/index.html", classes=classes, students=students)


@reports_bp.route("/daily")
@login_required
def daily():
    """Daily attendance breakdown with export capabilities."""
    date_str = request.args.get("date", date.today().isoformat())
    class_id = request.args.get("class_id", type=int)

    try:
        report_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        report_date = date.today()

    data = ReportService.get_daily_report(report_date, class_id=class_id)
    classes = Class.query.order_by(Class.name.asc()).all()

    return render_template(
        "reports/daily.html",
        data=data,
        report_date=report_date,
        selected_class_id=class_id,
        classes=classes,
    )


@reports_bp.route("/class")
@login_required
def class_report():
    """Class-wise student attendance summary table."""
    class_id = request.args.get("class_id", type=int)
    from_date_str = request.args.get("from_date")
    to_date_str = request.args.get("to_date")

    from_date = None
    to_date = None
    if from_date_str:
        try:
            from_date = datetime.strptime(from_date_str, "%Y-%m-%d").date()
        except ValueError:
            pass

    if to_date_str:
        try:
            to_date = datetime.strptime(to_date_str, "%Y-%m-%d").date()
        except ValueError:
            pass

    classes = Class.query.order_by(Class.name.asc()).all()
    data = None
    if class_id:
        data = ReportService.get_class_report(class_id, from_date, to_date)

    return render_template(
        "reports/class_wise.html",
        classes=classes,
        selected_class_id=class_id,
        data=data,
        from_date=from_date_str or "",
        to_date=to_date_str or "",
    )


@reports_bp.route("/student")
@login_required
def student_report():
    """Detailed attendance report for an individual student."""
    student_id = request.args.get("student_id", type=int)
    from_date_str = request.args.get("from_date")
    to_date_str = request.args.get("to_date")

    from_date = None
    to_date = None
    if from_date_str:
        try:
            from_date = datetime.strptime(from_date_str, "%Y-%m-%d").date()
        except ValueError:
            pass

    if to_date_str:
        try:
            to_date = datetime.strptime(to_date_str, "%Y-%m-%d").date()
        except ValueError:
            pass

    students = Student.query.filter_by(status="active").order_by(Student.name.asc()).all()
    data = None
    if student_id:
        data = ReportService.get_student_report(student_id, from_date, to_date)

    return render_template(
        "reports/student_wise.html",
        students=students,
        selected_student_id=student_id,
        data=data,
        from_date=from_date_str or "",
        to_date=to_date_str or "",
    )


@reports_bp.route("/export/csv")
@login_required
def export_csv():
    """
    Generate CSV file and either stream directly to browser or push to Amazon S3.
    Supported report types: 'daily', 'class', 'student'.
    Query params:
      - type: 'daily' | 'class' | 'student'
      - destination: 'browser' (direct download) | 's3' (upload to AWS S3 & return presigned link)
    """
    report_type = request.args.get("type", "daily")
    destination = request.args.get("destination", "browser")

    headers = []
    rows = []
    file_prefix = f"{report_type}_attendance"

    if report_type == "daily":
        date_str = request.args.get("date", date.today().isoformat())
        class_id = request.args.get("class_id", type=int)
        try:
            rep_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            rep_date = date.today()

        data = ReportService.get_daily_report(rep_date, class_id=class_id)
        headers = ["Date", "Class", "Session", "Student ID", "Student Name", "Status", "Remarks"]
        for r in data.get("records", []):
            rows.append([
                r.session.session_date.isoformat(),
                r.session.classroom.name if r.session.classroom else "",
                r.session.session_name,
                r.student.student_id if r.student else "",
                r.student.name if r.student else "",
                r.status.upper(),
                r.remarks or "",
            ])
        file_prefix = f"daily_attendance_{rep_date.isoformat()}"

    elif report_type == "class":
        class_id = request.args.get("class_id", type=int)
        from_date_str = request.args.get("from_date")
        to_date_str = request.args.get("to_date")
        from_date = datetime.strptime(from_date_str, "%Y-%m-%d").date() if from_date_str else None
        to_date = datetime.strptime(to_date_str, "%Y-%m-%d").date() if to_date_str else None

        if not class_id:
            flash("Please specify a class to export.", "danger")
            return redirect(url_for("reports.class_report"))

        data = ReportService.get_class_report(class_id, from_date, to_date)
        classroom = data.get("class")
        headers = ["Student ID", "Name", "Total Sessions", "Present", "Late", "Absent", "Attendance (%)"]
        for item in data.get("students", []):
            rows.append([
                item["student"].student_id,
                item["student"].name,
                item["total_sessions"],
                item["present"],
                item["late"],
                item["absent"],
                f"{item['percentage']}%",
            ])
        file_prefix = f"class_{classroom.code if classroom else class_id}_attendance"

    elif report_type == "student":
        student_id = request.args.get("student_id", type=int)
        from_date_str = request.args.get("from_date")
        to_date_str = request.args.get("to_date")
        from_date = datetime.strptime(from_date_str, "%Y-%m-%d").date() if from_date_str else None
        to_date = datetime.strptime(to_date_str, "%Y-%m-%d").date() if to_date_str else None

        if not student_id:
            flash("Please specify a student to export.", "danger")
            return redirect(url_for("reports.student_report"))

        data = ReportService.get_student_report(student_id, from_date, to_date)
        student = data.get("student")
        headers = ["Date", "Class", "Session", "Status", "Remarks"]
        for r in data.get("records", []):
            rows.append([
                r.session.session_date.isoformat(),
                r.session.classroom.name if r.session.classroom else "",
                r.session.session_name,
                r.status.upper(),
                r.remarks or "",
            ])
        file_prefix = f"student_{student.student_id if student else student_id}_attendance"

    csv_content = ReportService.generate_csv(headers, rows)

    # If S3 destination requested
    if destination == "s3":
        result = S3ExportService.upload_report_csv(csv_content, filename_prefix=file_prefix)
        if result.get("success"):
            flash(
                f"{result.get('message')} Mode: {result.get('mode').upper()}. "
                f"<a href='{result.get('download_url')}' class='alert-link' target='_blank'>Click here to download</a>",
                "success",
            )
        else:
            flash(f"Export failed: {result.get('error')}", "danger")
        return redirect(request.referrer or url_for("reports.index"))

    # Direct browser streaming
    response = Response(csv_content, mimetype="text/csv")
    response.headers["Content-Disposition"] = f"attachment; filename={file_prefix}.csv"
    return response


@reports_bp.route("/download-local/<path:filename>")
@login_required
def download_local(filename: str):
    """Serve locally stored export files when S3 is unavailable or in offline mode."""
    local_dir = current_app.config.get("LOCAL_EXPORTS_DIR", "exports")
    return send_from_directory(local_dir, filename, as_attachment=True)
