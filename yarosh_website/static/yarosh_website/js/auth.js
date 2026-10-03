const siteHeader = document.querySelector(".site-header");

if (siteHeader instanceof HTMLElement && "ResizeObserver" in window) {
    const headerObserver = new ResizeObserver(() => {
        const headerHeight = Math.ceil(siteHeader.getBoundingClientRect().height);
        document.documentElement.style.setProperty("--site-header-height", `${headerHeight}px`);
    });

    headerObserver.observe(siteHeader);
}

const authCard = document.querySelector(".auth-card");
const currentUrl = new URL(window.location.href);

window.scrollTo(0, 0);

if (currentUrl.searchParams.has("auth_flip") && authCard instanceof HTMLElement) {
    currentUrl.searchParams.delete("auth_flip");
    window.history.replaceState(window.history.state, "", currentUrl);
    authCard.classList.add("is-flipping-in");
}

document.addEventListener("click", (event) => {
    if (
        !(event instanceof MouseEvent)
        || event.button !== 0
        || event.metaKey
        || event.ctrlKey
        || event.shiftKey
        || event.altKey
        || !(event.target instanceof Element)
    ) {
        return;
    }

    const link = event.target.closest(".auth-transition-link");
    if (!(link instanceof HTMLAnchorElement) || !(authCard instanceof HTMLElement)) {
        return;
    }

    event.preventDefault();
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
        window.location.assign(link.href);
        return;
    }

    authCard.classList.add("is-flipping-out");
    const destination = new URL(link.href);
    destination.searchParams.set("auth_flip", "1");
    window.setTimeout(() => window.location.assign(destination), 620);
});
