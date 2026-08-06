# Этап 0. Аудит кодовой базы

Дата: 2026-08-05. Ветка `main`, коммит `c7f9827`.
Режим: только чтение, изменений в коде не вносилось.

Базовое состояние на момент аудита: `manage.py check` — 0 issues, `pytest` — 70 passed.

---

## 0. Фактический стек (вместо плейсхолдеров из брифа)

Бриф пришёл с незаполненными `<плейсхолдерами>`. Ниже — то, что реально в репозитории; сверьте, если где-то расходится с вашим представлением.

| Пункт брифа | Факт в коде |
|---|---|
| Django | **6.0.x** (`requirements.txt`: `Django>=6.0,<6.1`), Python `>=3.14` |
| Шаблоны | **Django Templates**, `APP_DIRS=True`, но все шаблоны лежат в корневом `templates/` (в приложениях нет ни одного) |
| Фронтенд | **Собственный CSS без фреймворка**, ~3800 строк. Bootstrap/Tailwind/jQuery отсутствуют |
| БД | PostgreSQL (`psycopg`), локально — SQLite через `DJANGO_USE_SQLITE=1` |
| Сборка статики | **Нет сборщика.** `collectstatic` + WhiteNoise `CompressedManifestStaticFilesStorage` |
| Интерактив | `django-htmx` установлен, middleware включён, htmx с CDN подключён — **и не используется вообще** (0 атрибутов `hx-*`). Плюс ~200 строк vanilla JS |
| Realtime | Channels + Daphne, WebSocket-чат (`apps/messaging`) |
| Язык | `LANGUAGE_CODE = "ru"`, `USE_I18N = True`, но **ни одного `{% trans %}`** — весь текст захардкожен по-русски |
| Тёмная тема | **Уже есть**, `[data-theme]` + localStorage. Тёмная — дефолт |

**Аудитория (по коду ролей `OrganizationMembership.Role`):** `student`, `teacher`, `assistant`, `curator`, `organization_admin`, `system_admin`. То есть аудитория брифа («студенты, преподаватели, админы школы») подтверждается, плюс есть ассистент и куратор потока.

---

## 1. Дерево приложений, шаблоны и рендерящие их view

### Приложения

```
apps/
├── accounts/       identity, роли, профиль, панель управления, документация  [views.py 670 строк]
├── organizations/  Organization / Faculty / Department / StudyGroup / Membership  (без views и urls)
├── courses/        Course, CourseRun, Section, Lesson, ContentBlock, конструктор  [views.py 670 строк]
├── learning/       Enrollment, прогресс, плеер урока                          [views.py 78]
├── assessments/    Quiz, Question, Option, Attempt                            [views.py 70]
├── grading/        журнал оценок                                              [views.py 14]
├── notifications/  уведомления + Celery-задачи                                [views.py 30]
├── messaging/      личные сообщения, чат курса, WebSocket-консьюмеры          [views.py 161]
├── audit/          журнал событий (без UI)
└── api/            DRF-сериализаторы и вьюхи для /api/v1/ (без UI)
```

Служебное: `apps/imaging.py` (сжатие загружаемых картинок), `apps/test_helpers.py`.

### Карта «шаблон → view → URL → контекст»

