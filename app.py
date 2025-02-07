from flask import Flask, jsonify, request, session
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from config import Config
from models import db, User, Doctor, Patient, Appointment  # Import models
from datetime import datetime, timedelta


app = Flask(__name__)
app.config.from_object(Config)

app.config["SECRET_KEY"] = "priyanka"
db.init_app(app)
bcrypt = Bcrypt(app)
CORS(app, supports_credentials=True)

#### sign up ####
@app.route("/signup", methods=["POST"])
def signup():
    data = request.get_json()

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
                specialty=data.get("specialty", "General"),
                available_slots=data.get("available_slots", "9:00AM-5:00PM"),
            )
            db.session.add(new_doctor)
            db.session.commit()  # Commit doctor record
        except Exception as e:
            db.session.rollback()  # Rollback if error occurs
            return jsonify({"error": f"Error adding doctor: {str(e)}"}), 500
    elif data["role"] == "Patient":
        try:
            new_patient = Patient(id=user_id, name=data["name"], email=data["email"])
            db.session.add(new_patient)
            db.session.commit()  # Commit patient record
        except Exception as e:
            db.session.rollback()  # Rollback if error occurs
            return jsonify({"error": f"Error adding patient: {str(e)}"}), 500

    return jsonify({"message": "User registered successfully!"}), 201

#### login ####
# we use POST to create a new resource, PUT to update an existing resource, and DELETE to remove a resource.
@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    user = User.query.filter_by(email=data["email"]).first()

    if user and user.check_password(data["password"]):
        session["user_id"] = user.id
        session["role"] = user.role
        return jsonify({"message": "Login successful!", "role": user.role})
    else:
        return jsonify({"error": "Invalid email or password"}), 401

#### logout ####
@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out successfully!"})


# @app.route("/dashboard", methods=["GET"])
# def dashboard():
#     if "user_id" not in session:
#         return jsonify({"error": "Unauthorized"}), 401
#     return jsonify({"message": f"Welcome {session['role']}!"})

@app.route("/dashboard", methods=["GET"])
def dashboard():
    if "role" not in session or "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    if session["role"] == "Patient":
        patient = Patient.query.get(session["user_id"])  
        if patient:
            return jsonify({
                "message": f"Welcome {patient.name}", 
                "name": patient.name,
                "patient_id": patient.id,
                "role": "Patient" 
            })
    
    return jsonify({"error": "Access denied"}), 403



# @app.route("/admin/doctors", methods=["GET"])
# def list_doctors():
#     if session.get("role") != "Admin":
#         return jsonify({"error": "Unauthorized"}), 403
#     doctors = Doctor.query.all()
#     return jsonify([{"id": doc.id, "name": doc.name} for doc in doctors])

# @app.route("/admin/patients", methods=["GET"])
# def list_patients():
#     if session.get("role") != "Admin":
#         return jsonify({"error": "Unauthorized"}), 403
#     patients = Patient.query.all()
#     return jsonify([{"id": pat.id, "name": pat.name} for pat in patients])


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


@app.route("/patient/book_appointment", methods=["POST"])
def book_appointment():
    if session.get("role") != "Patient":
        return jsonify({"error": "Unauthorized"}), 403

    data = request.get_json()

    doctor = Doctor.query.filter_by(name=data["doctor"]).first()
    if not doctor:
        return jsonify({"error": "Doctor not found"}), 404

    # Check if the time slot is already booked
    existing_appointment = Appointment.query.filter_by(
        doctor_id=doctor.id, date=data["date"], time_slot=data["time_slot"]
    ).first()

    if existing_appointment:
        return (
            jsonify(
                {"error": "This time slot is already taken. Please choose another one."}
            ),
            400,
        )

    # If the slot is free, create the appointment
    new_appointment = Appointment(
        patient_id=session["user_id"],
        doctor_id=doctor.id,
        date=data["date"],
        time_slot=data["time_slot"],
    )

    db.session.add(new_appointment)
    db.session.commit()

    return jsonify({"message": "Appointment booked successfully!"})


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
        return jsonify({"status": "success", "message": "Appointment booked successfully!"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": f"Database error: {str(e)}"}), 500


#####################################APPOINTMENT BOOKING##################################################


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
