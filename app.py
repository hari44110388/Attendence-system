import os
from datetime import datetime
from flask import Flask, render_template
from flask_wtf.csrf import CSRFProtect
from config import config_by_name
from models import db
from routes import (
    auth_bp,
    dashboard_bp,
    students_bp,
    classes_bp,
    attendance_bp,
    reports_bp,
)
from routes.auth import get_current_user

csrf = CSRFProtect()


def create_app(config_name: str = None) -> Flask:
    """Application factory for AttendanceSystem."""
    if config_name is None:
        config_name = os.getenv("FLASK_ENV", "development")

    app = Flask(__name__)
    config_class = config_by_name.get(config_name, config_by_name["default"])
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    csrf.init_app(app)

    # Ensure instance and exports directories exist
    os.makedirs(app.config.get("LOCAL_EXPORTS_DIR", "exports"), exist_ok=True)

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(students_bp)
    app.register_blueprint(classes_bp)
    app.register_blueprint(attendance_bp)
    app.register_blueprint(reports_bp)

    # Global context processors for Jinja templates
    @app.context_processor
    def inject_globals():
        return {
            "current_user": get_current_user(),
            "current_year": datetime.utcnow().year,
            "app_name": "AttendanceSystem",
        }

    # Custom Error Handlers
    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template("errors/500.html"), 500

    # Custom CLI Commands
    @app.cli.command("init-db")
    def init_db_command():
        """Initialize and create all database tables."""
        with app.app_context():
            db.create_all()
            print("Database tables initialized successfully.")

    @app.cli.command("seed-db")
    def seed_db_command():
        """Seed initial administrator, teachers, sample classes, and attendance."""
        from database.seed_data import seed_database
        seed_database(app)

    @app.cli.command("create-admin")
    def create_admin_command():
        """Create a new administrator account securely from command line."""
        import click
        from models import User
        username = click.prompt("Admin username", default="admin")
        email = click.prompt("Admin email", default="admin@attendance.edu")
        full_name = click.prompt("Full name", default="Administrator")
        password = click.prompt("Password", hide_input=True, confirmation_prompt=True)

        with app.app_context():
            if User.query.filter((User.username == username) | (User.email == email)).first():
                print(f"Error: User with username '{username}' or email '{email}' already exists.")
                return

            user = User(
                username=username,
                email=email,
                full_name=full_name,
                role="admin",
                is_active=True,
            )
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            print(f"Administrator account '{username}' successfully created!")

    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    # Ensure tables and default seed exist in development if not present
    with app.app_context():
        db.create_all()
        from database.seed_data import seed_database
        seed_database(app)

    print(f"AttendanceSystem running on http://127.0.0.1:{port}")
    app.run(host="0.0.0.0", port=port, debug=app.config.get("DEBUG", True))
