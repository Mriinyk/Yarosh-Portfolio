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

const TAP_FLASH_FALLBACK_DURATION = 800;

function clearThemeToggleFlash(button) {
    if (button.dataset.tapFlashTimer) {
        clearTimeout(Number(button.dataset.tapFlashTimer));
        delete button.dataset.tapFlashTimer;
    }

    button.classList.remove("is-tapped");
}

function flashThemeToggle(button, onAnimationEnd) {
    button.classList.add("is-tapped");

    // When a theme-change animation is running, put out the glow exactly
    // when that animation finishes so nothing lingers afterwards.
    if (typeof onAnimationEnd === "function") {
        onAnimationEnd(() => clearThemeToggleFlash(button));
        return;
    }

    const timer = window.setTimeout(() => {
        clearThemeToggleFlash(button);
    }, TAP_FLASH_FALLBACK_DURATION);

    button.dataset.tapFlashTimer = String(timer);
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
        const transition = document.startViewTransition(() => applyTheme(nextTheme));
        flashThemeToggle(button, (done) => {
            transition.finished.then(done, done);
        });
        return;
    }

    flashThemeToggle(button);
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
