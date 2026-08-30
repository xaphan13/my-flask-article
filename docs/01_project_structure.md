# 01 — Карта проекта

> Статус: актуально для ветки `new-frontend`, HEAD `b12f62c`, Python 3.12, Flask 3.1.2.
> Фронтенд-разделы актуализированы 2026-08-31 после заданий 003–004
> (подробности — [frontend/README.md](frontend/README.md)).
> Описание сфокусировано на текущей структуре исходного дерева и не заменяет инструкцию
> по запуску: [setup-and-run.md](setup-and-run.md).
> Связанные документы: [02_architecture.md](02_architecture.md) · [03_execution_flow.md](03_execution_flow.md) ·
> [04_code_quality.md](04_code_quality.md) · [05_optimization_roadmap.md](05_optimization_roadmap.md)

## 1. Назначение проекта

`flask-blog-1` — server-rendered сайт технических статей о программировании на Flask 3.1,
собранный по паттерну application factory. Проект совмещает две несвязанные модели контента.

**Первая модель — файловые статьи.** Это фактический продукт сайта: корень `/` редиректит
на `/art_home`, метаданные пяти статей загружаются из
`flaskblog/new_articles/articles.yaml`, а тело каждой статьи лежит отдельным HTML- или
Markdown-файлом в `flaskblog/templates/content_art/`. При открытии статьи файл читается с
диска на каждый запрос; Markdown преобразуется в HTML библиотекой `markdown`. База данных в
этом потоке не участвует вообще.

**Вторая модель — БД-сущности `User` / `Post`.** Реализована регистрация, вход, выход и
редактирование профиля с загрузкой аватара (Flask-SQLAlchemy + PostgreSQL, Flask-Login,
Flask-Bcrypt). Модель `Post` объявлена в `flaskblog/models.py`, но **ни один маршрут её не
использует** — CRUD постов отсутствует. Авторизация в текущем виде не влияет на доступ к
статьям: она меняет только навигацию в шапке и открывает `/account`.

Итого проект — учебно-демонстрационный стенд: работающий публичный контур статей плюс
заготовка блога на БД, не доведённая до CRUD.

## 2. Дерево проекта

Аннотации ниже описывают ответственность и содержащиеся абстракции. Каталоги `.venv/`,
`__pycache__/`, `.idea/`, `pg_db/` опущены как служебные.

