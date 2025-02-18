document
  .getElementById("signupForm")
  .addEventListener("submit", function (event) {
    event.preventDefault();

    const name = document.getElementById("name").value;
    const email = document.getElementById("email").value;
    const password = document.getElementById("password").value;
    const role = document.getElementById("role").value;

    fetch("http://127.0.0.1:5000/signup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include", // Ensure cookies (JWT) are included
      body: JSON.stringify({
        name: name,
        email: email,
        password: password,
        role: role,
      }),
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.message) {
          alert(data.message); // Success message
          window.location.href = "login.html"; // Redirect to login page after signup
        } else {
          alert(data.error || "Signup failed. Please try again."); // Error handling
        }
      })
      .catch((error) => console.error("Error:", error));
  });
