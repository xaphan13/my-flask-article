# 01 — Как устроен фронтенд сейчас

> Описание фактического состояния (ветка `auto-md`, HEAD `0d258f5`). Фронтенд —
> это целиком серверный рендеринг: Jinja-шаблоны в `flaskblog/templates/` и статика
> в `flaskblog/static/`. Отдельного клиентского приложения (SPA) нет и не было.

## 1. Состав фронтенд-слоя

```
flaskblog/templates/                  flaskblog/static/
├── layout.html          (база)       ├── art_css/
├── includes/                          │   ├── base.css
│   ├── _head.html                     │   ├── dark-theme.css
│   ├── _header.html                   │   ├── light-theme.css
│   ├── _sidebar.html                  │   └── scripts.js
│   ├── _flash_msg.html                └── profile_pics/
│   ├── _scripts.html                      ├── default.jpg
│   └── _footer_macro.html                 └── 1b77d4b53e95b974.jpg
├── new_art/
│   ├── art_home.html
│   ├── art_author.html
│   └── art_manage.html
├── register.html, login.html,
│   account.html, about.html
├── errors/  (403.html, 404.html, 500.html)
└── content_art/  (5 файлов .md — тела статей)
```

Всего 17 HTML-шаблонов, 3 CSS-файла (свои) и 1 JS-файл (свой). Внешних JS/CSS —
пять ресурсов с CDN.

## 2. Библиотеки и внешние ресурсы

| Ресурс | Версия | Источник | Где подключён |
|---|---|---|---|
| Bootstrap CSS | 4.0.0 (2018) | `maxcdn.bootstrapcdn.com` | `includes/_head.html` |
| Bootstrap JS | 4.0.0 | `maxcdn.bootstrapcdn.com` | `includes/_scripts.html` |
| jQuery slim | 3.2.1 (2017) | `code.jquery.com` | `includes/_scripts.html` |
| Popper.js | 1.12.9 (2017) | `cdnjs.cloudflare.com` | `includes/_scripts.html` |
| highlight.js JS | 11.9.0 (2024) | `cdnjs.cloudflare.com` | `includes/_scripts.html` |
| highlight.js CSS (`github-dark`) | 11.9.0 | `cdnjs.cloudflare.com` | `includes/_head.html` |

Свои ресурсы: `base.css` (базовые стили), `dark-theme.css` / `light-theme.css`
(две темы), `scripts.js` (37 строк).

Из Python-зависимостей фронтенду косвенно служит `markdown==3.9`
(`render_article()` в `schema_art.py`): файлы статей `.md` рендерятся в HTML
расширениями `fenced_code` и `tables` на сервере, затем вставляются в шаблон.

## 3. Jinja-шаблоны

### 3.1 Иерархия наследования — единая

Все страницы наследуют `layout.html`:

```
layout.html
├── includes/_head.html      <head>: мета, Bootstrap CSS, highlight CSS, тема, <title>
├── includes/_header.html    фиксированная навбар-шапка (Bootstrap 4 navbar)
├── includes/_sidebar.html   боковое меню (подключается условно)
├── includes/_flash_msg.html flash-сообщения
├── блок {% block content %} — заполняют страницы
├── includes/_footer_macro.html  футер через макрос footer_new(current_user)
└── includes/_scripts.html   jQuery, Popper, Bootstrap JS, highlight.js, scripts.js
```

Ключевые механизмы Jinja, используемые в проекте:

- **Наследование**: `{% extends "layout.html" %}` + `{% block content %}`. Страницы
  статей (`new_art/art_home.html`, `new_art/art_author.html`) дополнительно делают
  `{% set show_sidebar = true %}`, и `layout.html` по этой переменной включает
  сайдбар и меняет сетку (`container-fluid` + `col-md-2`/`col-md-10` против
  `container` + `col-md-8`).
- **Партиалы**: `{% include 'includes/_head.html' %}` и т.п. — 6 include в layout.
- **Макрос**: `includes/_footer_macro.html` объявляет
  `{% macro footer_new(current_user) %}` и импортируется в layout через
  `{% from 'includes/_footer_macro.html' import footer_new %}`.
- **Условные и циклы**: `{% if current_user.is_authenticated %}` в шапке,
  `{% for art in title_list %}` в `art_home`, `{% for category, message in messages %}`
  во flash-партиале.
- **Фильтры**: `{{ art.content|safe }}` — единственное место с отключённым
  экранированием (статьи — доверенные файлы с диска).
- **`url_for`**: все ссылки, включая статику
  (`url_for('static', filename='art_css/base.css')`).

### 3.2 Рендер форм (WTForms -> Bootstrap 4)

