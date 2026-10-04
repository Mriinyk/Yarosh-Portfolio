const heroSlider = document.querySelector("[data-hero-slider]");

if (heroSlider instanceof HTMLElement) {
    const slides = Array.from(heroSlider.querySelectorAll(".hero-slide"));
    const interval = Number.parseInt(heroSlider.dataset.interval ?? "5000", 10);
    const transitionDuration = 1800;

    if (slides.length > 1 && Number.isFinite(interval) && interval > 0) {
        let activeIndex = 0;
        let isTransitioning = false;

        window.setInterval(async () => {
            if (isTransitioning) {
                return;
            }

            const currentSlide = slides[activeIndex];
            const nextIndex = (activeIndex + 1) % slides.length;
            const nextSlide = slides[nextIndex];

            try {
                await nextSlide.decode();
            } catch (error) {
                console.error("Could not decode the next hero slide.", error);
                return;
            }

            isTransitioning = true;
            nextSlide.classList.add("is-preparing");
            window.requestAnimationFrame(() => {
                currentSlide.classList.add("is-leaving");
                currentSlide.setAttribute("aria-hidden", "true");
                nextSlide.classList.remove("is-preparing");
                nextSlide.classList.add("is-active");
                nextSlide.setAttribute("aria-hidden", "false");

                window.setTimeout(() => {
                    currentSlide.classList.remove("is-active", "is-leaving");
                    isTransitioning = false;
                }, transitionDuration);
            });

            activeIndex = nextIndex;
        }, interval);
    }
}
