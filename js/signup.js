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
      body: JSON.stringify({
        name: name,
        email: email,
        password: password,
        role: role,
      }),
    })
      .then((response) => response.json())
      .then((data) => {
        alert(data.message || data.error);
        if (data.message) {
          window.location.href = "login.html"; // Redirect to login page after signup
        }
      })
      .catch((error) => console.error("Error:", error));
  });
