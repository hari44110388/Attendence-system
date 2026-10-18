import pytest
from app import create_app
from models import db, User, Class, Student, Enrollment, AttendanceSession, AttendanceRecord


@pytest.fixture
def app():
    """Create and configure a clean Flask application instance for testing."""
    test_app = create_app("testing")

    with test_app.app_context():
        db.create_all()

        # Create standard test users
        admin = User(
            username="testadmin",
            email="admin@test.edu",
            full_name="Test Administrator",
            role="admin",
            is_active=True,
        )
        admin.set_password("AdminPass123!")

        teacher = User(
            username="testteacher",
            email="teacher@test.edu",
            full_name="Test Teacher",
            role="teacher",
            is_active=True,
        )
        teacher.set_password("TeacherPass123!")

        db.session.add_all([admin, teacher])
        db.session.commit()

        yield test_app

        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Flask CLI runner."""
    return app.test_cli_runner()


@pytest.fixture
def auth_admin(client):
    """Log in as test administrator."""
    client.post(
        "/login",
        data={"username": "testadmin", "password": "AdminPass123!"},
        follow_redirects=True,
    )
    return client


@pytest.fixture
def auth_teacher(client):
    """Log in as test teacher."""
    client.post(
        "/login",
        data={"username": "testteacher", "password": "TeacherPass123!"},
        follow_redirects=True,
    )
    return client


@pytest.fixture
def sample_class(app):
    """Create a sample class in test database."""
    with app.app_context():
        teacher = User.query.filter_by(username="testteacher").first()
        c = Class(
            name="Computer Networks",
            code="CS501",
            academic_year="2025-2026",
            teacher_id=teacher.id if teacher else None,
        )
        db.session.add(c)
        db.session.commit()
        return c.id


@pytest.fixture
def sample_student(app):
    """Create a sample student in test database."""
    with app.app_context():
        s = Student(
            student_id="TEST2026001",
            name="John Doe",
            email="john.doe@test.edu",
            phone="1234567890",
            status="active",
        )
        db.session.add(s)
        db.session.commit()
        return s.id
