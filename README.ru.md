# flask-blog-1

Блог/сайт технических статей с серверным рендерингом на **Flask 3.1**, построенный по
паттерну «фабрика приложения» (application factory).

🇬🇧 English version: [README.md](README.md)

Сайт намеренно совмещает **две независимые модели контента**:

1. **Статьи из файлов** — технические статьи хранятся как статические Jinja-HTML файлы в
   `flaskblog/templates/content_art/` и описываются Pydantic-моделями в
   `flaskblog/new_articles/schema_art.py`. Именно это — основной контент сайта:
   `/` перенаправляет на `/art_home`.
2. **Пользователи и посты в БД** — `User` / `Post` через Flask-SQLAlchemy на PostgreSQL,
   с регистрацией, входом и загрузкой аватара.

> Язык интерфейса, flash-сообщений и содержимого статей — **русский**.

## Возможности

- Список статей и страницы отдельных статей, собираемые из статических HTML-фрагментов
  (в репозитории 4 статьи: темы по Python и Rust).
- Регистрация / вход / выход пользователей на Flask-Login с хешированием паролей
  Flask-Bcrypt.
- Страница аккаунта с загрузкой аватара, который Pillow уменьшает в миниатюру и кладёт в
  `static/profile_pics/`.
- Переключение светлой и тёмной темы через `static/art_css/` + `scripts.js`.
- Своя обёртка `ConfigLogger` над `logging.config.dictConfig` с готовыми наборами логгеров:
  консоль / файл / оба сразу.
- Обработчики ошибок 403 / 404 / 500 на уровне приложения.
- Полноценное развёртывание в Docker: gunicorn за nginx с TLS, PostgreSQL 16 и pgAdmin.

## Стек

| Область | Выбор |
|---|---|
| Язык | Python 3.12 (`.python-version`) |
| Менеджер пакетов | `uv` (`uv.lock` — источник истины) |
| Веб-фреймворк | Flask 3.1.2 + Blueprints |
| ORM | Flask-SQLAlchemy 3.1.1 → PostgreSQL (`psycopg2-binary`) |
| Аутентификация | Flask-Login + Flask-Bcrypt |
| Формы | Flask-WTF / WTForms (+ `email-validator`) |
| Валидация / схемы | Pydantic 2.12 |
| WSGI-сервер | `waitress` локально, `gunicorn` в Docker |
| Обратный прокси | nginx с TLS (только в Docker) |
| Изображения | Pillow |

## Требования

