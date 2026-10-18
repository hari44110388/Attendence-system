from datetime import date, datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import db, Class, Student, AttendanceSession, AttendanceRecord
from services import AttendanceService
from .auth import login_required, roles_required

attendance_bp = Blueprint("attendance", __name__, url_prefix="/attendance")


@attendance_bp.route("/take", methods=["GET", "POST"])
@login_required
def take_attendance():
    """
    Step 1: Select class, date, session name.
    Step 2: Display list of enrolled students with radio buttons (Present, Absent, Late) & remarks.
    Step 3: Save attendance transactionally.
    """
    classes = Class.query.order_by(Class.name.asc()).all()
    selected_class_id = request.args.get("class_id", type=int)
    session_date_str = request.args.get("date", date.today().isoformat())
    session_name = request.args.get("session_name", "Regular Session").strip()

    try:
        session_date = datetime.strptime(session_date_str, "%Y-%m-%d").date()
    except ValueError:
        session_date = date.today()

    selected_class = None
    existing_session = None
    students_data = []

    if selected_class_id:
        selected_class = db.session.get(Class, selected_class_id)
        if selected_class:
            # Check if this session was already logged
            existing_session = AttendanceService.find_session(
                selected_class_id, session_date, session_name
            )

            # Map existing records by student_id
            existing_status_map = {}
            if existing_session:
                for r in existing_session.records:
                    existing_status_map[r.student_id] = {
                        "status": r.status,
                        "remarks": r.remarks or "",
                    }

            # Enrolled active students
            for student in selected_class.enrolled_students:
                if student.id in existing_status_map:
                    status = existing_status_map[student.id]["status"]
                    remarks = existing_status_map[student.id]["remarks"]
                else:
                    status = "present"  # Default mark
                    remarks = ""

                students_data.append({
                    "student": student,
                    "status": status,
                    "remarks": remarks,
                })

    if request.method == "POST":
        post_class_id = request.form.get("class_id", type=int)
        post_date_str = request.form.get("session_date")
        post_session_name = request.form.get("session_name", "Regular Session").strip()

        try:
            post_date = datetime.strptime(post_date_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            flash("Invalid date format provided.", "danger")
            return redirect(url_for("attendance.take_attendance"))

        classroom = db.session.get(Class, post_class_id)
        if not classroom:
            flash("Class not found.", "danger")
            return redirect(url_for("attendance.take_attendance"))

        enrolled_students = classroom.enrolled_students
        if not enrolled_students:
            flash("No students are currently enrolled in this class to record attendance for.", "warning")
            return redirect(url_for("attendance.take_attendance", class_id=post_class_id))

        student_records = []
        for stu in enrolled_students:
            status = request.form.get(f"status_{stu.id}", "present")
            remarks = request.form.get(f"remarks_{stu.id}", "")
            student_records.append({
                "student_id": stu.id,
                "status": status,
                "remarks": remarks,
            })

        user_id = session.get("user_id")
        success, msg, saved_session = AttendanceService.record_attendance(
            class_id=post_class_id,
            session_date=post_date,
            session_name=post_session_name,
            student_records=student_records,
            created_by_id=user_id,
        )

        if success:
            flash(msg, "success")
            return redirect(url_for("attendance.history", class_id=post_class_id))
        else:
            flash(msg, "danger")

    return render_template(
        "attendance/take.html",
        classes=classes,
        selected_class=selected_class,
        selected_class_id=selected_class_id,
        session_date=session_date,
        session_name=session_name,
        existing_session=existing_session,
        students_data=students_data,
    )


@attendance_bp.route("/history")
@login_required
def history():
    """View logged attendance sessions with filters for class and date range."""
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

    sessions = AttendanceService.get_sessions(
        class_id=class_id, from_date=from_date, to_date=to_date
    )
    all_classes = Class.query.order_by(Class.name.asc()).all()

    return render_template(
        "attendance/history.html",
        sessions=sessions,
        classes=all_classes,
        selected_class_id=class_id,
        from_date=from_date_str or "",
        to_date=to_date_str or "",
    )


@attendance_bp.route("/session/<int:session_id>/view")
@login_required
def view_session(session_id: int):
    """View details of a single attendance session and student breakdown."""
    att_session = AttendanceService.get_session_by_id(session_id)
    if not att_session:
        flash("Attendance session not found.", "danger")
        return redirect(url_for("attendance.history"))
    return render_template("attendance/view_session.html", session=att_session)


@attendance_bp.route("/session/<int:session_id>/edit", methods=["GET", "POST"])
@login_required
def edit_session(session_id: int):
    """Edit records of a previously logged attendance session."""
    att_session = AttendanceService.get_session_by_id(session_id)
    if not att_session:
        flash("Attendance session not found.", "danger")
        return redirect(url_for("attendance.history"))

    if request.method == "POST":
        student_records = []
        for record in att_session.records:
            status = request.form.get(f"status_{record.student_id}", record.status)
            remarks = request.form.get(f"remarks_{record.student_id}", record.remarks)
            student_records.append({
                "student_id": record.student_id,
                "status": status,
                "remarks": remarks,
            })

        success, msg, _ = AttendanceService.record_attendance(
            class_id=att_session.class_id,
            session_date=att_session.session_date,
            session_name=att_session.session_name,
            student_records=student_records,
            created_by_id=session.get("user_id"),
        )
        if success:
            flash("Attendance records successfully updated.", "success")
            return redirect(url_for("attendance.view_session", session_id=att_session.id))
        else:
            flash(msg, "danger")

    return render_template("attendance/edit.html", session=att_session)


@attendance_bp.route("/session/<int:session_id>/delete", methods=["POST"])
@login_required
@roles_required("admin")
def delete_session(session_id: int):
    """Delete attendance session (Admin only)."""
    success, msg = AttendanceService.delete_session(session_id)
    if success:
        flash(msg, "success")
    else:
        flash(msg, "danger")
    return redirect(url_for("attendance.history"))
