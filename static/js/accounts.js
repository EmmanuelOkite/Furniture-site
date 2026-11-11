/*
 * Account pages: show/hide password, password strength hint, confirm-password
 * matching, loading state on submit and printing backup codes.
 * Everything here is a convenience only; the server validates every request.
 */
(function () {
    "use strict";

    // Show / hide password ------------------------------------------------------
    document.querySelectorAll("[data-password-toggle]").forEach(function (button) {
        var input = document.getElementById(button.getAttribute("aria-controls"));
        if (!input) {
            return;
        }
        button.addEventListener("click", function () {
            var show = input.type === "password";
            input.type = show ? "text" : "password";
            button.textContent = show ? "Hide" : "Show";
            button.setAttribute("aria-pressed", String(show));
            button.setAttribute("aria-label", show ? "Hide password" : "Show password");
        });
        button.setAttribute("aria-label", "Show password");
    });

    // Password strength hint ---------------------------------------------------
    var COMMON = ["password", "123456", "qwerty", "letmein", "welcome", "admin", "iloveyou", "monkey", "furniture"];
    var LABELS = ["Too weak", "Weak", "Fair", "Good", "Strong"];

    function scorePassword(value) {
        if (!value) {
            return 0;
        }
        var lower = value.toLowerCase();
        if (COMMON.some(function (word) { return lower.indexOf(word) !== -1; }) || /^\d+$/.test(value)) {
            return Math.min(1, value.length >= 8 ? 1 : 0);
        }
        var variety = [/[a-z]/, /[A-Z]/, /\d/, /[^A-Za-z0-9]/].filter(function (re) { return re.test(value); }).length;
        var score = 0;
        if (value.length >= 12) { score += 2; } else if (value.length >= 8) { score += 1; }
        if (value.length >= 16) { score += 1; }
        if (variety >= 3) { score += 1; }
        if (/(.)\1\1/.test(value)) { score -= 1; }
        return Math.max(0, Math.min(4, score));
    }

    document.querySelectorAll("[data-strength-meter]").forEach(function (input) {
        var meter = document.createElement("div");
        meter.className = "strength";
        meter.id = input.id + "_strength";
        meter.setAttribute("aria-live", "polite");
        meter.innerHTML = '<div class="strength__bar" aria-hidden="true"><div class="strength__fill"></div></div><span class="strength__label"></span>';
        meter.hidden = true;
        input.closest(".form-field").insertBefore(meter, input.closest(".password-input").nextSibling);

        var fill = meter.querySelector(".strength__fill");
        var label = meter.querySelector(".strength__label");
        input.addEventListener("input", function () {
            var score = scorePassword(input.value);
            meter.hidden = !input.value;
            meter.dataset.score = String(score);
            fill.style.width = ((score + 1) * 20) + "%";
            label.textContent = "Strength: " + LABELS[score];
        });
    });

    // Confirm password must match ------------------------------------------------
    document.querySelectorAll("[data-match]").forEach(function (confirm) {
        var original = document.getElementById(confirm.dataset.match);
        if (!original) {
            return;
        }
        function check() {
            confirm.setCustomValidity(
                confirm.value && confirm.value !== original.value ? "The two passwords don’t match." : ""
            );
        }
        confirm.addEventListener("input", check);
        original.addEventListener("input", check);
    });

    // Loading state; also prevents double submission ------------------------------
    document.querySelectorAll("form[data-account-form]").forEach(function (form) {
        form.addEventListener("submit", function () {
            var button = form.querySelector("button[type=submit]");
            if (!button || button.getAttribute("aria-busy") === "true") {
                return;
            }
            button.setAttribute("aria-busy", "true");
            button.dataset.originalText = button.textContent;
            if (button.dataset.loadingText) {
                button.textContent = button.dataset.loadingText;
            }
            // Disable after the browser has captured the form data.
            window.setTimeout(function () { button.disabled = true; }, 0);
        });
    });

    // Re-enable buttons when the page is restored from the back/forward cache.
    window.addEventListener("pageshow", function (event) {
        if (event.persisted) {
            document.querySelectorAll("button[aria-busy=true]").forEach(function (button) {
                button.disabled = false;
                button.removeAttribute("aria-busy");
                if (button.dataset.originalText) {
                    button.textContent = button.dataset.originalText;
                }
            });
        }
    });

    document.querySelectorAll("[data-print]").forEach(function (button) {
        button.addEventListener("click", function () { window.print(); });
    });
})();
