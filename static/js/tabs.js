/* Вкладки поверх обычных якорных ссылок.

   Прогрессивное улучшение: без этого файла разметка остаётся тем, чем была
   до этапа 4.10 — навигацией по якорям, где все разделы видны сразу. Скрипт
   лишь прячет неактивные панели и достраивает роли ARIA.

   Разметка:
     <div data-tabs="имя">
       <nav class="ui-tabs"><a class="ui-tab" href="#panel-id">…</a></nav>
       <section id="panel-id">…</section>
     </div>

   Имя из data-tabs участвует в ключе sessionStorage: формы панели уходят
   обычным POST и возвращают пользователя на свежую страницу, поэтому
   выбранную вкладку нужно помнить — иначе после каждого действия человек
   оказывается в первом разделе. */
(() => {
    document.querySelectorAll("[data-tabs]").forEach((container) => {
        const tablist = container.querySelector(".ui-tabs");
        const tabs = [...container.querySelectorAll(".ui-tab")];
        if (!tablist || tabs.length < 2) return;

        const panels = tabs.map((tab) => document.getElementById(tab.getAttribute("href").slice(1)));
        // Хоть одна панель не найдена — оставляем страницу как есть: лучше
        // длинный список разделов, чем спрятанный и недостижимый раздел.
        if (panels.some((panel) => !panel)) return;

        const storageKey = `medlms-tab:${location.pathname}:${container.dataset.tabs}`;

        tablist.setAttribute("role", "tablist");
        tabs.forEach((tab, index) => {
            const panel = panels[index];
            tab.setAttribute("role", "tab");
            tab.id = tab.id || `${panel.id}-tab`;
            tab.setAttribute("aria-controls", panel.id);
            panel.setAttribute("role", "tabpanel");
            panel.setAttribute("aria-labelledby", tab.id);
            // Панель прокручивается и должна быть достижима с клавиатуры
            // после перехода по вкладке.
            panel.tabIndex = 0;
        });

        const activate = (index, { focus = false } = {}) => {
            tabs.forEach((tab, i) => {
                const selected = i === index;
                tab.setAttribute("aria-selected", String(selected));
                // Роving tabindex: Tab выводит из полосы вкладок целиком,
                // между вкладками ходят стрелками — паттерн WAI-ARIA.
                tab.tabIndex = selected ? 0 : -1;
                panels[i].hidden = !selected;
            });
            if (focus) tabs[index].focus();
            try {
                sessionStorage.setItem(storageKey, tabs[index].getAttribute("href"));
            } catch (e) {
                /* приватный режим: вкладка просто не запомнится */
            }
            // replaceState, а не присвоение hash: присвоение прокручивает
            // страницу к панели и дёргает экран при каждом переключении.
            history.replaceState(null, "", tabs[index].getAttribute("href"));
        };

        const initial = () => {
            let stored = null;
            try {
                stored = sessionStorage.getItem(storageKey);
            } catch (e) {
                /* см. выше */
            }
            const wanted = location.hash || stored;
            const index = tabs.findIndex((tab) => tab.getAttribute("href") === wanted);
            return index === -1 ? 0 : index;
        };

        tabs.forEach((tab, index) => {
            tab.addEventListener("click", (event) => {
                event.preventDefault();
                activate(index, { focus: true });
            });
        });

        tablist.addEventListener("keydown", (event) => {
            const current = tabs.indexOf(document.activeElement);
            if (current === -1) return;
            const last = tabs.length - 1;
            const moves = {
                ArrowRight: current === last ? 0 : current + 1,
                ArrowLeft: current === 0 ? last : current - 1,
                Home: 0,
                End: last,
            };
            if (!(event.key in moves)) return;
            event.preventDefault();
            activate(moves[event.key], { focus: true });
        });

        activate(initial());
    });
})();