| Шаблон | View | URL name | Ключевые контекстные переменные |
|---|---|---|---|
| `base.html` | — | — | из context processors (см. §2) |
| `dashboard.html` | `accounts.views.dashboard` | `dashboard` (`/`) | `enrollments` (срез 6) |
| `accounts/login.html` | `accounts.views.Login` (CBV) | `login` | `form` |
| `accounts/register.html` | `accounts.views.register` | `register` | `form` |
| `accounts/profile.html` | `accounts.views.profile` | `profile` | `profile_form`, `password_form`, `history` |
| `accounts/admin_dashboard.html` | `accounts.views.admin_dashboard` | `admin-dashboard` | `metrics`, `can_manage_users`, `can_create_organizations`, `institution_types`, `roles`, `organizations`, `course_runs`, `study_groups`, `students`, `teachers`, `enrollment_links`, `admin_documentation_url` |
| `accounts/study_group_detail.html` | `accounts.views.study_group_detail` | `study-group-detail` | `study_group`, `members`, `course_runs`, `enrollment_links` |
| `accounts/admin_documentation.html` | `accounts.views.admin_documentation` | `admin-documentation` | — (без контекста) |
| `accounts/documentation_home.html` | `accounts.views.documentation_home` | `documentation-home` | `can_access_management_documentation` |
| `accounts/documentation_courses.html` | `accounts.views.course_documentation` | `documentation-courses` | то же |
| `accounts/documentation_management.html` | `accounts.views.management_documentation` | `documentation-management` | то же |
| `courses/catalog.html` | `courses.views.catalog` | `course-catalog` | `runs`, `draft_courses` |
| `courses/my_courses.html` | `courses.views.my_courses` | `my-courses` | `enrollments` |
| `courses/detail.html` | `courses.views.course_detail` | `course-detail` | `course`, `can_edit` |
| `courses/create.html` | `courses.views.course_create` | `course-create` | — (читает `request.POST` напрямую!) |
| `courses/edit.html` | `courses.views.course_edit` | `course-edit` | `course`, `blocks`, `lessons`, `sections`, `material_links`, `active_run`, `schedule_run`, `is_editor_enrolled` |
| `courses/quiz_create.html` | `courses.views.quiz_create` | `quiz-create` | `course`, `lessons`, `selected_lesson` (+ `request.POST`) |
| `courses/enroll_by_link.html` | `courses.views.enroll_by_link` | `enroll-by-link` | `enrollment_link` |
| `learning/course.html` | `learning.views.course_learning` | `course-learning` | `enrollment`, `blocks`, `current_block`, `previous_block`, `next_block`, `progresses` |
| `assessments/take_quiz.html` | `assessments.views.take_quiz` | `take-quiz` | `quiz`, `attempt`, `questions`, `enrollment` |
| `assessments/result.html` | `assessments.views.take_quiz` (POST) | — | `attempt`, `enrollment` |
| `grading/gradebook.html` | `grading.views.gradebook` | `gradebook` | `run`, `enrollments` |
| `notifications/list.html` | `notifications.views.list_notifications` | `notifications` | `notifications` |
| `notifications/detail.html` | `notifications.views.notification_detail` | `notification-detail` | `item` |
| `messaging/direct_messages.html` | `messaging.views.direct_messages` | `direct-messages`, `direct-message-thread` | `contacts`, `recipient`, `thread`, `form`, `query`, `recipient_is_favorite`, `recipient_membership` |
| `messaging/course_chat.html` | `messaging.views.course_chat` | `course-chat` | `course_run`, `chat_messages`, `form` |
| `errors/{400,403,404,500}.html` | `config.views.*` | handlers | — |
| `components/alert.html` | `courses.views.enroll_view` / `enroll_by_link` (HTTP 400) | — | `message`, `level` |
| `components/enrollment_links.html` | `{% include %}` | — | `enrollment_links`, `enrollment_links_empty_message`, `enrollment_links_next_url`, `enrollment_links_page_anchor` |

**Всего 32 шаблона, 26 страниц.** Ни одного шаблона внутри приложений — всё в корневом `templates/`, хотя `APP_DIRS=True`.

---

## 2. Карта наследования шаблонов

**Она предельно плоская — и это её главная проблема.**

```
base.html  (104 строки, 7.5 КБ)
 └── {% extends %} ← ВСЕ 30 страничных шаблонов, ровно один уровень
```

- **`{% extends %}`**: 30 шаблонов, все напрямую от `base.html`. Промежуточных layout-шаблонов (`_two_column.html`, `_management_base.html`) нет — при этом три страницы управления и три страницы документации фактически разделяют одну и ту же двухколоночную раскладку, скопированную руками.
- **`{% include %}`**: всего **3 включения на весь проект**:
  - `components/enrollment_links.html` → включён в `admin_dashboard.html` и `study_group_detail.html` (единственный настоящий переиспользуемый партиал);
  - `messaging/realtime_chat.html` → включён в `direct_messages.html` и `course_chat.html`, но это **не UI-партиал, а `<script>`-блок с Django-переменной `{{ user.id }}` внутри JS**;
  - `components/alert.html` — не включается, а рендерится как самостоятельный ответ на HTTP 400.
