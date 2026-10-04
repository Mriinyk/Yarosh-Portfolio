(() => {
    const stats = document.querySelector("[data-site-stats]");
    if (!stats) {
        return;
    }

    const updateStats = async () => {
        try {
            const response = await fetch(stats.dataset.statsUrl, {
                headers: { Accept: "application/json" },
                cache: "no-store",
            });
            if (!response.ok) {
                throw new Error(`Статистика недоступна (HTTP ${response.status}).`);
            }
            const data = await response.json();
            stats.querySelector("[data-visits-count]").textContent = data.visits;
            stats.querySelector("[data-photos-count]").textContent = data.photo_sessions;
        } catch (error) {
            console.error("Не вдалося оновити лічильники сайту:", error);
        }
    };

    window.setInterval(updateStats, 15000);
})();
