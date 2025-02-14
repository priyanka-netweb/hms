from flask import Flask, jsonify, request, session
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from config import Config
from models import db, User, Doctor, Patient, Appointment  # Import models
from datetime import datetime, timedelta

app = Flask(__name__)
app.config.from_object(Config)

app.config["SECRET_KEY"] = "priyanka"  # this must stay constant
db.init_app(app)
bcrypt = Bcrypt(app)
CORS(app, supports_credentials=True)


#### sign up ####
@app.route("/signup", methods=["POST"])
def signup():
    data = request.get_json() # Get JSON data from request from front-end

    # Validate input
    if (
        not data.get("name")
        or not data.get("email")
        or not data.get("password")
        or not data.get("role")
    ):
        return jsonify({"error": "Missing required fields"}), 400

    # Check if email already exists in User table
    if User.query.filter_by(email=data["email"]).first():
        return jsonify({"error": "Email already exists"}), 400

    # Create a new User
    new_user = User(name=data["name"], email=data["email"], role=data["role"])
    new_user.set_password(data["password"])

    try:
        db.session.add(new_user)
        db.session.commit()  # Commit the user record to generate ID

    except Exception as e:
        db.session.rollback()  # Rollback if error occurs
        return jsonify({"error": f"Error adding user: {str(e)}"}), 500

    # Get the user ID after commit
    user_id = new_user.id

    # Add user to respective table based on role
    if data["role"] == "Doctor":
        try:
            new_doctor = Doctor(
                id=user_id,
                name=data["name"],
                email=data["email"],
                specialty=data.get("specialty", "General"),
                available_slots=data.get("available_slots", "9:00AM-5:00PM"),
            )
            db.session.add(new_doctor)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": f"Error adding doctor: {str(e)}"}), 500
    elif data["role"] == "Patient":
        try:
            new_patient = Patient(id=user_id, name=data["name"], email=data["email"])
            db.session.add(new_patient)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": f"Error adding patient: {str(e)}"}), 500

    return jsonify({"message": "User registered successfully!"}), 201


#### login ####
# we use POST to create a new resource, PUT to update an existing resource, and DELETE to remove a resource.
@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    user = User.query.filter_by(email=email).first()

    if user and user.check_password(password):  # Use check_password method
        session["user_id"] = user.id
        session["role"] = user.role
        session["email"] = user.email
        return jsonify({"message": f"Welcome {user.role}", "role": user.role}), 200
    else:
        return jsonify({"error": "Invalid credentials"}), 401


#### logout ####
@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out successfully!"})


@app.route("/dashboard", methods=["GET"])
def dashboard():
    if "role" not in session or "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    if session["role"] == "Patient":
        patient = Patient.query.get(session["user_id"])
        if patient:
            return jsonify(
                {
                    "message": f"Welcome {patient.name}",
                    "name": patient.name,
                    "patient_id": patient.id,
                    "role": "Patient",
                }
            )

    elif session["role"] == "Doctor":
        doctor = Doctor.query.get(session["user_id"])
        if doctor:
            return jsonify(
                {
                    "message": f"Welcome Dr. {doctor.name}",
                    "name": doctor.name,
                    "doctor_id": doctor.id,
                    "role": "Doctor",
                }
            )

    elif session["role"] == "Admin":
        return jsonify(
            {
                # "message": "Welcome Admin",
                "role": "Admin"
            }
        )

    return jsonify({"error": "Access denied"}), 403


#####################################APPOINTMENT BOOKING##################################################


@app.route("/doctors", methods=["GET"])
def get_doctors():
    doctors = Doctor.query.all()
    # print("Doctors Found:", doctors)  # Debugging Line
    doctor_list = [{"name": doc.name, "specialty": doc.specialty} for doc in doctors]
    return jsonify({"doctors": doctor_list})


@app.route("/available-times/<doctor_name>/<date>", methods=["GET"])
def available_times(doctor_name, date):
    doctor = Doctor.query.filter_by(name=doctor_name).first()
    if not doctor:
        return jsonify({"error": "Doctor not found"}), 404

    try:
        # Generate hourly time slots between 9:00 AM and 5:00 PM
        available_times = []
        start_time = datetime.strptime("09:00AM", "%I:%M%p")
        end_time = datetime.strptime("05:00PM", "%I:%M%p")

        while start_time < end_time:
            available_times.append(start_time.strftime("%I:%M%p"))
            start_time += timedelta(hours=1)  # Increment by 1 hour

        # Get all booked appointments for this doctor on the given date
        appointments = Appointment.query.filter_by(doctor_id=doctor.id, date=date).all()
        booked_times = {appointment.time_slot for appointment in appointments}

        # Remove booked times from available slots
        available_times = [time for time in available_times if time not in booked_times]

        return jsonify({"available_times": available_times})

    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route("/book-appointment-api", methods=["POST"])
