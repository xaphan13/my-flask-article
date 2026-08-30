# 01 — Как устроен фронтенд сейчас

> Описание фактического состояния (ветка `new-frontend`, HEAD `b12f62c`, 2026-08-31,
> после заданий 003 и 004). Фронтенд — это целиком серверный рендеринг: Jinja-шаблоны
> в `flaskblog/templates/` и статика в `flaskblog/static/`. Отдельного клиентского
> приложения (SPA) нет и не было.

## 1. Состав фронтенд-слоя

```
flaskblog/templates/                  flaskblog/static/
├── layout.html          (база)       ├── art_css/
├── includes/                          │   ├── base.css      (единый, CSS-переменные)
│   ├── _head.html                     │   └── scripts.js    (173 строки, IIFE)
│   ├── _header.html                   └── profile_pics/
│   ├── _sidebar.html  (заглушка)          ├── default.jpg
│   ├── _flash_msg.html                    └── 1b77d4b53e95b974.jpg
│   ├── _scripts.html
│   ├── _form_macro.html   (макросы форм)
│   ├── _hljs_theme_select.html (селектор тем hljs)
│   └── _footer_macro.html
├── new_art/
│   ├── art_home.html
│   ├── art_author.html
│   └── art_manage.html
├── register.html, login.html,
│   account.html, about.html
├── errors/  (403.html, 404.html, 500.html)
└── content_art/  (5 файлов .md — тела статей)
```

Всего 19 HTML-шаблонов, 1 CSS-файл (свой, 326 строк) и 1 JS-файл (свой, 173 строки).
Внешних ресурсов — 19, все с одного CDN (`cdn.jsdelivr.net`), у каждого SRI +
`crossorigin` (см. §2).

## 2. Библиотеки и внешние ресурсы

| Ресурс | Версия | Источник | Где подключён |
|---|---|---|---|
| Bootstrap CSS | 5.3.8 (2025) | `cdn.jsdelivr.net` + SRI | `includes/_head.html` |
| Bootstrap JS (bundle) | 5.3.8 | `cdn.jsdelivr.net` + SRI | `includes/_scripts.html` |
| highlight.js JS | 11.12.0 | `cdn.jsdelivr.net/gh/highlightjs/cdn-release` + SRI | `includes/_scripts.html` |
| highlight.js CSS — 15 тёмных тем | 11.12.0 | там же + SRI | `includes/_head.html`, активна `vs2015`, остальные `disabled` |
| highlight.js CSS — светлая тема `vs` | 11.12.0 | там же + SRI | `includes/_head.html`, всегда `disabled` |

jQuery и Popper удалены (Bootstrap 5 они не нужны). Все внешние ресурсы идут с
одного домена `cdn.jsdelivr.net`; упоминаний `maxcdn`, `code.jquery.com`,
`cdnjs.cloudflare.com` в шаблонах нет.

Свои ресурсы: `base.css` — единственная таблица стилей на CSS-переменных для обеих
тем, `scripts.js` — весь клиентский код.

Из Python-зависимостей фронтенду косвенно служит `markdown==3.9`
(`render_article()` в `schema_art.py`): файлы статей `.md` рендерятся в HTML
расширениями `fenced_code` и `tables` на сервере, затем вставляются в шаблон.

## 3. Jinja-шаблоны

### 3.1 Иерархия наследования — единая

Все страницы наследуют `layout.html`:

```
layout.html                  <html lang="ru" data-bs-theme="dark">
├── includes/_head.html      <head>: мета, meta description, инлайн-восстановление
│                            темы, Bootstrap 5 CSS, 16 таблиц hljs, base.css, <title>
├── includes/_header.html    фиксированная navbar-шапка (BS5) с тогглером
│                            мобильного меню; внутри — _hljs_theme_select.html
├── includes/_sidebar.html   левая колонка-заглушка (см. §3.2)
├── includes/_flash_msg.html flash-сообщения — видны на ВСЕХ страницах
├── блок {% block content %} — заполняют страницы
├── includes/_footer_macro.html  футер через макрос footer_new(current_user)
└── includes/_scripts.html   Bootstrap 5 bundle, highlight.js, scripts.js
```

Ключевые механизмы Jinja, используемые в проекте:

- **Наследование**: `{% extends "layout.html" %}` + `{% block content %}` — у всех
  девяти страниц. Отдельной базы для статей больше нет.