- **`{% block %}`** в `base.html`: только два — `title` и `content`. Нет блоков `extra_css`, `extra_js`, `page_actions`, `breadcrumbs`, `sidebar`. Из-за этого страничный JS вставляется прямо в `{% block content %}` (см. `courses/edit.html`, `courses/quiz_create.html`).
- **Кастомные теги/фильтры**: ровно один — `apps/learning/templatetags/learning_tags.py`, фильтр `get_item` (`mapping.get(key)`), используется в `learning/course.html` для доступа к словарю прогресса. `inclusion_tag` не используется нигде.
- **Context processors** (`config/context_processors.py`):
  - `navigation_context` → `unread_notifications_count`, `unread_messages_count`, `can_open_management`, `can_create_course`, `can_access_documentation`. Все пять используются в `base.html`. Для анонимов возвращает нули без запросов.
  - `static_asset_version` → `static_asset_version`; **на каждый запрос делает `rglob("*.css")` по диску и берёт максимальный mtime**. В DEBUG это приемлемо, в проде — лишний I/O при том, что WhiteNoise-манифест уже даёт хеш в имени файла.

---

## 3. Инвентаризация статики

### Подключённые библиотеки

Ровно одна внешняя: **htmx 2.0.4 с `https://unpkg.com/`** (`base.html:26`). Никаких CSS-фреймворков, шрифтов с CDN, иконочных наборов — иконки нарисованы inline-SVG прямо в `base.html`.

### Размеры

| Файл | Строк | Байт |
|---|---:|---:|
| `css/layouts/application.css` | 3002 | **57 125** |
| `css/components/navigation.css` | 419 | 8 935 |
| `css/components/forms.css` | 103 | 1 970 |
| `css/base/tokens.css` | 65 | 1 899 |
| `css/components/question-image.css` | 71 | 1 445 |
| `css/components/feedback.css` | 46 | 949 |
| `css/base/reset.css` | 34 | 635 |
| `css/components/table.css` | 39 | 658 |
| `css/components/card.css` | 14 | 257 |
| `css/app.css` (только `@import`) | 8 | 340 |
| **Итого CSS** | **3801** | **~74 КБ** |
| `js/theme_toggle.js` | — | 685 |
| `js/navigation/dropdown_hover.js` | — | 501 |
| htmx (CDN) | — | ~50 КБ gzip ~17 КБ |

**На каждой странице грузится 8 отдельных `<link>` + htmx + 2 скрипта = 11 сетевых запросов.** `app.css` с `@import`-ами существует, но `base.html` его игнорирует и подключает файлы по одному (причём `question-image.css` не подключён вообще — он только в `app.css`, то есть на странице теста стили маркеров **не загружаются**; это баг, а не только вопрос дизайна).

### Как собирается

`collectstatic` → WhiteNoise `CompressedManifestStaticFilesStorage` (хеш в имени + `.gz`). `WHITENOISE_MANIFEST_STRICT = True`. Никакого django-compressor, webpack, vite, esbuild. Минификации CSS/JS нет. Критического CSS нет. `staticfiles/` в `.gitignore` (в репозиторий не попадает), но локально лежит с ~7 поколениями старых хешей — мусор от прошлых прогонов.

### Дубли и мёртвый код

**Кеш-бастинг делается дважды:** WhiteNoise уже даёт `app.180141bf....css`, и поверх этого `base.html` добавляет `?v={{ static_asset_version }}`. Один из двух механизмов лишний.

**Дублирующиеся селекторы внутри `application.css`** (объявлены дважды, вторая декларация побеждает по порядку — классический источник «почему мой отступ не применяется»):

`.quiz-cta`, `.quiz-cta span`, `.management-panel`, `.management-form`, `.link-list`, `.content-block`, `.chat-composer`, `.chat-card header`, `.block-forms form`, `.add-block`.

**Мёртвый CSS — классы, объявленные в CSS и не встречающиеся ни в одном шаблоне:**

`.admin-documentation-card` (5 правил), `.compact-list` (3), `.content-list` (3), `.enrollment-forms` (1), `.grid` (3, включая `.grid .card` в `card.css`), `.management-grid` (2), `.management-inline-form` (5), `.management-workspace` (3), `.message-image` (1), `.role-form` (3), `.save-order` (1), `.topic-actions` (3).

**Мёртвая разметка — классы в шаблонах, под которые нет ни одного CSS-правила:**

`.dashboard-section` (`dashboard.html`), `.schedule-form` (`courses/edit.html`), `.result` (`assessments/result.html`).

**Мёртвая зависимость:** `django-htmx` в `INSTALLED_APPS` и `MIDDLEWARE`, htmx подключён с CDN на каждой странице — **и ни одного `hx-*` атрибута во всём проекте**. Сейчас это ~17 КБ gzip и сторонний домен в критическом пути на каждый запрос ради нуля функциональности.

