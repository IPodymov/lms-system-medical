/* Конструктор курса: перетаскивание тем и блоков, подтверждение удаления.

   До этапа 4.12 файл был инлайновым <script> в templates/courses/edit.html.

   Перетаскивание — улучшение, а не единственный способ: у каждой темы и
   каждого блока есть кнопки «вверх / вниз», которые работают без этого
   скрипта (WCAG 2.5.7). Поэтому здесь ничего не проверяется на доступность
   мыши: если скрипт не загрузился, страница остаётся рабочей. */
(() => {
    /* --- Подтверждение удаления --------------------------------------------
       Заменяет инлайновый onclick="return confirm(...)": инлайновый
       обработчик не проходит Content-Security-Policy и не переиспользуется. */
    document.querySelectorAll("[data-confirm]").forEach((button) => {
        button.addEventListener("click", (event) => {
            if (!window.confirm(button.dataset.confirm)) event.preventDefault();
        });
    });

    /* --- Перетаскивание ------------------------------------------------------ */
    const enableSorting = (zoneSelector, itemSelector) => {
        document.querySelectorAll(zoneSelector).forEach((zone) => {
            let dragged;
            let dragFromHandle = false;

            // Перетаскивание начинается только с ручки: иначе выделение
            // текста внутри карточки превращалось бы в её перенос.
            zone.addEventListener("pointerdown", (event) => {
                dragFromHandle = Boolean(event.target.closest("[data-drag-handle]"));
            });

            zone.addEventListener("dragstart", (event) => {
                if (!dragFromHandle) {
                    event.preventDefault();
                    return;
                }
                dragged = event.target.closest(itemSelector);
                if (dragged) {
                    dragged.classList.add("is-dragging");
                    event.dataTransfer.effectAllowed = "move";
                }
            });

            zone.addEventListener("dragover", (event) => {
                event.preventDefault();
                const target = event.target.closest(itemSelector);
                if (dragged && target && target !== dragged) {
                    const middle = target.getBoundingClientRect().top + target.offsetHeight / 2;
                    zone.insertBefore(dragged, event.clientY < middle ? target : target.nextSibling);
                }
            });

            zone.addEventListener("dragend", () => {
                if (!dragged) return;
                dragged.classList.remove("is-dragging");
                // Порядок уходит скрытой формой: поля с id элементов лежат
                // внутри самих карточек и связаны с ней атрибутом form.
                const form = document.getElementById(zone.dataset.sortForm);
                dragged = undefined;
                dragFromHandle = false;
                form?.requestSubmit();
            });
        });
    };

    enableSorting("[data-lesson-dropzone]", ".builder-topic");
    enableSorting("[data-block-dropzone]", ".builder-block");
})();