```
flask-blog-1/                       корень проекта — ВСЕГДА cwd для запуска (см. §4)
│
├── pyproject.toml                  зависимости (pin по версиям) + конфиг ruff и black,
│                                   line-length 120. Нет [build-system] → пакет не
│                                   устанавливается, импорт работает только из корня
├── uv.lock                         authoritative lock-файл; нужен для сборки Docker-образа
├── .python-version                 3.12
├── reqs_all.txt / reqs_top.txt      pip-совместимые слепки зависимостей (альтернатива uv)
│
├── local.env                       env для локального запуска. НЕ в git, создавать вручную
├── .env                            env для docker compose: DB_USER/DB_PASSWORD/DB_NAME,
│                                   PGADMIN_EMAIL/PGADMIN_PASSWORD. НЕ в git
├── compose-nginx-db.yml            4 сервиса: app_flask, nginx, db, pgadmin; внешняя сеть
│                                   app_net_new со статическими IP 172.20.1.x
├── docker_manager.sh               хелпер: net-create (создать docker-сеть), cont-stop
│                                   (остановить 4 контейнера). Содержит и мёртвые функции
├── git_manager.sh                  хелпер: br / st / brst / commit / push_two / lang
│
├── AGENTS.md, QWEN.md              инструктивный контекст для AI-агентов (+ .ru-версии)
├── README.md / README.ru.md        пользовательская документация
├── docs/
│   ├── setup-and-run.md            подробный отчёт по запуску и переменным окружения
│   └── 01..05_*.md                 настоящий набор документов
│
├── nginx/
│   ├── Docker-nginx                образ nginx:1.20-alpine; копирует conf, web, сертификаты
│   ├── nginx.conf                  TLS-терминация на 443, reverse proxy на
│   │                               172.20.1.50:5000 и /pgadmin → 172.20.1.3:5123.
│   │                               server_name и пути к сертификатам захардкожены
│   ├── cert/                       certificate.pem, private_key.pem — НЕ в git
│   └── web/default/                статические заглушки index.html, custom_50x.html
│
├── instance/site.db                ДЕЙСТВУЮЩАЯ локальная БД SQLite (см. §3.0): текущий
│                                   local.env задаёт DATABASE_URI=sqlite:///site.db.
│                                   Внутри таблицы user (1 запись) и post (0). Gitignored
│
└── flaskblog/                      пакет приложения
    │
    ├── __init__.py                 (42) ЯДРО. Объявляет модуль-level синглтоны db,
    │                               bcrypt, login_manager; фабрика
    │                               create_app(config_class, debug_mode) регистрирует
    │                               4 блюпринта. Логгер инициализируется ДО объявления
    │                               расширений — важно для порядка сбоев (см. §4)
    ├── run.py                      (17) точка входа WSGI: app = create_app(debug_mode=True).
    │                               Под __main__ поднимает waitress, обёрнутый в
    │                               paste TransLogger (access-лог)
    ├── config.py                   (24) класс Config — единственный источник настроек.
    │                               load_dotenv(<корень>/local.env). SQLALCHEMY_DATABASE_URI
    │                               читается ТОЛЬКО из DATABASE_URI; сборка DSN из DB_*
    │                               закомментирована
    ├── models.py                   (37) ORM-слой: User(db.Model, UserMixin) с
    │                               переопределённым __init__, Post(db.Model),
    │                               user_loader для Flask-Login. Классический стиль
    │                               db.Column, не 2.0 Mapped[]
    ├── DockerFlask                 Dockerfile приложения: python:3.12-slim, uv sync
    │                               --locked --no-dev --no-install-project, WORKDIR /flaskblog
    ├── dock_flask.env              env контейнера. НЕ в git. В текущем экземпляре НЕТ
    │                               DATABASE_URI → см. критическую находку в 04
    │
    ├── logger/
    │   ├── config_log.py           (111) ConfigLogger — статический фасад над
    │   │                           logging.config.dictConfig. Ленивая одноразовая
    │   │                           настройка через флаг isSetting, перегрузка getLogger
    │   │                           через multipledispatch. Внизу модуля — словарь
    │   │                           logging_config: 3 логгера (Stdout / FileStdout /
    │   │                           OnlyFile), RotatingFileHandler 1 МБ × 20 бэкапов
    │   └── loggerSettings.json     МЁРТВЫЙ файл: кодом не читается (проверено grep по
    │                               всем .py). Альтернативный dictConfig с логгерами
    │                               app2/app3/werkzeug/sqlalchemy
    │
    ├── main/routes_main.py        (38) блюпринт main: / и /home → редирект на art_home;
    │                               /about (рендер + 5 демонстрационных flash);
    │                               /createDB[/<post_id>] → db.create_all() БЕЗ авторизации
    │
    ├── users/
    │   ├── routes_users.py        (101) блюпринт users: register, login, logout, account.
    │   │                           Плюс save_picture() — ресайз аватара до 125×125 через
    │   │                           Pillow и запись в static/profile_pics со случайным
    │   │                           именем secrets.token_hex(8)
    │   └── forms_users.py         (50) WTForms-слой: LoginForm, RegistrationForm,
    │                               UpdateAccountForm. Валидаторы уникальности
    │                               validate_username/validate_email обращаются к БД
    │
    ├── new_articles/
    │   ├── routes_articles.py    (192) блюпринт art_main: /art_home (список),
    │   │                          /art/<author>/<art_id> (чтение и рендер файла),
    │   │                          /art_manage + два POST-обработчика (реестр статей,
    │   │                          @login_required); _is_complete/_allocate_art_id
    │   ├── schema_art.py         (210) контракт статей: Pydantic-модель ArticleLang;
    │   │                          get_articles()/get_art()/save_articles() — реестр
    │   │                          articles.yaml с mtime-кэшем и атомарной записью;
    │   │                          read_html() и render_article() с преобразованием
    │   │                          Markdown; scan_content_art() (.md/.markdown);
    │   │                          ниже — DTO для несуществующего API
    │   ├── articles.yaml         метаданные статей и имена файлов контента
    │   └── data_ex.py            (34) МЁРТВЫЙ модуль: классы ArticleEx, ArticleLang22,
    │                               список art_list. Упоминается только в
    │                               закомментированной строке routes_main.py
    │
    ├── errors/handlers.py          (18) блюпринт errors: app_errorhandler на 403/404/500.
    │                               Обработчики app-wide, не ограничены блюпринтом
    │
    ├── templates/
    │   ├── layout.html             ЕДИНСТВЕННАЯ база — все страницы, включая статьи.
    │   │                           <html data-bs-theme="dark">, включает
    │   │                           includes/_flash_msg.html → flash виден везде
    │   ├── about.html, login.html, register.html, account.html
    │   ├── includes/               _head.html (Bootstrap 5.3.8 + 16 тем hljs,
    │   │                           meta description, инлайн-восстановление темы),
    │   │                           _header.html (BS5-navbar с тогглером),
    │   │                           _sidebar.html (заглушка «Раздел 1/2/3»,
    │   │                           пережила миграцию — под удаление),
    │   │                           _scripts.html, _flash_msg.html,
    │   │                           _form_macro.html (макросы форм),
    │   │                           _hljs_theme_select.html (селектор тем hljs),
    │   │                           _footer_macro.html (макрос footer_new)
    │   ├── new_art/
    │   │   ├── art_home.html       список статей карточками с бейджами меты
    │   │   ├── art_author.html     страница статьи; единственный <h1>, тело
    │   │   │                       через art.content|safe с понижением
    │   │   │                       <h1>→<h2> фильтрами replace
    │   │   └── art_manage.html     управление реестром статей (POST-формы)
    │   ├── content_art/            ТЕЛА СТАТЕЙ: пять Markdown-файлов,
    │   │                           зарегистрированных в articles.yaml. Читаются
    │   │                           с диска на каждый запрос; Markdown рендерится
    │   │                           функцией render_article()
    │   └── errors/                 403.html, 404.html, 500.html — русские,
    │                               на общей базе layout.html
    │
    └── static/
        ├── art_css/               base.css (единый файл обеих тем на
        │                          CSS-переменных; dark/light-файлов больше нет)
        │                          + scripts.js (IIFE: тема data-bs-theme +
        │                          localStorage, селектор 15 тёмных тем hljs,
        │                          highlightAll только при наличии pre code)
        └── profile_pics/          default.jpg + загруженные аватары
```