**Слой «layout-fixes».** Коммит `c7f9827` влил `layout-fixes.css` в конец `application.css` (строки ~2254–3002, четверть файла). Это не компоненты, а глобальные заплатки поверх уже написанного:

```css
h1, h2, h3, h4, p, a, button, label, small, span { overflow-wrap: anywhere; }
p { max-width: 75ch; }                     /* включая <p> внутри таблиц и карточек */
body { overflow-x: hidden; }               /* прячет переполнение вместо починки */
.card, .form-card, .course-detail, .course-card,
.builder-section, .topic-card, .learning-card,
.empty-state { overflow: hidden; }         /* обрежет любой поповер/дропдаун внутри карточки */
```

Плюс в этом же блоке — 9 из 9 `!important` всего проекта и повторное объявление раскладок, которые уже описаны выше по файлу. Это прямой антипаттерн из проектного скилла `design` («если тянетесь к `!important`, значит существующее правило специфичнее, чем задумано»).

### Брейкпоинты

**11 разных `max-width` брейкпоинтов**, все ad-hoc, ни один не вынесен в токен:

`1040`, `1024`, `900`, `767`, `760`, `700`, `640`, `479`, `380`, `359` px (+ `prefers-reduced-motion`).

`767` и `760`, `1040` и `1024`, `380` и `359` — это по сути одна и та же граница, добавленная в разное время. Целевых размеров из брифа (360 / 768 / 1280 / 1920) в системе нет: **1280 и 1920 не обслуживаются вообще**, вся раскладка упирается в `--content-width: 1180px` и дальше просто центрируется.

---

## 4. Как рендерятся формы

**Ни crispy-forms, ни widget-tweaks — их нет ни в зависимостях, ни в коде.** Формы рендерятся тремя несовместимыми способами:

**(а) `{{ form.as_p }}` — Django по умолчанию.** 3 формы: `login.html`, `register.html`, обе формы в `profile.html`. Даёт `<p><label>…</label><input></p>` — вёрстку, которую нельзя оформить консистентно с остальным приложением, потому что она не совпадает по структуре с ручными `<label>…<input></label>` на других страницах.

**(б) Ручные поля по одному.** 2 формы: `direct_messages.html`, `course_chat.html` — `{{ form.client_token }}`, `{{ form.body }}`, `{{ form.attachment }}` вставлены по отдельности.

**(в) Полностью ручной HTML без Django-формы вообще.** **Основная масса — ~25 форм.** Конструктор курса (`courses/edit.html` — 8 форм), панель управления (`admin_dashboard.html` — 7 форм), `study_group_detail.html` (3), `courses/create.html`, `courses/quiz_create.html`, `enroll_by_link.html` и др. Поля пишутся как `<input name="section_title" required placeholder="…">`, а во view читаются через `request.POST.get(...)`.

Последствия этого напрямую видны в коде:

- **Ошибки валидации не отображаются рядом с полем.** Вместо этого view кладёт `messages.error(...)` и рендерит страницу заново со статусом 400 — сообщение всплывает наверху страницы, оторванное от поля. Пример: `courses/views.py:198,203`.
- **Введённые данные восстанавливаются через `{{ request.POST.title }}` прямо в шаблоне** (`courses/create.html`, `courses/quiz_create.html`) — то есть шаблон читает сырой POST. Это работает, но означает, что никакой формы, которую можно было бы отрендерить единообразно, для этих страниц просто не существует.
- Единого класса `.form-error`, `.field-error`, `.errorlist` в CSS **нет вообще** — состояние ошибки поля не оформлено ни для одной формы.

**Переопределения виджетов** — только в `apps/messaging/forms.py`: `Textarea(attrs={"rows": 3, "placeholder": "…"})` для `body` в `DirectMessageForm` и `CourseMessageForm`, плюс `HiddenInput` для `client_token`. В `accounts/forms.py` виджеты не переопределяются, задаются только `labels`.

**HTML, вшитый в Python:** прямого HTML в Python **нет** — это хорошая новость. Но есть его функциональный эквивалент: `components/alert.html` рендерится как полный HTTP-ответ с телом `<p class="alert error">…</p>` без `{% extends %}` (`courses/views.py:108,123,134`) — то есть при ошибке записи на курс пользователь получает страницу из одного голого абзаца, без шапки, навигации и стилей вокруг. **Это самый заметный функциональный дефект, найденный в аудите.**

---

## 5. Инвентаризация UI-компонентов и их вариаций

### Кнопки — 6 несводимых вариантов

