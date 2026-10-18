import functools
import time
from collections import defaultdict
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    g,
)
from models import db, User

auth_bp = Blueprint("auth", __name__)

# Basic in-memory rate limiting for login attempts: ip -> [timestamps]
_LOGIN_ATTEMPTS = defaultdict(list)
MAX_ATTEMPTS = 5
WINDOW_SECONDS = 300  # 5 minutes lockout window


def check_rate_limit(ip: str) -> bool:
    """Return True if request is allowed, False if IP exceeded rate limit."""
    now = time.time()
    # Filter attempts within current window
    _LOGIN_ATTEMPTS[ip] = [t for t in _LOGIN_ATTEMPTS[ip] if now - t < WINDOW_SECONDS]
    return len(_LOGIN_ATTEMPTS[ip]) < MAX_ATTEMPTS


def record_failed_attempt(ip: str):
    _LOGIN_ATTEMPTS[ip].append(time.time())


def clear_failed_attempts(ip: str):
    if ip in _LOGIN_ATTEMPTS:
        del _LOGIN_ATTEMPTS[ip]


def get_current_user():
    """Retrieve logged-in user model from database based on session."""
    if "user_id" not in session:
        return None
    if not hasattr(g, "_current_user"):
        g._current_user = db.session.get(User, session["user_id"])
    return g._current_user


def login_required(view):
    """Decorator to require login before accessing protected route."""
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if "user_id" not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("auth.login", next=request.url))
        return view(**kwargs)
    return wrapped_view


def roles_required(*allowed_roles):
    """Decorator to enforce role-based access control (e.g. admin, teacher)."""
    def decorator(view):
        @functools.wraps(view)
        def wrapped_view(**kwargs):
            if "user_id" not in session:
                flash("Please log in to access this page.", "warning")
                return redirect(url_for("auth.login", next=request.url))

            user_role = session.get("role")
            if user_role not in allowed_roles:
                flash("Access denied: You do not have permission to view this resource.", "danger")
                return redirect(url_for("dashboard.index"))
            return view(**kwargs)
        return wrapped_view
    return decorator


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Handle user login with secure verification and rate limiting."""
    if "user_id" in session:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        ip = request.remote_addr or "127.0.0.1"
        if not check_rate_limit(ip):
            flash("Too many failed login attempts. Please wait 5 minutes before trying again.", "danger")
            return render_template("login.html"), 429

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        next_url = request.form.get("next") or request.args.get("next")

        if not username or not password:
            flash("Please enter both username and password.", "danger")
            return render_template("login.html")

        user = User.query.filter(
            (User.username == username) | (User.email == username)
        ).first()

        if user and user.is_active and user.check_password(password):
            clear_failed_attempts(ip)
            # Create session
            session.clear()
            session["user_id"] = user.id
            session["username"] = user.username
            session["full_name"] = user.full_name
            session["role"] = user.role
            session.permanent = True

            flash(f"Welcome back, {user.full_name}!", "success")
            if next_url and next_url.startswith("/"):
                return redirect(next_url)
            return redirect(url_for("dashboard.index"))
        else:
            record_failed_attempt(ip)
            flash("Invalid credentials or account is deactivated.", "danger")

    return render_template("login.html")


@auth_bp.route("/logout", methods=["GET", "POST"])
def logout():
    """Clear session and log user out."""
    session.clear()
    flash("You have been securely logged out.", "info")
    return redirect(url_for("auth.login"))
