(() => {
    const getCookie = (name) => {
        const prefix = `${name}=`;
        const cookie = document.cookie
            .split(";")
            .map((part) => part.trim())
            .find((part) => part.startsWith(prefix));
        return cookie ? decodeURIComponent(cookie.slice(prefix.length)) : "";
    };

    const sendShare = (modal) => {
        const csrfToken = getCookie("csrftoken");
        fetch(modal.dataset.shareEndpoint, {
            method: "POST",
            headers: {
                "X-CSRFToken": csrfToken,
                "X-Requested-With": "XMLHttpRequest",
            },
            keepalive: true,
        })
            .then(async (response) => {
                const data = await response.json();
                if (!response.ok) {
                    throw new Error(data.error || "Не вдалося зареєструвати поширення.");
                }
                const card = document.getElementById(
                    `photoshoot-${modal.dataset.sessionId}`,
                );
                const count = card?.querySelector("[data-share-count]");
                if (count) {
                    count.textContent = data.shares_count;
                }
            })
            .catch((error) => {
                console.error("Не вдалося зареєструвати поширення фотосесії:", error);
                const status = modal.querySelector("[data-share-status]");
                if (status) {
                    status.textContent = "Не вдалося оновити лічильник поширень.";
                }
            });
    };

    document.querySelectorAll("[data-photo-like]").forEach((button) => {
        button.addEventListener("click", async () => {
            button.disabled = true;
            try {
                const response = await fetch(button.dataset.actionUrl, {
                    method: "POST",
                    headers: {
                        "X-CSRFToken": getCookie("csrftoken"),
                        "X-Requested-With": "XMLHttpRequest",
                    },
                });
                const data = await response.json();
                if (!response.ok) {
                    throw new Error(data.error || "Не вдалося оновити вподобання.");
                }
                button.classList.toggle("is-liked", data.liked);
                button.setAttribute("aria-pressed", String(data.liked));
                button.querySelector("[data-like-count]").textContent = data.likes_count;
            } catch (error) {
                console.error("Не вдалося оновити вподобання:", error);
                button.title = error.message;
            } finally {
                button.disabled = false;
            }
        });
    });

    document.querySelectorAll("[data-comment-form]").forEach((form) => {
        form.addEventListener("submit", async (event) => {
            event.preventDefault();
            const submitButton = form.querySelector('button[type="submit"]');
            const textarea = form.querySelector("textarea");
            const card = form.closest(".photo-work-card");
            const list = card.querySelector("[data-comments-list]");
            submitButton.disabled = true;
            try {
                const response = await fetch(form.action, {
                    method: "POST",
                    headers: {
                        "X-CSRFToken": getCookie("csrftoken"),
                        "X-Requested-With": "XMLHttpRequest",
                    },
                    body: new FormData(form),
                });
                const data = await response.json();
                if (!response.ok) {
                    throw new Error(data.error || "Не вдалося опублікувати коментар.");
                }
                textarea.value = "";
                list.querySelector(".photo-comments-empty")?.remove();
                const comment = document.createElement("article");
                comment.className = "photo-comment";
                const header = document.createElement("div");
                const author = document.createElement("strong");
                author.textContent = data.username;
                const time = document.createElement("time");
                time.textContent = data.created_at;
                header.append(author, time);
                const text = document.createElement("p");
                text.textContent = data.text;
                comment.append(header, text);
                list.prepend(comment);
                card.querySelector("[data-comment-count]").textContent = data.comment_count;
            } catch (error) {
                console.error("Не вдалося опублікувати коментар:", error);
                let message = form.querySelector("[data-comment-error]");
                if (!message) {
                    message = document.createElement("p");
                    message.className = "photo-form-error";
                    message.dataset.commentError = "";
                    form.append(message);
                }
                message.textContent = error.message;
            } finally {
                submitButton.disabled = false;
            }
        });
    });

    document.querySelectorAll(".photo-share-modal").forEach((modal) => {
        modal.querySelectorAll("[data-share-link]").forEach((link) => {
            link.addEventListener("click", () => sendShare(modal));
        });
        const copyButton = modal.querySelector("[data-copy-share]");
        copyButton?.addEventListener("click", async () => {
            const status = modal.querySelector("[data-share-status]");
            try {
                await navigator.clipboard.writeText(copyButton.dataset.shareUrl);
                sendShare(modal);
                status.textContent = "Посилання скопійовано.";
            } catch (error) {
                console.error("Не вдалося скопіювати посилання:", error);
                status.textContent = "Не вдалося скопіювати посилання. Спробуйте скопіювати його з поля вище.";
            }
        });
    });

    document.querySelectorAll("[data-new-category-field]").forEach((field) => {
        const typeSelect = document.getElementById("id_photo_type");
        const categoryInput = field.querySelector("input");
        if (!typeSelect) {
            return;
        }
        const updateVisibility = () => {
            const creatingCategory = typeSelect.value === "__new__";
            field.hidden = !creatingCategory;
            categoryInput.required = creatingCategory;
        };
        typeSelect.addEventListener("change", updateVisibility);
        updateVisibility();
    });
})();
