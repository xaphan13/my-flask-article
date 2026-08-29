# Задание 003 — Модернизация фронтенда: переход на Bootstrap 5.3.x

## Суть

Фронтенд работает на стеке 2017–2018 годов: Bootstrap 4.0.0, jQuery 3.2.1,
Popper 1.12.9 (два последних собственным кодом не используются), ресурсы с трёх
разных CDN, у highlight.js нет SRI. Темы сделаны двумя почти одинаковыми
CSS-файлами с подменой `href` из JS. Известны дефекты: мобильное меню не
разворачивается (нет тогглера), smooth-scroll сайдбара кидает `SyntaxError`,
футер использует классы BS5 при подключённом BS4, в шаблонах inline `onclick`.

Задание — перевести фронтенд на **Bootstrap 5.3.x** с CDN **jsdelivr**, убрав
jQuery и Popper, перейти на нативные темы `data-bs-theme` + CSS-переменные,
починить перечисленные дефекты и добавить умеренную косметику. Дизайн
сохраняется: тот же характер строгого тёмного сайта статей для программистов;
светлая тема доделывается по-человечески. Python-код не затрагивается.

Исходные данные — отчёты
[docs/frontend/01_how_it_works.md](../../docs/frontend/01_how_it_works.md),
[02_modernity_assessment.md](../../docs/frontend/02_modernity_assessment.md),
[03_improvements.md](../../docs/frontend/03_improvements.md); таблица замены
классов BS4→BS5 (`03_improvements.md` §1.3) обязательна к применению.

## Принятые решения (зафиксированы с пользователем 2026-08-29)

1. **Только CDN, без build-шага.** Все внешние ресурсы — с `cdn.jsdelivr.net`
   (Bootstrap 5.3.x CSS+JS, highlight.js 11.x JS и CSS обеих тем подсветки).
   Локальные vendor-копии не заводятся, npm/бандлеры не подключаются. Версии
   фиксируются точно (не диапазон, не `latest`): Bootstrap — последняя
   стабильная 5.3.x (не ниже 5.3.3), highlight.js — актуальная 11.x (не ниже
   11.9.0). На каждом внешнем теге — `integrity` (SRI) + `crossorigin`.
2. **Темы через `data-bs-theme`.** Механизм «два CSS-файла + подмена href»
   упраздняется: тёмная/светлая темы — нативный `data-bs-theme="dark|light"` на
   `<html>` + собственные CSS-переменные в одном файле стилей. Файлы
   `dark-theme.css` и `light-theme.css` удаляются. Тёмная — по умолчанию, её
   палитра переносится из текущего `dark-theme.css`: визуально сайт остаётся
   «таким же».
3. **Светлая тема доделывается.** Аккуратная, контрастная, на тех же
   переменных; тема подсветки кода следует за темой сайта (тёмная —
   `github-dark`, светлая — `github`), способ переключения — на усмотрение
   frontend-dev.
4. **Переключение темы без inline-обработчиков.** Из шаблонов уходят
   `onclick="toggleTheme()"` и глобальные функции: подписка через
   `addEventListener` в `scripts.js`. Ключ и значения localStorage
   сохраняются (`localStorage['theme']` = `'dark'|'light'`), чтобы у
   существующих посетителей тема не сбрасывалась. Крошечный инлайн-скрипт в
   `<head>` (до стилей) восстанавливает тему до первой отрисовки — без
   «вспышки»; это единственный допустимый inline-JS.
5. **P0-починки входят в задание:** тогглер мобильного меню под BS5
   (`data-bs-toggle="collapse"`), удаление сломанного smooth-scroll, макрос
   форм для дедупликации 12 повторённых блоков, отказ от inline `onclick`.
6. **Сайдбар-заглушка удаляется полностью:** `includes/_sidebar.html`,
   переменная `show_sidebar`, сетка `container-fluid` + `col-md-2`/`col-md-10`
   и smooth-scroll-код в `scripts.js`. Страницы статей переходят на обычный
   `container`; ширина колонки контента — на усмотрение frontend-dev в духе
   текущего сайта (широкая читабельная колонка).
