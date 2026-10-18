from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, url_for, flash
from sqlalchemy.exc import IntegrityError
from models import db, Student, Class, Enrollment
from .auth import login_required, roles_required

students_bp = Blueprint("students", __name__, url_prefix="/students")


@students_bp.route("/")
@login_required
def list_students():
    """List students with search, class filter, and pagination."""
    search_query = request.args.get("q", "").strip()
    class_filter = request.args.get("class_id", type=int)
    page = request.args.get("page", 1, type=int)
    per_page = 15

    query = Student.query

    if search_query:
        search_like = f"%{search_query}%"
        query = query.filter(
            (Student.name.ilike(search_like))
            | (Student.student_id.ilike(search_like))
            | (Student.email.ilike(search_like))
        )

    if class_filter:
        query = query.join(Enrollment).filter(
            Enrollment.class_id == class_filter,
            Enrollment.status == "active",
        )

    pagination = query.order_by(Student.name.asc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    all_classes = Class.query.order_by(Class.name.asc()).all()

    return render_template(
        "students/list.html",
        pagination=pagination,
        students=pagination.items,
        search_query=search_query,
        class_filter=class_filter,
        classes=all_classes,
    )


@students_bp.route("/create", methods=["GET", "POST"])
@login_required
def create_student():
    """Add a new student and optionally assign to initial classes."""
    classes = Class.query.order_by(Class.name.asc()).all()

    if request.method == "POST":
        student_id = request.form.get("student_id", "").strip().upper()
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        status = request.form.get("status", "active")
        selected_class_ids = request.form.getlist("classes")

        # Server-side validation
        errors = []
        if not student_id:
            errors.append("Student ID is required.")
        if not name:
            errors.append("Student Name is required.")
        if not email or "@" not in email:
            errors.append("A valid Email address is required.")

        # Check uniqueness
        if Student.query.filter_by(student_id=student_id).first():
            errors.append(f"Student ID '{student_id}' is already registered.")
        if Student.query.filter_by(email=email).first():
            errors.append(f"Email '{email}' is already in use by another student.")

        if errors:
            for err in errors:
                flash(err, "danger")
            return render_template("students/form.html", student=None, classes=classes, form_data=request.form)

        try:
            student = Student(
                student_id=student_id,
                name=name,
                email=email,
                phone=phone,
                status=status,
                enrollment_date=date.today(),
            )
            db.session.add(student)
            db.session.flush()

            # Assign to selected classes
            for cid in selected_class_ids:
                cid_int = int(cid)
                enrollment = Enrollment(student_id=student.id, class_id=cid_int, status="active")
                db.session.add(enrollment)

            db.session.commit()
            flash(f"Student '{name}' ({student_id}) created successfully.", "success")
            return redirect(url_for("students.list_students"))
        except IntegrityError:
            db.session.rollback()
            flash("Database integrity error. Check for duplicate ID or Email.", "danger")
        except Exception as e:
            db.session.rollback()
            flash(f"Failed to create student: {str(e)}", "danger")

    return render_template("students/form.html", student=None, classes=classes, form_data={})


@students_bp.route("/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit_student(id: int):
    """Update student profile and enrolled classes."""
    student = db.get_or_404(Student, id)
    classes = Class.query.order_by(Class.name.asc()).all()

    if request.method == "POST":
        student_id = request.form.get("student_id", "").strip().upper()
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        status = request.form.get("status", "active")
        selected_class_ids = set(map(int, request.form.getlist("classes")))

        errors = []
        if not student_id:
            errors.append("Student ID is required.")
        if not name:
            errors.append("Student Name is required.")
        if not email or "@" not in email:
            errors.append("A valid Email address is required.")

        # Check duplicate ID/Email on other students
        existing_id = Student.query.filter(Student.student_id == student_id, Student.id != id).first()
        if existing_id:
            errors.append(f"Student ID '{student_id}' is already registered to another student.")
        existing_email = Student.query.filter(Student.email == email, Student.id != id).first()
        if existing_email:
            errors.append(f"Email '{email}' is already in use by another student.")

        if errors:
            for err in errors:
                flash(err, "danger")
            return render_template("students/form.html", student=student, classes=classes)

        try:
            student.student_id = student_id
            student.name = name
            student.email = email
            student.phone = phone
            student.status = status

            # Synchronize enrollments
            current_enrolled_cids = {e.class_id for e in student.enrollments}
            # Remove unselected
            for e in list(student.enrollments):
                if e.class_id not in selected_class_ids:
                    db.session.delete(e)

            # Add newly selected
            for cid in selected_class_ids:
                if cid not in current_enrolled_cids:
                    new_e = Enrollment(student_id=student.id, class_id=cid, status="active")
                    db.session.add(new_e)

            db.session.commit()
            flash(f"Student '{student.name}' details updated successfully.", "success")
            return redirect(url_for("students.list_students"))
        except Exception as e:
            db.session.rollback()
            flash(f"Failed to update student: {str(e)}", "danger")

    return render_template("students/form.html", student=student, classes=classes)


@students_bp.route("/<int:id>/view")
@login_required
def view_student(id: int):
    """View detailed student profile and class enrollments."""
    student = db.get_or_404(Student, id)
    return render_template("students/view.html", student=student)


@students_bp.route("/<int:id>/delete", methods=["POST"])
@login_required
@roles_required("admin")
def delete_student(id: int):
    """Delete student after confirmation (Admin only)."""
    student = db.get_or_404(Student, id)
    name = student.name
    try:
        db.session.delete(student)
        db.session.commit()
        flash(f"Student '{name}' and related records were deleted.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Could not delete student: {str(e)}", "danger")
    return redirect(url_for("students.list_students"))
