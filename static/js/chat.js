/* Живой чат: приём сообщений по websocket и отправка без перезагрузки.

   До этапа 4.8 файл был <script> внутри templates/messaging/realtime_chat.html,
   и id пользователя стоял прямо в JS-строке: `"{{ user.id }}"`. Такой скрипт
   нельзя ни закешировать, ни минифицировать — он менялся у каждого
   пользователя. Теперь идентификатор приходит data-атрибутом формы.

   Разметку сообщения повторяет templates/components/chat_message.html.
   Меняешь одно — меняй второе, иначе пришедшее сообщение будет отличаться
   от того же самого после перезагрузки страницы. */
(() => {
    const form = document.querySelector("[data-chat-form]");
    if (!form) return;

    /* --- Видимое состояние «файл выбран» -------------------------------------
       Настоящий input убран с экрана, кнопку изображает <label>. Без этого
       блока после выбора файла на странице не менялось ничего: пользователь
       не знал, приложится ли вложение к сообщению. */

    const fileInput = form.querySelector("input[type='file']");
    const fileName = form.querySelector("[data-attachment-name]");
    if (fileInput && fileName) {
        fileInput.addEventListener("change", () => {
            const file = fileInput.files[0];
            fileName.textContent = file ? file.name : "";
            form.classList.toggle("has-attachment", Boolean(file));
        });
    }

    /* --- Websocket ----------------------------------------------------------- */

    const list = document.querySelector("[data-chat-list]");
    if (!list || !window.WebSocket) return;

    const currentUserId = form.dataset.currentUser;
    const scheme = window.location.protocol === "https:" ? "wss" : "ws";
    const socket = new WebSocket(
        `${scheme}://${window.location.host}${form.dataset.websocketPath}`,
    );
    const bodyInput = form.querySelector("textarea");
    const tokenInput = form.querySelector("input[name='client_token']");

    const appendMessage = (message) => {
        // Своё же сообщение возвращается сокетом обратно — по якорю видно,
        // что оно уже на странице, и второй раз его рисовать не нужно.
        if (document.getElementById(`message-${message.id}`)) return;

        const article = document.createElement("article");
        article.id = `message-${message.id}`;
        article.className = "chat-msg";
        const senderId = message.sender_id || message.author_id;
        if (senderId === currentUserId) article.classList.add("chat-msg--own");

        const author = document.createElement("strong");
        author.className = "chat-msg__author";
        author.textContent = message.sender_name || message.author_name;
        article.append(author);

        if (message.body) {
            const text = document.createElement("p");
            text.className = "chat-msg__body";
            text.textContent = message.body;
            article.append(text);
        }

        if (message.attachment_url) {
            const attachment = document.createElement("a");
            attachment.className = "chat-msg__attachment";
            attachment.href = message.attachment_url;
            attachment.target = "_blank";
            attachment.rel = "noopener";
            attachment.textContent = "Скачать вложение";
            article.append(attachment);
        }

        const time = document.createElement("time");
        time.className = "chat-msg__time";
        time.textContent = message.created_at;
        article.append(time);

        // Пустое состояние живёт внутри той же области: с приходом первого
        // сообщения ему там больше не место.
        list.querySelector(".ui-empty")?.remove();
        list.append(article);
        list.scrollTop = list.scrollHeight;
    };

    socket.addEventListener("message", (event) => {
        const payload = JSON.parse(event.data);
        if (payload.type === "message") appendMessage(payload.message);
    });

    /* Обработчик висит на document в фазе перехвата, а не на самой форме.
       Иначе первым отработает защита от двойной отправки из forms.js: она
       пометит форму как отправленную и погасит кнопку, хотя никакой отправки
       не было — сообщение ушло сокетом. На document в перехвате мы получаем
       событие раньше и, отправив сообщение сами, останавливаем его. */
    document.addEventListener(
        "submit",
        (event) => {
            if (event.target !== form) return;
            // Вложение уходит обычной отправкой формы: файл через сокет не
            // передать. Закрытый сокет — тоже повод отдать всё серверу.
            if (socket.readyState !== WebSocket.OPEN || fileInput.files.length) return;
            const body = bodyInput.value.trim();
            if (!body) return;
            event.preventDefault();
            event.stopPropagation();
            socket.send(JSON.stringify({body, client_token: tokenInput.value}));
            bodyInput.value = "";
            tokenInput.value = crypto.randomUUID();
        },
        true,
    );
})();
