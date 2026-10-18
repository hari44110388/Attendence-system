from models import Class, AttendanceSession, db


def test_list_classes(auth_teacher, sample_class):
    """Verify class list renders for teachers."""
    response = auth_teacher.get("/classes/")
    assert response.status_code == 200
    assert b"CS501" in response.data
    assert b"Computer Networks" in response.data


def test_create_class(auth_admin, app):
    """Verify admin can create a new class."""
    response = auth_admin.post(
        "/classes/create",
        data={
            "name": "Distributed Systems",
            "code": "CS601",
            "academic_year": "2025-2026",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"created successfully" in response.data

    with app.app_context():
        created = Class.query.filter_by(code="CS601").first()
        assert created is not None
        assert created.name == "Distributed Systems"


def test_create_duplicate_class_code_fails(auth_admin, sample_class):
    """Verify duplicate class code is rejected."""
    response = auth_admin.post(
        "/classes/create",
        data={
            "name": "Duplicate Class",
            "code": "CS501",  # Existing code
            "academic_year": "2025-2026",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"already exists" in response.data


def test_safe_class_deletion_prevented_when_sessions_exist(auth_admin, sample_class, app):
    """
    Requirement 7: Prevent deletion when it would leave inconsistent attendance records.
    """
    with app.app_context():
        from datetime import date
        session = AttendanceSession(
            class_id=sample_class,
            session_date=date.today(),
            session_name="Lecture 1",
            status="completed",
        )
        db.session.add(session)
        db.session.commit()

    # Attempt deletion
    response = auth_admin.post(f"/classes/{sample_class}/delete", follow_redirects=True)
    assert response.status_code == 200
    assert b"Cannot delete class" in response.data
    assert b"attendance session" in response.data

    # Verify class was NOT deleted
    with app.app_context():
        assert db.session.get(Class, sample_class) is not None
