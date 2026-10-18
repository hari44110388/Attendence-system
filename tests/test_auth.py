def test_login_page_renders(client):
    """Verify login page renders with HTTP 200."""
    response = client.get("/login")
    assert response.status_code == 200
    assert b"Sign In" in response.data


def test_login_success(client):
    """Verify successful authentication sets session and redirects to dashboard."""
    response = client.post(
        "/login",
        data={"username": "testadmin", "password": "AdminPass123!"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"System Overview" in response.data
    assert b"Test Administrator" in response.data


def test_login_invalid_password(client):
    """Verify invalid password fails with error message."""
    response = client.post(
        "/login",
        data={"username": "testadmin", "password": "WrongPassword!"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Invalid credentials" in response.data


def test_logout(auth_admin):
    """Verify logout clears session and redirects to login."""
    response = auth_admin.get("/logout", follow_redirects=True)
    assert response.status_code == 200
    assert b"You have been securely logged out" in response.data


def test_protected_route_requires_login(client):
    """Verify protected dashboard redirects unauthenticated requests."""
    response = client.get("/dashboard", follow_redirects=True)
    assert response.status_code == 200
    assert b"Please log in to access this page" in response.data


def test_admin_route_forbidden_for_teacher(auth_teacher):
    """Verify teacher is blocked from admin-only routes."""
    # Attempting to delete or create class as teacher
    response = auth_teacher.get("/classes/create", follow_redirects=True)
    assert response.status_code == 200
    assert b"Access denied" in response.data