## 3. Внешние зависимости и их роль

### 3.0 Какая СУБД используется фактически

Различие между целевой и фактической конфигурацией — первое, что нужно проверять при
работе с этим проектом:

| | Целевая конфигурация | Фактическая на момент проверки |
|---|---|---|
| СУБД | PostgreSQL 16 (сервис `db` в compose, `psycopg2-binary` в зависимостях) | **SQLite** |
| Значение `DATABASE_URI` | `postgresql+psycopg2://…@127.0.0.1:9032/flask_blog` | `sqlite:///site.db` в `local.env` |
| Файл данных | том `./pg_db` | `instance/site.db` (Flask кладёт относительный SQLite-путь в `instance/`) |

Проверено запуском: `app.config['SQLALCHEMY_DATABASE_URI'] == 'sqlite:///site.db'`,
в файле присутствуют таблицы `user` (1 запись) и `post` (0 записей) — значит `/createDB`
уже вызывался. Переключение между СУБД выполняется одной переменной `DATABASE_URI`,
код от диалекта не зависит. Таблицы ниже описывают целевой Docker-контур.

### 3.1 Инфраструктурные сервисы

| Сервис | Где объявлен | Роль | Как адресуется |
|---|---|---|---|
| PostgreSQL 16 | `compose-nginx-db.yml`, сервис `db` | Хранение `User` / `Post`. В потоке статей не участвует | DSN целиком из `DATABASE_URI`; наружу порт `9032:5432`, внутри статический IP `172.20.1.2`. Данные — bind-mount `./pg_db` |
| nginx 1.20-alpine | `nginx/Docker-nginx`, `nginx/nginx.conf` | TLS-терминация и reverse proxy; отдаёт статические заглушки | Слушает `443`, публикуется как `1443:443`. Проксирует на захардкоженный `172.20.1.50:5000` |
| pgAdmin 4 | `compose-nginx-db.yml`, сервис `pgadmin` | Веб-администрирование БД | Проксируется по `/pgadmin` на `172.20.1.3:5123` |
| Docker-сеть `app_net_new` | внешняя, создаётся `./docker_manager.sh net-create` | Общая bridge-сеть `172.20.0.0/16` со статической адресацией | Помечена `external: true` — compose её не создаёт |

Брокеров сообщений, кэшей (Redis/Memcached), очередей задач и сторонних HTTP-API в проекте
**нет**. Единственный внешний сетевой вызов из runtime — подключение к PostgreSQL.

### 3.2 Внешние ресурсы фронтенда (CDN)

Загружаются напрямую из шаблонов, без бандлера и без локальных копий — офлайн-режим
ломается. После задания 003 все ресурсы идут с одного домена `cdn.jsdelivr.net`,
у каждого тега `integrity` (SRI) + `crossorigin`:

| Ресурс | Версия | Где подключён |
|---|---|---|
| Bootstrap CSS | 5.3.8 | `includes/_head.html` |
| Bootstrap JS (bundle) | 5.3.8 | `includes/_scripts.html` |
| highlight.js JS | 11.12.0 (`gh/highlightjs/cdn-release`) | `includes/_scripts.html` |
| highlight.js CSS — 15 тёмных тем | 11.12.0 | `includes/_head.html`, активна `vs2015`, остальные `disabled` |
| highlight.js CSS — светлая `vs` | 11.12.0 | `includes/_head.html`, всегда `disabled` |