| Вариант | Где объявлен | Использований | Вид |
|---|---|---:|---|
| голый `<button>` (глобальный селектор!) | `forms.css:1` | **35** | primary, синий |
| `.button-link` (это `<a>`) | `application.css:410` | 9 | выглядит как primary-кнопка |
| `.button-secondary` | `application.css:1710` | 8 | серая |
| `.button-danger` | `application.css:2358` | 1 | красная |
| `.table-action-danger` | `application.css:1244` | 1 | красная, **другая** |
| `.favorite-button`, `.attachment-button` | `application.css:1529,1646` | 3 | самостоятельные одноразовые стили |

Проблема не в количестве, а в том, что **primary-кнопка задана селектором по тегу `button`**. Любой `<button>` где угодно автоматически становится синим primary — включая кнопки-иконки и служебные кнопки. Чтобы сделать кнопку невыразительной, приходится добавлять класс-перебивку, а не наоборот. Состояний `:disabled` и `loading` нет ни у одного варианта (единственное исключение — `.chat-composer button:disabled`).

### Карточки — 8 параллельных реализаций одного и того же

`.card` (базовая, `card.css`), `.form-card`, `.course-card`, `.learning-card`, `.topic-card`, `.management-panel` (объявлена **дважды**), `.documentation-card`, `.documentation-link-card`, `.profile-card`, `.contacts-card`, `.chat-card`, `.notification-item`, `.link-row`, `.group-row`. У каждой свои `padding`, `border-radius`, `box-shadow` и hover — сведённого «одного вида карточки» не существует.

### Остальные паттерны

| Паттерн | Состояние |
|---|---|
| **Таблицы** | Стилизуются глобально по тегу `table`/`th`/`td` (`table.css`). Реальных таблиц две: `gradebook.html`, `study_group_detail.html`. Обёртка `.table-wrap` (горизонтальный скролл) есть, но применена не везде. Сортировки, sticky-заголовка, зебры нет |
| **Модалки** | **Отсутствуют полностью.** Подтверждение удаления блока сделано через `onclick="return confirm(...)"` (`courses/edit.html`) — нативный браузерный диалог |
| **Табы** | **Отсутствуют.** Роль табов играет `<nav>` со ссылками и классом `.is-active` (`documentation-nav`, `management-sidebar`) |
| **Аккордеон** | Нативный `<details>/<summary>`: `.add-topic`, `.add-block`, `.edit-details`, `.block-edit-details`, `.nav-menu`, `.profile-menu`, `.mobile-nav-menu`. Работает, но у каждого свой стиль `summary` и своя иконка-маркер |
| **Прогресс-бары** | **Две независимые реализации.** `.mini-progress > i` (карточки курсов) и `.progress-track > .progress-value` (страница обучения). Обе через inline `style="width: N%"` |
| **Пагинация** | **Одна на весь проект** — `.pagination` в `components/enrollment_links.html` (ссылки на запись). Каталог курсов, «Мои курсы», уведомления, сообщения, журнал — **все без пагинации**, выводят весь queryset |
| **Тосты / флеш-сообщения** | `django.contrib.messages` рендерится в `base.html` как `<p class="alert" role="status">`. Один стиль на все уровни: `.alert` всегда синий/info. `messages.error()` визуально неотличим от `messages.success()` |
| **Бейджи** | `.nav-badge` (счётчик в навигации), `.status-pill` / `.status-pill.is-muted` (активна/отключена). Семантических вариантов success/warning/danger нет |
| **Аватар** | `.avatar` (буква), `.avatar-image` (файл), `.avatar-small`, `.nav-avatar` — 4 варианта, размеры заданы в разных местах |
| **Пустые состояния** | `.empty-state` — есть и сделан правильно (заголовок + пояснение + CTA), применён в 6 местах. Плюс `.empty-inline` и `.contacts-empty` — ещё два параллельных стиля для того же |
| **Скелетоны / loading** | **Отсутствуют полностью.** Ни одного класса, ни одного спиннера |
| **Иконки** | Inline-SVG прямо в `base.html` (сообщения, уведомления, солнце, луна) + текстовые псевдоиконки в разметке: `⌄`, `→`, `←`, `↗`, `✓`, `🔒`, `★`, `☆`, `⠿`, `▣`, `Г` |

### Что уже сделано хорошо (не ломать при редизайне)

