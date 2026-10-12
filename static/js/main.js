/*
 * Sam's Stunning Furniture: site interactions
 * - Header turns solid once the page scrolls past the hero.
 * - Mobile menu toggle.
 * - Search panel toggle.
 */
(function () {
    "use strict";

    var header = document.querySelector("[data-site-header]");
    if (!header) {
        return;
    }

    var menuToggle = header.querySelector("[data-menu-toggle]");
    var nav = header.querySelector("[data-main-nav]");
    var searchToggle = header.querySelector("[data-search-toggle]");
    var searchPanel = header.querySelector("[data-site-search]");
    var hasHero = document.body.classList.contains("has-hero");
    var desktopQuery = window.matchMedia("(min-width: 1024px)");

    var menuOpen = false;
    var searchOpen = false;

    function updateHeaderState() {
        var scrolled = window.scrollY > 40;
        header.classList.toggle("is-solid", !hasHero || scrolled || menuOpen || searchOpen);
    }

    function setMenu(open) {
        menuOpen = open;
        nav.classList.toggle("is-open", open);
        menuToggle.setAttribute("aria-expanded", String(open));
        menuToggle.setAttribute("aria-label", open ? "Close menu" : "Open menu");
        document.body.classList.toggle("is-locked", open);
        if (open) {
            setSearch(false);
        }
        updateHeaderState();
    }

    function setSearch(open) {
        searchOpen = open;
        searchPanel.hidden = !open;
        searchToggle.setAttribute("aria-expanded", String(open));
        if (open) {
            if (menuOpen) {
                setMenu(false);
            }
            searchPanel.querySelector("input").focus();
        }
        updateHeaderState();
    }

    menuToggle.addEventListener("click", function () {
        setMenu(!menuOpen);
    });

    searchToggle.addEventListener("click", function () {
        setSearch(!searchOpen);
    });

    // Close the mobile menu after choosing a link (e.g. in-page anchors).
    nav.addEventListener("click", function (event) {
        if (menuOpen && event.target.closest("a")) {
            setMenu(false);
        }
    });

    document.addEventListener("keydown", function (event) {
        if (event.key !== "Escape") {
            return;
        }
        if (menuOpen) {
            setMenu(false);
            menuToggle.focus();
        } else if (searchOpen) {
            setSearch(false);
            searchToggle.focus();
        }
    });

    // Leaving the mobile layout while the menu is open should not leave the page locked.
    desktopQuery.addEventListener("change", function (event) {
        if (event.matches && menuOpen) {
            setMenu(false);
        }
    });

    window.addEventListener("scroll", updateHeaderState, { passive: true });
    updateHeaderState();
})();