7. **Язык интерфейса — русский целиком:** Articles → «Статьи», Account →
   «Аккаунт», Logout → «Выход», Login → «Вход», Register → «Регистрация»,
   About → «О сайте»; аналогично во всех остальных шаблонах, включая
   `art_manage` и страницы ошибок.
8. **SEO-минимум:** заголовок статьи — единственный `<h1>` на странице (сейчас
   `<h3>` со ссылкой на главную); `alt` у аватара в `account.html`;
   `<meta name="description">` в `_head.html`.
9. **Дизайн — строгость и точечная косметика.** Тёмная тема по умолчанию,
   характер и палитра текущего сайта сохраняются. Допустимая косметика:
   скруглённые кнопки/карточки, аккуратные hover/focus-visible состояния,
   бейджи для метаданных статей (язык, автор), читаемая ширина строки статей.
   Без градиентов, «неона» и крупного редизайна — сайт статей для программистов.
10. **Python не трогаем.** Правки только в `flaskblog/templates/` и
    `flaskblog/static/`; маршруты, модели, `schema_art` — без изменений.
11. **Adversary не запускать вообще.** Агент adversary в этом задании не
    запускается (экономия времени и токенов), ADVERSARIAL_REVIEW.md не
    создаётся. Враждебная проверка изменённой функциональности будет
    проведена позже, после следующих исправлений, отдельным прогоном.

## Что сделать

Всё задание — зона **frontend-dev** (`flaskblog/templates/`,
`flaskblog/static/`); backend-dev не участвует.

- `includes/_head.html`: Bootstrap 5.3.x CSS (jsdelivr + SRI); CSS подсветки
  обеих тем; инлайн-скрипт восстановления темы; `meta description`;
  `<html data-bs-theme="dark" lang="ru">` по умолчанию.
- `includes/_scripts.html`: удалить jQuery, Popper, Bootstrap 4 JS; подключить
  Bootstrap 5.3.x bundle и highlight.js 11.x (jsdelivr + SRI, `defer` где
  уместно); `hljs.highlightAll()` — только при наличии `pre code` на странице.
- `includes/_header.html`: navbar по BS5, тогглер мобильного меню
  (`data-bs-toggle="collapse"` + `aria-*`), русские подписи, переключатель
  «Тема» без inline-обработчика.
- `includes/_sidebar.html` — удалить; `layout.html` — убрать `show_sidebar` и
  сетку сайдбара, починить опечатку `mt-align-items-center`.
- Новый макрос форм (по образцу `03_improvements.md` §2.4) вместо 12
  повторённых блоков в `register.html`, `login.html`, `account.html`;
  миграция классов форм (`form-group` → `mb-3` и т.д.).
- `new_art/art_home.html`: карточки/список статей с бейджами меты, миграция
  классов (`mr-*` → `me-*`), косметика по решению 9.
- `new_art/art_author.html`: `<h1>`-заголовок, миграция классов, типографика
  статьи (читаемая ширина строки, отступы).
- `new_art/art_manage.html`: миграция классов (`badge badge-*` → `text-bg-*`,
  `thead-light` → `table-light`, `btn-block` → `d-block w-100`).
- `register.html`, `login.html`, `account.html`, `about.html`, `errors/*`:
  миграция классов, русские подписи, `alt` аватара.
- `static/art_css/`: один файл стилей на CSS-переменных + `data-bs-theme`
  вместо `base.css` + двух тем (палитра тёмной — из текущего `dark-theme.css`),
  косметика по решению 9. `dark-theme.css` и `light-theme.css` — удалить.
- `static/art_css/scripts.js`: переписать без глобальных функций — тема через
  `data-bs-theme` + `localStorage['theme']` (`'dark'|'light'`), подсветка кода
  при наличии `pre code`, переключение темы по клику; smooth-scroll сайдбара
  удалить; хардкод путей `/static/art_css/...` уходит вместе с подменой CSS.