- Токены в CSS-переменных существуют и **соблюдаются**: за пределами `tokens.css` во всём CSS ровно **один** захардкоженный цвет (`navigation.css:213: color: #fff`).
- Тёмная тема работает через `[data-theme]` с анти-FOUC инлайн-скриптом в `<head>` до загрузки CSS — это сделано правильно.
- `:focus-visible` объявлен для `input`, `button`, `a` (`forms.css`).
- `prefers-reduced-motion: reduce` учтён.
- `.table-wrap`, `aria-label` на всех иконочных ссылках, `aria-hidden` на декоративных SVG, `alt` есть у **всех** `<img>` без исключения.
- Мобильная навигация (гамбургер) уже реализована.

---

## 6. Что уже есть по интерактиву

| Технология | Статус |
|---|---|
| **htmx** | Установлен (`django-htmx` + CDN-скрипт), **использование нулевое** |
| **Alpine.js** | Нет |
| **Vue / React / острова** | Нет |
| **jQuery** | Нет |
| **Vanilla JS** | ~200 строк, 4 места |
| **WebSocket** | Есть, Channels + Daphne, `apps/messaging/consumers.py` |

Все четыре места с JS:

1. `static/js/theme_toggle.js` — переключатель темы. Аккуратный, defensive (`if (!toggle) return`), с обработкой недоступного localStorage.
2. `static/js/navigation/dropdown_hover.js` — открытие `<details>`-меню по наведению, только для `(hover: hover) and (pointer: fine)`. Аккуратный.
3. **`templates/courses/edit.html`** — 35 строк drag&drop-сортировки разделов и блоков **инлайном в шаблоне**, внутри `{% block content %}`. Работает через нативный HTML5 DnD → `form.requestSubmit()` → полная перезагрузка страницы. **Клавиатурой недоступно вообще** — переупорядочить программу курса без мыши невозможно.
4. **`templates/courses/quiz_create.html`** — 40 строк логики редактора вопросов по изображению, тоже инлайном в шаблоне.
5. **`templates/messaging/realtime_chat.html`** — WebSocket-клиент, вставлен как `<script>` через `{% include %}` и содержит `"{{ user.id }}"` — **Django-переменную внутри JS-строки**. Такой файл нельзя ни вынести в статику, ни закешировать, ни минифицировать.

Итог по интерактиву: заявленный в ADR-003 путь «Django Templates + HTMX» **на практике не реализован**. htmx оплачивается (вес + CDN), но не используется; там, где нужна была динамика, написан ручной JS прямо в шаблонах.

---

## 7. Боли UX, видимые в разметке

Отсортировано по тяжести.

### 7.1. Ошибка записи на курс возвращает голый абзац вместо страницы

`courses/views.py:108,123,134` → `render(request, "components/alert.html", ..., status=400)`. Шаблон — `<p class="alert error">{{ message }}</p>`, **без `{% extends 'base.html' %}`**. Пользователь, у которого истекла ссылка-приглашение или который уже записан, получает белую страницу с одной строкой текста: ни шапки, ни навигации, ни ссылки «назад», ни даже применённых стилей (CSS не подключается — нет `<head>`). Выхода со страницы, кроме кнопки «назад» в браузере, нет.

### 7.2. Стили страницы прохождения теста не загружаются

`components/question-image.css` (71 строка: `.question-image-answer`, `.image-answer-marker`, `.question-image-editor`, `.image-marker`) подключён **только в `app.css`**, а `base.html` подключает файлы по отдельности и этот пропускает. `app.css` при этом не подключён нигде. Значит, на `take_quiz.html` и `quiz_create.html` маркеры на изображении рендерятся **без позиционирования** — инлайновые `left/top` в процентах применяются к элементу, у которого нет `position: absolute`.

Дополнительно: `.visually-hidden` объявлен **только** в этом же неподключённом файле (`question-image.css:62`), а используется в `take_quiz.html` (`<span class="visually-hidden">Область N</span>`). То есть текст, предназначенный только для скринридера, показывается на экране обычным текстом.

### 7.3. Все уведомления, ошибки и успехи выглядят одинаково

`base.html` рендерит `{% for message in messages %}<p class="alert" role="status">`, игнорируя `message.tags`. `.alert` в `feedback.css` — всегда синяя info-плашка. `messages.error("Пароли не совпадают")` и `messages.success("Курс создан")` неотличимы. Токены `--color-success` / `--color-warning` / `--color-danger` существуют, но для уведомлений не используются. Плюс `role="status"` — неверная роль для ошибки, скринридер не объявит её ассертивно.

