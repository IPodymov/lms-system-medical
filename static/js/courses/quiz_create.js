const form = document.querySelector('#quiz-form');
const answerMode = document.querySelector('#answer-mode');
const textOptions = document.querySelector('#text-options');
const imageOptions = document.querySelector('#image-options');
const imageInput = document.querySelector('#question-image');
const imageEditor = document.querySelector('#image-editor');
const imagePreview = document.querySelector('#image-preview');
const markerLayer = document.querySelector('#marker-layer');
const markerControls = document.querySelector('#marker-controls');
let markers = [];

function selectionType() {
    return answerMode.value === 'multiple' ? 'checkbox' : 'radio';
}

function updateChoiceInputs() {
    document.querySelectorAll('.correct-option').forEach((input) => {
        input.type = selectionType();
    });
    renderMarkers();
}

function renderMarkers() {
    markerLayer.replaceChildren();
    markerControls.replaceChildren();
    markers.forEach((marker, index) => {
        const pin = document.createElement('span');
        pin.className = 'image-marker';
        pin.style.left = `${marker.x}%`;
        pin.style.top = `${marker.y}%`;
        pin.textContent = index + 1;
        markerLayer.append(pin);
        const control = document.createElement('label');
        control.className = 'choice';
        const correct = document.createElement('input');
        correct.type = selectionType();
        correct.name = 'correct_option';
        correct.value = index;
        correct.checked = marker.correct;
        correct.addEventListener('change', () => {
            marker.correct = correct.checked;
        });
        const x = document.createElement('input');
        x.type = 'hidden';
        x.name = 'marker_x';
        x.value = marker.x;
        const y = document.createElement('input');
        y.type = 'hidden';
        y.name = 'marker_y';
        y.value = marker.y;
        const remove = document.createElement('button');
        remove.type = 'button';
        remove.className = 'button-secondary';
        remove.textContent = 'Удалить отметку';
        remove.addEventListener('click', () => {
            markers.splice(index, 1);
            renderMarkers();
        });
        control.append(correct, ` Область ${index + 1}`, x, y);
        markerControls.append(control, remove);
    });
}

document.querySelectorAll('input[name="question_kind"]').forEach((input) => input.addEventListener('change', () => {
    const imageQuestion = form.question_kind.value === 'image';
    textOptions.hidden = imageQuestion;
    imageOptions.hidden = !imageQuestion;
    document.querySelectorAll('#text-options input[name="option"]').forEach((field) => {
        field.required = !imageQuestion;
    });
    imageInput.required = imageQuestion;
}));
answerMode.addEventListener('change', updateChoiceInputs);
imageInput.addEventListener('change', () => {
    const [file] = imageInput.files;
    if (!file) return;
    imagePreview.src = URL.createObjectURL(file);
    imageEditor.hidden = false;
    markers = [];
    renderMarkers();
});
imagePreview.addEventListener('click', (event) => {
    const box = imagePreview.getBoundingClientRect();
    markers.push({
        x: Number(((event.clientX - box.left) / box.width * 100).toFixed(2)),
        y: Number(((event.clientY - box.top) / box.height * 100).toFixed(2)),
        correct: false
    });
    renderMarkers();
});