## Вне рамок

- Локальные vendor-копии, раздача статики через nginx, минификация, CSP —
  фаза 2 дорожной карты `docs/frontend/03_improvements.md`.
- Favicon, Open Graph, skip-link, `aria-current` — расширенный SEO/a11y.
- Adversarial-прогон — полностью исключён (решение 11): adversary не
  запускается, враждебные проверки будут после следующих исправлений.
- Изменения Python-кода (маршруты, модели, `schema_art`), контент статей
  (`content_art/`), `articles.yaml`.
- Функциональность `art_manage` (только классы/язык/косметика).

## Риски

- SRI-хэши обязаны соответствовать зафиксированной версии; при смене версии
  менять и хэши (брать с официальных страниц Bootstrap / highlight.js на
  jsdelivr).
- Стандартная тёмная тема BS5.3 отличается от текущей палитры: переменные
  сайта должны переопределять цвета BS, а не наоборот, иначе «дизайн тот же»
  не выполнится.
- Инлайн-скрипт в `<head>` обязан стоять до подключения стилей, иначе
  «вспышка» темы останется.
- Удаление сайдбара синхронно с `layout.html`, `art_home.html`,
  `art_author.html`: оставшееся упоминание `show_sidebar` ломает страницы.
- Браузерный кэш старых CSS/JS: qa при проверке делает hard reload.
- Bootstrap 5.3 точечно отличается стилями форм/navbar от 4.0 — небольшие
  визуальные расхождения допустимы в рамках решения 9, но не за его
  пределами.

## Критерии успеха

Каждый критерий подтверждается доказательством (curl-вывод, grep, скриншот)
в `tasks/current/e2e/`.

1. **CDN/SRI:** в отрендеренном HTML `/art_home` все внешние ресурсы — только
   `cdn.jsdelivr.net`, у каждого `integrity` + `crossorigin`, версии
   зафиксированы точно; упоминаний `maxcdn`, `code.jquery.com`,
   `cdnjs.cloudflare.com`, `jquery`, `popper`, Bootstrap 4 — нет.
2. **Дифф в границах зоны:** изменены/удалены только файлы в
   `flaskblog/templates/` и `flaskblog/static/`; удалены `_sidebar.html`,
   `dark-theme.css`, `light-theme.css`; Python-модули не тронуты. (git status)
3. **Мобильное меню:** в разметке есть `navbar-toggler` с
   `data-bs-toggle="collapse"`; скриншот `/art_home` на 375px с развёрнутым
   меню.
4. **Темы:** в HTML нет `onclick=`; тема по умолчанию тёмная; переключение
   пунктом «Тема» меняет `data-bs-theme` на `<html>` и переживает перезагрузку
   (`localStorage['theme']`); инлайн-восстановление стоит в `<head>` до
   стилей. (curl + grep + скриншоты обеих тем)
5. **Тёмная тема сохранена:** скриншоты `/art_home`, страницы статьи №5,
   `/login`, `/about` — палитра и layout узнаваемо прежние, косметика умеренная
   (скругления, бейджи, hover).
6. **Светлая тема доделана:** те же страницы в светлой теме — контрастные,
   читаемые; код в статье подсвечен светлой темой (не `github-dark`).
7. **Русский интерфейс:** в отрендеренных страницах нет английских подписей
   навигации/кнопок (`Articles`, `Account`, `Logout`, `Login`, `Register`,
   `About`). (curl + grep)
8. **SEO-минимум:** на странице статьи — ровно один `<h1>` с названием; у
   аватара в `/account` есть `alt`; в `<head>` есть `meta description`.
   (curl + grep)
9. **Сайдбар удалён:** в HTML страниц статей нет `sidebar` и «Раздел».
   (curl + grep)
