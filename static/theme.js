document.addEventListener("DOMContentLoaded", function () {
    const themeToggle = document.getElementById("theme-toggle");
    const body = document.body;

    const savedTheme = localStorage.getItem("theme") || "light"; 
    body.classList.add(savedTheme === "dark" ? "dark-mode" : "light-mode");
    themeToggle.textContent = savedTheme === "dark" ? "🌙 Dark Mode" : "🌞 Light Mode";


    themeToggle.addEventListener("click", function () {
        if (body.classList.contains("dark-mode")) {
            body.classList.remove("dark-mode");
            body.classList.add("light-mode");
            localStorage.setItem("theme", "light");
            themeToggle.textContent = "🌞 Light Mode";
        } else {
            body.classList.remove("light-mode");
            body.classList.add("dark-mode");
            localStorage.setItem("theme", "dark");
            themeToggle.textContent = "🌙 Dark Mode";
        }
    });


    function removeOverlay() {
        const overlay = document.getElementById("userPopupOverlay");
        const popup = document.getElementById("userPopup");

        if (overlay) {
            overlay.style.opacity = "0";  
            setTimeout(() => {
                overlay.style.display = "none";
                overlay.remove(); 
            }, 200); 
        }

        if (popup) {
            popup.style.opacity = "0"; 
            setTimeout(() => {
                popup.style.display = "none"; 
            }, 200);
        }

        document.body.style.overflow = "auto"; 
        console.log("✅ Overlay and popup removed.");
    }

    
    const skipButton = document.getElementById("skipPopup");
    if (skipButton) {
        skipButton.addEventListener("click", function () {
            console.log("✅ Skip clicked - removing overlay...");
            sessionStorage.setItem("popupDismissed", "true");
            removeOverlay();
        });
    }

   
    const userForm = document.getElementById("userForm");
    if (userForm) {
        userForm.addEventListener("submit", function (event) {
            event.preventDefault(); 
            console.log("✅ Form submitted - removing overlay...");

            const formData = new FormData(userForm);
            fetch("/save-user", {
                method: "POST",
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    alert("Error: " + data.error);
                } else {
                    localStorage.setItem("user_email", formData.get("email"));
                    sessionStorage.setItem("popupDismissed", "true");
                    removeOverlay();
                }
            })
            .catch(error => console.error("❌ Error submitting form:", error));
        });
    }
});
