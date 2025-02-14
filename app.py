from flask import Flask, jsonify, request, session
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from config import Config
from models import db, User, Doctor, Patient, Appointment  # Import models
from datetime import datetime, timedelta

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)
app.config["SECRET_KEY"] = "priyanka"  # This must stay constant for session security
SESSION_COOKIE_SECURE = True  # Ensures cookies are only sent over HTTPS.

# Initialize extensions
db.init_app(app)
bcrypt = Bcrypt(app)
CORS(app, supports_credentials=True)

# ------------------------- AUTHENTICATION & AUTHORIZATION using session-based authentication -------------------------


@app.route("/signup", methods=["POST"])
def signup():
    """
    Handles user registration.

    Expected JSON payload:
    {
        "name": "John Doe",
        "email": "johndoe@example.com",
        "password": "securepassword",
        "role": "Doctor/Patient"
    }

    Returns:
        201 - User registered successfully
        400 - Missing fields or email already exists
        500 - Database error
    """
    data = request.get_json()

    # Validate input fields
    required_fields = ["name", "email", "password", "role"]
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400

    # Check if email already exists in User table
    if User.query.filter_by(email=data["email"]).first():
        return jsonify({"error": "Email already exists"}), 400

    # Create a new User
    new_user = User(name=data["name"], email=data["email"], role=data["role"])
    new_user.set_password(data["password"])  # Hash password

    try:
        db.session.add(new_user)
        db.session.commit()  # Commit the user record to generate ID
    except Exception as e:
        db.session.rollback()  # Rollback if error occurs
        return jsonify({"error": f"Error adding user: {str(e)}"}), 500

    # Assign user to respective role table
    user_id = new_user.id
    if data["role"] == "Doctor":
        new_doctor = Doctor(
            id=user_id,
            name=data["name"],
            email=data["email"],
            specialty=data.get("specialty", "General"),
            available_slots=data.get("available_slots", "9:00AM-5:00PM"),
        )
    elif data["role"] == "Patient":
        new_doctor = Patient(id=user_id, name=data["name"], email=data["email"])

    try:
        db.session.add(new_doctor)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Error adding {data['role'].lower()}: {str(e)}"}), 500

    return jsonify({"message": "User registered successfully!"}), 201


@app.route("/login", methods=["POST"])
def login():
    """
    Handles user login.

    Expected JSON payload:
    {
        "email": "user@example.com",
        "password": "securepassword"
    }

    Returns:
        200 - Login successful
        401 - Invalid credentials
    """
    data = request.get_json()
    email, password = data.get("email"), data.get("password")

    user = User.query.filter_by(email=email).first()

    if user and user.check_password(password):  # Use check_password method
        session.update({"user_id": user.id, "role": user.role, "email": user.email})
        return jsonify({"message": f"Welcome {user.role}", "role": user.role}), 200
    return jsonify({"error": "Invalid credentials"}), 401


@app.route("/logout", methods=["POST"])
def logout():
    """Clears user session and logs out."""
    session.clear()
    return jsonify({"message": "Logged out successfully"})


# ------------------------- DASHBOARD -------------------------


@app.route("/dashboard", methods=["GET"])
def dashboard():
    """
    Returns dashboard information based on user role.

    Returns:
        401 - Unauthorized
        403 - Access denied
        200 - User-specific dashboard data
    """
    if "role" not in session or "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    user_id, role = session["user_id"], session["role"]

    if role == "Patient":
        patient = Patient.query.get(user_id)
        if patient:
            return jsonify(
                {
                    "message": f"Welcome {patient.name}",
                    "patient_id": patient.id,
                    "role": "Patient",
                }
            )

    elif role == "Doctor":
        doctor = Doctor.query.get(user_id)
        if doctor:
            return jsonify(
                {
                    "message": f"Welcome Dr. {doctor.name}",
                    "doctor_id": doctor.id,
                    "role": "Doctor",
                }
            )

    elif role == "Admin":
        return jsonify({"message": "Welcome Admin", "role": "Admin"})

    return jsonify({"error": "Access denied"}), 403


# ------------------------- DOCTOR MANAGEMENT -------------------------


@app.route("/doctors", methods=["GET"])
def get_doctors():
    """Returns a list of all doctors."""
    doctors = Doctor.query.all()
    doctor_list = [{"name": doc.name, "specialty": doc.specialty} for doc in doctors]
    return jsonify({"doctors": doctor_list})


# ------------------------- APPOINTMENT MANAGEMENT -------------------------