jQuery и Popper удалены при миграции на Bootstrap 5 (задание 003).

### 3.3 Python-зависимости

Пины из `pyproject.toml`:

| Пакет | Версия | Роль в коде |
|---|---|---|
| `flask` | 3.1.2 | ядро, блюпринты, Jinja, сессии |
| `flask-sqlalchemy` | 3.1.1 | ORM-слой в `flaskblog/models.py` |
| `psycopg2-binary` | не пинован | драйвер PostgreSQL |
| `flask-login` | 0.6.3 | сессии пользователя, `login_required`, `current_user` |
| `flask-bcrypt` | 1.0.1 | хэширование пароля (`User.password` = `String(60)`) |
| `flask-wtf` / `wtforms` | 1.2.2 / 3.2.1 | формы + CSRF-защита |
| `email-validator` | ≥2.3.0 | транзитивно нужен валидатору `Email()` |
| `pydantic` | 2.12.5 | модель `ArticleLang` и неиспользуемые схемы в `schema_art.py` |
| `pillow` | 12.0.0 | ресайз аватара в `save_picture()` |
| `python-dotenv` | 1.2.1 | `load_dotenv()` в `flaskblog/config.py` |
| `waitress` | 3.0.2 | WSGI-сервер при локальном запуске |
| `gunicorn` | 23.0.0 | WSGI-сервер в Docker (`command` сервиса `app_flask`) |
| `pastescript` | 3.7.0 | `paste.translogger.TransLogger` — access-лог вокруг приложения в `run.py` |
| `multipledispatch` | 1.0.0 | перегрузка `ConfigLogger.getLogger` по числу аргументов |

`ruff` и `black` настроены в `pyproject.toml`, но **не объявлены зависимостями** — ставятся
как инструменты (`uv tool install ruff`). Тестовых зависимостей нет: `pytest` отсутствует.

## 4. Инварианты окружения

Четыре свойства, нарушение которых ломает запуск. Проверены экспериментально.

1. **cwd обязан быть корнем проекта.** `get_path_dir()` в `flaskblog/new_articles/schema_art.py`
   строит путь как `os.getcwd() + "flaskblog/templates" + "content_art"`. Более того, этот путь
   вычисляется **один раз при импорте модуля** — он зафиксирован в значении по умолчанию
   параметра `read_html(name_html, name_dir=get_path_dir())`, поэтому `chdir` после импорта
   уже ничего не изменит.
2. **Запускать только как модуль.** `python -m flaskblog.run` или
   `gunicorn flaskblog.run:app`. Прямой `python flaskblog/run.py` кладёт в `sys.path[0]`
   каталог `flaskblog/`, и `from flaskblog import create_app` падает с `ModuleNotFoundError`,
   потому что пакет не установлен (нет `[build-system]`).
3. **`LOG_DIR` обязателен и должен быть однин уровень.** Логгер инициализируется на этапе
   импорта `flaskblog`, до объявления `db`; при отсутствующем `LOG_DIR` падение будет
   `TypeError` из `os.path.exists(None)` ещё на импорте. `ConfigLogger.__createLogDir`
   использует `os.mkdir`, а не `os.makedirs`, поэтому вложенный путь вида `./log_app/flask`
   даст `FileNotFoundError`.
4. **`DATABASE_URI` — основной источник DSN.** Если она не задана, `config.py` собирает
   DSN из `DB_USER`/`DB_PASSWORD`/`DB_HOST`/`DB_PORT`/`DB_NAME` (эти же переменные
   использует docker compose). Если не задано ни то, ни другое полностью — приложение
   падает в `db.init_app(app)` с `RuntimeError: Either 'SQLALCHEMY_DATABASE_URI' or
   'SQLALCHEMY_BINDS' must be set.`

## 5. Метрики

| Показатель | Значение |
|---|---|
| Python-кода | Текущее количество зависит от состава исходников; метрика не фиксируется в этом документе |
| Из них мёртвый код | 34 (`data_ex.py`) + ~32 (DTO в `schema_art.py`) ≈ 11 % |
| Маршрутов в `url_map` | 16 (15 прикладных + встроенный `static`; проверено запуском 2026-08-31) |
| Блюпринтов | 4 (`art_main`, `main`, `users`, `errors`) |
| ORM-моделей | 2 (`User`, `Post`; для `Post` нет ни одного маршрута) |
| Jinja-шаблонов | 19 HTML, единая иерархия наследования `layout.html` (+ 5 Markdown-файлов тел статей в `content_art/`) |
| Тестов | 0 |
| Миграций | 0 (нет Flask-Migrate/Alembic) |
| CI-пайплайнов | 0 (каталога `.github` нет) |
