/* Панель программы курса: состояние свёрнутости и прокрутка к текущему блоку.

   Разметка — нативный <details open>, поэтому без JS программа просто
   остаётся раскрытой везде. Здесь только улучшения. */
(() => {
    const outline = document.getElementById("course-outline");
    if (!outline) return;

    const STORAGE_KEY = "medlms-outline-open";
    const WIDE_SCREEN = window.matchMedia("(min-width: 1024px)");

    const readPreference = () => {
        try {
            const stored = localStorage.getItem(STORAGE_KEY);
            return stored === null ? null : stored === "1";
        } catch (e) {
            /* localStorage недоступен: приватный режим или запрет хранилища */
            return null;
        }
    };

    // На узком экране раскрытая программа отодвигает материал далеко вниз,
    // поэтому по умолчанию она свёрнута. Явный выбор пользователя важнее
    // умолчания и переносится между страницами курса.
    const preference = readPreference();
    outline.open = preference === null ? WIDE_SCREEN.matches : preference;

    outline.addEventListener("toggle", () => {
        try {
            localStorage.setItem(STORAGE_KEY, outline.open ? "1" : "0");
        } catch (e) {
            /* см. выше — сохранять некуда, поведение остаётся корректным */
        }
    });

    // Текущий блок может оказаться далеко в списке: панель прокручивается
    // сама, но только внутри себя, чтобы не дёргать страницу.
    const current = outline.querySelector('[aria-current="true"]');
    if (current && outline.open) {
        const panel = outline.querySelector(".outline__body");
        if (panel && outline.scrollHeight > outline.clientHeight) {
            outline.scrollTop = Math.max(
                0,
                current.offsetTop - outline.clientHeight / 2,
            );
        }
    }
})();