Формы (`register.html`, `login.html`, `account.html`) рендерятся вручную: каждое
поле — `{{ form.field(class="form-control form-control-lg") }}`, ошибки валидации —
вручную через `{% if form.field.errors %}` + `is-invalid` + `invalid-feedback`.
Блок «поле + ошибки» (6 строк) продублирован в трёх шаблонах 12 раз дословно.

### 3.3 Рендер статей и подсветка кода

1. `art_author` в `routes_articles.py` вызывает `render_article(file_name, dir)`:
   `.md`/`.markdown` прогоняются через `markdown()` (расширения `fenced_code`,
   `tables`), `.html` вставляются как есть.
2. Результат кладётся в `art.content` и выводится `{{ art.content|safe }}`.
3. На клиенте `scripts.js` вызывает `hljs.highlightAll()` — подсвечивает все
   `<pre><code class="language-...">`, созданные из fenced-блоков Markdown.

Тема подсветки фиксированная (`github-dark`), не зависит от выбранной темы сайта.

### 3.4 Темы (светлая/тёмная)

- В `_head.html` подключается `dark-theme.css` с `id="theme-link"` (тёмная — по
  умолчанию); `light-theme.css` в HTML не подключён, загружается только через JS.
- `scripts.js`: `toggleTheme()` переключает `href` между
  `/static/art_css/light-theme.css` и `dark-theme.css`, пишет выбор в
  `localStorage['theme']`; при загрузке страницы тема восстанавливается.
- Переключатель — пункт «Тема» в шапке с inline-обработчиком
  `onclick="toggleTheme()"`.
- `base.css` содержит общие стили (типографика, сайдбар, подсветка), темы
  переопределяют цвета. Типографика — системные шрифты (`Segoe UI`, `Courier New`),
  внешние шрифты не грузятся.

## 4. JavaScript — весь клиентский код

Весь свой JS — `static/art_css/scripts.js` (37 строк), без модулей и зависимостей:

| Строки | Что делает | Оценка |
|---|---|---|
| 2 | `hljs.highlightAll()` на каждом запросе | работает, но грузит полный бандл всех языков |
| 4-15 | `toggleTheme()` — смена темы + localStorage | рабочая логика, но глобальная функция + inline onclick |
| 18-26 | IIFE восстановления темы | работает, но выполняется в конце body — возможна вспышка неверной темы |
| 29-37 | smooth-scroll пунктов сайдбара | **сломано**: `document.querySelector(this.getAttribute('href'))` с `href="#"` бросает `SyntaxError: '#' is not a valid selector` |

Внешние библиотеки: jQuery (требуется Bootstrap 4 JS), Popper (требуется
Bootstrap 4 JS для выпадающих списков), Bootstrap JS (для collapse/dropdown —
но кнопки-тогглера в шапке нет, см. ниже), highlight.js.

В собственном коде jQuery не используется ни разу — `$` не встречается в
`scripts.js` и в шаблонах нет JS-кода с jQuery.

## 5. Что рендерится на каждой странице

| Страница | Шаблон | Особенности |
|---|---|---|
| `/` → `/art_home` | `art_home.html` | список статей: `art_id`, автор, язык, ссылка на статью |
| `/art/<author>/<art_id>` | `art_author.html` | заголовок (h3 со ссылкой на home), мета, `{{ art.content|safe }}` |
| `/art_manage` | `art_manage.html` | таблица статей + формы обновления метаданных (POST) |
| `/register`, `/login` | `register.html`, `login.html` | WTForms-формы с ручным рендером ошибок |
| `/account` | `account.html` | аватар + форма профиля с загрузкой файла |
| `/about`, ошибки | `about.html`, `errors/*.html` | заглушки |

Страницы статей (включая главную) показывают flash-сообщения: они наследуют
`layout.html`, который включает `_flash_msg.html`.

## 6. Сводка: как всё связано

```
браузер
  │  GET /art/<author>/<art_id>
  ▼
Flask → routes_articles.art_author
  │    → render_article(): markdown(.md) → HTML
  ▼
Jinja: layout.html ← art_author.html  ({{ art.content|safe }})
  │
  ├── CDN: Bootstrap 4.0.0 CSS+JS, jQuery, Popper, highlight.js
  └── свои: base.css + dark/light-theme.css + scripts.js
        ├── hljs.highlightAll()   — подсветка кода в статьях
        ├── toggleTheme()         — переключение темы (localStorage)
        └── сайдбар smooth-scroll — сломано на href="#"
```

Серверная часть не делает ничего для фронтенда, кроме рендера шаблонов и раздачи
статики через встроенный `static`-эндпоинт Flask; nginx в Docker проксирует и
`/static/*` в приложение (кэширования на уровне nginx нет).
