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
let themeTransitionRunning = false;

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
    if (themeTransitionRunning) {
        return;
    }
    const nextTheme = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    const bounds = button.getBoundingClientRect();
    const setRevealGeometry = (snapshotLeft, snapshotTop, snapshotWidth, snapshotHeight) => {
        const originX = bounds.left + bounds.width / 2 - snapshotLeft;
        const originY = bounds.top + bounds.height / 2 - snapshotTop;
        const farthestCorner = Math.hypot(
            Math.max(originX, snapshotWidth - originX),
            Math.max(originY, snapshotHeight - originY),
        );
        // Overshoot the farthest corner so viewport changes and subpixel
        // clipping cannot leave a corner for a sudden final fill.
        const revealRadius = farthestCorner + Math.max(snapshotWidth, snapshotHeight) * 0.08;

        document.documentElement.style.setProperty("--theme-origin-x", `${originX}px`);
        document.documentElement.style.setProperty("--theme-origin-y", `${originY}px`);
        document.documentElement.style.setProperty("--theme-reveal-radius", `${revealRadius}px`);
    };
    const viewportWidth = document.documentElement.clientWidth || window.innerWidth;
    const viewportHeight = document.documentElement.clientHeight || window.innerHeight;
    setRevealGeometry(0, 0, viewportWidth, viewportHeight);

    if (
        typeof document.startViewTransition === "function"
        && !window.matchMedia("(prefers-reduced-motion: reduce)").matches
    ) {
        themeTransitionRunning = true;
        const transition = document.startViewTransition(() => applyTheme(nextTheme));
        transition.ready.then(() => {
            const snapshot = window.getComputedStyle(
                document.documentElement,
                "::view-transition",
            );
            const snapshotLeft = Number.parseFloat(snapshot.left) || 0;
            let snapshotTop = Number.parseFloat(snapshot.top) || 0;
            const snapshotWidth = Number.parseFloat(snapshot.width) || viewportWidth;
            let snapshotHeight = Number.parseFloat(snapshot.height) || viewportHeight;
            if (
                Math.abs(snapshotTop) < 1
                && window.matchMedia("(max-width: 767.98px)").matches
            ) {
                // Some mobile browsers expose a zero inset despite including
                // their retractable top bar in the snapshot containing block.
                const topBrowserChrome = Math.max(
                    0,
                    window.outerHeight - window.innerHeight,
                );
                if (topBrowserChrome > 1) {
                    snapshotTop = -topBrowserChrome;
                    snapshotHeight = Math.max(
                        snapshotHeight,
                        viewportHeight + topBrowserChrome,
                    );
                }
            }
            setRevealGeometry(snapshotLeft, snapshotTop, snapshotWidth, snapshotHeight);
        }).catch(() => {});
        transition.finished.then(
            () => { themeTransitionRunning = false; },
            () => { themeTransitionRunning = false; },
        );
        flashThemeToggle(button, (done) => {
            transition.finished.then(done, done);
        });
        return;
    }

    flashThemeToggle(button);
    const useFallbackFade = !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (useFallbackFade) {
        document.documentElement.classList.add("theme-fallback-transition");
    }
    applyTheme(nextTheme);
    if (useFallbackFade) {
        window.setTimeout(() => {
            document.documentElement.classList.remove("theme-fallback-transition");
        }, 495);
    }
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
