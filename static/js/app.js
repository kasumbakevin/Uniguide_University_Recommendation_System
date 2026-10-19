(function () {
    "use strict";

    var toggle = document.querySelector(".nav-toggle");
    var navLinks = document.querySelector(".nav-links");
    if (toggle && navLinks) {
        toggle.addEventListener("click", function () {
            navLinks.classList.toggle("open");
        });
    }

    var citizenship = document.getElementById("citizenship");
    var ugandaFields = document.getElementById("uganda-fields");
    var foreignFields = document.getElementById("foreign-fields");

    function applyCitizenship() {
        if (!citizenship || !ugandaFields || !foreignFields) return;
        var isForeign = citizenship.value === "foreign";
        ugandaFields.classList.toggle("hidden", isForeign);
        foreignFields.classList.toggle("hidden", !isForeign);
    }

    if (citizenship) {
        citizenship.addEventListener("change", applyCitizenship);
        applyCitizenship();
    }

    var mailtoLaunch = document.getElementById("mailto-launch");
    if (mailtoLaunch) {
        window.location.href = mailtoLaunch.href;
    }

    var chatForm = document.getElementById("chat-form");
    if (chatForm) {
        var messages = document.getElementById("chat-messages");
        var input = document.getElementById("chat-question");

        function addBubble(text, who) {
            var bubble = document.createElement("div");
            bubble.className = "chat-bubble " + who;
            var avatar = document.createElement("div");
            avatar.className = "chat-avatar";
            avatar.textContent = who === "bot" ? "Uni" : "You";
            var p = document.createElement("p");
            p.textContent = text;
            bubble.appendChild(avatar);
            bubble.appendChild(p);
            messages.appendChild(bubble);
            messages.scrollTop = messages.scrollHeight;
            return bubble;
        }

        chatForm.addEventListener("submit", function (event) {
            event.preventDefault();
            var question = input.value.trim();
            if (!question) return;

            addBubble(question, "user");
            input.value = "";
            var typing = addBubble("Uni is thinking...", "bot");
            typing.classList.add("typing");

            var body = new FormData();
            body.append("question", question);

            fetch("/chatbot/ask", { method: "POST", body: body, headers: { "X-CSRFToken": getCsrfToken() } })
                .then(function (res) { return res.json(); })
                .then(function (data) {
                    typing.textContent = data.answer || "Sorry, I could not answer that.";
                    typing.classList.remove("typing");
                })
                .catch(function () {
                    typing.textContent = "Something went wrong while contacting Uni.";
                    typing.classList.remove("typing");
                });
        });
    }

    /* ---- CSRF token helper for JS-initiated requests ---- */
    function getCsrfToken() {
        var meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.getAttribute("content") : "";
    }

    /* ---- Confirmation dialogs: data-confirm / data-prompt on any form ---- */
    document.addEventListener("submit", function (event) {
        var form = event.target;
        if (!form || form.tagName !== "FORM") return;
        if (form.dataset.confirmed === "1") return;
        var message = form.getAttribute("data-confirm");
        if (message && !window.confirm(message)) {
            event.preventDefault();
            event.stopPropagation();
            return;
        }
        var expected = form.getAttribute("data-prompt");
        if (expected) {
            var typed = window.prompt(
                "Type the exact name to confirm deletion:\n" + expected, "");
            if (typed === null || typed.trim().toLowerCase() !== expected.trim().toLowerCase()) {
                window.alert("Deletion cancelled — the name did not match '" + expected + "'.");
                event.preventDefault();
                event.stopPropagation();
                return;
            }
            var hidden = form.querySelector('input[name="confirm_name"]');
            if (hidden) hidden.value = typed.trim();
        }
    });

    /* ---- Admin sidebar (mobile) ---- */
    var sideToggle = document.querySelector(".admin-toggle");
    var sidebar = document.getElementById("admin-sidebar");
    if (sideToggle && sidebar) {
        sideToggle.addEventListener("click", function () {
            sidebar.classList.toggle("open");
        });
    }

    /* ---- Appearance preview: accent swatches ---- */
    var swatches = document.querySelectorAll(".swatch[data-accent]");
    swatches.forEach(function (swatch) {
        swatch.addEventListener("click", function () {
            swatches.forEach(function (s) { s.classList.remove("selected"); });
            swatch.classList.add("selected");
            var hidden = document.getElementById("accent-color-input");
            if (hidden) hidden.value = swatch.getAttribute("data-accent");
            document.documentElement.style.setProperty("--green", swatch.getAttribute("data-accent"));
        });
    });
})();