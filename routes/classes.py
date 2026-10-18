from flask import Blueprint, render_template, request, redirect, url_for, flash
from sqlalchemy.exc import IntegrityError
from models import db, Class, User, Student, Enrollment, AttendanceSession
from .auth import login_required, roles_required

classes_bp = Blueprint("classes", __name__, url_prefix="/classes")


@classes_bp.route("/")
@login_required
def list_classes():
    """List all classes with assigned teacher and student enrollment counts."""
    classes = Class.query.order_by(Class.name.asc()).all()
    return render_template("classes/list.html", classes=classes)


@classes_bp.route("/create", methods=["GET", "POST"])
@login_required
@roles_required("admin")
def create_class():
    """Create a new academic class (Admin only)."""
    teachers = User.query.filter(User.role.in_(["teacher", "admin"])).order_by(User.full_name.asc()).all()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        code = request.form.get("code", "").strip().upper()
        academic_year = request.form.get("academic_year", "").strip()
        teacher_id = request.form.get("teacher_id", type=int)

        errors = []
        if not name:
            errors.append("Class Name is required.")
        if not code:
            errors.append("Class Code is required.")
        if not academic_year:
            errors.append("Academic Year is required (e.g. 2025-2026).")

        if Class.query.filter_by(code=code).first():
            errors.append(f"A class with code '{code}' already exists.")

        if errors:
            for err in errors:
                flash(err, "danger")
            return render_template("classes/form.html", classroom=None, teachers=teachers, form_data=request.form)

        try:
            new_class = Class(
                name=name,
                code=code,
                academic_year=academic_year,
                teacher_id=teacher_id or None,
            )
            db.session.add(new_class)
            db.session.commit()
            flash(f"Class '{name}' ({code}) created successfully.", "success")
            return redirect(url_for("classes.list_classes"))
        except IntegrityError:
            db.session.rollback()
            flash("Integrity error: Duplicate class code detected.", "danger")
        except Exception as e:
            db.session.rollback()
            flash(f"Error creating class: {str(e)}", "danger")

    return render_template("classes/form.html", classroom=None, teachers=teachers, form_data={})


@classes_bp.route("/<int:id>/edit", methods=["GET", "POST"])
@login_required
@roles_required("admin")
def edit_class(id: int):
    """Edit class details (Admin only)."""
    classroom = db.get_or_404(Class, id)
    teachers = User.query.filter(User.role.in_(["teacher", "admin"])).order_by(User.full_name.asc()).all()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        code = request.form.get("code", "").strip().upper()
        academic_year = request.form.get("academic_year", "").strip()
        teacher_id = request.form.get("teacher_id", type=int)

        errors = []
        if not name:
            errors.append("Class Name is required.")
        if not code:
            errors.append("Class Code is required.")
        if not academic_year:
            errors.append("Academic Year is required.")

        duplicate = Class.query.filter(Class.code == code, Class.id != id).first()
        if duplicate:
            errors.append(f"Class code '{code}' is already used by another class.")

        if errors:
            for err in errors:
                flash(err, "danger")
            return render_template("classes/form.html", classroom=classroom, teachers=teachers)

        try:
            classroom.name = name
            classroom.code = code
            classroom.academic_year = academic_year
            classroom.teacher_id = teacher_id or None
            db.session.commit()
            flash(f"Class '{classroom.name}' updated successfully.", "success")
            return redirect(url_for("classes.list_classes"))
        except Exception as e:
            db.session.rollback()
            flash(f"Error updating class: {str(e)}", "danger")

    return render_template("classes/form.html", classroom=classroom, teachers=teachers)


@classes_bp.route("/<int:id>/view")
@login_required
def view_class(id: int):
    """View class details, enrolled students, and past sessions."""
    classroom = db.get_or_404(Class, id)
    # Available students for fast enrollment assignment
    enrolled_student_ids = {e.student_id for e in classroom.enrollments}
    available_students = (
        Student.query.filter(Student.status == "active")
        .order_by(Student.name.asc())
        .all()
    )
    return render_template(
        "classes/view.html",
        classroom=classroom,
        enrolled_student_ids=enrolled_student_ids,
        available_students=available_students,
    )


@classes_bp.route("/<int:id>/assign-students", methods=["POST"])
@login_required
def assign_students(id: int):
    """Assign or unassign multiple students to a class."""
    classroom = db.get_or_404(Class, id)
    selected_student_ids = set(map(int, request.form.getlist("student_ids")))

    try:
        # Existing enrollments
        current_map = {e.student_id: e for e in classroom.enrollments}

        # Remove unchecked
        for stu_id, enrollment in list(current_map.items()):
            if stu_id not in selected_student_ids:
                db.session.delete(enrollment)

        # Add checked
        for stu_id in selected_student_ids:
            if stu_id not in current_map:
                new_e = Enrollment(student_id=stu_id, class_id=classroom.id, status="active")
                db.session.add(new_e)

        db.session.commit()
        flash("Student enrollments updated successfully.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error updating enrollments: {str(e)}", "danger")

    return redirect(url_for("classes.view_class", id=classroom.id))


@classes_bp.route("/<int:id>/delete", methods=["POST"])
@login_required
@roles_required("admin")
def delete_class(id: int):
    """
    Safely delete a class.
    Requirement: Prevent deletion when it would leave inconsistent attendance records.
    """
    classroom = db.get_or_404(Class, id)

    # Check if there are recorded attendance sessions
    session_count = classroom.attendance_sessions.count()
    if session_count > 0:
        flash(
            f"Cannot delete class '{classroom.name}' because it contains {session_count} attendance session(s). "
            f"Deleting this class would leave inconsistent attendance records. "
            f"Please review or archive the sessions first.",
            "danger",
        )
        return redirect(url_for("classes.list_classes"))

    try:
        name = classroom.name
        db.session.delete(classroom)
        db.session.commit()
        flash(f"Class '{name}' was deleted successfully.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting class: {str(e)}", "danger")

    return redirect(url_for("classes.list_classes"))
