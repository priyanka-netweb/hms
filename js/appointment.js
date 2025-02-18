// Fetch patient details from session (Ensure patient is logged in)
fetch("http://127.0.0.1:5000/dashboard", {
  method: "GET",
  credentials: "include", // Include JWT token via cookies
})
  .then((response) => response.json())
  .then((data) => {
    if (data.error) {
      window.location.href = "login.html"; // Redirect to login if no valid JWT
    } else {
      const patientName = data.name; // Get patient name
      const patientId = data.patient_id; // Get patient ID

      // Display welcome message
      document.getElementById("welcomeMessage").textContent =
        "Welcome " + patientName + "!";
      
      // Autofill Patient ID
      document.getElementById("patient_id").value = patientId;

      // Ensure only patients can access the page
      if (data.role !== "Patient") {
        alert("Access denied. Only Patients can view this page.");
        window.location.href = "login.html"; // Redirect if the role isn't patient
      }
    }
  })
  .catch((error) => {
    console.error("Error:", error);
    window.location.href = "login.html"; // In case of any error, redirect to login
  });

// Booking Appointment
document
  .getElementById("appointmentForm")
  .addEventListener("submit", function (event) {
    event.preventDefault(); // Prevent default form submission

    let patientId = document.getElementById("patient_id").value;
    let doctor = document.getElementById("doctor").value;
    let date = document.getElementById("date").value;
    let time = document.getElementById("time").value;

    if (!patientId || !doctor || !date || !time) {
      alert("Please fill all fields.");
      return;
    }

    let appointmentData = { patient_id: patientId, doctor, date, time };

    fetch("http://127.0.0.1:5000/book-appointment-api", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include", // Ensure JWT is sent in cookies
      body: JSON.stringify(appointmentData),
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.status === "success") {
          alert("Appointment booked successfully!");
          let savedPatientId = document.getElementById("patient_id").value;

          document.getElementById("appointmentForm").reset(); // Reset form

          document.getElementById("patient_id").value = savedPatientId;
        } else {
          alert("Error: " + data.message);
        }
      })
      .catch((error) => {
        console.error("Error booking appointment:", error);
        alert("Failed to book appointment.");
      });
  });

// Fetching available doctors for the dropdown
document.addEventListener("DOMContentLoaded", function () {
  fetchDoctors();
});

// Fetch available doctors
function fetchDoctors() {
  fetch("http://127.0.0.1:5000/doctors")
    .then((response) => response.json())
    .then((data) => {
      let doctorDropdown = document.getElementById("doctor");
      doctorDropdown.innerHTML = '<option value="">Select a Doctor</option>'; // Default option

      if (data.doctors.length === 0) {
        doctorDropdown.innerHTML =
          '<option value="">No doctors available</option>';
      } else {
        data.doctors.forEach((doc) => {
          let option = document.createElement("option");
          option.value = doc.name;
          option.textContent = `${doc.name} (${doc.specialty})`;
          doctorDropdown.appendChild(option);
        });
      }
    })
    .catch((error) => {
      console.error("Error fetching doctors:", error);
      doctorDropdown.innerHTML =
        '<option value="">Error loading doctors</option>';
    });
}

// Fetch available times based on selected doctor and date
function fetchAvailableTimes() {
  let doctorName = document.getElementById("doctor").value;
  let date = document.getElementById("date").value;
  let timeDropdown = document.getElementById("time");
  let submitBtn = document.getElementById("submitBtn");

  if (!doctorName || !date) {
    console.log("Doctor or date not selected.");
    timeDropdown.innerHTML = '<option value="">Select a Date First</option>';
    submitBtn.disabled = true;
    return;
  }

  let apiUrl = `http://127.0.0.1:5000/available-times/${encodeURIComponent(
    doctorName
  )}/${date}`;

  fetch(apiUrl)
    .then((response) => {
      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }
      return response.json();
    })
    .then((data) => {
      timeDropdown.innerHTML = ""; // Clear old options
      if (data.available_times.length === 0) {
        timeDropdown.innerHTML = '<option value="">No slots available</option>';
        submitBtn.disabled = true;
      } else {
        data.available_times.forEach((time) => {
          let option = document.createElement("option");
          option.value = time;
          option.textContent = time;
          timeDropdown.appendChild(option);
        });
        submitBtn.disabled = false;
      }
    })
    .catch((error) => {
      console.error("Error fetching available times:", error);
      timeDropdown.innerHTML = '<option value="">Error loading slots</option>';
      submitBtn.disabled = true;
    });
}

// Logout
document.getElementById("logoutBtn").addEventListener("click", function () {
  fetch("http://127.0.0.1:5000/logout", {
    method: "POST",
    credentials: "include", // Ensure JWT is sent in cookies
  })
    .then((response) => response.json())
    .then((data) => {
      alert(data.message);
      window.location.href = "login.html";
    });
});

document.getElementById("date").addEventListener("change", fetchAvailableTimes);
document
  .getElementById("doctor")
  .addEventListener("change", fetchAvailableTimes);