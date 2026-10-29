from datetime import datetime, date
from extensions import db
from werkzeug.security import generate_password_hash, check_password_hash


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(120))
    caregiver_email = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    medicines = db.relationship("Medicine", backref="user", cascade="all, delete-orphan")
    prescriptions = db.relationship("Prescription", backref="user", cascade="all, delete-orphan")

    def set_password(self, raw_password):
        self.password = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password, raw_password)


class Medicine(db.Model):
    __tablename__ = "medicines"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    medicine_name = db.Column(db.String(120), nullable=False)
    dosage = db.Column(db.String(80))
    time = db.Column(db.String(5), nullable=False)  # HH:MM (primary time, kept for backward compat)
    frequency = db.Column(db.String(80))  # e.g. "Morning, Night"
    start_date = db.Column(db.Date, default=date.today)
    end_date = db.Column(db.Date)
    notes = db.Column(db.Text)
    status = db.Column(db.String(20), default="Active")  # Active / Completed / Stopped
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    history = db.relationship("ReminderHistory", backref="medicine", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "medicine_name": self.medicine_name,
            "dosage": self.dosage,
            "time": self.time,
            "frequency": self.frequency,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "notes": self.notes,
            "status": self.status,
        }


class Prescription(db.Model):
    __tablename__ = "prescriptions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    original_name = db.Column(db.String(255))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)


class ReminderHistory(db.Model):
    __tablename__ = "reminder_history"

    id = db.Column(db.Integer, primary_key=True)
    medicine_id = db.Column(db.Integer, db.ForeignKey("medicines.id"), nullable=False)
    scheduled_time = db.Column(db.String(5))
    status = db.Column(db.String(20), default="Taken")  # Taken / Missed / Snoozed
    logged_at = db.Column(db.DateTime, default=datetime.utcnow)