- **Партиалы**: 6 include в `layout.html` плюс include селектора тем hljs внутри
  `_header.html` (в обеих ветках `if current_user.is_authenticated`).
- **Макросы**: `includes/_footer_macro.html` (`footer_new(current_user)`) и
  `includes/_form_macro.html` (`field_with_errors(field, size)`,
  `file_field(field)`) — импортируются в шаблоны через `{% from ... import %}`.
- **Условные и циклы**: `{% if current_user.is_authenticated %}` в шапке и футере,
  `{% for art in title_list %}` в `art_home`, `{% for category, message in messages %}`
  во flash-партиале.
- **Фильтры**: `{{ art.content|safe }}` в `art_author.html` — отключение
  экранирования для доверенных файлов статей; там же цепочка
  `| replace('<h1>', '<h2>')` для понижения заголовков тела статьи (см. §3.4).
- **`url_for`**: все ссылки, включая статику
  (`url_for('static', filename='art_css/base.css')`).

### 3.2 Сайдбар — остаток миграции (не удалён)

Решение 6 задания 003 требовало удалить сайдбар полностью. Фактически удалён только
JS (smooth-scroll), а разметка и стили остались:

- `includes/_sidebar.html` — список «Раздел 1/2/3» с `href="#"`;
- `layout.html` держит сетку `container-fluid` + `col-md-2` (сайдбар) +
  `col-md-10` (контент) на всех страницах;
- `base.css` содержит блок стилей `.margin-right-sidebar` / `.sidebar .nav-link`
  (оранжевые пункты, hover — синий).

Клик по пункту теперь просто прокручивает страницу вверх (обработчика JS нет,
`SyntaxError` из прежнего кода ушёл вместе с ним). Это мёртвый UI-элемент,
подлежащий удалению.

### 3.3 Рендер форм (WTForms -> макрос -> Bootstrap 5)

Формы (`register.html`, `login.html`, `account.html`) рендерятся макросом
`field_with_errors` из `includes/_form_macro.html`: блок «label + input +
invalid-feedback» объявлен один раз, дублирование из 12 копий устранено. Поле
загрузки аватара идёт через отдельный макрос `file_field` (у file-input нет
удобного `invalid-feedback`). Классы BS5: `mb-3`, `form-check`, `form-label`.

### 3.4 Рендер статей и подсветка кода

1. `art_author` в `routes_articles.py` вызывает `render_article(file_name, dir)`:
   `.md`/`.markdown` прогоняются через `markdown()` (расширения `fenced_code`,
   `tables`), `.html` вставляются как есть.
2. Результат кладётся в `art.content`; шаблон понижает заголовки тела статьи
   (`<h1>`→`<h2>`) фильтрами `replace`, чтобы на странице был ровно один `<h1>` —
   заголовок статьи. Способ рабочий, но хрупкий: `replace` не разбирает HTML и
   заденет `<h1>` внутри примеров кода, если такой появится в статье.
3. Тело выводится `{{ body_html|safe }}` внутри `<article class="art-content">`
   с шапкой (`<h1 class="art-title">`, бейджи языка и автора, `#art_id`).
4. На клиенте `scripts.js` вызывает `hljs.highlightAll()` — только если на странице
   есть `pre code`. Подсвечиваются fenced-блоки Markdown
   (`<pre><code class="language-...">`).

Тема подсветки — отдельная настройка пользователя (не привязана жёстко к теме сайта):
15 тёмных тем hljs на выбор через селектор в шапке, по умолчанию `vs2015`; блок кода
всегда на тёмном фоне в обеих темах сайта (задание 004).

### 3.5 Темы (светлая/тёмная) и темы подсветки

- **Тема сайта** — нативный механизм Bootstrap 5: атрибут `data-bs-theme="dark|light"`
  на `<html>`, тёмная по умолчанию. Палитра — CSS-переменные в едином `base.css`:
  тёмная перенесена из прежнего `dark-theme.css` (`#1e1e1e`/`#e0e0e0`/`#61dafb`/
  `#ff6f61`/`#354754`), светлая — кремовая (фон `#f7f3ec`, карточки `#fffdf8`,
  футер `#ede8de`, границы `#e0d8cc`; акценты h1 `#c0338e`, h2 `#2563eb`,
  h3 `#7c3aed`; navbar в обеих темах тёмный `#354754`). Инлайн-код в светлой теме —
  тёмный фон `#2e2e2e`, светлый текст `#e0e0e0`.
