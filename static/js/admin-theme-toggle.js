(function () {
    const STORAGE_KEY = "awas_admin_theme"; // "light" or "dark"
    const CLASS_DARK = "jazzmin-dark-mode";
    const CLASS_LIGHT = "jazzmin-light-mode";

    function ensureToggleButton() {
        // Jazzmin places the profile dropdown inside #jazzy-usermenu
        const userMenu = document.getElementById("jazzy-usermenu");
        if (!userMenu) {
            return;
        }

        if (document.getElementById("theme-toggle")) {
            return; // already added or overridden by template
        }

        const changePwdLink = userMenu.querySelector("a[href*='password_change']");
        const logoutBlock = document.getElementById("logout-form");

        const link = document.createElement("a");
        link.href = "#";
        link.id = "theme-toggle";
        link.className = changePwdLink ? changePwdLink.className : "dropdown-item";
        link.setAttribute("role", "button");
        link.setAttribute("aria-label", "Toggle dark mode");
        link.innerHTML = '<i class="fas fa-moon mr-2"></i><span id="theme-toggle-label">Dark mode</span>';

        if (logoutBlock && logoutBlock.parentNode === userMenu) {
            userMenu.insertBefore(link, logoutBlock);
            const divider = document.createElement("div");
            divider.className = "dropdown-divider";
            userMenu.insertBefore(divider, logoutBlock);
        } else if (changePwdLink && changePwdLink.parentNode === userMenu) {
            userMenu.insertBefore(link, changePwdLink.nextSibling);
        } else {
            userMenu.appendChild(link);
        }
    }

    function applyTheme(theme) {
        const body = document.body;
        body.classList.remove(CLASS_DARK, CLASS_LIGHT);

        if (theme === "dark") {
            body.classList.add(CLASS_DARK);
        } else {
            body.classList.add(CLASS_LIGHT);
        }

        const toggle = document.getElementById("theme-toggle");
        const label = document.getElementById("theme-toggle-label");

        if (toggle) {
            toggle.dataset.theme = theme;

            if (label) {
                label.textContent = theme === "dark" ? "Light mode" : "Dark mode";
            }

            const icon = toggle.querySelector("i");
            if (icon) {
                if (theme === "dark") {
                    icon.classList.remove("fa-moon");
                    icon.classList.add("fa-sun");
                } else {
                    icon.classList.remove("fa-sun");
                    icon.classList.add("fa-moon");
                }
            }
        }
    }

    function getSavedTheme() {
        try {
            const value = window.localStorage.getItem(STORAGE_KEY);
            return value === "dark" ? "dark" : "light";
        } catch (e) {
            return "light";
        }
    }

    function saveTheme(theme) {
        try {
            window.localStorage.setItem(STORAGE_KEY, theme);
        } catch (e) {
            // Ignore storage errors (e.g. disabled storage)
        }
    }

    function init() {
        // Make sure the button exists in the current Jazzmin user dropdown
        ensureToggleButton();

        const initialTheme = getSavedTheme();
        applyTheme(initialTheme);

        document.addEventListener("click", function (event) {
            const toggle = event.target.closest("#theme-toggle");
            if (!toggle) return;

            event.preventDefault();
            const current = toggle.dataset.theme === "dark" ? "dark" : "light";
            const next = current === "dark" ? "light" : "dark";
            applyTheme(next);
            saveTheme(next);
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();


