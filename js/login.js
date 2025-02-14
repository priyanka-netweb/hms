credentials: "include";
document
  .getElementById("loginForm")
  .addEventListener("submit", function (event) {
    event.preventDefault();

    const email = document.getElementById("email").value;
    const password = document.getElementById("password").value;

    fetch("http://127.0.0.1:5000/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ email, password }),
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.message) {
          alert("Login successful! Role: " + data.role);

          // Store role in localStorage or sessionStorage for later use
          localStorage.setItem("userRole", data.role);

          // Redirect based on role
          if (data.role === "Admin") {
            window.location.href = "admin_dashboard.html";
          } else if (data.role === "Doctor") {
            window.location.href = "doctor_dashboard.html";
          } else if (data.role === "Patient") {
            window.location.href = "appointment.html";
          } else {
            // window.location.href = "dashboard.html"; // Default redirect
            alert("Invalid role.");
          }
        } else {
          alert("Invalid credentials.");
        }
      })
      .catch((error) => console.error("Error:", error));
  });