- **Восстановление без вспышки**: крошечный инлайн-скрипт в `_head.html` (до
  подключения стилей — единственный допустимый inline-JS) ставит
  `data-bs-theme` из `localStorage['theme']` до первой отрисовки.
- **Переключатель** — пункт «Тема» в шапке с `id="theme-toggle"`, обработчик через
  `addEventListener` в `scripts.js`, без inline `onclick`.
- **Тема подсветки кода** — селектор в шапке (`_hljs_theme_select.html`,
  `id="hljs-theme-select"`): 15 тёмных тем, выбор хранится в
  `localStorage['hljs-theme']` (дефолт `vs2015`), невалидные значения из localStorage
  и лишние `<option>` из разметки отбрасываются. Все 16 таблиц стилей hljs подключены
  в `<head>` заранее (одна активна, остальные `disabled`) — переключение мгновенное,
  ценой 16 CSS-запросов на каждой странице.
- Типографика — системные шрифты (`Segoe UI`, `Courier New`), внешние шрифты не
  грузятся.

## 4. JavaScript — весь клиентский код

Весь свой JS — `static/art_css/scripts.js` (173 строки), IIFE в `'use strict'`,
без глобальных функций, inline-обработчиков и зависимостей:

| Блок | Что делает |
|---|---|
| Хранилища | `localStorage['theme']` = `'dark'\|'light'` (ключ сохранён от прежней версии, чтобы выбор посетителей не сбросился); `localStorage['hljs-theme']` = id темы hljs |
| `syncHighlightTheme()` | активирует ровно одну тёмную таблицу hljs (по `data-hljs-dark`-ссылкам), светлую `vs` держит всегда выключенной — код всегда на тёмном фоне |
| `applyTheme(t)` | ставит `data-bs-theme` на `<html>` + синхронизация hljs |
| `initThemeToggle()` | `addEventListener('click')` на `#theme-toggle` |
| `initHljsThemeSelect()` | выставляет `value` селектора из localStorage, чистит неизвестные `<option>`, подписка на `change` |
| `highlightAll()` | `hljs.highlightAll()` только при наличии `pre code` и только если `hljs` загружен |
| `init()` | точка входа на `DOMContentLoaded` (или сразу, если DOM готов) |

Bootstrap collapse для мобильного меню работает нативно через
`data-bs-toggle="collapse"` — своего кода не требует.

## 5. Что рендерится на каждой странице

| Страница | Шаблон | Особенности |
|---|---|---|
| `/` → `/art_home` | `new_art/art_home.html` | `<h1>Статьи</h1>`, карточки `list-group` с бейджами меты (`text-bg-secondary` — язык, `text-bg-info` — автор) |
| `/art/<author>/<art_id>` | `new_art/art_author.html` | единственный `<h1>` (заголовок статьи), бейджи меты, `{{ body_html|safe }}` |
| `/art_manage` | `new_art/art_manage.html` | три секции: таблица статей, нераспределённые файлы, записи без файла; POST-формы метаданных; alert при ошибке YAML |
| `/register`, `/login` | `register.html`, `login.html` | формы на макросе, русские заголовки |
| `/account` | `account.html` | аватар с `alt`, форма профиля с загрузкой файла |
| `/about`, ошибки | `about.html`, `errors/*.html` | русские заглушки на общей базе |

Flash-сообщения видны на всех страницах: `_flash_msg.html` включён в `layout.html`.

## 6. Сводка: как всё связано

```
браузер
  │  GET /art/<author>/<art_id>
  ▼
Flask → routes_articles.art_author
  │    → render_article(): markdown(.md) → HTML
  ▼
Jinja: layout.html ← art_author.html  ({{ body_html|safe }})
  │
  ├── CDN (cdn.jsdelivr.net, всё с SRI):
  │     Bootstrap 5.3.8 CSS + bundle JS,
  │     highlight.js 11.12.0 JS + 16 таблиц тем
  └── свои: base.css (обе темы на переменных) + scripts.js
        ├── тема сайта: data-bs-theme + localStorage['theme']
        ├── селектор тем hljs: localStorage['hljs-theme'], 15 тёмных тем
        └── hljs.highlightAll() — только при наличии pre code
```

Серверная часть не делает ничего для фронтенда, кроме рендера шаблонов и раздачи
статики через встроенный `static`-эндпоинт Flask; nginx в Docker проксирует и
`/static/*` в приложение (кэширования на уровне nginx нет).
