function enableSorting(zoneSelector, itemSelector) {
    document.querySelectorAll(zoneSelector).forEach((zone) => {
        let dragged;
        let dragFromHandle = false;
        zone.addEventListener('pointerdown', (event) => {
            dragFromHandle = Boolean(event.target.closest('[data-drag-handle]'));
        });
        zone.addEventListener('dragstart', (event) => {
            if (!dragFromHandle) {
                event.preventDefault();
                return;
            }
            dragged = event.target.closest(itemSelector);
            if (dragged) {
                dragged.classList.add('is-dragging');
                event.dataTransfer.effectAllowed = 'move';
            }
        });
        zone.addEventListener('dragover', (event) => {
            event.preventDefault();
            const target = event.target.closest(itemSelector);
            if (dragged && target && target !== dragged) {
                const before = event.clientY < target.getBoundingClientRect().top + target.offsetHeight / 2;
                zone.insertBefore(dragged, before ? target : target.nextSibling);
            }
        });
        zone.addEventListener('dragend', () => {
            if (!dragged) return;
            dragged.classList.remove('is-dragging');
            const form = document.querySelector(`#${zone.dataset.sortForm}`);
            dragged = undefined;
            dragFromHandle = false;
            form?.requestSubmit();
        });
    });
}

enableSorting('[data-lesson-dropzone]', '.topic-card');
enableSorting('[data-block-dropzone]', '.content-block');
