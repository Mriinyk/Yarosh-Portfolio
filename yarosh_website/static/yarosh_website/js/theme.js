const themeStorageKey = "yarosh-theme";
const savedTheme = localStorage.getItem(themeStorageKey);

document.documentElement.dataset.theme = savedTheme === "dark" ? "dark" : "light";

function updateThemeToggle() {
    const toggle = document.getElementById("siteThemeToggle");
    if (!(toggle instanceof HTMLButtonElement)) {
        return;
    }

    const isDark = document.documentElement.dataset.theme === "dark";
    toggle.setAttribute("aria-pressed", String(isDark));
    toggle.setAttribute(
        "aria-label",
        isDark ? "Увімкнути світлу тему" : "Увімкнути темну тему",
    );
}

document.addEventListener("DOMContentLoaded", updateThemeToggle);

document.addEventListener("click", (event) => {
    if (!(event.target instanceof Element)) {
        return;
    }

    const toggle = event.target.closest("#siteThemeToggle");
    if (!(toggle instanceof HTMLButtonElement)) {
        return;
    }

    const nextTheme = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = nextTheme;
    localStorage.setItem(themeStorageKey, nextTheme);
    updateThemeToggle();
});
