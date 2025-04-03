document.addEventListener("DOMContentLoaded", function () {
    console.log("✅ script.js loaded");

    const sidebar = document.getElementById("sidebar");
    const openSidebarBtn = document.getElementById("openSidebar");
    const closeSidebarBtn = document.getElementById("closeSidebar");
    const toggleThemeBtn = document.getElementById("toggleTheme");

    if (sidebar && openSidebarBtn && closeSidebarBtn) {
        openSidebarBtn.addEventListener("click", () => sidebar.classList.add("open"));
        closeSidebarBtn.addEventListener("click", () => sidebar.classList.remove("open"));
    }

    const existingSidebarBtns = document.querySelectorAll("#openSidebar");
    if (existingSidebarBtns.length > 1) {
        existingSidebarBtns.forEach((btn, index) => {
            if (index > 0) btn.remove();
        });
    }

    if (toggleThemeBtn) {
        const savedTheme = localStorage.getItem("theme");
        if (savedTheme === "dark") {
            document.body.classList.add("dark-theme");
            toggleThemeBtn.textContent = "🌞 Light Mode";
        }

        toggleThemeBtn.addEventListener("click", function () {
            document.body.classList.toggle("dark-theme");
            const isDark = document.body.classList.contains("dark-theme");
            localStorage.setItem("theme", isDark ? "dark" : "light");
            toggleThemeBtn.textContent = isDark ? "🌞 Light Mode" : "🌙 Dark Mode";
        });
    }

    const questionnaireForm = document.getElementById("questionnaire-form");
    const resultContainer = document.getElementById("result-container");
    const clearResultsBtn = document.getElementById("clear-results");

    if (questionnaireForm && resultContainer) {
        questionnaireForm.addEventListener("submit", function (event) {
            event.preventDefault();
            const email = localStorage.getItem("user_email");
            if (!email) return alert("⚠️ Please enter your details first!");

            const formData = new FormData(this);
            formData.append("email", email);
            const queryString = new URLSearchParams(formData).toString();

            resultContainer.innerHTML = "<p>🔄 Searching for EVs...</p>";
            fetch(`/results?${queryString}`, {
                method: "GET",
                headers: { "Content-Type": "application/json" }
            })
                .then(res => res.text())
                .then(html => {
                    resultContainer.innerHTML = html;
                    clearResultsBtn.style.display = "block";
                })
                .catch(() => {
                    resultContainer.innerHTML = "<p style='color:red;'>❌ An error occurred. Please try again.</p>";
                });
        });

        clearResultsBtn.addEventListener("click", () => {
            resultContainer.innerHTML = "";
            clearResultsBtn.style.display = "none";
        });
    }

    const recommendBtn = document.getElementById("getRecommendations");
    if (recommendBtn) {
        recommendBtn.addEventListener("click", function () {
            const budget = document.getElementById("price_max").value;
            const range = document.getElementById("range_min").value;

            fetch("/recommend", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ budget, range })
            })
                .then(res => res.json())
                .then(data => {
                    const resultDiv = document.getElementById("recommendations");
                    resultDiv.innerHTML = "<h3>🧠 Recommended EVs</h3>";

                    if (data.error) {
                        resultDiv.innerHTML += `<p style="color:red;">❌ ${data.error}</p>`;
                    } else {
                        data.recommendations.forEach(car => {
                            resultDiv.innerHTML += `<p>🚗 <strong>${car.brand}</strong> - Budget: €${car.budget}, Range: ${car.range} km</p>`;
                        });
                    }
                })
                .catch(error => console.error("❌ Error fetching recommendations:", error));
        });
    }

    document.body.addEventListener("click", function (event) {
        if (event.target.classList.contains("like-button")) {
            const carName = event.target.dataset.car;
            const email = prompt("📧 Enter your email to like this EV:");

            if (!email || email.trim() === "") return alert("⚠️ You must enter an email!");

            fetch("/like-ev", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ car_name: carName, email: email.trim() })
            })
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        event.target.disabled = true;
                        event.target.textContent = "❤️ Liked!";
                        showNotification(data.message);
                    } else {
                        showNotification(data.message, "warning");
                    }
                })
                .catch(error => console.error("❌ Error liking EV:", error));
        }
    });

    const registerForm = document.getElementById("register-form");
    if (registerForm) {
        registerForm.addEventListener("submit", function (event) {
            event.preventDefault();
            const formData = new FormData(this);
            const data = Object.fromEntries(formData.entries());

            fetch("/register", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(data)
            })
                .then(res => res.json())
                .then(data => {
                    alert(data.message || data.error);
                    if (data.success) window.location.href = "/login";
                })
                .catch(error => console.error("❌ Error registering:", error));
        });
    }

    const loginStatusDiv = document.getElementById("login-status");
    const userEmail = localStorage.getItem("user_email");

    if (loginStatusDiv && userEmail) {
        loginStatusDiv.innerHTML = `👤 Logged in as ${userEmail} <a href="/logout">Logout</a>`;
    }

    const loginForm = document.getElementById("login-form");
    const loginMsg = document.getElementById("login-message");

    if (loginForm) {
        console.log("✅ login-form found");

        loginForm.addEventListener("submit", function (e) {
            e.preventDefault();

            const formData = new FormData(loginForm);
            const data = Object.fromEntries(formData.entries());

            console.log("📦 Sending login data:", data);

            fetch("/login", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(data)
            })
                .then(res => res.json())
                .then(response => {
                    console.log("📨 Response received:", response);

                    if (loginMsg) {
                        loginMsg.textContent = response.message || response.error;
                        loginMsg.style.color = response.success ? "green" : "red";
                    }

                    if (response.success && response.redirect) {
                        localStorage.setItem("user_email", data.email);
                        setTimeout(() => {
                            window.location.href = response.redirect;
                        }, 1000);
                    }
                })
                .catch(error => {
                    console.error("❌ Error logging in:", error);
                    if (loginMsg) {
                        loginMsg.textContent = "❌ Login failed. Please try again.";
                        loginMsg.style.color = "red";
                    }
                });
        });
    }
});
