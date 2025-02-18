document.addEventListener("DOMContentLoaded", function () {
  // Fetch admin details and verify the role using JWT in cookies
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
        if (role !== "Admin") {
          alert("Access denied. Only admins can view this page.");
          window.location.href = "login.html"; // Redirect if the role isn't admin
        } else {
          document.getElementById("roleDisplay").innerHTML = `Welcome, Admin`;
          // Optionally, load doctors, patients, and admins
          viewDoctors();
          viewPatients();
          viewAdmins();
        }
      }
    })
    .catch((error) => console.error("Error:", error));
});

// Fetch and display list of doctors
function viewDoctors() {
  fetch("http://127.0.0.1:5000/admin/doctors", {
    method: "GET",
    credentials: "include", // Ensure JWT is sent in cookies
  })
    .then((response) => response.json())
    .then((doctors) => {
      displayData(doctors, "Doctors", "doctor");
    })
    .catch((error) => console.error("Error loading doctors:", error));
}

// Fetch and display list of patients
function viewPatients() {
  fetch("http://127.0.0.1:5000/admin/patients", {
    method: "GET",
    credentials: "include", // Ensure JWT is sent in cookies
  })
    .then((response) => response.json())
    .then((patients) => {
      displayData(patients, "Patients", "patient");
    })
    .catch((error) => console.error("Error loading patients:", error));
}

// Fetch and display list of admins
function viewAdmins() {
  fetch("http://127.0.0.1:5000/admin/admins", {
    method: "GET",
    credentials: "include", // Ensure JWT is sent in cookies
  })
    .then((response) => response.json())
    .then((admins) => {
      displayData(admins, "Admins", "admin");
    })
    .catch((error) => console.error("Error loading admins:", error));
}

// Display list of doctors, patients, or admins
function displayData(items, title, type) {
  const dataDiv = document.getElementById("adminDataList");
  dataDiv.innerHTML = `<h4>${title} List</h4>`;
  if (items.length === 0) {
    dataDiv.innerHTML += "<p>No data found.</p>";
    return;
  }

  let table = `<table class='table'>
                <tr>
                  <th>Name</th>
                  <th>Email</th>
                  <th>Actions</th>
                </tr>`;
  items.forEach((item) => {
    table += `<tr>
                <td>${item.name}</td>
                <td>${item.email}</td>
                <td>
                  <button class="btn btn-danger btn-sm" onclick="deleteItem('${type}', ${item.id})">Delete</button>
                </td>
              </tr>`;
  });
  table += "</table>";
  dataDiv.innerHTML = table;
}

// Delete a doctor, patient, or admin
function deleteItem(type, itemId) {
  if (confirm(`Are you sure you want to delete this ${type}?`)) {
    fetch(`http://127.0.0.1:5000/admin/${type}s/${itemId}`, {
      method: "DELETE",
      credentials: "include", // Include JWT in cookies
      headers: {
        "Content-Type": "application/json",
      },
    })
      .then((response) => {
        if (!response.ok) {
          return response.json().then((data) => {
            throw new Error(data.error || "Failed to delete item");
          });
        }
        return response.json();
      })
      .then((data) => {
        alert(data.message);
        // Refresh the list after deleting
        if (type === "doctor") viewDoctors();
        else if (type === "patient") viewPatients();
        else if (type === "admin") viewAdmins();
      })
      .catch((error) => console.error(`Error deleting ${type}:`, error));
  }
}

// Logout functionality
document.getElementById("logoutBtn").addEventListener("click", function () {
  fetch("http://127.0.0.1:5000/logout", {
    method: "POST",
    credentials: "include", // Ensure JWT is sent in cookies
  })
    .then((response) => response.json())
    .then((data) => {
      alert(data.message);
      window.location.href = "login.html"; // Redirect to login page after logout
    });
});
