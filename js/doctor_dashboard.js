// Helper function to get cookie value by name
function getCookie(name) {
  const cookies = document.cookie.split("; ");
  for (const cookie of cookies) {
    const [cookieName, cookieValue] = cookie.split("=");
    if (cookieName === name) {
      return decodeURIComponent(cookieValue);
    }
  }
  return null;
}

document.addEventListener("DOMContentLoaded", function () {
  // Fetch doctor details and ensure valid JWT token in cookies
  fetch("http://127.0.0.1:5000/dashboard", {
    method: "GET",
    credentials: "include", // Ensure JWT is sent in cookies
  })
    .then((response) => response.json())
    .then((data) => {
      if (!data || data.error) {
        window.location.href = "login.html"; // Redirect to login if no valid JWT
      } else {
        let role = data.role;
        if (role !== "Doctor") {
          alert("Access denied. Only doctors can view this page.");
          window.location.href = "login.html"; // Redirect if the role isn't doctor
        } else {
          document.getElementById(
            "roleDisplay"
          ).innerHTML = `Welcome Dr. ${(data.name).toUpperCase()}`;
          viewAppointments(); // Automatically load appointments
        }
      }
    })
    .catch((error) => console.error("Error:", error));
});

// Fetch and display doctor's appointments
function viewAppointments() {
  fetch(`http://127.0.0.1:5000/doctor/appointments?timestamp=${Date.now()}`, {
    method: "GET",
    credentials: "include", // Ensure JWT is sent in cookies
  })
    .then((response) => response.json())
    .then((data) => {
      const appointments = data.appointments; // Extract the array
      const appointmentsDiv = document.getElementById("appointmentsList");
      appointmentsDiv.innerHTML = "";

      if (!appointments || appointments.length === 0) {
        appointmentsDiv.innerHTML = "<p>No appointments found.</p>";
        return;
      }

      let table = `<table class='table'>
          <thead>
            <tr>
              <th>Patient Name</th>
              <th>Date</th>
              <th>Time</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>`;

      appointments.forEach((app) => {
        table += `<tr>
          <td>${app.patient_name}</td>
          <td>${app.date}</td>
          <td>${app.time}</td>
          <td id="status-${app.id}">${app.status || "pending"}</td>
          <td>
              <button class="btn btn-success btn-sm" onclick="markAsDone(${
                app.id
              })" ${app.status === "done" ? "disabled" : ""}>
                Mark as Done
              </button>
              <button class="btn btn-danger btn-sm" onclick="deleteAppointment(${
                app.id
              })">
                Delete
              </button>
          </td>
      </tr>`;
      });

      table += "</tbody></table>";
      appointmentsDiv.innerHTML = table;
    })
    .catch((error) => {
      console.error("Error loading appointments:", error);
      document.getElementById("appointmentsList").innerHTML =
        "<p>Error loading appointments.</p>";
    });
}

// Delete an appointment
function deleteAppointment(appointmentId) {
  if (confirm("Are you sure you want to delete this appointment?")) {
    const csrfToken = getCookie("csrf_access_token"); // Get CSRF token
    if (!csrfToken) {
      alert("CSRF token is missing. Please log in again.");
      return;
    }

    fetch(`http://127.0.0.1:5000/doctor/appointments/${appointmentId}`, {
      method: "DELETE",
      credentials: "include", // Ensure JWT is sent in cookies
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-TOKEN": csrfToken, // Send CSRF token
      },
    })
      .then((response) => {
        if (!response.ok) {
          return response.json().then((data) => {
            throw new Error(data.error || "Failed to delete appointment");
          });
        }
        return response.json();
      })
      .then((data) => {
        alert(data.message);
        viewAppointments();
      })
      .catch((error) => {
        console.error("Error deleting appointment:", error);
        alert("Error: " + error.message);
      });
  }
}

// Mark appointment as done
function markAsDone(appointmentId) {
  if (confirm("Are you sure this appointment is done?")) {
    const csrfToken = getCookie("csrf_access_token"); // Get CSRF token
    if (!csrfToken) {
      alert("CSRF token is missing. Please log in again.");
      return;
    }
    fetch(`http://127.0.0.1:5000/doctor/appointments/${appointmentId}/done`, {
      method: "PUT",
      credentials: "include", // Ensure JWT is sent in cookies
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-TOKEN": csrfToken, // Send CSRF token
      },
    })
      .then((response) => response.json())
      .then((data) => {
        alert(data.message);
        document.getElementById(`status-${appointmentId}`).innerText = "done"; // Update status immediately
        document.querySelector(
          `button[onclick="markAsDone(${appointmentId})"]`
        ).disabled = true; // Disable button
      })
      .catch((error) =>
        console.error("Error marking appointment as done:", error)
      );
  }
}

// Logout functionality
document
  .getElementById("logoutBtn")
  .addEventListener("click", async function () {
    try {
      // Retrieve CSRF token from cookies
      const csrfToken = getCookie("csrf_access_token");

      const response = await fetch("http://127.0.0.1:5000/logout", {
        method: "POST",
        credentials: "include", // Ensure JWT is sent in cookies
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-TOKEN": csrfToken, // Send CSRF token
        },
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Logout failed");
      }

      alert(data.message);
      window.location.href = "login.html"; // Redirect to login
    } catch (error) {
      console.error("Logout error:", error);
      alert("Session expired or invalid request. Redirecting to login.");
      window.location.href = "login.html";
    }
  });
