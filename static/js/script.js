// ---------- Sidebar toggle (mobile) ----------
const sidebarToggle = document.getElementById("sidebarToggle");
const sidebar = document.getElementById("sidebar");
if (sidebarToggle && sidebar) {
    sidebarToggle.addEventListener("click", () => sidebar.classList.toggle("open"));
}

// ---------- Dark mode ----------
const themeToggle = document.getElementById("themeToggle");
function applyTheme(theme) {
    document.body.classList.toggle("dark-mode", theme === "dark");
    if (themeToggle) {
        themeToggle.innerHTML = theme === "dark"
            ? '<i class="fa-solid fa-sun"></i>'
            : '<i class="fa-solid fa-moon"></i>';
    }
}
const savedTheme = localStorage.getItem("medi-theme") || "light";
applyTheme(savedTheme);
if (themeToggle) {
    themeToggle.addEventListener("click", () => {
        const next = document.body.classList.contains("dark-mode") ? "light" : "dark";
        localStorage.setItem("medi-theme", next);
        applyTheme(next);
    });
}

// ---------- Live clock ----------
const liveClock = document.getElementById("liveClock");
function tickClock() {
    if (!liveClock) return;
    const now = new Date();
    liveClock.textContent = now.toLocaleString([], {
        weekday: "short", month: "short", day: "numeric",
        hour: "2-digit", minute: "2-digit"
    });
}
tickClock();
setInterval(tickClock, 1000 * 30);

// ---------- Reminder polling (voice + browser notification) ----------
// Runs on every logged-in page so a due medicine is announced no matter
// where the user is in the app.
if (document.getElementById("sidebar")) {
    if ("Notification" in window && Notification.permission === "default") {
        Notification.requestPermission();
    }

    const alreadyAnnounced = new Set(JSON.parse(sessionStorage.getItem("medi-announced") || "[]"));

    function speak(text) {
        if (!("speechSynthesis" in window)) return;
        const utter = new SpeechSynthesisUtterance(text);
        utter.rate = 0.95;
        window.speechSynthesis.speak(utter);
    }

    function announce(med) {
        const key = med.id + "_" + med.time + "_" + new Date().toDateString();
        if (alreadyAnnounced.has(key)) return;
        alreadyAnnounced.add(key);
        sessionStorage.setItem("medi-announced", JSON.stringify([...alreadyAnnounced]));

        speak(`Please take your medicine now: ${med.medicine_name}`);

        if ("Notification" in window && Notification.permission === "granted") {
            new Notification("💊 Medicine Reminder", {
                body: `Time to take ${med.medicine_name} (${med.dosage || ""})`,
            });
        }
    }

    async function pollDueMedicines() {
        try {
            const res = await fetch("/api/due-medicines");
            if (!res.ok) return;
            const data = await res.json();
            (data.due || []).forEach(announce);
        } catch (e) { /* silent */ }
    }

    pollDueMedicines();
    setInterval(pollDueMedicines, 30000);
}