### 7.4. Ошибки полей форм не показываются вообще

Ни `.errorlist`, ни `.field-error` в CSS нет. `{{ form.as_p }}` выведет `<ul class="errorlist">` неоформленным списком, а ~25 ручных форм не выводят ошибки в принципе — только `messages.error` наверху страницы. На форме создания пользователя в панели управления (9 полей) при ошибке валидации пользователь не узнает, какое поле неверно.

### 7.5. Нет ни одного состояния загрузки

Ни скелетонов, ни спиннеров, ни `disabled` на сабмите. При этом в приложении есть заведомо долгие операции: импорт студентов из Excel (`import-students`), загрузка обложки курса с пересжатием, загрузка файла-материала. Пользователь жмёт «Импортировать» и не получает никакой обратной связи — типовой сценарий двойной отправки. Атрибут `data-submit-once` в `course_chat.html` присутствует в разметке, но **обработчика для него нет ни в одном JS-файле** — то есть защита от двойной отправки задумывалась и не была дописана.

### 7.6. Списки без пагинации

Каталог курсов (`runs` — все активные потоки), «Мои курсы», уведомления (`request.user.notifications.all()`), журнал оценок, тред сообщений, список контактов, все `<select>` в панели управления (`students`, `teachers`, `course_runs`) выводятся целиком. На демо-данных незаметно, на реальном колледже с 500+ студентами `<select name="user_id">` в форме «Записать на поток» превратится в список из 500 `<option>` без поиска.

### 7.7. Конструктор курса недоступен с клавиатуры

Переупорядочивание тем и блоков — только нативный HTML5 drag&drop с `draggable="true"` и `pointerdown` по ручке `⠿`. Ни `role="listbox"`, ни обработки стрелок, ни кнопок «вверх/вниз» как fallback. Для преподавателя, работающего с клавиатуры, программа курса неперестраиваема. Ручка `⠿` — это текстовый символ, а не кнопка; в таб-порядок она не попадает.

### 7.8. `<summary>`-меню открываются по наведению без клавиатурного эквивалента

`dropdown_hover.js` открывает `.nav-menu` / `.profile-menu` по `mouseenter`. Клик работает (нативный `<details>`), но при табуляции меню не раскрывается до нажатия Enter, а закрытие по Escape не реализовано. Фокус-ловушка внутри открытой панели отсутствует.

### 7.9. Заголовочная иерархия сломана на большинстве страниц

- `dashboard.html`: `<h1>Добро пожаловать</h1>`, дальше `<h2>Продолжить обучение</h2>`, но **внутри карточки курса — `<h3>`**, а в `my_courses.html` та же самая карточка использует `<h2>`. Один компонент, разные уровни заголовка.
- `empty-state` содержит `<h2>` — и вставляется как внутрь `<section>` с `<h1>`, так и внутрь `<div class="group-directory">` на третьем уровне вложенности.
- `courses/catalog.html`: `<h1>Каталог курсов</h1>`, затем `<h2>Черновики курсов</h2>`, и **каждая карточка курса — тоже `<h2>`**. На странице с 20 курсами — 21 заголовок второго уровня подряд.
- `grading/gradebook.html` и `notifications/detail.html` — `<h1>` без всякой обвязки, без `.page-header`, без хлебных крошек.

### 7.10. Пять разных «шапок страницы»

`.page-header`, `.catalog-heading`, `.builder-header`, `.management-header`, `.group-detail-header`, `.section-heading`, `.form-card-heading` — семь классов для одной и той же сущности «заголовок + подзаголовок + опциональное действие справа». Отступы у всех разные.

### 7.11. Отступы не образуют шкалу

В токенах **нет ни одной переменной для spacing**. По CSS россыпью: `margin: 16px`, `padding: 24px`, `padding: 26px`, `padding: 22px`, `padding: 13px 16px`, `padding: 9px 15px`, `padding: 10px 12px`, `gap: 12px`, `margin: 20px 0`, `margin: 8px 0`. 4/8pt-сетки нет — есть 5, 7, 9, 13, 22, 26.

### 7.12. Типографика без шкалы

В токенах нет ни одной переменной для размера шрифта. По CSS: `font-size: 15px` (body), `13px`, `12px`, `14px` — заданы поштучно в разных файлах. `--content-width: 1180px` — единственная размерная переменная во всём проекте.

### 7.13. Мобильная версия держится на заплатках

