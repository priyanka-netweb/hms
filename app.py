from flask import Flask, jsonify, request, session
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from config import Config
from models import db, User, Doctor, Patient, Appointment  # Import models

app = Flask(__name__)
app.config.from_object(Config)
app.config["SECRET_KEY"] = "priyanka"
db.init_app(app)
bcrypt = Bcrypt(app)
CORS(app, supports_credentials=True)

@app.route("/signup", methods=["POST"])
def signup():
    data = request.get_json()
    
    # Validate input
    if not data.get("name") or not data.get("email") or not data.get("password") or not data.get("role"):
        return jsonify({"error": "Missing required fields"}), 400

    # Check if email already exists in User table
    if User.query.filter_by(email=data["email"]).first():
        return jsonify({"error": "Email already exists"}), 400

    # Create a new User
    new_user = User(name=data["name"], email=data["email"], role=data["role"])
    new_user.set_password(data["password"])
    db.session.add(new_user)
    db.session.commit()

    # Get the user ID after commit
    user_id = new_user.id

    # Add user to respective table based on role
    if data["role"] == "Doctor":
        new_doctor = Doctor(id=user_id, name=data["name"], specialty=data.get("specialty", "General"))
        db.session.add(new_doctor)
    elif data["role"] == "Patient":
        new_patient = Patient(id=user_id, name=data["name"], email=data["email"])
        db.session.add(new_patient)
        
    db.session.commit()

    return jsonify({"message": "User registered successfully!"}), 201

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

@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out successfully!"})

@app.route("/dashboard", methods=["GET"])
def dashboard():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    return jsonify({"message": f"Welcome {session['role']}!"})

@app.route("/admin/doctors", methods=["GET"])
def list_doctors():
    if session.get("role") != "Admin":
        return jsonify({"error": "Unauthorized"}), 403
    doctors = Doctor.query.all()
    return jsonify([{ "id": doc.id, "name": doc.name } for doc in doctors])

@app.route("/admin/patients", methods=["GET"])
def list_patients():
    if session.get("role") != "Admin":
        return jsonify({"error": "Unauthorized"}), 403
    patients = Patient.query.all()
    return jsonify([{ "id": pat.id, "name": pat.name } for pat in patients])

@app.route("/patient/book_appointment", methods=["POST"])
def book_appointment():
    if session.get("role") != "Patient":
        return jsonify({"error": "Unauthorized"}), 403
    
    data = request.get_json()
    new_appointment = Appointment(
        patient_id=session["user_id"],
        doctor_id=data["doctor_id"],
        date=data["date"],
        time_slot=data["time_slot"],
        symptoms=data["symptoms"]
    )
    db.session.add(new_appointment)
    db.session.commit()
    return jsonify({"message": "Appointment booked successfully!"})

@app.route("/doctor/appointments", methods=["GET"])
def view_appointments():
    if session.get("role") != "Doctor":
        return jsonify({"error": "Unauthorized"}), 403
    appointments = Appointment.query.filter_by(doctor_id=session["user_id"]).all()
    return jsonify([{ "patient": app.patient.name, "date": app.date, "time": app.time_slot, "symptoms": app.symptoms } for app in appointments])

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