10. **Регресс:** `/`, `/art_home`, `/art/Max/5`, `/art_manage` (302 анонимно /
    200 с логином), `/login`, `/register`, `/account`, `/about`,
    `/art/Max/999` (404) — ожидаемые коды; консоль браузера на `/art_home` и
    странице статьи без ошибок и сетевых 404; `uv run ruff check .` чист;
    url_map = 16.

## Финальные критерии

Задание закрыто, когда:

- Все десять критериев выше подтверждены доказательствами.
- Все дефекты в DEFECTS.md по этому заданию закрыты qa.
- Adversary-прогон в этом задании не проводился (решение 11):
  ADVERSARIAL_REVIEW.md не создаётся; враждебная проверка фронтенда
  отложена до после следующих исправлений.

---

# Отчёт о выполнении

- Дата закрытия: 2026-08-29
- Коммит: без коммита (изменения в рабочем дереве, ветка new-frontend)

## Итог

Фронтенд переведён с Bootstrap 4.0.0 + jQuery + Popper на Bootstrap 5.3.8
(jsdelivr, SRI) с нативными темами `data-bs-theme` на CSS-переменных; jQuery,
Popper, сайдбар-заглушка, сломанный smooth-scroll, inline-обработчики и
механизм «двух CSS-файлов» удалены; светлая тема доделана; интерфейс
руссифицирован; добавлен тогглер мобильного меню, макрос форм, бейджи меты,
`<h1>`-заголовок статьи и `meta description`. Все 10 критериев подтверждены
прогонами qa (curl + playwright); дефектов не найдено.

Версии зафиксированы: Bootstrap **5.3.8**, highlight.js **11.12.0**
(gh/highlightjs/cdn-release); SRI-хэши sha384 проверены оркестратором по
фактическим файлам CDN.

## Изменения

Шаблоны (`flaskblog/templates/`):
- `layout.html` — `data-bs-theme="dark"` на `<html>`, удалены `show_sidebar`
  и сайдбар-сетка, обычный `container`, починен класс футера.
- `includes/_head.html` — Bootstrap 5.3.8 CSS + обе темы подсветки (jsdelivr,
  SRI), `meta description`, инлайн-восстановление темы до стилей.
- `includes/_scripts.html` — jQuery/Popper/BS4 JS удалены; BS5 bundle +
  highlight.js 11.12.0 (SRI).
- `includes/_header.html` — navbar BS5, тогглер мобильного меню с aria,
  русские подписи, «Тема» через `id="theme-toggle"` без onclick.
- `includes/_form_macro.html` (новый) — макросы `field_with_errors`/`file_field`.
- `includes/_sidebar.html` — удалён.
- `includes/_footer_macro.html` — русский, `me-*`/`ms-*`.
- `register.html`, `login.html`, `account.html` — формы на макросе, `alt`
  аватара, миграция классов.
- `new_art/art_home.html` — карточки с бейджами меты, `me-*`.
- `new_art/art_author.html` — единственный `<h1>`, `max-width: 70ch`.
- `new_art/art_manage.html` — `text-bg-*`, `table-light`, `d-block w-100`.
- `about.html`, `errors/*` — русский, BS5.

