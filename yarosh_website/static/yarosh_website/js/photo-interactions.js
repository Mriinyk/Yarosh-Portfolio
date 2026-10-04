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

    const commentsGrid = document.querySelector(".photo-session-grid");
    const createCommentElement = (data, actionUrl) => {
        const comment = document.createElement("article");
        comment.className = "photo-comment";
        comment.dataset.commentId = data.comment_id;

        const heading = document.createElement("div");
        heading.className = "photo-comment-heading";
        const author = document.createElement("strong");
        author.textContent = data.username;
        const time = document.createElement("time");
        time.textContent = data.created_at;
        heading.append(author, time);

        const text = document.createElement("p");
        text.textContent = data.text;
        const replyButton = document.createElement("button");
        replyButton.className = "photo-comment-reply";
        replyButton.type = "button";
        replyButton.dataset.replyToggle = "";
        replyButton.setAttribute("aria-expanded", "false");
        replyButton.setAttribute("aria-controls", `photoReplyForm-${data.comment_id}`);
        replyButton.textContent = "Відповісти";

        const replyForm = document.createElement("form");
        replyForm.className = "photo-comment-form photo-comment-reply-form";
        replyForm.id = `photoReplyForm-${data.comment_id}`;
        replyForm.method = "post";
        replyForm.action = actionUrl;
        replyForm.dataset.commentForm = "";
        replyForm.hidden = true;

        const csrfInput = document.createElement("input");
        csrfInput.type = "hidden";
        csrfInput.name = "csrfmiddlewaretoken";
        csrfInput.value = getCookie("csrftoken");
        const parentInput = document.createElement("input");
        parentInput.type = "hidden";
        parentInput.name = "parent_id";
        parentInput.value = data.comment_id;
        const label = document.createElement("label");
        label.className = "visually-hidden";
        label.htmlFor = `photoReplyText-${data.comment_id}`;
        label.textContent = `Відповідь на коментар від ${data.username}`;
        const textarea = document.createElement("textarea");
        textarea.id = `photoReplyText-${data.comment_id}`;
        textarea.name = "text";
        textarea.maxLength = 2000;
        textarea.rows = 2;
        textarea.placeholder = "Ваша відповідь...";
        textarea.required = true;
        const submitButton = document.createElement("button");
        submitButton.type = "submit";
        submitButton.textContent = "Опублікувати";
        replyForm.append(
            csrfInput,
            parentInput,
            label,
            textarea,
            submitButton,
        );

        const replies = document.createElement("div");
        replies.className = "photo-comment-replies";
        replies.dataset.repliesList = "";
        comment.append(heading, text, replyButton, replyForm, replies);
        return comment;
    };

    commentsGrid?.addEventListener("click", (event) => {
        const toggle = event.target.closest("[data-reply-toggle]");
        if (!toggle) {
            return;
        }
        const comment = toggle.closest("[data-comment-id]");
        const form = comment?.querySelector(":scope > [data-comment-form]");
        if (!form) {
            return;
        }
        form.hidden = !form.hidden;
        toggle.setAttribute("aria-expanded", String(!form.hidden));
    });

    commentsGrid?.addEventListener("submit", async (event) => {
        const form = event.target.closest("[data-comment-form]");
        if (!form) {
            return;
        }
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
            const parentId = data.parent_id;
            const destination = parentId
                ? card.querySelector(`[data-comment-id="${parentId}"] [data-replies-list]`)
                : list;
            if (!destination) {
                throw new Error("Не вдалося знайти місце для відповіді.");
            }
            if (!parentId) {
                destination.querySelector(".photo-comments-empty")?.remove();
            }
            destination.append(createCommentElement(data, form.action));
            card.querySelector("[data-comment-count]").textContent = data.comment_count;
            form.hidden = true;
            form.closest("[data-comment-id]")?.querySelector(
                "[data-reply-toggle]",
            )?.setAttribute("aria-expanded", "false");
            form.querySelector("[data-comment-error]")?.remove();
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

    document.querySelectorAll("[data-cover-image]").forEach((image) => {
        const applyCoverRatio = () => {
            if (!image.naturalWidth || !image.naturalHeight) {
                return;
            }
            image.closest(".photo-work-cover")?.style.setProperty(
                "--cover-ratio",
                String(image.naturalWidth / image.naturalHeight),
            );
        };
        if (image.complete) {
            applyCoverRatio();
        } else {
            image.addEventListener("load", applyCoverRatio, { once: true });
        }
    });
})();
