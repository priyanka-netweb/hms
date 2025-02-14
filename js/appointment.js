// Fetch patient details from session
fetch("http://127.0.0.1:5000/dashboard", {
  method: "GET",
  credentials: "include",
})
  .then((response) => response.json())
  .then((data) => {
    if (data.error) {
      window.location.href = "login.html";
    } else {
      const patientName = data.name; // Get patient name
      const patientId = data.patient_id; // Get patient ID

      // Display welcome message
      document.getElementById("welcomeMessage").textContent =
        "Welcome " + patientName + "!";

      // Autofill Patient ID
      document.getElementById("patient_id").value = patientId;

      // Ensure only patients can access the page
      if (!data.role.includes("Patient")) {
        alert("Access denied. Only Patients can view this page.");
        window.location.href = "login.html";
      }
    }
  })
  .catch((error) => console.error("Error:", error));

///////////////////////////////////////////////////////////////////////////////////////////////////
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

document.addEventListener("DOMContentLoaded", function () {
  fetchDoctors();
});
////////////////////////////////////////////////////////////////////////////////////////////////////////
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
//////////////////////////////////////////////////////////////////////////////////////////
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
  // console.log("Fetching:", apiUrl); // Debugging line

  fetch(apiUrl)
    .then((response) => {
      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }
      return response.json();
    })
    .then((data) => {
      // console.log("Available Times:", data); // Debugging line
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

document.getElementById("logoutBtn").addEventListener("click", function () {
  fetch("http://127.0.0.1:5000/logout", {
    method: "POST",
    credentials: "include",
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
