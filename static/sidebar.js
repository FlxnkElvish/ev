document.addEventListener("DOMContentLoaded", function () {
    const sidebarTitle = document.getElementById("sidebar-title");

    if (sidebarTitle) {
        sidebarTitle.textContent = document.title; 
    }

    const tooltips = {
        "/": "🏠 Home: Go back to the main dashboard.",
        "/analysis": "📊 Analysis: View trends and insights of EVs.",
        "/graphs": "📈 Graphs Section: See EV data visualizations.",
        "/finder": "🚗 EV Finder: Find the perfect EV based on your needs.",
        "/questionnaire": "📝 Questionnaire: Get EV recommendations."
    };

    document.querySelectorAll("#sidebar ul li a").forEach(link => {
        let tooltip = document.createElement("div");
        tooltip.className = "tooltip-box";
        tooltip.innerText = tooltips[link.getAttribute("href")] || "";
        document.body.appendChild(tooltip);

        link.addEventListener("mouseenter", function () {
            let rect = link.getBoundingClientRect();
            tooltip.style.top = `${rect.top + window.scrollY}px`;
            tooltip.style.left = `${rect.right + 10}px`;
            tooltip.classList.add("show-tooltip-box");
        });

        link.addEventListener("mouseleave", function () {
            setTimeout(() => {
                tooltip.classList.remove("show-tooltip-box");
            }, 300);
        });
    });
});
