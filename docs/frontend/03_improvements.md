# 03 — Предложения по улучшению

> Рекомендации для фронтенд-слоя (Jinja-шаблоны, CSS, JavaScript). Опирается на
> факты из [`01_how_it_works.md`](01_how_it_works.md) и
> [`02_modernity_assessment.md`](02_modernity_assessment.md). Приоритеты: **P0** —
> дефекты, которые видны пользователю уже сейчас; **P1** — модернизация стека;
> **P2** — плановые улучшения.

## 1. CSS-фреймворк: Bootstrap 5, Tailwind или что-то ещё

### 1.1 Сравнение вариантов

| Вариант | Нужен build-этап | Размер (CSS) | jQuery/Popper | Темы | Миграция с текущего кода | Вердикт для этого проекта |
|---|---|---|---|---|---|---|
| **Bootstrap 5.3.x** | нет (CDN или свои файлы) | ~30 КБ min | не нужен | нативные `data-bs-theme` + CSS-переменные | средняя: классы в шаблонах знакомые, но есть переименования (см. 1.3) | **рекомендуется** |
| **Tailwind CSS 4** | да (CLI/standalone, иначе Play CDN — только для прототипов) | ~10-30 КБ после purge | не нужен | легко, утилиты + токены | высокая: вся разметка пишется заново | оправдан только при готовности ввести сборку |
| **Bulma** | нет | ~80 КБ (или сасс-сборка) | не нужен | своя система переменных | высокая: другая сетка, другие классы | допустим, но без явных преимуществ |
| **Pico.css** | нет | ~10 КБ, classless | не нужен | `data-theme` + `prefers-color-scheme` из коробки | средняя: разметку упрощает, но сетку/навбар придётся дописать самим | хорош для «чистого» контентного сайта |
| **Чистый CSS + design tokens** | нет | свой | не нужен | CSS-переменные, полный контроль | высокая, всё пишется с нуля | оверхед для текущего масштаба |

### 1.2 Рекомендация

**Bootstrap 5.3.x** — прагматичный выбор для этого проекта:

1. **Снимает две лишние библиотеки сразу.** Bootstrap 5 не требует jQuery и
   Popper (Popper v2 нужен только для тултипов/dropdown, которых в проекте нет).
   Из шаблонов удаляются три `<script>` — минус ~230 КБ рендер-блокирующего JS.
2. **Нативная тёмная тема.** `data-bs-theme="dark|light"` + CSS-переменные
   заменяют механизм «два CSS-файла + JS подмена href» (см. 2.3): убирается
   `toggleTheme()`, `theme-link`, дублирование тем.
3. **Совместимость разметки.** Сетка, навбар, таблицы, формы, алерты — те же
   концепции; миграция — механическая замена утилит (таблица в 1.3).
4. **Никакого build-этапа.** Подключение с jsdelivr или локальная копия — как
   сейчас с CDN; проекту не придётся заводить node/таскраннер (проект сознательно
   без тяжёлых dev-зависимостей).

**Tailwind CSS** — лучший выбор для проекта с дизайн-системой и сборкой, но не
здесь: он требует build-этапа (даже standalone-бинарник), а в серверных
Jinja-шаблонах утилитарные классы распухают и мешают читать разметку. Если когда-то
появится желание полностью переработать дизайн — сначала Bootstrap 5, потом
осознанный переход на Tailwind, а не наоборот.

**Pico.css** — интересная лёгкая альтернатива, если хочется «не-бутстраповского»
вида: classless-стили хорошо ложатся на статьи, тёмная тема из коробки. Минус —
сетку, шапку и сайдбар придётся строить вручную, что вернёт нас к написанию
собственного CSS, от которого проект ушёл в Bootstrap.

### 1.3 Карта замены классов Bootstrap 4 → 5 (по шаблонам)

