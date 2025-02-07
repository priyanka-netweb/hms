from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # Admin, Doctor, Patient

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {"id": self.id, "name": self.name, "email": self.email, "role": self.role}

# Doctor Model
class Doctor(db.Model):
    id = db.Column(db.Integer, db.ForeignKey("user.id"), primary_key=True)  # Foreign key from User
    name = db.Column(db.String(80), nullable=False)
    specialty = db.Column(db.String(100), nullable=False)
    available_slots = db.Column(db.String(100), nullable=False) #, default="9:00AM-5:00PM"
    appointments = db.relationship("Appointment", backref="doctor", lazy=True)

# Patient Model
class Patient(db.Model):
    id = db.Column(db.Integer, db.ForeignKey("user.id"), primary_key=True)  # Foreign key from User
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    appointments = db.relationship("Appointment", backref="patient", lazy=True)

# Appointment Model
class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patient.id"), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctor.id"), nullable=False)
    date = db.Column(db.String(20), nullable=False)
    time_slot = db.Column(db.String(20), nullable=False)