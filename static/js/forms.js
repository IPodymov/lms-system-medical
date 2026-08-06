/* Поведение форм, общее для всего приложения.

   Загружается на каждой странице, поэтому каждый блок сначала проверяет,
   есть ли для него разметка, и молча выходит, если её нет. */
(() => {
    /* --- Фокус на сводку ошибок ---------------------------------------------
       Паттерн GOV.UK: после неудачной отправки пользователь клавиатуры должен
       сразу оказаться у описания проблемы, а не искать её по странице.
       Заодно к заголовку вкладки приписывается «Ошибка:» — так о неудаче
       узнаёт и тот, кто переключился на другую вкладку. */

    const summary = document.querySelector("[data-error-summary]");
    if (summary) {
        summary.focus();
        if (!document.title.startsWith("Ошибка:")) {
            document.title = `Ошибка: ${document.title}`;
        }
    }

    /* --- Гашение ошибки при исправлении --------------------------------------
       Исследование Baymard: сообщение обязано исчезать сразу, как только ввод
       стал корректным, а не при следующем уходе с поля. Иначе пользователь
       решает, что его правка не сработала, и начинает менять верное значение.

       Здесь нет собственной валидации — используется встроенная браузерная
       (checkValidity), чтобы не расходиться с тем, что проверит сервер. */

    document.querySelectorAll(".ui-field.is-invalid").forEach((wrapper) => {
        const control = wrapper.querySelector(".ui-input, .ui-select, .ui-textarea");
        const error = wrapper.querySelector(".ui-error");
        if (!control) return;

        let touched = false;

        const clear = () => {
            wrapper.classList.remove("is-invalid");
            control.removeAttribute("aria-invalid");
            if (error) error.hidden = true;
        };

        control.addEventListener("input", () => {
            touched = true;
            // Серверную ошибку снимаем при первом же осмысленном изменении:
            // проверить её повторно на клиенте мы не можем.
            if (control.value.trim()) clear();
        });

        control.addEventListener("blur", () => {
            if (touched && !control.checkValidity()) {
                wrapper.classList.add("is-invalid");
                control.setAttribute("aria-invalid", "true");
            }
        });
    });

    /* --- Защита от двойной отправки ------------------------------------------
       Атрибут data-submit-once уже встречался в разметке проекта, но
       обработчика для него не существовало — то есть защита была задумана
       и не дописана.

       Кнопка не выключается через disabled: отключённая кнопка не отправляет
       своё имя и значение, а формы с несколькими кнопками (конструктор курса)
       на этом ломаются. Вместо этого блокируется повторная отправка формы. */

    document.querySelectorAll("form").forEach((form) => {
        const button = form.querySelector("[data-submit-once]");
        if (!button) return;

        let submitted = false;
        form.addEventListener("submit", (event) => {
            if (submitted) {
                event.preventDefault();
                return;
            }
            // Невалидную форму браузер не отправит — блокировать её нельзя,
            // иначе после исправления пользователь не сможет отправить снова.
            if (!form.checkValidity()) return;

            submitted = true;
            button.classList.add("is-loading");
            button.setAttribute("aria-busy", "true");
        });
    });
})();
