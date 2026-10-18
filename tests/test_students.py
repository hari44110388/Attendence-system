from models import Student, db


def test_list_students(auth_admin, sample_student):
    """Verify students directory lists existing student."""
    response = auth_admin.get("/students/")
    assert response.status_code == 200
    assert b"TEST2026001" in response.data
    assert b"John Doe" in response.data


def test_create_student_success(auth_admin, app):
    """Verify admin can add a new student with valid data."""
    response = auth_admin.post(
        "/students/create",
        data={
            "student_id": "NEW2026999",
            "name": "Jane Smith",
            "email": "jane.smith@university.edu",
            "phone": "+1 555 1234",
            "status": "active",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"created successfully" in response.data

    with app.app_context():
        created = Student.query.filter_by(student_id="NEW2026999").first()
        assert created is not None
        assert created.name == "Jane Smith"


def test_create_duplicate_student_id_fails(auth_admin, sample_student):
    """Verify server rejects duplicate student ID."""
    response = auth_admin.post(
        "/students/create",
        data={
            "student_id": "TEST2026001",  # Duplicate ID
            "name": "Duplicate Student",
            "email": "unique.email@test.edu",
            "phone": "555-0000",
            "status": "active",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"already registered" in response.data


def test_edit_student(auth_admin, sample_student, app):
    """Verify editing student details."""
    response = auth_admin.post(
        f"/students/{sample_student}/edit",
        data={
            "student_id": "TEST2026001",
            "name": "Johnathan Doe Updated",
            "email": "john.doe@test.edu",
            "phone": "999-999-9999",
            "status": "active",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"updated successfully" in response.data

    with app.app_context():
        updated = db.session.get(Student, sample_student)
        assert updated.name == "Johnathan Doe Updated"


def test_delete_student_by_admin(auth_admin, sample_student, app):
    """Verify administrator can delete a student."""
    response = auth_admin.post(
        f"/students/{sample_student}/delete", follow_redirects=True
    )
    assert response.status_code == 200
    assert b"deleted" in response.data

    with app.app_context():
        deleted = db.session.get(Student, sample_student)
        assert deleted is None
