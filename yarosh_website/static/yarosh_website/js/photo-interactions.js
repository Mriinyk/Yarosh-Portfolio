(() => {
    const getCookie = (name) => {
        const prefix = `${name}=`;
        const cookie = document.cookie
            .split(";")
            .map((part) => part.trim())
            .find((part) => part.startsWith(prefix));
        return cookie ? decodeURIComponent(cookie.slice(prefix.length)) : "";
    };

    const showAuthHint = (control, loginUrl, signupUrl) => {
        document.querySelector(".photo-auth-hint")?.remove();
        const hint = document.createElement("span");
        hint.className = "photo-auth-hint";
        hint.dataset.authHint = "";
        hint.setAttribute("role", "status");
        hint.append("Потрібно ");
        if (loginUrl) {
            const loginLink = document.createElement("a");
            loginLink.href = loginUrl;
            loginLink.textContent = "Увійти";
            hint.append(loginLink);
            if (signupUrl) {
                hint.append(", або ");
            }
        }
        if (signupUrl) {
            const signupLink = document.createElement("a");
            signupLink.href = signupUrl;
            signupLink.textContent = "Зареєструватися";
            hint.append(signupLink);
        }
        hint.append(" на сайті.");
        document.body.append(hint);

        const controlRect = control.getBoundingClientRect();
        const hintRect = hint.getBoundingClientRect();
        const left = Math.min(
            Math.max(
                controlRect.left + controlRect.width / 2 - hintRect.width / 2,
                8,
            ),
            window.innerWidth - hintRect.width - 8,
        );
        hint.style.left = `${left}px`;
        hint.style.top = `${Math.max(controlRect.top - hintRect.height - 8, 8)}px`;
        window.setTimeout(() => hint.remove(), 4000);
    };

    // Delegated handlers keep working after the category carousel swaps the
    // grid contents without a full page reload.
    document.addEventListener("click", (event) => {
        const control = event.target.closest?.("[data-auth-hint]");
        if (!control) {
            return;
        }
        event.preventDefault();
        showAuthHint(control, control.href, control.dataset.signupUrl);
    });

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

    document.addEventListener("click", async (event) => {
        const button = event.target.closest?.("[data-photo-like]");
        if (!button) {
            return;
        }
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
                const error = new Error(
                    data.error || "Не вдалося оновити вподобання.",
                );
                error.status = response.status;
                throw error;
            }
            button.classList.toggle("is-liked", data.liked);
            button.setAttribute("aria-pressed", String(data.liked));
            button.querySelector("[data-like-count]").textContent = data.likes_count;
        } catch (error) {
            console.error("Не вдалося оновити вподобання:", error);
            button.title = error.message;
            if (error.status === 401) {
                showAuthHint(
                    button,
                    button.dataset.loginUrl,
                    button.dataset.signupUrl,
                );
            }
        } finally {
            button.disabled = false;
        }
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

    document.addEventListener("click", (event) => {
        const shareLink = event.target.closest?.("[data-share-link]");
        if (shareLink) {
            const modal = shareLink.closest(".photo-share-modal");
            if (modal) {
                sendShare(modal);
            }
            return;
        }
        const copyButton = event.target.closest?.("[data-copy-share]");
        if (!copyButton) {
            return;
        }
        const modal = copyButton.closest(".photo-share-modal");
        if (!modal) {
            return;
        }
        const status = modal.querySelector("[data-share-status]");
        (async () => {
            try {
                await navigator.clipboard.writeText(copyButton.dataset.shareUrl);
                sendShare(modal);
                status.textContent = "Посилання скопійовано.";
            } catch (error) {
                console.error("Не вдалося скопіювати посилання:", error);
                status.textContent = "Не вдалося скопіювати посилання. Спробуйте скопіювати його з поля вище.";
            }
        })();
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

    const applyCoverRatio = (image) => {
        if (!image.naturalWidth || !image.naturalHeight) {
            return;
        }
        image.closest(".photo-work-cover")?.style.setProperty(
            "--cover-ratio",
            String(image.naturalWidth / image.naturalHeight),
        );
    };
    const applyReadyCovers = () => {
        document.querySelectorAll("[data-cover-image]").forEach((image) => {
            if (image.complete) {
                applyCoverRatio(image);
            }
        });
    };
    // `load` does not bubble, so listen in the capture phase to also catch
    // cover images injected later by the category carousel.
    document.addEventListener("load", (event) => {
        const image = event.target;
        if (image instanceof HTMLImageElement && image.hasAttribute("data-cover-image")) {
            applyCoverRatio(image);
        }
    }, true);
    applyReadyCovers();
    document.addEventListener("photos:grid-updated", applyReadyCovers);
})();
