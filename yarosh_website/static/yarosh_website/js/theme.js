const themeStorageKey = "yarosh-theme";
const savedTheme = localStorage.getItem(themeStorageKey);

document.documentElement.dataset.theme = savedTheme === "dark" ? "dark" : "light";

function updateThemeToggle() {
    const isDark = document.documentElement.dataset.theme === "dark";
    document.querySelectorAll(".site-theme-toggle").forEach((toggle) => {
        if (!(toggle instanceof HTMLButtonElement)) {
            return;
        }

        toggle.setAttribute("aria-pressed", String(isDark));
        toggle.setAttribute(
            "aria-label",
            isDark ? "Увімкнути світлу тему" : "Увімкнути темну тему",
        );
    });
}

function applyTheme(theme) {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem(themeStorageKey, theme);
    updateThemeToggle();
}

function toggleTheme(button) {
    const nextTheme = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    const bounds = button.getBoundingClientRect();
    const originX = bounds.left + bounds.width / 2;
    const originY = bounds.top + bounds.height / 2;
    const revealRadius = Math.hypot(
        Math.max(originX, window.innerWidth - originX),
        Math.max(originY, window.innerHeight - originY),
    );

    document.documentElement.style.setProperty("--theme-origin-x", `${originX}px`);
    document.documentElement.style.setProperty("--theme-origin-y", `${originY}px`);
    document.documentElement.style.setProperty("--theme-reveal-radius", `${revealRadius}px`);

    if (
        typeof document.startViewTransition === "function"
        && !window.matchMedia("(prefers-reduced-motion: reduce)").matches
    ) {
        document.startViewTransition(() => applyTheme(nextTheme));
        return;
    }

    applyTheme(nextTheme);
}

document.addEventListener("DOMContentLoaded", updateThemeToggle);

document.addEventListener("click", (event) => {
    if (!(event.target instanceof Element)) {
        return;
    }

    const toggle = event.target.closest(".site-theme-toggle");
    if (!(toggle instanceof HTMLButtonElement)) {
        return;
    }

    toggleTheme(toggle);
});