- Python 3.12+
- [`uv`](https://docs.astral.sh/uv/)
- PostgreSQL — своя инсталляция либо та, что поднимается в Docker compose
- Для варианта с Docker: Docker + Compose v2

## Быстрый старт (локально)

```bash
cd flask-blog-1
uv sync                      # создаёт .venv по uv.lock
source .venv/bin/activate
```

Создайте `local.env` в корне проекта (файл в `.gitignore`):

```dotenv
SECRET_KEY=<длинная-случайная-строка>
DATABASE_URI=postgresql+psycopg2://flask_user:flask_password@127.0.0.1:9032/flask_blog
LOG_DIR=./log
LOG_FILE=FLASK.log
```

Запуск приложения:

```bash
python -m flaskblog.run                                        # предпочтительно
waitress-serve --host=0.0.0.0 --port=5000 flaskblog.run:app    # WSGI-таргет
gunicorn -w 1 -b 0.0.0.0:5000 flaskblog.run:app
```

Затем **один раз** откройте <http://127.0.0.1:5000/createDB>, чтобы создать таблицы в БД, и
<http://127.0.0.1:5000/> — для самого сайта.

> ⚠️ **Всегда запускайте из корня проекта и никогда как `python flaskblog/run.py`.**
> Python поместит в `sys.path[0]` каталог `flaskblog/`, а не корень проекта, поэтому
> `from flaskblog import create_app` упадёт с `ModuleNotFoundError`. Проект не
> устанавливается как пакет (в `pyproject.toml` нет `[build-system]`). Загрузка статей тоже
> разрешается относительно текущего рабочего каталога.

## Конфигурация

Вся конфигурация читается из переменных окружения в `flaskblog/config.py`, который
подгружает `<корень-проекта>/local.env` через `python-dotenv`.

| Переменная | Кто использует | Обязательна | Примечания |
|---|---|---|---|
| `SECRET_KEY` | сессии Flask, CSRF | да | любая длинная случайная строка |
| `DATABASE_URI` | SQLAlchemy | да | **единственный** источник DSN |
| `LOG_DIR` | `ConfigLogger` | да | должен быть **одноуровневым**, например `./log` |
| `LOG_FILE` | `ConfigLogger` | да | например `FLASK.log` |
| `DB_USER`, `DB_PASSWORD`, `DB_NAME` | docker compose → postgres | только Docker | не входят в DSN |
| `PGADMIN_EMAIL`, `PGADMIN_PASSWORD` | docker compose → pgadmin | только Docker | |

`DB_HOST` / `DB_PORT` по-прежнему читаются в `Config`, но сборка DSN, которая их
использовала, закомментирована — их установка сама по себе ни на что не влияет.

## Маршруты

Регистрируются 13 URL-правил (12 маршрутов приложения плюс встроенный `static` от Flask):

| Методы | Маршрут | Эндпоинт | Назначение |
|---|---|---|---|
| GET | `/`, `/home` | `main.home` | перенаправляет на `/art_home` |
| GET | `/art_home` | `art_main.art_home` | список статей — главная страница |
| GET | `/art/<author>/<art_id>` | `art_main.art_author` | отдельная статья |
| GET | `/about` | `main.about` | страница «о проекте» (и демо всех категорий flash) |
| GET | `/createDB`, `/createDB/`, `/createDB/<post_id>` | `main.createDB` | вызывает `db.create_all()` |
| GET, POST | `/register` | `users.register` | регистрация |
| GET, POST | `/login` | `users.login` | вход |
| GET | `/logout` | `users.logout` | выход |
| GET, POST | `/account` | `users.account` | профиль и загрузка аватара |

Блюпринты: `art_main`, `main`, `users`, `errors` — все регистрируются в `create_app()`
в `flaskblog/__init__.py`.

## Запуск в Docker

```bash
./docker_manager.sh net-create                       # внешняя сеть app_net_new, 172.20.0.0/16
docker compose -f compose-nginx-db.yml build
docker compose -f compose-nginx-db.yml up -d
docker compose -f compose-nginx-db.yml logs -f app_flask
./docker_manager.sh cont-stop                        # остановить все четыре контейнера
```

Перед первой сборкой нужно создать три вещи, которых нет в git (см.
[`docs/setup-and-run.md`](docs/setup-and-run.md) §5.2):

- `flaskblog/dock_flask.env` — окружение контейнера
- `.env` рядом с compose-файлом — значения `DB_*` и `PGADMIN_*`
- self-signed сертификаты в `nginx/cert/` (`certificate.pem`, `private_key.pem`)

| Сервис | Контейнер | Доступен по |
|---|---|---|
| nginx (TLS) | `nginx_flask` | <https://localhost:1443/> |
| Flask + gunicorn | `app_flask` | только внутри сети, `172.20.1.50:5000` |
| PostgreSQL 16 | `postgresql_db_flask` | `127.0.0.1:9032` |
| pgAdmin | `pgadmin_flask` | <https://localhost:1443/pgadmin> |

Логи контейнера монтируются в `flaskblog/log_app/`, файлы базы данных — в `pg_db/`.
В контейнерах предпочитайте абсолютный `LOG_DIR`, например `/flaskblog/log`.

## Структура проекта

```
flask-blog-1/                   <- корень проекта; всегда cwd для любого запуска
├── pyproject.toml              зависимости + настройки ruff/black
├── uv.lock
├── local.env                   локальные переменные окружения — НЕ в git, создать вручную
├── compose-nginx-db.yml        app_flask + nginx + db + pgadmin
├── docker_manager.sh           хелперы net-create | cont-stop
├── git_manager.sh              хелперы br | st | brst | commit
├── docs/setup-and-run.md       подробный отчёт по настройке и разбору проблем (рус.)
├── nginx/                      Docker-nginx, nginx.conf, cert/ (сертификатов нет в git)
└── flaskblog/                  пакет приложения
    ├── __init__.py             create_app(), db, bcrypt, login_manager
    ├── run.py                  точка входа: app = create_app(debug_mode=True)
    ├── config.py               класс Config; load_dotenv(<корень>/local.env)
    ├── models.py               User, Post
    ├── DockerFlask             Dockerfile приложения
    ├── logger/config_log.py    ConfigLogger + dictConfig
    ├── main/ users/ new_articles/ errors/   блюпринты
    ├── templates/ static/
    └── log/                    вывод логов (относительно cwd)
```

## Модель данных

```python
User(id, username, email, image_file, password) -> posts
Post(id, title, date_posted, content, user_id)
```

Статьи — это Pydantic-модели `ArticleLang` с полями
`author`, `lang`, `art_id`, `title`, `file_name`, `content`.
Метаданные статей хранятся в `flaskblog/new_articles/articles.yaml`, а тела статей — в
`flaskblog/templates/content_art/`. Поддерживаются файлы `.html`, `.md` и `.markdown`.

**Чтобы добавить статью:**

1. Создайте `flaskblog/templates/content_art/<file>.html` или `<file>.md` с телом статьи.
2. Добавьте запись с метаданными в `flaskblog/new_articles/articles.yaml`:

```yaml
  - author: Max
    lang: Python
    art_id: 6
    title: Название статьи
    file_name: my_article.md
```

Словарь `art_dict_file` загружается из YAML и индексируется по `art_id` — именно его ищет
маршрут `/art/<author>/<art_id>`. HTML-файлы выводятся как готовая разметка, Markdown
рендерится на сервере в HTML.

## Линтеры и форматирование

```bash
uv run ruff check .
uv run ruff format .     # либо: uv run black .
```

Длина строки — 120. Ruff намеренно игнорирует `F401` (неиспользуемые импорты), `E402`
(импорты не в начале файла) и `F541` (f-строка без подстановок) — код осознанно
инициализирует логгер до остальных импортов и реэкспортирует имена.

Ruff и black **не** объявлены в зависимостях; устанавливайте их как инструменты
(`uv tool install ruff`) либо добавьте dev-группу.

## Проверка изменений

Тестов нет, поэтому изменения проверяются запуском самого приложения:

```bash
python -c "from flaskblog import create_app; print(len(list(create_app().url_map.iter_rules())))"   # 13
python -m flaskblog.run                                                                            # затем curl /
```

## Известные ограничения

- **Нет тестов** и **нет фреймворка миграций.** `db.create_all()` вызывается только из
  маршрута `/createDB` и не изменяет уже существующие таблицы — после правок `models.py`
  таблицы нужно пересоздавать вручную либо подключать Flask-Migrate.
- **`run.py` жёстко задаёт `debug_mode=True`**, и команда `gunicorn` в Docker это
  наследует. Это проблема для production, а не намеренная настройка.
- **`/createDB` не требует аутентификации** — любой посетитель может вызвать
  `db.create_all()`.
- В `compose-nginx-db.yml` остался устаревший ключ `version: "3.7"`, а у `app_flask`
  указан `depends_on: nginx` вместо `db` — поэтому первое обращение к БД после холодного
  старта может упасть и потребовать повтора.
- В `nginx.conf` жёстко прописаны `server_name xaphan.ru` и пути к сертификатам.

## Документация

Всё в `docs/` написано по-русски. Нумерованная серия 01–05 рассчитана на чтение по порядку;
`setup-and-run.md` — операционный спутник к ней.

| Документ | Содержание |
|---|---|
| [`docs/01_project_structure.md`](docs/01_project_structure.md) | карта проекта, дерево файлов, внешние зависимости и их роль, инварианты окружения, метрики |
| [`docs/02_architecture.md`](docs/02_architecture.md) | высокоуровневая архитектура, применённые паттерны, поток данных, состояние / кэширование / конфигурация, развёртывание |
| [`docs/03_execution_flow.md`](docs/03_execution_flow.md) | жизненный цикл приложения, маршруты и обработка запроса, ключевые процессы пошагово, обработка ошибок, логирование |
| [`docs/04_code_quality.md`](docs/04_code_quality.md) | оценка качества, читаемость и связность, тестируемость как главный долг, дефекты по критичности |
| [`docs/05_optimization_roadmap.md`](docs/05_optimization_roadmap.md) | порядок работ, архитектурные улучшения, производительность, очередь рефакторинга, DX, сводка приоритетов |
| [`docs/setup-and-run.md`](docs/setup-and-run.md) | отчёт по настройке и разбору проблем, с полными таблицами переменных окружения |
| [`AGENTS.md`](AGENTS.md) / [`AGENTS.ru.md`](AGENTS.ru.md) | соглашения и «грабли» для AI-агентов, работающих с кодом |
