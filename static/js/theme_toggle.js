(function () {
    var STORAGE_KEY = "medlms-theme";
    var root = document.documentElement;

    // Без явного выбора тему задаёт система (prefers-color-scheme в tokens.css),
    // поэтому эффективную тему нельзя вывести из одного лишь атрибута: при
    // светлой системной теме и пустом data-theme первое нажатие иначе
    // «переключало» на светлую, то есть визуально не делало ничего.
    function currentTheme() {
        var explicit = root.getAttribute("data-theme");
        if (explicit === "light" || explicit === "dark") {
            return explicit;
        }
        return window.matchMedia("(prefers-color-scheme: dark)").matches
            ? "dark"
            : "light";
    }

    document.addEventListener("DOMContentLoaded", function () {
        var toggle = document.getElementById("theme-toggle");
        if (!toggle) return;

        toggle.addEventListener("click", function () {
            var next = currentTheme() === "dark" ? "light" : "dark";
            root.setAttribute("data-theme", next);
            try {
                localStorage.setItem(STORAGE_KEY, next);
            } catch (e) {
                /* localStorage unavailable (private mode, disabled storage) */
            }
        });
    });
})();