| Класс BS4 (сейчас) | Класс BS5 | Где встречается |
|---|---|---|
| `mr-2`, `mr-4`, `mr-auto`, `ml-2` | `me-2`, `me-4`, `me-auto`, `ms-2` | `_header`, `art_home`, `art_manage` |
| `badge badge-success/badge-warning/badge-danger` | `badge text-bg-success` и т.п. | `art_manage.html` |
| `btn-block` | убран (ширина через `d-block w-100`) | `art_manage.html` |
| `form-group` | `mb-3` (класс удалён) | `register`, `login`, `account` |
| `thead-light` | `table-light` | `art_manage.html` |
| `navbar-dark` + свои цвета | `navbar` + CSS-переменные | `_header.html` |
| `text-body-secondary` (уже BS5!) | оставить | `_footer_macro.html` — начнёт работать |
| `data-toggle="collapse"` | `data-bs-toggle="collapse"` | добавить тогглер (см. 2.1) |

Остальное (сетка `col-md-*`, `container`, `alert`, `form-control`, `btn`,
`nav-item`, `table` и т.д.) — без изменений.

## 2. Быстрые исправления JS и шаблонов (P0)

### 2.1 Мобильное меню

Добавить в `includes/_header.html` кнопку-тогглер перед
`.collapse.navbar-collapse`:

```html
<button class="navbar-toggler" type="button" data-toggle="collapse"
        data-target="#navbarToggle" aria-controls="navbarToggle"
        aria-expanded="false" aria-label="Toggle navigation">
  <span class="navbar-toggler-icon"></span>
</button>
```

(при переходе на Bootstrap 5 — `data-bs-toggle="collapse"` +
`data-bs-target`). Это чинит недоступность навигации на мобильных.

### 2.2 Сайдбар

Либо наполнить сайдбар реальными якорями (`<a href="#section-1">` к
`id="section-1"` в статьях), либо убрать smooth-scroll-код. На текущем этапе
сайдбар — заглушка, поэтому честный минимум — удалить блок `document.querySelectorAll(...)`
из `scripts.js` и оставить сайдбар-заглушку без JS, либо заменить селектор на
`data-target`-атрибут и обрабатывать только реальные якоря:

```javascript
document.querySelectorAll('.sidebar a[href^="#"]').forEach(anchor => {
  anchor.addEventListener('click', function (e) {
    const target = document.querySelector(this.getAttribute('href'));
    if (!target) return;
    e.preventDefault();
    target.scrollIntoView({ behavior: 'smooth' });
  });
});
```

### 2.3 Темы через CSS-переменные (P1, но дёшево)

Заменить пару `dark-theme.css`/`light-theme.css` на один файл с переменными:

```css
:root[data-theme="light"] { --bg: #f9f9f9; --text: #333; ... }
:root[data-theme="dark"]  { --bg: #1e1e1e; --text: #e0e0e0; ... }
```

JS-переключатель сокращается до установки `data-theme` на `<html>` + localStorage;
в `<head>` добавляется маленький inline-скрипт восстановления темы до отрисовки
(убирает «вспышку»). При переходе на Bootstrap 5 это же делает `data-bs-theme`,
и `toggleTheme()` исчезает совсем. Пути в JS заменить на `url_for`-совместимый
вариант — сейчас в `scripts.js` захардкожены `/static/art_css/...`.

### 2.4 Дедупликация форм макросом Jinja

Блок «поле + ошибки» повторён 12 раз в `register.html`, `login.html`,
`account.html`. Вынести в макрос:

```jinja
{% macro field_with_errors(field, size='form-control-lg') %}
  {{ field.label(class="form-control-label") }}
  {% if field.errors %}
    {{ field(class="form-control " + size + " is-invalid") }}
    <div class="invalid-feedback">
      {% for error in field.errors %}<span>{{ error }}</span>{% endfor %}
    </div>
  {% else %}
    {{ field(class="form-control " + size) }}
  {% endif %}
{% endmacro %}
```

Это убирает ~70 строк дублирования и делает добавление полей однострочным.

### 2.5 Убрать inline `onclick` и глобальные функции

`onclick="toggleTheme()"` в `_header.html` заменить на
`<a class="nav-item nav-link theme-toggle" href="#" id="theme-toggle">Тема</a>` и
`addEventListener` в `scripts.js`. Параллельно: `hljs.highlightAll()` вызывать
только если на странице есть `pre code` (`document.querySelector('pre code')`),
чтобы не гонять парсер на страницах без кода.

