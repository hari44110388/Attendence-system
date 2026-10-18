import os
from datetime import date, timedelta
from werkzeug.security import generate_password_hash
from models import db, User, Student, Class, Enrollment, AttendanceSession, AttendanceRecord


def seed_database(app):
    """Populate database with initial admin, teachers, classes, students, and attendance records."""
    with app.app_context():
        # Ensure tables exist
        db.create_all()

        # Check if already seeded
        if User.query.filter_by(username="admin").first():
            print("Database already contains an admin account. Skipping seed.")
            return

        print("Seeding initial data...")

        # 1. Administrators and Teachers
        admin_user = User(
            username=os.getenv("ADMIN_USERNAME", "admin"),
            email=os.getenv("ADMIN_EMAIL", "admin@attendance.edu"),
            full_name=os.getenv("ADMIN_FULL_NAME", "System Administrator"),
            role="admin",
            is_active=True,
        )
        admin_user.set_password(os.getenv("ADMIN_PASSWORD", "Admin@123"))

        teacher1 = User(
            username="prof.sharma",
            email="sharma@attendance.edu",
            full_name="Prof. Rajesh Sharma",
            role="teacher",
            is_active=True,
        )
        teacher1.set_password("Teacher@123")

        teacher2 = User(
            username="dr.anita",
            email="anita@attendance.edu",
            full_name="Dr. Anita Desai",
            role="teacher",
            is_active=True,
        )
        teacher2.set_password("Teacher@123")

        db.session.add_all([admin_user, teacher1, teacher2])
        db.session.flush()

        # 2. Classes
        classes = [
            Class(name="Cloud Computing & AWS", code="CS401", academic_year="2025-2026", teacher_id=teacher1.id),
            Class(name="Database Management Systems", code="CS302", academic_year="2025-2026", teacher_id=teacher1.id),
            Class(name="Data Structures & Algorithms", code="CS201", academic_year="2025-2026", teacher_id=teacher2.id),
            Class(name="Web Technologies", code="CS305", academic_year="2025-2026", teacher_id=teacher2.id),
        ]
        db.session.add_all(classes)
        db.session.flush()

        # 3. Students
        sample_students = [
            ("STU2026001", "Aarav Patel", "aarav.p@student.edu", "+91 98765 43210"),
            ("STU2026002", "Diya Sengupta", "diya.s@student.edu", "+91 98765 43211"),
            ("STU2026003", "Rohan Verma", "rohan.v@student.edu", "+91 98765 43212"),
            ("STU2026004", "Ananya Iyer", "ananya.i@student.edu", "+91 98765 43213"),
            ("STU2026005", "Kabir Nair", "kabir.n@student.edu", "+91 98765 43214"),
            ("STU2026006", "Sneha Kulkarni", "sneha.k@student.edu", "+91 98765 43215"),
            ("STU2026007", "Vikram Malhotra", "vikram.m@student.edu", "+91 98765 43216"),
            ("STU2026008", "Pooja Reddy", "pooja.r@student.edu", "+91 98765 43217"),
        ]

        created_students = []
        for sid, name, email, phone in sample_students:
            s = Student(
                student_id=sid,
                name=name,
                email=email,
                phone=phone,
                status="active",
                enrollment_date=date.today() - timedelta(days=60),
            )
            created_students.append(s)
        db.session.add_all(created_students)
        db.session.flush()

        # 4. Enrollments (Assign students to classes)
        for s in created_students:
            # Enroll all in CS401 (Cloud Computing) and CS302
            e1 = Enrollment(student_id=s.id, class_id=classes[0].id, status="active")
            e2 = Enrollment(student_id=s.id, class_id=classes[1].id, status="active")
            db.session.add_all([e1, e2])

        # Enroll subset in CS201 and CS305
        for s in created_students[:5]:
            e3 = Enrollment(student_id=s.id, class_id=classes[2].id, status="active")
            e4 = Enrollment(student_id=s.id, class_id=classes[3].id, status="active")
            db.session.add_all([e3, e4])

        db.session.flush()

        # 5. Realistic Attendance Sessions & Records
        # Create past 5 days of attendance for CS401
        today = date.today()
        statuses = ["present", "present", "present", "present", "late", "absent", "present", "present"]

        for i in range(5, -1, -1):
            session_date = today - timedelta(days=i)
            # Skip weekends
            if session_date.weekday() >= 5:
                continue

            sess = AttendanceSession(
                class_id=classes[0].id,
                session_date=session_date,
                session_name="Lecture " + str(10 - i),
                status="completed",
                created_by=teacher1.id,
            )
            db.session.add(sess)
            db.session.flush()

            for idx, student in enumerate(created_students):
                status = statuses[(idx + i) % len(statuses)]
                remarks = "Arrived 10 mins late" if status == "late" else ("Sick leave" if status == "absent" else None)
                rec = AttendanceRecord(
                    attendance_session_id=sess.id,
                    student_id=student.id,
                    status=status,
                    remarks=remarks,
                )
                db.session.add(rec)

        db.session.commit()
        print("Database seeded successfully!")
        print(f"Admin User created: {admin_user.username} / Password from .env (default: Admin@123)")
        print(f"Teacher 1 created: {teacher1.username} / Teacher@123")
        print(f"Teacher 2 created: {teacher2.username} / Teacher@123")


if __name__ == "__main__":
    from app import create_app
    app = create_app()
    seed_database(app)