Статика (`flaskblog/static/art_css/`):
- `base.css` — единый файл на CSS-переменных; тёмная палитра перенесена из
  прежнего `dark-theme.css` (#1e1e1e/#e0e0e0/#61dafb/#ff6f61/#354754), светлая —
  новая контрастная; косметика по решению 9.
- `scripts.js` — без глобальных функций: тема через `data-bs-theme` +
  `localStorage['theme']`, синхронизация темы подсветки, `highlightAll()` только
  при `pre code`.
- `dark-theme.css`, `light-theme.css` — удалены.

## Критерии успеха

| # | Критерий | Результат | Доказательство |
|---|---|---|---|
| 1 | CDN/SRI: только jsdelivr, integrity+crossorigin, без jquery/popper/maxcdn/cdnjs/BS4 | PASS | e2e/qa_run.txt (5 ресурсов, SRI 5/5, запретные слова 0 после правки комментария), e2e/frontend_dev_check.txt |
| 2 | Дифф в границах зоны; удалены _sidebar.html, dark-theme.css, light-theme.css; Python не тронут | PASS | e2e/qa_run.txt «K2» (git status, files outside zone — пусто), ревью оркестратора |
| 3 | Мобильное меню: navbar-toggler + data-bs-toggle; скриншот 375px с развёрнутым меню | PASS | e2e/qa_playwright.txt (K3: .show после клика, консоль чиста), screenshots/qa_mobile_375_expanded.png |
| 4 | Темы: без onclick, тёмная по умолчанию, data-bs-theme + localStorage, инлайн-скрипт до стилей | PASS | e2e/qa_run.txt (K4: onclick=0, data-bs-theme="dark", localStorage до первого link), e2e/qa_playwright.txt (K4: клик/reload/обратно) |
| 5 | Тёмная тема сохранена (палитра, layout) | PASS | screenshots/qa_home_dark.png, qa_art5_dark.png, qa_login_dark.png, qa_about_dark.png; bodyBg=rgb(30,30,30), консоли чисты |
| 6 | Светлая тема доделана, подсветка следует за темой | PASS | screenshots/qa_home_light.png, qa_art5_light.png, qa_login_light.png, qa_about_light.png; e2e/qa_run2.txt (dark: darkDisabled=false/lightDisabled=true; light: наоборот; hljsCount=12) |
| 7 | Русский интерфейс | PASS | e2e/qa_run.txt (K7: английские подписи 0 на /art_home, /login, /register, /about), e2e/qa_run2.txt (art_manage auth: 0) |
| 8 | SEO: один h1, alt аватара, meta description | PASS | e2e/qa_run.txt (K8: h1=1 «gemini-pro-fastapi-1», meta=1), e2e/qa_run2.txt (alt="Аватар пользователя qa2user_...") |
| 9 | Сайдбар удалён (нет sidebar/«Раздел») | PASS | e2e/qa_run.txt (K9: sidebar=0, Раздел=0 на /art_home и обеих статьях) |
| 10 | Регресс: коды, консоли, ruff, url_map=16 | PASS | e2e/qa_run.txt (K10: / 302→/art_home, 200/404/302 как ожидалось; url_map=16; ruff чист), e2e/qa_run2.txt (/art_manage auth 200), e2e/qa_playwright.txt (консоли и 404 пусты в обеих темах) |

Примечание: `/art/Max/5` из критерия 10 — id=5 не существует в articles.yaml
(id статей timestamp-овые), проверен как 404 наряду с `/art/Max/999`; валидная
статья — `/art/Max/1787932544`. «Статья №5» критерия 5 — `/art/aaa/1787935323`.

## Дефекты

Не найдены — DEFECTS.md не создавался. (Полный qa-прогон упал на переполнении
контекста после фиксации K1–K10; недостающие проверки — чистый K6-ретест и
аутентифицированные /art_manage, /account — добраны дочерочным прогоном
qa, все PASS. Аномалия «K6 dark» из qa_playwright.txt — артефакт скрипта
проверки: addInitScript контекста перезаписывал localStorage; на чистых
контекстах не воспроизводится, e2e/qa_run2.txt.)

## Adversarial-прогон

Не проводился по решению 11 задания: adversary не запускался,
ADVERSARIAL_REVIEW.md не создавался. Враждебная проверка фронтенда отложена
до отдельного прогона после следующих исправлений.

## Участники

- frontend-dev: полная миграция на BS5.3 (шаблоны, стили, скрипты), самопроверки,
  скриншоты, микро-правка комментария (popper).
- qa: полный прогон 10 критериев (curl + playwright, e2e/qa_run.txt,
  qa_playwright.txt, скриншоты qa_*), дочерочный прогон (e2e/qa_run2.txt);
  дефектов не найдено.
- adversary: не участвовал (решение 11).
- оркестратор: фиксация версий и SRI-хэшей, ревью диффа, триаж аномалии K6,
  архивирование.