## 3. CDN, доставка статики, безопасность (P1)

### 3.1 CDN

- Все внешние ресурсы перевести на **jsdelivr** (один источник): Bootstrap 5.3,
  highlight.js 11.x. `maxcdn.bootstrapcdn.com` — устаревший домен.
- Добавить `integrity` (SRI) для highlight.js CSS и JS (сейчас отсутствует).
- Рассмотреть `defer` для highlight.js: `hljs.highlightAll()` всё равно вызывается
  после загрузки DOM, порядок с Bootstrap JS не важен.

### 3.2 Локальные копии или fallback

Сайт полностью зависит от CDN: при недоступности — нет стилей и навигации.
Варианты по возрастанию сложности: (а) оставить CDN, но добавить
`onerror`-fallback на локальную копию; (б) скачать Bootstrap и highlight.js в
`static/vendor/` и раздавать свои. Для проекта с Docker и nginx вариант (б)
предпочтительнее: статика и так должна отдаваться nginx'ом, а не Python-воркером.

### 3.3 Статика через nginx (P2, но почти бесплатно)

В `nginx/nginx.conf` добавить:

```nginx
location /static/ {
    alias /app/flaskblog/static/;
    expires 7d;
    add_header Cache-Control "public";
    gzip on; gzip_types text/css application/javascript;
}
```

Плюс `Cache-Control`/`ETag` для страниц статей — контент почти неизменяемый.
Это снимает с gunicorn-воркера раздачу файлов и даёт кэширование.

### 3.4 Минификация и заголовки

- Свои `base.css` / `scripts.js` минифицировать (одной командой на деплое, без
  build-этапа в рантайме) и/или подключить сжатие gzip на nginx (3.3).
- Рассмотреть CSP: `default-src 'self'; script-src 'self' https://cdn.jsdelivr.net;`
  — это попутно требует убрать inline `onclick` (2.5), что уже запланировано.

## 4. Доступность, семантика, SEO (P2)

- Заголовок статьи в `art_author.html` сделать `<h1>` (сейчас `<h3>`).
- `alt` для аватара в `account.html`.
- Skip-link «К содержанию» и `aria-current="page"` для активного пункта меню.
- `<meta name="description">` (можно из `art.title`), favicon, Open Graph для
  страниц статей.
- Привести язык интерфейса к единому (русский): `Articles` → «Статьи»,
  `Account` → «Аккаунт», `Logout` → «Выход», `Login`/`Register` → «Вход»/«Регистрация».
- `{{ art.content|safe }}` оставить как есть (доверенные файлы), но зафиксировать
  в коде комментарием, почему экранирование отключено.

## 5. Дорожная карта

| Фаза | Что делать | Эффект |
|---|---|---|
| **0. P0-починки** (не связаны с версиями) | тогглер мобильного меню (2.1); фикс/удаление smooth-scroll сайдбара (2.2); дедупликация форм макросом (2.4); убрать inline onclick (2.5) | чинятся видимые дефекты, уходит ~100 строк дублирования |
| **1. Bootstrap 4 → 5.3** | замена классов по таблице 1.3; удаление jQuery/Popper/BS4 JS из `_scripts.html`; `data-bs-theme` для тем (2.3); CDN на jsdelivr + SRI (3.1) | стек 2024-2026, минус 2 библиотеки, нативная тёмная тема |
| **2. Доставка** | статика через nginx (3.3); локальные копии vendor (3.2); минификация (3.4) | меньше нагрузки на воркер, кэширование, офлайн-устойчивость |
| **3. Доступность и SEO** | раздел 4 | качество страниц, поисковая видимость |

**Ключевая мысль.** Ни один пункт не требует переписывания шаблонов с нуля:
структура Jinja-иерархии уже правильная, меняются библиотеки и точечные практики.
Суммарный объём работ — порядка нескольких дней, наибольший эффект даёт фаза 1
(обновление Bootstrap), которая попутно решает jQuery/Popper, темы и CDN.