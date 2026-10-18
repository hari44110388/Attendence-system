from datetime import date, datetime
from typing import Dict, List, Optional, Tuple
from sqlalchemy.exc import IntegrityError
from models import db, AttendanceSession, AttendanceRecord, Class, Student, Enrollment


class AttendanceService:
    """Business logic for attendance sessions and student attendance records."""

    @staticmethod
    def get_session_by_id(session_id: int) -> Optional[AttendanceSession]:
        return db.session.get(AttendanceSession, session_id)

    @staticmethod
    def find_session(class_id: int, session_date: date, session_name: str) -> Optional[AttendanceSession]:
        return AttendanceSession.query.filter_by(
            class_id=class_id,
            session_date=session_date,
            session_name=session_name.strip(),
        ).first()

    @staticmethod
    def record_attendance(
        class_id: int,
        session_date: date,
        session_name: str,
        student_records: List[Dict[str, any]],
        created_by_id: Optional[int] = None,
    ) -> Tuple[bool, str, Optional[AttendanceSession]]:
        """
        Create a new attendance session or update an existing one.
        Uses a database transaction to ensure atomicity.

        student_records format:
        [
            {"student_id": 1, "status": "present", "remarks": "On time"},
            {"student_id": 2, "status": "absent", "remarks": "Sick leave"},
            ...
        ]
        """
        classroom = db.session.get(Class, class_id)
        if not classroom:
            return False, "Selected class does not exist.", None

        if not student_records:
            return False, "No student attendance records provided.", None

        session_name = (session_name or "Regular Session").strip()

        try:
            # Check if session exists or create a new one
            session = AttendanceService.find_session(class_id, session_date, session_name)
            is_new = False

            if not session:
                is_new = True
                session = AttendanceSession(
                    class_id=class_id,
                    session_date=session_date,
                    session_name=session_name,
                    status="completed",
                    created_by=created_by_id,
                )
                db.session.add(session)
                db.session.flush()  # Populates session.id

            # Map existing records by student_id to prevent duplicate entries
            existing_records = {r.student_id: r for r in session.records}

            for item in student_records:
                student_id = int(item["student_id"])
                status = item.get("status", "present").lower()
                if status not in ("present", "absent", "late"):
                    status = "present"
                remarks = (item.get("remarks") or "").strip() or None

                if student_id in existing_records:
                    record = existing_records[student_id]
                    record.status = status
                    record.remarks = remarks
                    record.recorded_at = datetime.utcnow()
                else:
                    new_record = AttendanceRecord(
                        attendance_session_id=session.id,
                        student_id=student_id,
                        status=status,
                        remarks=remarks,
                    )
                    db.session.add(new_record)

            db.session.commit()
            msg = "Attendance logged successfully." if is_new else "Attendance updated successfully."
            return True, msg, session

        except IntegrityError as e:
            db.session.rollback()
            return False, f"Integrity error recording attendance: Duplicate entry detected.", None
        except Exception as e:
            db.session.rollback()
            return False, f"Failed to record attendance: {str(e)}", None

    @staticmethod
    def get_sessions(
        class_id: Optional[int] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        limit: Optional[int] = None,
    ) -> List[AttendanceSession]:
        query = AttendanceSession.query.order_by(
            AttendanceSession.session_date.desc(), AttendanceSession.id.desc()
        )
        if class_id:
            query = query.filter(AttendanceSession.class_id == class_id)
        if from_date:
            query = query.filter(AttendanceSession.session_date >= from_date)
        if to_date:
            query = query.filter(AttendanceSession.session_date <= to_date)
        if limit:
            query = query.limit(limit)
        return query.all()

    @staticmethod
    def delete_session(session_id: int) -> Tuple[bool, str]:
        session = db.session.get(AttendanceSession, session_id)
        if not session:
            return False, "Attendance session not found."
        try:
            db.session.delete(session)
            db.session.commit()
            return True, "Attendance session deleted."
        except Exception as e:
            db.session.rollback()
            return False, f"Error deleting session: {str(e)}"