def book_appointment_api():
    data = request.get_json()
    patient_id = data.get("patient_id")
    doctor_name = data.get("doctor")
    date = data.get("date")
    time_slot = data.get("time")

    if not patient_id or not doctor_name or not date or not time_slot:
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


#######################################APPOINTMENT BOOKING##################################################


########################################DOCTOR DASHBOARD#################################################


@app.route("/doctor/appointments", methods=["GET"])
def get_doctor_appointments():
    if "role" not in session or session["role"] != "Doctor":
        return jsonify({"error": "Unauthorized"}), 403

    doctor_id = session["user_id"]
    appointments = Appointment.query.filter_by(doctor_id=doctor_id).all()

    if not appointments:
        return jsonify([])  # Return an empty list if no appointments found

    appointment_list = []
    for app in appointments:
        patient = Patient.query.get(app.patient_id)
        appointment_list.append(
            {
                "id": app.id,
                "patient_name": patient.name if patient else "Unknown",
                "date": app.date,
                "time": app.time_slot,
                "status": app.status,  # Include the status field
            }
        )

    return jsonify(appointment_list)


@app.route("/doctor/appointments/<int:appointment_id>", methods=["DELETE"])
def delete_appointment(appointment_id):
    if "role" not in session or session["role"] != "Doctor":
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
    if "role" not in session or session["role"] != "Doctor":
        return jsonify({"error": "Unauthorized"}), 403

    appointment = Appointment.query.get(appointment_id)
    if not appointment:
        return jsonify({"error": "Appointment not found"}), 404

    if appointment.doctor_id != session["user_id"]:
        return jsonify({"error": "Unauthorized to mark this appointment"}), 403

    appointment.status = (
        "done"  # Add a "status" column to your Appointment table if it doesn't exist
    )
    db.session.commit()
    return jsonify({"message": "Appointment marked as done"})


########################################DOCTOR DASHBOARD#################################################


######################################## ADMIN DASHBOARD #################################################


# Fetch all doctors
@app.route("/admin/doctors", methods=["GET"])
def list_doctors():
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


# Fetch all patients
@app.route("/admin/patients", methods=["GET"])
def list_patients():
    if session.get("role") != "Admin":
        return jsonify({"error": "Unauthorized"}), 403
    patients = Patient.query.all()
    return jsonify(
        [{"id": pat.id, "name": pat.name, "email": pat.email} for pat in patients]
    )


# Fetch all admins
@app.route("/admin/admins", methods=["GET"])
def list_admins():
    if session.get("role") != "Admin":
        return jsonify({"error": "Unauthorized"}), 403
    admins = User.query.filter_by(role="Admin").all()
    return jsonify(
        [{"id": admin.id, "name": admin.name, "email": admin.email} for admin in admins]
    )


# Delete a doctor
@app.route("/admin/doctors/<int:doctor_id>", methods=["DELETE"])
def delete_doctor(doctor_id):
    if session.get("role") != "Admin":
        return jsonify({"error": "Unauthorized"}), 403

    doctor = db.session.get(Doctor, doctor_id)
    user = db.session.get(User, doctor_id)  # Assuming doctor_id == user_id

    if not doctor or not user:
        return jsonify({"message": "Doctor not found"}), 404

    try:
        # Delete all appointments associated with the doctor
        Appointment.query.filter_by(doctor_id=doctor_id).delete()

        # Delete the doctor and user
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


# Delete a patient
@app.route("/admin/patients/<int:patient_id>", methods=["DELETE", "OPTIONS"])
def delete_patient(patient_id):
    if request.method == "OPTIONS":
        response = jsonify({"message": "CORS preflight successful"})
        response.status_code = 200
        return response  # 👈 Handles preflight requests

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


# Delete an admin
@app.route("/admin/admins/<int:admin_id>", methods=["DELETE"])
def delete_admin(admin_id):
    if session.get("role") != "Admin":
        return jsonify({"error": "Unauthorized"}), 403

    admin = User.query.get(admin_id)

    if not admin or admin.role != "Admin":
        return jsonify({"error": "Admin not found"}), 404

    try:
        db.session.delete(admin)
        db.session.commit()
        return jsonify({"message": "Admin deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# Add a new admin
# @app.route("/admin/add_admin", methods=["POST"])
# def add_admin():
#     if session.get("role") != "Admin":
#         return jsonify({"error": "Unauthorized"}), 403

#     data = request.get_json()
#     name = data.get("name")
#     email = data.get("email")
#     password = data.get("password")

#     if not name or not email or not password:
#         return jsonify({"error": "Missing required fields"}), 400

#     if User.query.filter_by(email=email).first():
#         return jsonify({"error": "Email already exists"}), 400

#     new_admin = User(name=name, email=email, role="Admin")
#     new_admin.set_password(password)

#     db.session.add(new_admin)
#     db.session.commit()
#     return jsonify({"message": "Admin added successfully"}), 201


######################################## ADMIN DASHBOARD #################################################


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