@app.route("/available-times/<doctor_name>/<date>", methods=["GET"])
def available_times(doctor_name, date):
    """
    Returns available time slots for a doctor on a specific date.

    Args:
        doctor_name (str): Name of the doctor
        date (str): Appointment date in YYYY-MM-DD format

    Returns:
        200 - Available times
        404 - Doctor not found
        500 - Internal error
    """
    doctor = Doctor.query.filter_by(name=doctor_name).first()
    if not doctor:
        return jsonify({"error": "Doctor not found"}), 404

    try:
        # Generate hourly time slots between 9:00 AM and 5:00 PM
        start_time = datetime.strptime("09:00AM", "%I:%M%p")
        end_time = datetime.strptime("05:00PM", "%I:%M%p")

        available_times = []
        while start_time < end_time:
            available_times.append(start_time.strftime("%I:%M%p"))
            start_time += timedelta(hours=1)  # Increment by 1 hour

        # Get booked appointments
        booked_times = {
            app.time_slot
            for app in Appointment.query.filter_by(doctor_id=doctor.id, date=date)
        }
        # Remove booked times from available slots
        available_times = [time for time in available_times if time not in booked_times]

        return jsonify({"available_times": available_times})

    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


@app.route("/book-appointment-api", methods=["POST"])
def book_appointment_api():
    """Handles booking of an appointment."""
    data = request.get_json()
    patient_id, doctor_name, date, time_slot = (
        data.get("patient_id"),
        data.get("doctor"),
        data.get("date"),
        data.get("time"),
    )

    if not all([patient_id, doctor_name, date, time_slot]):
        return jsonify({"status": "error", "message": "Missing data"}), 400

    # Fetch the doctor by name
    doctor = Doctor.query.filter_by(name=doctor_name).first()
    if not doctor:
        return jsonify({"status": "error", "message": "Doctor not found"}), 404

    # Check if the selected time slot is already booked
    existing_appointment = Appointment.query.filter_by(
        doctor_id=doctor.id, date=date, time_slot=time_slot
    ).first()
    if existing_appointment:
        return jsonify({"status": "error", "message": "Time slot already booked"}), 400

    # Create a new appointment
    new_appointment = Appointment(
        patient_id=patient_id, doctor_id=doctor.id, date=date, time_slot=time_slot
    )

    try:
        db.session.add(new_appointment)
        db.session.commit()
        return jsonify(
            {"status": "success", "message": "Appointment booked successfully!"}
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": f"Database error: {str(e)}"}), 500


# ------------------------- DOCTOR DASHBOARD -------------------------


@app.route("/doctor/appointments", methods=["GET"])
def get_doctor_appointments():
    """
    Fetch all appointments assigned to the logged-in doctor.

    Returns:
        JSON: List of appointments with patient details.
    """
    if "user_id" not in session or session.get("role") != "Doctor":
        return jsonify({"error": "Unauthorized"}), 403

    doctor_id = session.get("user_id")
    appointments = Appointment.query.filter_by(doctor_id=doctor_id).all()

    appointment_list = [
        {
            "id": app.id,
            "patient_name": (
                Patient.query.get(app.patient_id).name
                if Patient.query.get(app.patient_id)
                else "Unknown"
            ),
            "date": app.date,
            "time": app.time_slot,
            "status": app.status,
        }
        for app in appointments
    ]

    return jsonify(appointment_list)


@app.route("/doctor/appointments/<int:appointment_id>", methods=["DELETE"])
def delete_appointment(appointment_id):
    """
    Allow a doctor to delete an appointment they own.

    Args:
        appointment_id (int): The ID of the appointment to be deleted.

    Returns:
        JSON: Success or error message.
    """
    if session.get("role") != "Doctor":
        return jsonify({"error": "Unauthorized"}), 403

    appointment = Appointment.query.get(appointment_id)
    if not appointment:
        return jsonify({"error": "Appointment not found"}), 404

    if appointment.doctor_id != session["user_id"]:
        return jsonify({"error": "Unauthorized to delete this appointment"}), 403

    db.session.delete(appointment)
    db.session.commit()
    return jsonify({"message": "Appointment deleted successfully"})


@app.route("/doctor/appointments/<int:appointment_id>/done", methods=["PUT"])
def mark_appointment_done(appointment_id):
    """
    Allow a doctor to mark an appointment as 'done'.

    Args:
        appointment_id (int): The ID of the appointment.

    Returns:
        JSON: Success or error message.
    """
    if session.get("role") != "Doctor":
        return jsonify({"error": "Unauthorized"}), 403

    appointment = Appointment.query.get(appointment_id)
    if not appointment:
        return jsonify({"error": "Appointment not found"}), 404

    if appointment.doctor_id != session["user_id"]:
        return jsonify({"error": "Unauthorized to mark this appointment"}), 403

    appointment.status = "done"
    db.session.commit()
    return jsonify({"message": "Appointment marked as done"})


# ------------------------- ADMIN DASHBOARD -------------------------


@app.route("/admin/doctors", methods=["GET"])
def list_doctors():
    """
    Fetch all doctors.

    Returns:
        JSON: List of doctors.
    """
    if session.get("role") != "Admin":
        return jsonify({"error": "Unauthorized"}), 403

    doctors = Doctor.query.all()
    return jsonify(
        [
            {
                "id": doc.id,
                "name": doc.name,
                "email": doc.email,
                "specialty": doc.specialty,
            }
            for doc in doctors
        ]
    )


@app.route("/admin/patients", methods=["GET"])
def list_patients():
    """
    Fetch all patients.

    Returns:
        JSON: List of patients.
    """
    if session.get("role") != "Admin":
        return jsonify({"error": "Unauthorized"}), 403

    patients = Patient.query.all()
    return jsonify(
        [{"id": pat.id, "name": pat.name, "email": pat.email} for pat in patients]
    )


@app.route("/admin/admins", methods=["GET"])
def list_admins():
    """
    Fetch all admins.

    Returns:
        JSON: List of admins.
    """
    if session.get("role") != "Admin":
        return jsonify({"error": "Unauthorized"}), 403

    admins = User.query.filter_by(role="Admin").all()
    return jsonify(
        [{"id": admin.id, "name": admin.name, "email": admin.email} for admin in admins]
    )


@app.route("/admin/doctors/<int:doctor_id>", methods=["DELETE"])
def delete_doctor(doctor_id):
    """
    Delete a doctor and their associated appointments.

    Args:
        doctor_id (int): The ID of the doctor to be deleted.

    Returns:
        200 - Doctor deleted
        404 - Doctor not found
        500 - Database error
    """
    if session.get("role") != "Admin":
        return jsonify({"error": "Unauthorized"}), 403

    doctor = db.session.get(Doctor, doctor_id)
    user = db.session.get(User, doctor_id)

    if not doctor or not user:
        return jsonify({"message": "Doctor not found"}), 404

    try:
        # Delete all appointments associated with the doctor
        Appointment.query.filter_by(doctor_id=doctor_id).delete()

        # Delete the doctor and user records
        db.session.delete(doctor)
        db.session.delete(user)
        db.session.commit()

        return (
            jsonify(
                {"message": "Doctor and associated appointments deleted successfully"}
            ),
            200,
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@app.route("/admin/patients/<int:patient_id>", methods=["DELETE", "OPTIONS"])
def delete_patient(patient_id):
    """
     Delete a patient and their associated appointments.

     Args:
         patient_id (int): The ID of the patient to be deleted.

    Returns:
         200 - Patient deleted
         404 - Patient not found
         500 - Database error
    """
    if request.method == "OPTIONS":
        return (
            jsonify({"message": "CORS preflight successful"}),
            200,
        )  # Handle preflight requests

    if session.get("role") != "Admin":
        return jsonify({"error": "Unauthorized"}), 403

    patient = db.session.get(Patient, patient_id)
    user = db.session.get(User, patient_id)

    if not patient or not user:
        return jsonify({"error": "Patient not found"}), 404

    try:
        # Delete related appointments first
        Appointment.query.filter_by(patient_id=patient_id).delete()

        # Delete patient and user records
        db.session.delete(patient)
        db.session.delete(user)
        db.session.commit()

        return jsonify({"message": "Patient deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@app.route("/admin/admins/<int:admin_id>", methods=["DELETE"])
def delete_admin(admin_id):
    """
    Deletes an admin user.

    Args:
        admin_id (int): The ID of the admin to delete.

    Returns:
        200 - Admin deleted
        404 - Admin not found
        500 - Database error
    """
    admin = User.query.get(admin_id)

    if not admin or admin.role != "Admin":
        return jsonify({"error": "Admin not found"}), 404

    try:
        db.session.delete(admin)
        db.session.commit()
        return jsonify({"message": "Admin deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Database error: {str(e)}"}), 500


# ------------------------- ERROR HANDLING -------------------------


@app.errorhandler(404)
def page_not_found(error):
    """Handles 404 errors (resource not found)."""
    return jsonify({"error": "Resource not found"}), 404


@app.errorhandler(500)
def internal_server_error(error):
    """Handles 500 errors (internal server error)."""
    return jsonify({"error": "Internal server error"}), 500


# ------------------------- RUN FLASK APP -------------------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
