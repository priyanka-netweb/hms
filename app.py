from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from config import Config
from models import db, User, Doctor, Patient, Appointment  # Import models
from datetime import datetime, timedelta
import time
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    jwt_required,
    get_jwt_identity,
    get_jwt,
    set_access_cookies,
)

# Initialize Flask app
app = Flask(__name__)

# Enable CORS
CORS(app, supports_credentials=True)

# Configure app
app.config.from_object(Config)
app.config["JWT_SECRET_KEY"] = (
    "5hufr8fh4i5hs8gh4iw9427hd"  # Change this key to something secure
)
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=1)
app.config["JWT_TOKEN_LOCATION"] = ["cookies"]  # Store JWT in cookies
app.config["JWT_COOKIE_SECURE"] = True  # Ensures cookie is sent only over HTTPS
app.config["JWT_COOKIE_HTTPONLY"] = True  # Prevents JavaScript access to cookies
app.config["JWT_COOKIE_SAMESITE"] = "Lax"  # Prevents CSRF attacks

# Initialize extensions
jwt = JWTManager(app)
db.init_app(app)
bcrypt = Bcrypt(app)


# ------------------------- AUTHENTICATION & AUTHORIZATION using using JWT Tokens -------------------------
@app.route("/signup", methods=["POST"])
def signup():
    """
    Handles user registration.

    Expected JSON payload:
    {
        "name": "John Doe",
        "email": "johndoe@example.com",
        "password": "securepassword",
        "role": "Doctor/Patient/Admin"
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

    # Validate role
    if data["role"] not in ["Doctor", "Patient", "Admin"]:
        return (
            jsonify(
                {
                    "error": "Invalid role. Please select 'Doctor', 'Patient', or 'Admin'."
                }
            ),
            400,
        )

    # For Doctor or Patient, create a corresponding entry in the respective table
    user_id = new_user.id
    if data["role"] == "Doctor":
        new_role_entry = Doctor(
            id=user_id,
            name=data["name"],
            email=data["email"],
            specialty=data.get("specialty", "General"),
            available_slots=data.get("available_slots", "9:00AM-5:00PM"),
        )
        try:
            db.session.add(new_role_entry)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": f"Error adding doctor: {str(e)}"}), 500
    elif data["role"] == "Patient":
        new_role_entry = Patient(id=user_id, name=data["name"], email=data["email"])
        try:
            db.session.add(new_role_entry)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": f"Error adding patient: {str(e)}"}), 500

    response = jsonify({"message": "Signup successful!", "role": data["role"]})
    return response, 201


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

        # instead of Generating JWT token we will use HTTP-only cookies to store JWTs, to prevent token leaks.
        access_token = create_access_token(
            identity=str(user.id), expires_delta=timedelta(hours=1)
        )
        response = jsonify(
            {"message": f"Welcome {user.role}!", "role": user.role, "name": user.name}
        )
        set_access_cookies(response, access_token)
        return response, 200

    return jsonify({"error": "Invalid credentials"}), 401


revoked_tokens = {}


@app.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    jti = get_jwt()["jti"]
    revoked_tokens[jti] = time.time() + 3600  # Revoke token for 1 hour

    # Create a response object
    response = jsonify({"message": "Logged out successfully"})

    # Expire the cookies immediately
    response.set_cookie(
        "access_token_cookie",
        "",
        expires=0,
        httponly=True,
        samesite="None",
        secure=True,
    )
    response.set_cookie(
        "csrf_access_token", "", expires=0, httponly=False, samesite="None", secure=True
    )

    return response, 200


# ------------------------- GET USER DETAILS -------------------------
@app.route("/me", methods=["GET"])
@jwt_required()
def get_current_user():
    """Fetches user details from the JWT token."""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user:
        return jsonify({"error": "User not found"}), 404

    return (
        jsonify(
            {"id": user.id, "name": user.name, "email": user.email, "role": user.role}
        ),
        200,
    )


# ------------------------- DASHBOARD -------------------------


@app.route("/dashboard", methods=["GET"])
@jwt_required()
def dashboard():
    """
    Returns dashboard information based on user role.

    Returns:
        401 - Unauthorized
        403 - Access denied
        200 - User-specific dashboard data
    """
    current_user_id = get_jwt_identity()  # Get user ID from JWT token
    user = User.query.get(current_user_id)
    if user.role not in ["Doctor", "Patient", "Admin"]:
        return jsonify({"error": "Invalid role"}), 403

    if user.role == "Patient":
        patient = Patient.query.get(current_user_id)
        if patient:
            return jsonify(
                {
                    "message": f"Welcome {patient.name}",
                    "patient_id": patient.id,
                    "role": "Patient",
                    "name": patient.name,
                }
            )

    elif user.role == "Doctor":
        doctor = Doctor.query.get(current_user_id)
        if doctor:
            return jsonify(
                {
                    "message": f"Welcome Dr. {doctor.name}",
                    "doctor_id": doctor.id,
                    "role": "Doctor",
                    "name": doctor.name,
                    "specialty": doctor.specialty,
                }
            )

    elif user.role == "Admin":
        return jsonify({"message": "Welcome Admin", "role": "Admin"})

    return jsonify({"error": "Access denied"}), 403


# ------------------------- DOCTOR MANAGEMENT -------------------------


@app.route("/doctors", methods=["GET"])
@jwt_required()
def get_doctors():
    """Returns a list of all doctors."""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    # Allow access to Patients, Doctors, and Admins
    if user.role in ["Doctor", "Patient", "Admin"]:
        doctors = Doctor.query.all()
        doctor_list = [
            {"id": doc.id, "name": doc.name, "specialty": doc.specialty}
            for doc in doctors
        ]
        return jsonify({"doctors": doctor_list}), 200

    return jsonify({"error": "Unauthorized"}), 403


# ------------------------- APPOINTMENT MANAGEMENT -------------------------


@app.route("/available-times/<doctor_name>/<date>", methods=["GET"])
@jwt_required()
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

    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    # Patients, Doctors, and Admins can access this route
    if user.role not in ["Doctor", "Admin", "Patient"]:
        return jsonify({"error": "Unauthorized"}), 403

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
@jwt_required()
def book_appointment_api():
    """Handles booking of an appointment."""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    # Allow only Patients and Admins to book appointments
    if user.role not in ["Patient", "Admin"]:
        return jsonify({"error": "Unauthorized"}), 403

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
        return (
            jsonify({"status": "error", "message": "Time slot already booked"}),
            400,
        )

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
        return (
            jsonify({"status": "error", "message": f"Database error: {str(e)}"}),
            500,
        )


# ------------------------- DOCTOR DASHBOARD -------------------------


@app.route("/doctor/appointments", methods=["GET"])
@jwt_required()
def get_doctor_appointments():
    """
    Fetch all appointments assigned to the logged-in doctor.

    Returns:
        JSON: List of appointments with patient details.
    """
    current_user_id = get_jwt_identity()  # Get user ID from JWT token
    user = User.query.get(current_user_id)

    if user.role != "Doctor":
        return jsonify({"error": "Unauthorized"}), 403

    doctor = Doctor.query.get(current_user_id)
    if not doctor:
        return jsonify({"error": "Doctor not found"}), 404

    # Fetch all appointments for the doctor
    appointments = Appointment.query.filter_by(doctor_id=doctor.id).all()

    # Fetch patient details in one go
    patient_ids = [app.patient_id for app in appointments]
    patients = {
        p.id: p.name for p in Patient.query.filter(Patient.id.in_(patient_ids)).all()
    }

    # Map the appointments to include patient names
    appointments_data = [
        {
            "id": app.id,
            "patient_name": patients.get(app.patient_id, "Unknown"),
            "date": app.date,
            "time": app.time_slot,
            "status": app.status,
        }
        for app in appointments
    ]

    return jsonify({"appointments": appointments_data}), 200


@app.route("/doctor/appointments/<int:appointment_id>", methods=["DELETE"])
@jwt_required()
def delete_appointment(appointment_id):
    """
    Allow a doctor to delete an appointment they own.

    Args:
        appointment_id (int): The ID of the appointment to be deleted.

    Returns:
        200 - Appointment deleted
        403 - Unauthorized
        404 - Appointment not found
        500 - Database error
    """
    current_user_id = get_jwt_identity()  # Retrieve user ID from JWT
    user = User.query.get(current_user_id)

    if user.role != "Doctor":
        return jsonify({"error": "Unauthorized role"}), 403

    appointment = Appointment.query.get(appointment_id)
    if not appointment:
        return jsonify({"error": "Appointment not found"}), 404

    if int(appointment.doctor_id) != int(current_user_id):
        return jsonify({"error": "Unauthorized to delete this appointment"}), 403

    try:
        db.session.delete(appointment)
        db.session.commit()
        return jsonify({"message": "Appointment deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Database error: {str(e)}"}), 500


@app.route("/doctor/appointments/<int:appointment_id>/done", methods=["PUT"])
@jwt_required()
def mark_appointment_done(appointment_id):
    """
    Allow a doctor to mark an appointment as 'done'.

    Args:
        appointment_id (int): The ID of the appointment.

    Returns:
        JSON: Success or error message.
    """
    current_user_id = get_jwt_identity()  # Retrieve user ID from JWT
    user = User.query.get(current_user_id)

    if user.role != "Doctor":
        return jsonify({"error": "Unauthorized"}), 403

    appointment = Appointment.query.get(appointment_id)
    if not appointment:
        return jsonify({"error": "Appointment not found"}), 404

    if int(appointment.doctor_id) != int(current_user_id):
        return jsonify({"error": "Unauthorized to mark this appointment as done"}), 403

    try:
        appointment.status = "done"
        db.session.commit()
        return jsonify({"message": "Appointment marked as done"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Database error: {str(e)}"}), 500


# ------------------------- ADMIN DASHBOARD -------------------------


@app.route("/admin/doctors", methods=["GET"])
@jwt_required()
def list_doctors():
    """
    Fetch all doctors.

    Returns:
        JSON: List of doctors.
    """
    current_user_id = get_jwt_identity()  # Retrieve user ID from JWT
    user = User.query.get(current_user_id)

    if user.role != "Admin":
        return jsonify({"error": "Unauthorized"}), 403

    doctors = Doctor.query.all()
    doctor_list = [
        {
            "id": doc.id,
            "name": doc.name,
            "email": doc.email,
            "specialty": doc.specialty,
        }
        for doc in doctors
    ]
    return jsonify({"doctors": doctor_list}), 200


@app.route("/admin/patients", methods=["GET"])
@jwt_required()
def list_patients():
    """
    Fetch all patients.

    Returns:
        JSON: List of patients.
    """
    current_user_id = get_jwt_identity()  # Retrieve user ID from JWT
    user = User.query.get(current_user_id)

    if user.role != "Admin":
        return jsonify({"error": "Unauthorized"}), 403

    patients = Patient.query.all()
    patient_list = [
        {"id": pat.id, "name": pat.name, "email": pat.email} for pat in patients
    ]

    return jsonify({"patients": patient_list}), 200


@app.route("/admin/admins", methods=["GET"])
@jwt_required()
def list_admins():
    """
    Fetch all admins.

    Returns:
        JSON: List of admins.
    """
    current_user_id = get_jwt_identity()  # Retrieve user ID from JWT
    user = User.query.get(current_user_id)

    if user.role != "Admin":
        return jsonify({"error": "Unauthorized"}), 403

    admins = User.query.filter_by(role="Admin").all()
    admin_list = [
        {"id": admin.id, "name": admin.name, "email": admin.email} for admin in admins
    ]

    return jsonify({"admins": admin_list}), 200


@app.route("/admin/doctors/<int:doctor_id>", methods=["DELETE"])
@jwt_required()
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
    current_user_id = get_jwt_identity()  # Retrieve user ID from JWT
    user = User.query.get(current_user_id)

    if user.role != "Admin":
        return jsonify({"error": "Unauthorized"}), 403

    doctor = Doctor.query.get(doctor_id)
    user_account = User.query.get(doctor_id)

    if not doctor or not user_account:
        return jsonify({"message": "Doctor not found"}), 404

    try:
        # Delete all appointments related to the doctor
        Appointment.query.filter_by(doctor_id=doctor_id).delete()

        # Delete doctor profile and associated user account
        db.session.delete(doctor)
        db.session.delete(user_account)
        db.session.commit()

        return (
            jsonify(
                {"message": "Doctor and associated appointments deleted successfully"}
            ),
            200,
        )

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Database error: {str(e)}"}), 500


@app.route("/admin/patients/<int:patient_id>", methods=["DELETE", "OPTIONS"])
@jwt_required()
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

    current_user_id = get_jwt_identity()  # Retrieve user ID from JWT
    user = User.query.get(current_user_id)

    if user.role != "Admin":
        return jsonify({"error": "Unauthorized"}), 403

    patient = Patient.query.get(patient_id)
    user_account = User.query.get(patient_id)

    if not patient or not user_account:
        return jsonify({"error": "Patient not found"}), 404

    try:
        # Delete related appointments first
        Appointment.query.filter_by(patient_id=patient_id).delete()

        # Delete patient and user records
        db.session.delete(patient)
        db.session.delete(user_account)
        db.session.commit()

        return (
            jsonify(
                {"message": "Patient and associated appointments deleted successfully"}
            ),
            200,
        )

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Database error: {str(e)}"}), 500


@app.route("/admin/admins/<int:admin_id>", methods=["DELETE"])
@jwt_required()
def delete_admin(admin_id):
    """
    Deletes an admin user.

    Args:
        admin_id (int): The ID of the admin to delete.

    Returns:
        200 - Admin deleted
        400 - Cannot delete own account
        404 - Admin not found
        500 - Database error
    """
    current_user_id = get_jwt_identity()  # Retrieve user ID from JWT
    user = User.query.get(current_user_id)

    if not user or user.role != "Admin":
        return jsonify({"error": "Unauthorized"}), 403

    admin = User.query.get(admin_id)

    if not admin:
        return jsonify({"error": "Admin not found"}), 404

    if admin.id == user.id:
        return jsonify({"error": "You cannot delete yourself!"}), 400
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
