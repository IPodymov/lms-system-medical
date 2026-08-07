/* Панель управления: организация запоминается между формами.

   На странице четыре формы, и в каждой свой список организаций. WCAG 2.2
   SC 3.3.7 (Redundant Entry) требует не заставлять вводить одно и то же
   повторно в рамках одного процесса: администратор колледжа выбирал свою
   организацию четыре раза подряд.

   Выбор синхронизируется между формами сразу и переживает перезагрузку —
   формы уходят обычным POST, после которого страница собирается заново. */
(() => {
    const selects = [...document.querySelectorAll('select[name="organization"]')];
    if (selects.length < 2) return;

    const storageKey = "medlms-organization";
    const has = (select, value) => [...select.options].some((option) => option.value === value);

    const apply = (value, source) => {
        if (!value) return;
        selects.forEach((select) => {
            if (select !== source && has(select, value)) select.value = value;
        });
    };

    let stored = null;
    try {
        stored = sessionStorage.getItem(storageKey);
    } catch (e) {
        /* приватный режим: выбор просто не переживёт перезагрузку */
    }
    if (stored) apply(stored);

    selects.forEach((select) => {
        select.addEventListener("change", () => {
            apply(select.value, select);
            try {
                sessionStorage.setItem(storageKey, select.value);
            } catch (e) {
                /* см. выше */
            }
        });
    });
})();
