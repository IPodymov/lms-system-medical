/* Редактор вопроса теста: переключение типа вопроса и разметка изображения.

   До этапа 4.11 файл был инлайновым <script> в шаблоне quiz_create.html —
   некешируемым и неминифицируемым. Разметку отметок здесь строит только
   этот скрипт: на сервер она уходит парами полей marker_x / marker_y. */
(() => {
    const form = document.querySelector("[data-quiz-form]");
    if (!form) return;

    const textOptions = form.querySelector("[data-text-options]");
    const imageOptions = form.querySelector("[data-image-options]");
    const imageInput = form.querySelector("input[type='file']");
    const editor = form.querySelector("[data-image-editor]");
    const preview = form.querySelector("[data-image-preview]");
    const markerLayer = form.querySelector("[data-marker-layer]");
    const markerControls = form.querySelector("[data-marker-controls]");
    const answerMode = form.querySelector("[name='answer_mode']");
    let markers = [];

    /* Один правильный ответ — радиокнопки, несколько — флажки. Тип
       переключается у уже отрисованных полей, чтобы не терять выбранное. */
    const selectionType = () => (answerMode.value === "multiple" ? "checkbox" : "radio");

    const renderMarkers = () => {
        markerLayer.replaceChildren();
        markerControls.replaceChildren();

        markers.forEach((marker, index) => {
            const pin = document.createElement("span");
            pin.className = "quiz-editor__marker";
            // Координата — данное, а не оформление: она уходит в CSS
            // кастомными свойствами, а позиционирование остаётся в стилях.
            pin.style.setProperty("--marker-x", `${marker.x}%`);
            pin.style.setProperty("--marker-y", `${marker.y}%`);
            pin.textContent = index + 1;
            markerLayer.append(pin);

            const row = document.createElement("div");
            row.className = "quiz-create__option";

            const control = document.createElement("label");
            control.className = "ui-check";
            const correct = document.createElement("input");
            correct.type = selectionType();
            correct.name = "correct_option";
            correct.value = index;
            correct.checked = marker.correct;
            correct.addEventListener("change", () => {
                marker.correct = correct.checked;
            });
            const caption = document.createElement("span");
            caption.textContent = `Область ${index + 1}`;
            control.append(correct, caption);

            const x = document.createElement("input");
            x.type = "hidden";
            x.name = "marker_x";
            x.value = marker.x;
            const y = document.createElement("input");
            y.type = "hidden";
            y.name = "marker_y";
            y.value = marker.y;

            const remove = document.createElement("button");
            remove.type = "button";
            remove.className = "ui-btn ui-btn--secondary ui-btn--sm";
            remove.textContent = "Удалить отметку";
            remove.addEventListener("click", () => {
                markers.splice(index, 1);
                renderMarkers();
            });

            row.append(control, x, y, remove);
            markerControls.append(row);
        });
    };

    const applyQuestionKind = () => {
        const isImageQuestion = form.question_kind.value === "image";
        textOptions.hidden = isImageQuestion;
        imageOptions.hidden = !isImageQuestion;
        // Скрытое поле с required не даёт отправить форму и не показывает,
        // что именно мешает: браузер не умеет фокусировать невидимое.
        textOptions.querySelectorAll("input[name='option']").forEach((field) => {
            field.required = !isImageQuestion;
        });
        imageInput.required = isImageQuestion;
    };

    form.querySelectorAll("input[name='question_kind']").forEach((input) => {
        input.addEventListener("change", applyQuestionKind);
    });

    answerMode.addEventListener("change", () => {
        form.querySelectorAll(".correct-option").forEach((input) => {
            input.type = selectionType();
        });
        renderMarkers();
    });

    imageInput.addEventListener("change", () => {
        const [file] = imageInput.files;
        if (!file) return;
        preview.src = URL.createObjectURL(file);
        editor.hidden = false;
        markers = [];
        renderMarkers();
    });

    preview.addEventListener("click", (event) => {
        const box = preview.getBoundingClientRect();
        markers.push({
            x: Number((((event.clientX - box.left) / box.width) * 100).toFixed(2)),
            y: Number((((event.clientY - box.top) / box.height) * 100).toFixed(2)),
            correct: false,
        });
        renderMarkers();
    });

    applyQuestionKind();
})();
