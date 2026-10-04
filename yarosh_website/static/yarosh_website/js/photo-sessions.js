(() => {
    const carousel = document.querySelector("[data-session-carousel]");
    const gallery = document.querySelector("[data-photo-gallery-modal]");
    let pauseMobileCarouselFocus = () => {};
    let waitForMobileScrollToResume = () => {};

    if (carousel) {
        const originalCards = Array.from(carousel.querySelectorAll("[data-session-card]"));
        const firstCard = originalCards[0];
        const count = originalCards.length;
        let cards = originalCards;
        let frameRequested = false;
        let settleTimer = null;
        let wheelTimer = null;
        let maintainTimer = null;
        let wheelLocked = false;
        let focusPaused = false;
        let mobileResumeScrollY = null;
        let hasInteracted = false;
        let focusedCardIndex = 0;
        const isMobile = () => window.matchMedia("(max-width: 767.98px)").matches;

        const measureCoverRatios = () => {
            const applyRatio = (card, image) => {
                if (!image.naturalWidth || !image.naturalHeight) {
                    return;
                }
                const ratio = image.naturalWidth / image.naturalHeight;
                cards
                    .filter((candidate) => (
                        candidate.dataset.sessionId === card.dataset.sessionId
                    ))
                    .forEach((candidate) => {
                        candidate.style.setProperty("--cover-ratio", ratio);
                        candidate.querySelector(
                            ".photo-session-cover",
                        ).style.setProperty("--cover-ratio", ratio);
                    });
                scheduleMaintainCenteredCard();
                scheduleFocusUpdate();
            };

            const pendingImages = [];
            originalCards.forEach((card) => {
                const image = card.querySelector("img");
                if (image.complete && image.naturalWidth) {
                    applyRatio(card, image);
                } else {
                    pendingImages.push({ card, image });
                }
            });

            if (pendingImages.length === 0) {
                window.requestAnimationFrame(revealCarousel);
                return;
            }

            let remaining = pendingImages.length;
            let finished = false;
            const finish = () => {
                if (finished) {
                    return;
                }
                finished = true;
                window.requestAnimationFrame(revealCarousel);
            };
            pendingImages.forEach(({ card, image }) => {
                const resolve = () => {
                    applyRatio(card, image);
                    remaining -= 1;
                    if (remaining <= 0) {
                        finish();
                    }
                };
                image.addEventListener("load", resolve, { once: true });
                image.addEventListener("error", resolve, { once: true });
            });
            // Safety net: never leave the carousel hidden if a cover is slow.
            window.setTimeout(finish, 2500);
        };

        const centerOnCard = (card, behavior = "smooth") => {
            if (!card) {
                return;
            }
            carousel.scrollTo({
                left: card.offsetLeft + card.offsetWidth / 2 - carousel.clientWidth / 2,
                behavior,
            });
        };

        // Card widths depend on the cover aspect ratio, which is applied only
        // once each image reports its natural size. Recenter the focused card
        // whenever that happens so the carousel still starts on the first photo.
        // It stops as soon as the user scrolls, so it never fights navigation.
        const maintainCenteredCard = () => {
            if (hasInteracted || isMobile()) {
                return;
            }
            const target = cards.find((card) => card.classList.contains("is-centered"))
                || firstCard;
            centerOnCard(target, "instant");
        };

        // The cover ratio (and therefore the card width/height) is animated by
        // CSS, so recenter only after that transition has settled.
        const scheduleMaintainCenteredCard = () => {
            window.clearTimeout(maintainTimer);
            maintainTimer = window.setTimeout(maintainCenteredCard, 700);
        };

        // Reveal the carousel only once every cover ratio is applied, so the
        // cards never visibly move after load.
        const revealCarousel = () => {
            if (!carousel.classList.contains("is-measuring")) {
                return;
            }
            carousel.classList.remove("is-measuring");
            if (!isMobile()) {
                centerOnCard(firstCard, "instant");
            }
            scheduleFocusUpdate();
        };

        const insertLoopClones = () => {
            if (originalCards.length <= 3) {
                carousel.classList.add("is-short-carousel");
            }
            if (originalCards.length < 2) {
                return;
            }
            const cloneCard = (source) => {
                const clone = source.cloneNode(true);
                clone.classList.add("carousel-clone");
                clone.setAttribute("aria-hidden", "true");
                clone.querySelectorAll("button").forEach((button) => {
                    button.tabIndex = -1;
                });
                return clone;
            };
            const beforeSet = document.createDocumentFragment();
            const afterSet = document.createDocumentFragment();
            originalCards.forEach((card) => {
                beforeSet.appendChild(cloneCard(card));
                afterSet.appendChild(cloneCard(card));
            });
            carousel.insertBefore(beforeSet, firstCard);
            carousel.appendChild(afterSet);
            cards = Array.from(carousel.querySelectorAll("[data-session-card]"));
        };

        const updateFocusedCard = () => {
            frameRequested = false;
            if (focusPaused) {
                return;
            }
            const mobile = isMobile();
            const visibleCards = mobile ? originalCards : cards;
            const bounds = mobile
                ? { x: window.innerWidth / 2, y: window.innerHeight / 2 }
                : {
                    x: carousel.getBoundingClientRect().left + carousel.clientWidth / 2,
                    y: carousel.getBoundingClientRect().top + carousel.clientHeight / 2,
                };
            let closestCard = null;
            let closestDistance = Infinity;

            visibleCards.forEach((card) => {
                const rect = card.getBoundingClientRect();
                const xDistance = rect.left + rect.width / 2 - bounds.x;
                const yDistance = rect.top + rect.height / 2 - bounds.y;
                const distance = mobile
                    ? Math.abs(yDistance)
                    : Math.hypot(xDistance, yDistance);
                if (distance < closestDistance) {
                    closestDistance = distance;
                    closestCard = card;
                }
            });

            focusedCardIndex = closestCard ? Math.max(0, cards.indexOf(closestCard)) : 0;

            if (mobile) {
                const centerThreshold = Math.min(
                    window.innerHeight * 0.22,
                    (closestCard ? closestCard.offsetHeight : 0) * 0.45,
                );
                cards.forEach((card) => card.classList.toggle(
                    "is-centered",
                    card === closestCard && closestDistance < centerThreshold,
                ));
                return;
            }

            // The seamless loop renders three copies of every session
            // (before / middle / after set). All copies share the focused state
            // so that when the loop snaps the centered card back to the middle
            // set, its twin is already focused and nothing visually "pulses".
            // Using the closest card directly (no distance threshold) also makes
            // the focus a single crossfade instead of a brief unfocused blink.
            const focusedSessionId = closestCard ? closestCard.dataset.sessionId : null;
            cards.forEach((card) => card.classList.toggle(
                "is-centered",
                focusedSessionId !== null &&
                    card.dataset.sessionId === focusedSessionId,
            ));
        };

        const scheduleFocusUpdate = () => {
            if (!focusPaused && !frameRequested) {
                frameRequested = true;
                window.requestAnimationFrame(updateFocusedCard);
            }
        };

        pauseMobileCarouselFocus = () => {
            if (!isMobile()) {
                return;
            }
            focusPaused = true;
            mobileResumeScrollY = null;
        };

        waitForMobileScrollToResume = () => {
            if (isMobile()) {
                focusPaused = true;
                mobileResumeScrollY = window.scrollY;
            }
        };

        const resumeMobileFocusAfterScroll = () => {
            if (
                !focusPaused ||
                !isMobile() ||
                mobileResumeScrollY === null ||
                Math.abs(window.scrollY - mobileResumeScrollY) < 1
            ) {
                return;
            }
            focusPaused = false;
            mobileResumeScrollY = null;
            scheduleFocusUpdate();
        };

        const normalizeLoopPosition = () => {
            const setSize = originalCards.length;
            if (isMobile() || setSize < 2 || cards.length <= setSize) {
                return;
            }
            const index = focusedCardIndex;
            if (index < 0 || index >= cards.length) {
                return;
            }
            // The layout is [before set][middle set][after set]; always snap the
            // visually centered card back to its twin in the middle set so the
            // loop never hits a hard edge. Both cards look identical, so the jump
            // is invisible.
            const positionInSet = ((index % setSize) + setSize) % setSize;
            const target = cards[setSize + positionInSet];
            if (target && cards.indexOf(target) !== index) {
                centerOnCard(target, "instant");
                scheduleFocusUpdate();
            }
        };

        const moveToAdjacentCard = (direction, behavior = "smooth") => {
            const targetCard = cards[focusedCardIndex + direction];
            if (targetCard) {
                centerOnCard(targetCard, behavior);
            }
        };

        carousel.addEventListener("scroll", scheduleFocusUpdate, { passive: true });
        carousel.addEventListener("scroll", () => {
            window.clearTimeout(settleTimer);
            settleTimer = window.setTimeout(normalizeLoopPosition, 140);
        }, { passive: true });
        window.addEventListener("scroll", scheduleFocusUpdate, { passive: true });
        window.addEventListener("scroll", resumeMobileFocusAfterScroll, { passive: true });
        window.addEventListener("resize", scheduleFocusUpdate);
        window.addEventListener("load", () => {
            maintainCenteredCard();
            scheduleFocusUpdate();
            revealCarousel();
        }, { once: true });
        insertLoopClones();
        measureCoverRatios();
        if (!isMobile() && count) {
            window.requestAnimationFrame(() => centerOnCard(firstCard, "instant"));
        }
        scheduleFocusUpdate();

        carousel.addEventListener("wheel", (event) => {
            if (isMobile()) {
                return;
            }
            const wheelDelta = Math.abs(event.deltaX) > Math.abs(event.deltaY)
                ? event.deltaX
                : event.deltaY;
            if (Math.abs(wheelDelta) < 2) {
                return;
            }
            event.preventDefault();
            if (wheelLocked) {
                return;
            }
            wheelLocked = true;
            hasInteracted = true;
            moveToAdjacentCard(wheelDelta > 0 ? 1 : -1);
            window.clearTimeout(wheelTimer);
            wheelTimer = window.setTimeout(() => {
                wheelLocked = false;
            }, 450);
        }, { passive: false });

        window.addEventListener("resize", () => {
            if (!isMobile()) {
                focusPaused = false;
            }
            scheduleFocusUpdate();
        });
    }

    if (!gallery) {
        return;
    }

    const closeButton = gallery.querySelector("[data-gallery-close]");
    const image = gallery.querySelector("[data-gallery-image]");
    const status = gallery.querySelector("[data-gallery-status]");
    const counter = gallery.querySelector("[data-gallery-counter]");
    const previousButton = gallery.querySelector("[data-gallery-previous]");
    const nextButton = gallery.querySelector("[data-gallery-next]");
    const viewer = gallery.querySelector(".photo-gallery-viewer");
    let images = [];
    let currentIndex = 0;
    let activeTrigger = null;
    let requestVersion = 0;
    let touchStartX = null;
    let previousBodyOverflow = "";

    const showImage = (index) => {
        if (!images.length) {
            return;
        }
        currentIndex = (index + images.length) % images.length;
        image.hidden = false;
        image.src = images[currentIndex];
        counter.textContent = `${currentIndex + 1} / ${images.length}`;
        status.textContent = "";
    };

    const openGallery = async (trigger) => {
        activeTrigger = trigger;
        images = [];
        currentIndex = 0;
        requestVersion += 1;
        const thisRequest = requestVersion;
        image.hidden = true;
        image.removeAttribute("src");
        counter.textContent = "";
        status.textContent = "Завантаження галереї…";
        pauseMobileCarouselFocus();
        previousBodyOverflow = document.body.style.overflow;
        document.body.style.overflow = "hidden";
        gallery.hidden = false;
        closeButton.focus();

        try {
            const response = await fetch(trigger.dataset.galleryUrl, {
                headers: { Accept: "application/json" },
            });
            const result = await response.json();
            if (!response.ok) {
                throw new Error(result.error || "Не вдалося завантажити галерею.");
            }
            if (!Array.isArray(result.images) || result.images.length === 0) {
                throw new Error("У цій фотосесії поки немає доступних фотографій.");
            }
            if (thisRequest !== requestVersion || gallery.hidden) {
                return;
            }
            images = result.images;
            showImage(0);
        } catch (error) {
            if (thisRequest === requestVersion && !gallery.hidden) {
                status.textContent = error.message || "Не вдалося завантажити галерею.";
            }
        }
    };

    const closeGallery = () => {
        requestVersion += 1;
        gallery.hidden = true;
        image.hidden = true;
        image.removeAttribute("src");
        document.body.style.overflow = previousBodyOverflow;
        waitForMobileScrollToResume();
        if (activeTrigger) {
            activeTrigger.focus({ preventScroll: true });
        }
    };

    document.querySelectorAll("[data-gallery-url]").forEach((trigger) => {
        trigger.addEventListener("click", () => openGallery(trigger));
    });
    closeButton.addEventListener("click", closeGallery);
    previousButton.addEventListener("click", () => showImage(currentIndex - 1));
    nextButton.addEventListener("click", () => showImage(currentIndex + 1));
    gallery.addEventListener("click", (event) => {
        if (event.target === gallery || event.target === viewer) {
            closeGallery();
        }
    });
    image.addEventListener("error", () => {
        image.hidden = true;
        status.textContent = "Не вдалося завантажити це фото. Спробуйте переглянути інше.";
    });
    gallery.addEventListener("touchstart", (event) => {
        touchStartX = event.changedTouches[0].clientX;
    }, { passive: true });
    gallery.addEventListener("touchend", (event) => {
        if (touchStartX === null) {
            return;
        }
        const distance = event.changedTouches[0].clientX - touchStartX;
        touchStartX = null;
        if (Math.abs(distance) > 45) {
            showImage(currentIndex + (distance < 0 ? 1 : -1));
        }
    }, { passive: true });
    document.addEventListener("keydown", (event) => {
        if (gallery.hidden) {
            return;
        }
        if (event.key === "Escape") {
            closeGallery();
        } else if (event.key === "ArrowLeft") {
            showImage(currentIndex - 1);
        } else if (event.key === "ArrowRight") {
            showImage(currentIndex + 1);
        }
    });
})();