`body { overflow-x: hidden }` прячет горизонтальное переполнение вместо того, чтобы его устранить; `overflow-wrap: anywhere` на всех текстовых тегах ломает переносы в нормальном тексте, чтобы не ломались длинные URL в одном месте (`.link-row a`); `.card { overflow: hidden }` обрежет любой будущий тултип или дропдаун внутри карточки. На 360px `.contacts-card` получает `max-height: 220px` со своим скроллом — это отдельный скроллящийся контейнер внутри скроллящейся страницы.

### 7.14. Панель управления — «форма из форм»

`admin_dashboard.html` — одна страница на 10 КБ, где 7 независимых `<form>` с разными `action` и разной раскладкой (`.inline-form`, `.management-form`, `.management-user-form`, `.management-link-form` — четыре класса формы, отличающиеся только сеткой). Плюс якорная навигация `#groups / #people / #courses / #links` вместо табов. Разделение на шаги («1. Группы → 2. Пользователи → 3. Потоки → 4. Ссылки») есть в тексте, но не поддержано интерфейсом — все четыре секции всегда видны одновременно.

### 7.15. Прочее

- Ссылки навигации в `base.html` захардкожены строками (`href="/courses/mine/"`, `/courses/catalog/`, `/notifications/`) вместо `{% url %}`, хотя рядом в том же файле `{% url %}` используется. При изменении URL-схемы половина шапки молча сломается.
- `{{ form.attachment }}` спрятан внутрь `<label class="attachment-button">` — нативный `input[type=file]` перекрыт стилями; состояние «файл выбран» пользователю не показывается никак.
- `role="status"` — единственная ARIA-роль на весь проект. Ни `aria-current` на активном пункте навигации, ни `aria-expanded` на `<summary>`, ни `aria-live` для приходящих по WebSocket сообщений (новое сообщение в чате для скринридера не объявляется).
- В `learning/course.html` состояние «заблокировано» передаётся эмодзи `🔒` в тексте — без `aria-label`, скринридер прочитает «замок» либо промолчит.
- Нет `<footer>`, нет `skip to content`, нет `<breadcrumbs>` — при том что глубина навигации доходит до 4 уровней (Управление → Группа → Поток → Ссылка).

---

## Сводка: 10 приоритетов на редизайн

| # | Проблема | Тип |
|---|---|---|
| 1 | `components/alert.html` как полноценный ответ 400 → голая страница | **баг** |
| 2 | `question-image.css` не подключён → сломана вёрстка тестов с изображением | **баг** |
| 3 | Все `messages` рендерятся одним синим стилем, `error` = `success` | **баг** |
| 4 | Ошибки полей форм не отображаются нигде | UX |
| 5 | Нет ни одного loading-состояния при заведомо долгих операциях | UX |
| 6 | htmx грузится на каждой странице и не используется | вес/долг |
| 7 | 750 строк «layout-fixes» с 9 `!important` поверх основного CSS | долг |
| 8 | Нет токенов spacing и типографики; 11 ad-hoc брейкпоинтов; 1280/1920 не обслуживаются | система |
| 9 | 6 вариантов кнопок (primary — селектор по тегу) и 8+ вариантов карточек | система |
| 10 | Конструктор курса и меню недоступны с клавиатуры | a11y |

---

## Вопросы, которые нужно решить до Этапа 1

Аудит их не решает — они меняют состав работ:

1. **Ширина 1920.** Сейчас всё упирается в 1180px. Расширять контент на больших экранах (для журнала и панели управления — да), или оставить центрированную колонку?
2. **i18n.** `USE_I18N = True`, но `{% trans %}` нет ни одного. Оборачивать строки в `{% trans %}` по ходу редизайна (это большой объём и много diff-шума), или сохранить как есть? Правило №6 брифа предполагает наличие переводов — их нет.
3. **Django Admin.** `ADMIN_URL` в проде выключен по умолчанию. Если админкой реально не пользуются, тему (django-unfold/jazzmin) в скоуп брать не стоит.
4. **`/styleguide/`** из Этапа 2 требует новый URL и новый view. Бриф запрещает менять URL-схему без согласования — это как раз тот случай.
5. **Реальные объёмы данных.** Сколько студентов/курсов в самой крупной организации? От этого зависит, нужна ли пагинация и поиск в `<select>` панели управления (п. 7.6), или это преждевременно.

---

**Следующий шаг:** жду подтверждения отчёта перед переходом к Этапу 1 (исследование референсов).
