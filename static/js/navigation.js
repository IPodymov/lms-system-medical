/* Поведение выпадающих меню в шапке.
   Заменяет navigation/dropdown_hover.js, который открывал меню по наведению,
   но не закрывал их ни по Escape, ни по клику вне меню, ни при открытии
   соседнего — то есть с клавиатуры меню было ловушкой.

   Разметка — нативный <details>: раскрытие по клику и с клавиатуры работает
   и без этого файла. Здесь только то, чего нативное поведение не даёт. */
(() => {
    const menus = Array.from(document.querySelectorAll(".app-menu"));
    if (!menus.length) return;

    const closeAll = (except) => {
        menus.forEach((menu) => {
            if (menu !== except) menu.open = false;
        });
    };

    menus.forEach((menu) => {
        // Открытие соседнего меню закрывает предыдущее — иначе на широком экране
        // две панели висят одновременно и перекрывают друг друга.
        menu.addEventListener("toggle", () => {
            if (menu.open) closeAll(menu);
        });

        // Escape закрывает меню и возвращает фокус на его кнопку, иначе фокус
        // остаётся внутри скрытой панели.
        menu.addEventListener("keydown", (event) => {
            if (event.key !== "Escape" || !menu.open) return;
            menu.open = false;
            menu.querySelector("summary")?.focus();
        });

        // Уход фокуса за пределы меню закрывает его. Проверка отложена на кадр:
        // в момент focusout activeElement ещё не обновлён.
        menu.addEventListener("focusout", () => {
            requestAnimationFrame(() => {
                if (menu.open && !menu.contains(document.activeElement)) menu.open = false;
            });
        });
    });

    document.addEventListener("click", (event) => {
        if (!event.target.closest(".app-menu")) closeAll(null);
    });

    // Раскрытие по наведению — только для мыши. На тач-устройстве наведение
    // эмулируется первым касанием, из-за чего меню открывалось бы «само».
    if (!window.matchMedia("(hover: hover) and (pointer: fine)").matches) return;

    menus.forEach((menu) => {
        let closeTimer;

        menu.addEventListener("mouseenter", () => {
            clearTimeout(closeTimer);
            menu.open = true;
        });

        menu.addEventListener("mouseleave", () => {
            // Задержка нужна, чтобы меню не захлопывалось при переводе курсора
            // через промежуток между кнопкой и панелью.
            closeTimer = setTimeout(() => {
                if (!menu.contains(document.activeElement)) menu.open = false;
            }, 250);
        });
    });
})();
