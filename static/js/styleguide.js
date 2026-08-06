/* Интерактив страницы /styleguide/.
   Загружается только на ней, поэтому каждый обработчик заранее проверяет
   наличие своего элемента и молча выходит, если разметки нет. */
(() => {
    const root = document.documentElement;

    /* --- Контраст ---------------------------------------------------------
       Коэффициенты считаются из фактически применённых значений токенов, а не
       из таблицы в документации. Поэтому цифры на странице всегда описывают
       текущую тему и обновляются при её переключении: расхождение между
       спецификацией и реальностью становится видно сразу. */

    const parseColor = (value) => {
        const text = value.trim();
        if (text.startsWith("#")) {
            const hex = text.slice(1);
            const full =
                hex.length === 3
                    ? hex
                        .split("")
                        .map((c) => c + c)
                        .join("")
                    : hex;
            return [0, 2, 4].map((i) => parseInt(full.slice(i, i + 2), 16));
        }
        const numbers = text.match(/[\d.]+/g);
        return numbers ? numbers.slice(0, 3).map(Number) : null;
    };

    const luminance = (rgb) => {
        const [r, g, b] = rgb.map((channel) => {
            const c = channel / 255;
            return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
        });
        return 0.2126 * r + 0.7152 * g + 0.0722 * b;
    };

    const contrast = (foreground, background) => {
        const a = parseColor(foreground);
        const b = parseColor(background);
        if (!a || !b) return null;
        const [light, dark] = [luminance(a), luminance(b)].sort((x, y) => y - x);
        return (light + 0.05) / (dark + 0.05);
    };

    const paintContrast = () => {
        const styles = getComputedStyle(root);
        document.querySelectorAll("[data-sg-contrast]").forEach((node) => {
            const [foreground, background] = node.dataset.sgContrast.split("|");
            const ratio = contrast(
                styles.getPropertyValue(foreground),
                styles.getPropertyValue(background),
            );
            if (ratio === null) {
                node.textContent = "—";
                return;
            }
            const minimum = Number(node.dataset.sgMin || 4.5);
            const passes = ratio >= minimum;
            node.textContent = `${ratio.toFixed(2)}:1 ${passes ? "AA" : "НЕ ПРОХОДИТ"}`;
            node.classList.toggle("sg-pass", passes);
            node.classList.toggle("sg-fail", !passes);
        });
    };

    paintContrast();
    document.getElementById("theme-toggle")?.addEventListener("click", () => {
        // Атрибут data-theme меняется синхронно, но пересчёт нужен уже по новым
        // значениям — переносим его в следующий кадр.
        requestAnimationFrame(paintContrast);
    });
    window
        .matchMedia("(prefers-color-scheme: dark)")
        .addEventListener("change", paintContrast);

    /* --- Плотность --------------------------------------------------------- */

    document.querySelectorAll("[data-sg-density]").forEach((button) => {
        button.addEventListener("click", () => {
            const target = document.querySelector(button.dataset.sgDensity);
            if (!target) return;
            const compact = target.getAttribute("data-density") === "compact";
            if (compact) {
                target.removeAttribute("data-density");
            } else {
                target.setAttribute("data-density", "compact");
            }
            button.setAttribute("aria-pressed", String(!compact));
            button.textContent = compact ? "Включить плотный режим" : "Обычный режим";
        });
    });

    /* --- Модальное окно ----------------------------------------------------
       Нативный <dialog> с showModal() даёт ловушку фокуса, закрытие по Escape
       и инертный фон. Вручную остаётся только вернуть фокус на триггер. */

    document.querySelectorAll("[data-sg-modal-open]").forEach((trigger) => {
        const dialog = document.querySelector(trigger.dataset.sgModalOpen);
        if (!dialog) return;
        trigger.addEventListener("click", () => {
            dialog.showModal();
            dialog.addEventListener("close", () => trigger.focus(), {once: true});
        });
        dialog
            .querySelectorAll("[data-sg-modal-close]")
            .forEach((button) => button.addEventListener("click", () => dialog.close()));
    });

    /* --- Всплывающие уведомления ------------------------------------------
       Область объявлена в разметке заранее: если добавить её в DOM вместе с
       сообщением, скринридер ничего не объявит. */

    const toastRegion = document.querySelector("[data-sg-toast-region]");

    document.querySelectorAll("[data-sg-toast]").forEach((button) => {
        button.addEventListener("click", () => {
            if (!toastRegion) return;
            const level = button.dataset.sgToast;
            const toast = document.createElement("div");
            toast.className = `ui-alert ui-alert--${level} ui-toast`;
            // Ошибка объявляется ассертивно, остальное — в порядке очереди.
            toast.setAttribute("role", level === "danger" ? "alert" : "status");
            const body = document.createElement("div");
            body.className = "ui-alert__body";
            body.textContent = button.dataset.sgToastText || "Готово";
            toast.append(body);
            toastRegion.append(toast);
            setTimeout(() => toast.remove(), 5000);
        });
    });

    /* --- Состояние загрузки ------------------------------------------------ */

    document.querySelectorAll("[data-sg-loading]").forEach((button) => {
        button.addEventListener("click", () => {
            button.classList.add("is-loading");
            button.setAttribute("aria-busy", "true");
            setTimeout(() => {
                button.classList.remove("is-loading");
                button.removeAttribute("aria-busy");
            }, 2000);
        });
    });

    /* --- Валидация поля ----------------------------------------------------
       Baymard: проверять на blur, но гасить ошибку сразу при исправлении, а не
       дожидаясь повторного ухода с поля. */

    document.querySelectorAll("[data-sg-validate]").forEach((field) => {
        const input = field.querySelector("input");
        const error = field.querySelector(".ui-error");
        if (!input || !error) return;

        const validate = () => {
            const invalid = !input.value.includes("@");
            field.classList.toggle("is-invalid", invalid);
            input.setAttribute("aria-invalid", String(invalid));
            error.hidden = !invalid;
            return invalid;
        };

        input.addEventListener("blur", validate);
        input.addEventListener("input", () => {
            if (field.classList.contains("is-invalid")) validate();
        });
    });
})();
