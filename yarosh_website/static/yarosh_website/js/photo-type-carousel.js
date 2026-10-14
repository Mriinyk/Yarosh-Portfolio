(() => {
    // Adaptive infinite category carousel for the photos page. The strip
    // clones its links to loop seamlessly, snaps the centred category into
    // place and loads the matching sessions without a full page reload.
    const nav = document.querySelector(".photo-type-nav");
    const grid = document.querySelector(".photo-session-grid");
    const section = document.querySelector(".photos-page");
    if (!nav || !grid || !section) {
        return;
    }

    const searchForm = section.querySelector(".photos-search");
    const photosPath = window.location.pathname;
    let baseLinks = [];
    let anchorClone = null;
    let scrollable = false;
    let fetchVersion = 0;
    let activeHref = "";
    let lastContentWidth = 0;
    let lastClientWidth = 0;
    let settleTimer = null;
    let resizeTimer = null;
    let wheelTimer = null;
    let wheelLocked = false;

    const hrefOf = (link) => link.getAttribute("href") || "";

    const prefersReducedMotion = () => window.matchMedia(
        "(prefers-reduced-motion: reduce)",
    ).matches;

    const centerBehavior = () => (prefersReducedMotion() ? "instant" : "smooth");

    const normalizeUrl = (url) => {
        try {
            const parsed = new URL(url, window.location.origin);
            const params = Array.from(parsed.searchParams.entries())
                .map(([key, value]) => `${key}=${value}`)
                .sort()
                .join("&");
            return `${parsed.pathname}?${params}`;
        } catch (error) {
            return url;
        }
    };

    const contentWidth = () => {
        if (!baseLinks.length) {
            return 0;
        }
        const style = window.getComputedStyle(nav);
        const padLeft = parseFloat(style.paddingLeft) || 0;
        const padRight = parseFloat(style.paddingRight) || 0;
        const first = baseLinks[0].getBoundingClientRect();
        const last = baseLinks[baseLinks.length - 1].getBoundingClientRect();
        return (last.right - first.left) + padLeft + padRight;
    };

    const activeBaseLink = () => (
        baseLinks.find((link) => link.classList.contains("is-active"))
        || baseLinks[0]
        || null
    );

    const periodLength = () => {
        if (!anchorClone || !baseLinks[0]) {
            return 0;
        }
        return anchorClone.getBoundingClientRect().left
            - baseLinks[0].getBoundingClientRect().left;
    };

    const removeClones = () => {
        nav.querySelectorAll(".photo-type-link[data-clone]").forEach((link) => link.remove());
        anchorClone = null;
    };

    const cloneSet = () => baseLinks.map((link) => {
        const clone = link.cloneNode(true);
        clone.setAttribute("data-clone", "");
        clone.setAttribute("aria-hidden", "true");
        clone.tabIndex = -1;
        clone.removeAttribute("aria-current");
        return clone;
    });

    const centerTargetFor = (link) => {
        const navRect = nav.getBoundingClientRect();
        const linkRect = link.getBoundingClientRect();
        return nav.scrollLeft
            + (linkRect.left - navRect.left)
            - (navRect.width - linkRect.width) / 2;
    };

    // The strip cannot scroll past its ends, so links in the outermost clone
    // band have no reachable centred position. Always centre the same-category
    // copy whose centred position is closest to the current scroll offset and
    // still within [0, maxScroll], so picking a far-edge clone never clamps
    // to the wrong category.
    const centerableLink = (link) => {
        if (!link) {
            return null;
        }
        const href = normalizeUrl(hrefOf(link));
        const maxScroll = nav.scrollWidth - nav.clientWidth;
        let best = null;
        let bestDistance = Infinity;
        nav.querySelectorAll(".photo-type-link").forEach((candidate) => {
            if (normalizeUrl(hrefOf(candidate)) !== href) {
                return;
            }
            const target = centerTargetFor(candidate);
            if (target < -0.5 || target > maxScroll + 0.5) {
                return;
            }
            const distance = Math.abs(target - nav.scrollLeft);
            if (distance < bestDistance) {
                bestDistance = distance;
                best = candidate;
            }
        });
        return best || link;
    };

    const centerOn = (link, behavior) => {
        if (!scrollable || !link) {
            return;
        }
        nav.scrollTo({ left: Math.max(0, centerTargetFor(link)), behavior });
    };

    const build = () => {
        removeClones();
        // The strip is always a scrollable carousel — even on wide desktop
        // screens where the base links would fit on their own.
        nav.classList.add("is-carousel", "is-scrollable");
        scrollable = true;
        lastClientWidth = nav.clientWidth;
        lastContentWidth = contentWidth();
        const style = window.getComputedStyle(nav);
        const gap = parseFloat(style.columnGap) || 0;
        const first = baseLinks[0].getBoundingClientRect();
        const last = baseLinks[baseLinks.length - 1].getBoundingClientRect();
        const period = Math.max((last.right - first.left) + gap, 1);
        const copies = Math.max(1, Math.ceil(nav.clientWidth / period));
        for (let index = 0; index < copies; index += 1) {
            nav.prepend(...cloneSet());
        }
        for (let index = 0; index < copies; index += 1) {
            nav.append(...cloneSet());
        }
        anchorClone = baseLinks[baseLinks.length - 1].nextElementSibling;
        centerOn(activeBaseLink(), "instant");
    };

    const setActive = (link) => {
        activeHref = normalizeUrl(hrefOf(link));
        nav.querySelectorAll(".photo-type-link").forEach((candidate) => {
            const match = normalizeUrl(hrefOf(candidate)) === activeHref;
            candidate.classList.toggle("is-active", match);
            if (candidate.hasAttribute("data-clone")) {
                return;
            }
            if (match) {
                candidate.setAttribute("aria-current", "page");
            } else {
                candidate.removeAttribute("aria-current");
            }
        });
    };

    // Jump one full period so the visible window always sits on real links,
    // keeping the loop seamless while the scroll position stays bounded.
    const normalizeLoop = () => {
        const period = periodLength();
        if (!scrollable || period <= 0) {
            return;
        }
        const padLeft = parseFloat(window.getComputedStyle(nav).paddingLeft) || 0;
        const maxScroll = nav.scrollWidth - nav.clientWidth;
        const left = nav.scrollLeft;
        if (left > maxScroll - period) {
            nav.scrollLeft = left - period;
        } else if (left < padLeft + period) {
            nav.scrollLeft = left + period;
        }
    };

    const nearestLink = () => {
        const center = nav.getBoundingClientRect().left + nav.clientWidth / 2;
        let best = null;
        let bestDistance = Infinity;
        nav.querySelectorAll(".photo-type-link").forEach((link) => {
            const rect = link.getBoundingClientRect();
            const distance = Math.abs(rect.left + rect.width / 2 - center);
            if (distance < bestDistance) {
                bestDistance = distance;
                best = link;
            }
        });
        return best;
    };
    // Rebuild after font loading or a width change, but skip height-only
    // resizes (mobile URL bar) that would needlessly reset the scroll.
    const rebuildIfNeeded = () => {
        if (!baseLinks.length) {
            return false;
        }
        if (Math.abs(contentWidth() - lastContentWidth) < 0.5
            && nav.clientWidth === lastClientWidth) {
            return false;
        }
        build();
        return true;
    };

    const syncSearchType = (url) => {
        if (!searchForm) {
            return;
        }
        let typeValue = "";
        try {
            typeValue = new URL(url, window.location.origin).searchParams.get("type") || "";
        } catch (error) {
            typeValue = "";
        }
        const hidden = searchForm.querySelector('input[name="type"]');
        if (!typeValue) {
            hidden?.remove();
            return;
        }
        if (hidden) {
            hidden.value = typeValue;
            return;
        }
        const input = document.createElement("input");
        input.type = "hidden";
        input.name = "type";
        input.value = typeValue;
        searchForm.append(input);
    };

    // Share modals and pagination live outside the grid, so swap them too.
    const syncSidePanels = (doc) => {
        section.querySelectorAll(".photo-share-modal, .photo-pagination")
            .forEach((node) => node.remove());
        let anchor = grid;
        doc.querySelectorAll(".photo-share-modal, .photo-pagination").forEach((node) => {
            const imported = document.importNode(node, true);
            anchor.after(imported);
            anchor = imported;
        });
    };

    const applyFilter = async (url, { push = true } = {}) => {
        const version = ++fetchVersion;
        try {
            const response = await fetch(url, {
                credentials: "same-origin",
                headers: { "X-Requested-With": "XMLHttpRequest" },
            });
            if (!response.ok) {
                throw new Error(`Сервер повернув ${response.status}.`);
            }
            const html = await response.text();
            if (version !== fetchVersion) {
                return;
            }
            const doc = new DOMParser().parseFromString(html, "text/html");
            const nextGrid = doc.querySelector(".photo-session-grid");
            if (!nextGrid) {
                throw new Error("У відповіді немає сітки фотосесій.");
            }
            // Reuse the grid node so delegated comment handlers keep working.
            grid.innerHTML = nextGrid.innerHTML;
            syncSidePanels(doc);
            syncSearchType(url);
            document.dispatchEvent(new CustomEvent("photos:grid-updated"));
            if (push) {
                history.pushState({ photosUrl: url }, "", url);
            }
        } catch (error) {
            if (version !== fetchVersion) {
                return;
            }
            console.error("Не вдалося оновити добірку фотосесій:", error);
            // Degrade to a normal page load so filtering always works.
            window.location.assign(url);
        }
    };
    nav.addEventListener("click", (event) => {
        const link = event.target.closest?.(".photo-type-link");
        if (!link || !nav.contains(link)) {
            return;
        }
        event.preventDefault();
        const url = hrefOf(link);
        if (!url) {
            return;
        }
        const alreadyActive = normalizeUrl(url) === activeHref;
        setActive(link);
        centerOn(centerableLink(link), centerBehavior());
        if (alreadyActive) {
            return;
        }
        applyFilter(url, { push: true });
    });

    nav.addEventListener("wheel", (event) => {
        if (!scrollable) {
            return;
        }
        if (Math.abs(event.deltaY) < Math.abs(event.deltaX)) {
            // A deliberate horizontal gesture: let the browser scroll natively.
            return;
        }
        if (!event.deltaY && !event.deltaX) {
            return;
        }
        event.preventDefault();
        if (wheelLocked) {
            return;
        }
        // The strip snaps to link centres, so a pixel nudge (scrollLeft += x)
        // smaller than the gap to the next snap point is silently discarded by
        // the browser and small wheel steps do nothing. Like the sessions
        // carousel, glide to the adjacent category instead and lock briefly so
        // one gesture moves exactly one category.
        const direction = (event.deltaY || event.deltaX) > 0 ? 1 : -1;
        const current = nearestLink() || activeBaseLink();
        const sibling = direction > 0
            ? current?.nextElementSibling
            : current?.previousElementSibling;
        if (!sibling?.classList?.contains("photo-type-link")) {
            return;
        }
        wheelLocked = true;
        window.clearTimeout(wheelTimer);
        wheelTimer = window.setTimeout(() => {
            wheelLocked = false;
        }, 450);
        centerOn(centerableLink(sibling), centerBehavior());
    }, { passive: false });

    nav.addEventListener("scroll", () => {
        window.clearTimeout(settleTimer);
        settleTimer = window.setTimeout(() => {
            if (!scrollable) {
                return;
            }
            normalizeLoop();
            const nearest = nearestLink();
            if (!nearest || normalizeUrl(hrefOf(nearest)) === activeHref) {
                return;
            }
            setActive(nearest);
            centerOn(centerableLink(nearest), "instant");
            applyFilter(hrefOf(nearest), { push: true });
        }, 150);
    });

    section.addEventListener("click", (event) => {
        const link = event.target.closest?.(".photo-pagination a");
        if (!link) {
            return;
        }
        event.preventDefault();
        const url = link.getAttribute("href");
        if (!url) {
            return;
        }
        applyFilter(url, { push: true });
        grid.scrollIntoView({
            behavior: prefersReducedMotion() ? "instant" : "smooth",
            block: "start",
        });
    });

    window.addEventListener("popstate", () => {
        const url = `${window.location.pathname}${window.location.search}`;
        if (!window.location.pathname.startsWith(photosPath)) {
            window.location.assign(url);
            return;
        }
        const match = baseLinks.find(
            (link) => normalizeUrl(hrefOf(link)) === normalizeUrl(url),
        );
        if (match) {
            setActive(match);
            centerOn(centerableLink(match), "instant");
        }
        applyFilter(url, { push: false });
    });

    window.addEventListener("resize", () => {
        window.clearTimeout(resizeTimer);
        resizeTimer = window.setTimeout(rebuildIfNeeded, 200);
    });

    // Initial setup: keep the selected category centred.
    baseLinks = Array.from(nav.querySelectorAll(".photo-type-link"));
    const initial = activeBaseLink();
    if (initial) {
        activeHref = normalizeUrl(hrefOf(initial));
    }
    build();
    // Web fonts change the link widths, so re-measure once they are ready.
    document.fonts?.ready?.then(rebuildIfNeeded);
})();
