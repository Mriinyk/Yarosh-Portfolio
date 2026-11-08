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
        let navLocked = false;
        let isScrolling = false;
        let scrollTargetLeft = null;
        let touchStart = null;
        let touchTimer = null;
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
            if (isMobile()) {
                const cardTop = card.getBoundingClientRect().top + window.scrollY;
                window.scrollTo({
                    top: cardTop + card.offsetHeight / 2 - window.innerHeight / 2,
                    behavior,
                });
                return;
            }
            const targetLeft = card.offsetLeft + card.offsetWidth / 2 - carousel.clientWidth / 2;
            scrollTargetLeft = targetLeft;
            carousel.scrollTo({
                left: targetLeft,
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

        const currentCenteredCardIndex = () => {
            const bounds = {
                x: carousel.getBoundingClientRect().left + carousel.clientWidth / 2,
                y: carousel.getBoundingClientRect().top + carousel.clientHeight / 2,
            };
            let closestCard = null;
            let closestDistance = Infinity;
            cards.forEach((card) => {
                const rect = card.getBoundingClientRect();
                const xDistance = rect.left + rect.width / 2 - bounds.x;
                const yDistance = rect.top + rect.height / 2 - bounds.y;
                const distance = Math.hypot(xDistance, yDistance);
                if (distance < closestDistance) {
                    closestDistance = distance;
                    closestCard = card;
                }
            });
            return closestCard ? cards.indexOf(closestCard) : focusedCardIndex;
        };

        const moveToAdjacentCard = (direction, behavior = "smooth") => {
            const currentIndex = currentCenteredCardIndex();
            const targetCard = cards[currentIndex + direction];
            if (targetCard) {
                centerOnCard(targetCard, behavior);
            }
        };

        carousel.addEventListener("scroll", scheduleFocusUpdate, { passive: true });
        carousel.addEventListener("scroll", () => {
            isScrolling = true;
            window.clearTimeout(settleTimer);
            // Якщо вже досягли цільової позиції — скрутінг закінчився.
            if (
                scrollTargetLeft !== null &&
                Math.abs(carousel.scrollLeft - scrollTargetLeft) < 2
            ) {
                scrollTargetLeft = null;
            }
            settleTimer = window.setTimeout(() => {
                isScrolling = false;
                scrollTargetLeft = null;
                normalizeLoopPosition();
            }, 140);
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
            if (scrollTargetLeft !== null || isScrolling || navLocked) {
                return;
            }
            navLocked = true;
            hasInteracted = true;
            moveToAdjacentCard(wheelDelta > 0 ? 1 : -1);
            window.clearTimeout(wheelTimer);
            window.clearTimeout(touchTimer);
            wheelTimer = window.setTimeout(() => {
                navLocked = false;
            }, 800);
        }, { passive: false });

        carousel.addEventListener("touchstart", (event) => {
            if (isMobile() || scrollTargetLeft !== null || isScrolling || navLocked) {
                return;
            }
            const touch = event.changedTouches[0];
            touchStart = { x: touch.clientX, y: touch.clientY };
        }, { passive: true });

        carousel.addEventListener("touchmove", (event) => {
            if (isMobile() || !touchStart) {
                return;
            }
            event.preventDefault();
        }, { passive: false });

        carousel.addEventListener("touchend", (event) => {
            if (isMobile()) {
                touchStart = null;
                return;
            }
            if (!touchStart || navLocked) {
                touchStart = null;
                return;
            }
            const touch = event.changedTouches[0];
            const dx = touch.clientX - touchStart.x;
            touchStart = null;
            const distance = dx;
            if (Math.abs(distance) < 40) {
                return;
            }
            event.preventDefault();
            navLocked = true;
            hasInteracted = true;
            moveToAdjacentCard(distance > 0 ? 1 : -1, "smooth");
            window.clearTimeout(wheelTimer);
            window.clearTimeout(touchTimer);
            touchTimer = window.setTimeout(() => {
                navLocked = false;
            }, 800);
        }, { passive: false });

        window.addEventListener("keydown", (event) => {
            // Arrow keys belong to the open gallery while it is active.
            // Do not let them also navigate the "New photos" carousel behind it.
            if (gallery && !gallery.hidden) {
                return;
            }
            if (isMobile()) {
                return;
            }
            if (event.target.tagName.match(/input|textarea|select/i)) {
                return;
            }
            if (event.key === "ArrowLeft") {
                event.preventDefault();
                if (scrollTargetLeft !== null || isScrolling || navLocked) {
                    return;
                }
                navLocked = true;
                hasInteracted = true;
                moveToAdjacentCard(-1, "smooth");
                window.clearTimeout(wheelTimer);
                window.clearTimeout(touchTimer);
                wheelTimer = window.setTimeout(() => {
                    navLocked = false;
                }, 800);
            } else if (event.key === "ArrowRight") {
                event.preventDefault();
                if (scrollTargetLeft !== null || isScrolling || navLocked) {
                    return;
                }
                navLocked = true;
                hasInteracted = true;
                moveToAdjacentCard(1, "smooth");
                window.clearTimeout(wheelTimer);
                window.clearTimeout(touchTimer);
                wheelTimer = window.setTimeout(() => {
                    navLocked = false;
                }, 800);
            }
        });

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
    let previousBodyPaddingRight = "";
    let preloadedImages = new Map();
    let galleryFlightImage = null;
    let galleryFlightTimer = null;
    let galleryClosing = false;
    let galleryCloseTimer = null;
    const navHighlightTimers = new Map();

    const highlightNavigationButton = (button) => {
        button.classList.add("photo-gallery-nav--hovered");
        window.clearTimeout(navHighlightTimers.get(button));
        navHighlightTimers.set(button, window.setTimeout(() => {
            button.classList.remove("photo-gallery-nav--hovered");
            navHighlightTimers.delete(button);
        }, 500));
    };

    const showImage = (index, direction = 0) => {
        if (!images.length || galleryClosing) {
            return;
        }
        currentIndex = (index + images.length) % images.length;
        const imageUrl = images[currentIndex];
        viewer.querySelectorAll(".photo-gallery-image--outgoing").forEach((outgoingImage) => {
            outgoingImage.remove();
        });
        image.classList.remove("photo-gallery-image--fade-in");
        if (direction && !image.hidden && image.complete && image.naturalWidth) {
            const outgoingImage = image.cloneNode();
            outgoingImage.removeAttribute("id");
            outgoingImage.setAttribute("aria-hidden", "true");
            outgoingImage.classList.remove("photo-gallery-image--fade-in");
            outgoingImage.classList.add("photo-gallery-image--outgoing");
            viewer.insertBefore(outgoingImage, image);
            window.setTimeout(() => outgoingImage.remove(), 760);
        }
        image.hidden = false;
        image.src = imageUrl;
        if (direction) {
            const animateImage = () => {
                if (image.src !== imageUrl || gallery.hidden) {
                    return;
                }
                image.classList.remove("photo-gallery-image--fade-in");
                void image.offsetWidth;
                image.classList.add("photo-gallery-image--fade-in");
                image.addEventListener("animationend", () => {
                    if (image.src === imageUrl) {
                        image.classList.remove("photo-gallery-image--fade-in");
                    }
                }, { once: true });
            };
            if (image.complete && image.naturalWidth) {
                animateImage();
            } else {
                image.addEventListener("load", animateImage, { once: true });
            }
        }
        counter.textContent = `${currentIndex + 1} / ${images.length}`;
        status.textContent = "";
    };

    const animateGalleryOpen = (trigger, decoded = false) => {
        if (gallery.hidden) {
            image.classList.remove("photo-gallery-image--opening");
            return;
        }
        window.clearTimeout(galleryFlightTimer);
        galleryFlightImage?.remove();
        galleryFlightImage = null;
        const cover = trigger.querySelector("img");
        if (window.matchMedia("(prefers-reduced-motion: reduce)").matches || !cover) {
            image.classList.remove("photo-gallery-image--opening");
            return;
        }
        if (!image.complete || !image.naturalWidth) {
            image.addEventListener("load", () => animateGalleryOpen(trigger), { once: true });
            return;
        }
        if (!decoded && typeof image.decode === "function") {
            const imageUrl = image.currentSrc || image.src;
            image.decode().then(
                () => {
                    if ((image.currentSrc || image.src) === imageUrl) {
                        animateGalleryOpen(trigger, true);
                    }
                },
                () => animateGalleryOpen(trigger, true),
            );
            return;
        }

        const start = cover.getBoundingClientRect();
        const end = image.getBoundingClientRect();
        if (!start.width || !start.height || !end.width || !end.height) {
            image.classList.remove("photo-gallery-image--opening");
            return;
        }

        const flightImage = cover.cloneNode();
        flightImage.removeAttribute("id");
        flightImage.setAttribute("aria-hidden", "true");
        Object.assign(flightImage.style, {
            position: "fixed",
            zIndex: "2001",
            top: `${start.top}px`,
            left: `${start.left}px`,
            width: `${start.width}px`,
            height: `${start.height}px`,
            display: "block",
            maxWidth: "none",
            maxHeight: "none",
            margin: "0",
            objectFit: "cover",
            borderRadius: getComputedStyle(cover).borderRadius,
            transformOrigin: "top left",
            transition: "transform 680ms cubic-bezier(0.22, 1, 0.36, 1), opacity 300ms ease",
            opacity: "1",
            willChange: "transform, opacity",
            pointerEvents: "none",
        });
        document.body.appendChild(flightImage);
        galleryFlightImage = flightImage;
        let flightFinished = false;
        const finishFlight = () => {
            if (flightFinished) {
                return;
            }
            flightFinished = true;
            window.clearTimeout(galleryFlightTimer);
            if (gallery.hidden) {
                flightImage.remove();
                return;
            }
            // Reveal the already-loaded full-size image underneath the flight
            // layer before fading that layer away. This avoids a black gap on
            // mobile browsers while their compositor catches up.
            image.classList.add("photo-gallery-image--ready");
            image.classList.remove("photo-gallery-image--opening");
            void image.offsetWidth;
            requestAnimationFrame(() => image.classList.remove("photo-gallery-image--ready"));
            flightImage.style.opacity = "0";
            galleryFlightTimer = window.setTimeout(() => {
                flightImage.remove();
                if (galleryFlightImage === flightImage) {
                    galleryFlightImage = null;
                }
            }, 320);
        };
        flightImage.addEventListener("transitionend", (event) => {
            if (event.propertyName === "transform") {
                finishFlight();
            }
        });
        void flightImage.offsetWidth;
        requestAnimationFrame(() => {
            if (gallery.hidden) {
                flightImage.remove();
                return;
            }
            flightImage.style.transform = `translate(${end.left - start.left}px, ${end.top - start.top}px) scale(${end.width / start.width}, ${end.height / start.height})`;
        });
        galleryFlightTimer = window.setTimeout(finishFlight, 820);
    };

    // Завантажуємо списки зображень усіх галерей одразу після прогрузки сторінки,
    // і попередньо завантажуємо самі зображення в кеш браузера, щоб при відкритті
    // галереї фото з'являлися миттєво, без очікування мережі.
    const preloadGalleries = async () => {
        const triggers = Array.from(document.querySelectorAll("[data-gallery-url]"));
        const urls = [...new Set(triggers.map((trigger) => trigger.dataset.galleryUrl))];
        await Promise.all(
            urls.map(async (url) => {
                try {
                    const response = await fetch(url, {
                        headers: { Accept: "application/json" },
                    });
                    if (!response.ok) {
                        return;
                    }
                    const result = await response.json();
                    if (Array.isArray(result.images) && result.images.length) {
                        preloadedImages.set(url, result.images);
                        // Завантажуємо самі зображення в кеш браузера.
                        result.images.forEach((imageUrl) => {
                            const img = new Image();
                            img.src = imageUrl;
                        });
                    }
                } catch {
                    // Ігноруємо помилки: openGallery завантажить галерею по потреби.
                }
            })
        );
    };

    const openGallery = async (trigger) => {
        const coverTrigger = trigger.matches(
            ".photo-work-card, .photo-session-card",
        )
            ? trigger.querySelector(".photo-work-cover, .photo-session-cover")
            : trigger;
        const galleryUrl = trigger.dataset.galleryUrl;
        if (!coverTrigger || !galleryUrl) {
            return;
        }
        activeTrigger = coverTrigger;
        images = [];
        currentIndex = 0;
        requestVersion += 1;
        const thisRequest = requestVersion;
        image.hidden = true;
        image.removeAttribute("src");
        image.classList.add("photo-gallery-image--opening");
        counter.textContent = "";
        status.textContent = "Завантаження галереї…";
        pauseMobileCarouselFocus();
        previousBodyOverflow = document.body.style.overflow;
        previousBodyPaddingRight = document.body.style.paddingRight;
        const scrollbarWidth = window.innerWidth - document.documentElement.clientWidth;
        if (scrollbarWidth > 0) {
            const currentPadding = parseFloat(getComputedStyle(document.body).paddingRight) || 0;
            document.body.style.paddingRight = `${currentPadding + scrollbarWidth}px`;
        }
        document.body.style.overflow = "hidden";
        document.body.classList.add("photo-gallery-open");
        gallery.classList.add("photo-gallery-modal--opening");
        gallery.hidden = false;
        void gallery.offsetWidth;
        requestAnimationFrame(() => gallery.classList.remove("photo-gallery-modal--opening"));
        // Keep keyboard focus on the dialog while it is open. Focusing the
        // close button here activates its focus-visible styling even when the
        // user is only navigating photos with the arrow keys.
        gallery.focus({ preventScroll: true });

        const preloaded = preloadedImages.get(galleryUrl);
        if (preloaded) {
            images = preloaded;
            showImage(0);
            animateGalleryOpen(coverTrigger);
            return;
        }

        try {
            const response = await fetch(galleryUrl, {
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
            animateGalleryOpen(coverTrigger);
        } catch (error) {
            if (thisRequest === requestVersion && !gallery.hidden) {
                status.textContent = error.message || "Не вдалося завантажити галерею.";
            }
        }
    };

    const finishCloseGallery = ({ pointerInitiated = false } = {}) => {
        gallery.classList.remove(
            "photo-gallery-modal--opening",
            "photo-gallery-modal--closing",
            "photo-gallery-modal--returning",
        );
        gallery.hidden = true;
        image.hidden = true;
        image.removeAttribute("src");
        galleryClosing = false;
        document.body.style.overflow = previousBodyOverflow;
        document.body.style.paddingRight = previousBodyPaddingRight;
        document.body.classList.remove("photo-gallery-open");
        waitForMobileScrollToResume();
        if (activeTrigger) {
            const activeCard = activeTrigger.closest(".photo-work-card");
            if (activeCard) {
                if (pointerInitiated) {
                    activeTrigger.blur();
                    if (activeCard.matches(":hover")) {
                        activeCard.classList.add("is-gallery-dismissed");
                        const clearDismissedState = () => {
                            activeCard.classList.remove("is-gallery-dismissed");
                            activeCard.removeEventListener(
                                "pointerleave",
                                clearDismissedState,
                            );
                        };
                        activeCard.addEventListener(
                            "pointerleave",
                            clearDismissedState,
                        );
                    } else {
                        activeCard.classList.remove("is-gallery-dismissed");
                    }
                } else {
                    activeCard.classList.add("is-gallery-dismissed");
                    const clearOnFocusLeave = (event) => {
                        if (
                            event.type === "pointerenter"
                            || !activeCard.contains(event.relatedTarget)
                        ) {
                            activeCard.classList.remove("is-gallery-dismissed");
                            activeCard.removeEventListener(
                                "focusout",
                                clearOnFocusLeave,
                            );
                            activeCard.removeEventListener(
                                "pointerenter",
                                clearOnFocusLeave,
                            );
                        }
                    };
                    activeCard.addEventListener("focusout", clearOnFocusLeave);
                    activeCard.addEventListener("pointerenter", clearOnFocusLeave);
                    activeTrigger.focus({ preventScroll: true });
                }
            }
        }
    };

    const closeGallery = ({ pointerInitiated = false } = {}) => {
        if (gallery.hidden || galleryClosing) {
            return;
        }
        galleryClosing = true;
        requestVersion += 1;
        closeButton.classList.remove("photo-gallery-close--hovered");
        previousButton.classList.remove("photo-gallery-nav--hovered");
        nextButton.classList.remove("photo-gallery-nav--hovered");
        navHighlightTimers.forEach((timer) => window.clearTimeout(timer));
        navHighlightTimers.clear();
        gallery.classList.remove("photo-gallery-modal--opening");
        image.classList.remove("photo-gallery-image--opening");
        image.classList.remove("photo-gallery-image--fade-in");
        window.clearTimeout(galleryFlightTimer);
        image.classList.remove("photo-gallery-image--ready");
        galleryFlightImage?.remove();
        galleryFlightImage = null;
        viewer.querySelectorAll(".photo-gallery-image--outgoing").forEach((outgoingImage) => {
            outgoingImage.remove();
        });

        const activeCard = activeTrigger?.closest(".photo-work-card");
        if (activeCard) {
            activeCard.classList.add("is-gallery-dismissed", "is-gallery-returning");
            void activeCard.offsetWidth;
        }
        const cover = activeTrigger?.querySelector("img");
        const returnToCover = currentIndex === 0 && image.complete && image.naturalWidth && cover;
        gallery.classList.add("photo-gallery-modal--closing");
        let closeDuration = window.matchMedia("(prefers-reduced-motion: reduce)").matches
            ? 0
            : 820;

        if (returnToCover && !window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
            const start = image.getBoundingClientRect();
            const end = cover.getBoundingClientRect();
            if (start.width && start.height && end.width && end.height) {
                const flightImage = image.cloneNode();
                flightImage.classList.remove("photo-gallery-image--opening", "photo-gallery-image--fade-in");
                flightImage.removeAttribute("id");
                flightImage.setAttribute("aria-hidden", "true");
                Object.assign(flightImage.style, {
                    position: "fixed",
                    zIndex: "2001",
                    top: `${start.top}px`,
                    left: `${start.left}px`,
                    width: `${start.width}px`,
                    height: `${start.height}px`,
                    display: "block",
                    maxWidth: "none",
                    maxHeight: "none",
                    margin: "0",
                    objectFit: "cover",
                    borderRadius: "0.5rem",
                    transformOrigin: "top left",
                    transition: "transform 680ms cubic-bezier(0.22, 1, 0.36, 1), opacity 220ms ease",
                    willChange: "transform, opacity",
                    pointerEvents: "none",
                });
                document.body.appendChild(flightImage);
                // The traveling clone now carries the image back to its cover.
                // Hide the stationary gallery copy immediately to prevent a
                // second, fading image from lingering in the center.
                gallery.classList.add("photo-gallery-modal--returning");
                void flightImage.offsetWidth;
                requestAnimationFrame(() => {
                    if (!galleryClosing) {
                        flightImage.remove();
                        return;
                    }
                    flightImage.style.transform = `translate(${end.left - start.left}px, ${end.top - start.top}px) scale(${end.width / start.width}, ${end.height / start.height})`;
                });
                window.setTimeout(() => { flightImage.style.opacity = "0"; }, 500);
                closeDuration = 820;
                galleryFlightImage = flightImage;
            }
        }

        galleryCloseTimer = window.setTimeout(() => {
            galleryFlightImage?.remove();
            galleryFlightImage = null;
            activeCard?.classList.remove("is-gallery-returning");
            finishCloseGallery({ pointerInitiated });
        }, closeDuration);
    };

    // Delegate to the document so cards replaced by the category carousel
    // keep opening the gallery without re-binding individual triggers.
    document.addEventListener("click", (event) => {
        const trigger = event.target.closest?.("[data-gallery-url]");
        if (!trigger) {
            return;
        }
        const control = event.target.closest?.(
            "button, a, input, select, textarea, [role='button']",
        );
        const isCoverButton = control?.matches(
            ".photo-work-cover, .photo-session-cover",
        );
        if (control && !isCoverButton) {
            return;
        }
        openGallery(trigger);
    });
    closeButton.addEventListener("click", (event) => {
        closeGallery({ pointerInitiated: event.detail > 0 });
    });
    previousButton.addEventListener("click", () => {
        highlightNavigationButton(previousButton);
        showImage(currentIndex - 1, -1);
    });
    nextButton.addEventListener("click", () => {
        highlightNavigationButton(nextButton);
        showImage(currentIndex + 1, 1);
    });
    [previousButton, nextButton].forEach((button) => {
        button.addEventListener("pointerdown", () => {
            gallery.classList.remove("photo-gallery-modal--keyboard-navigation");
            highlightNavigationButton(button);
        });
    });
    gallery.addEventListener("pointermove", (event) => {
        if (event.pointerType === "mouse" || event.pointerType === "pen") {
            gallery.classList.remove("photo-gallery-modal--keyboard-navigation");
        }
    }, { passive: true });
    gallery.addEventListener("click", (event) => {
        if (event.target === gallery || event.target === viewer) {
            closeGallery({ pointerInitiated: event.detail > 0 });
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
            const direction = distance < 0 ? 1 : -1;
            highlightNavigationButton(direction > 0 ? nextButton : previousButton);
            showImage(currentIndex + direction, direction);
        }
    }, { passive: true });
    document.addEventListener("keydown", (event) => {
        if (gallery.hidden || galleryClosing) {
            return;
        }
        if (event.key === "Escape") {
            closeButton.classList.add("photo-gallery-close--hovered");
            closeGallery();
            closeButton.blur();
            closeButton.classList.remove("photo-gallery-close--hovered");
        } else if (event.key === "ArrowLeft") {
            gallery.classList.add("photo-gallery-modal--keyboard-navigation");
            if (previousButton === document.activeElement || nextButton === document.activeElement) {
                gallery.focus({ preventScroll: true });
            }
            highlightNavigationButton(previousButton);
            showImage(currentIndex - 1, -1);
        } else if (event.key === "ArrowRight") {
            gallery.classList.add("photo-gallery-modal--keyboard-navigation");
            if (previousButton === document.activeElement || nextButton === document.activeElement) {
                gallery.focus({ preventScroll: true });
            }
            highlightNavigationButton(nextButton);
            showImage(currentIndex + 1, 1);
        }
    });

    document.addEventListener("keyup", (event) => {
        if (gallery.hidden || galleryClosing) {
            return;
        }
        if (event.key === "Escape") {
            closeButton.classList.remove("photo-gallery-close--hovered");
        }
    });

    // Завантажуємо списки галерей одразу після завантаження сторінки,
    // щоб при відкритті галереї фото були відразу доступні.
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", preloadGalleries);
    } else {
        preloadGalleries();
    }
})();
