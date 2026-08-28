# flask-blog-1 — запуск и настройка

Отчёт по фактическому состоянию репозитория: как правильно запускать приложение,
какие переменные окружения нужны и какие грабли есть в текущем коде.

- Python: 3.12 (`.python-version`, venv `.venv` = Python 3.12.13)
- Менеджер пакетов: `uv` (есть `uv.lock`)
- WSGI-серверы: `waitress` (локально), `gunicorn` (в Docker)
- БД: PostgreSQL через `psycopg2-binary` + Flask-SQLAlchemy
- Статьи: метаданные в YAML, содержимое в HTML или Markdown (`markdown`, `PyYAML`)

---

## 1. Структура проекта

```
flask-blog-1/                  <- корень проекта (ВСЕГДА cwd для запуска)
├── pyproject.toml             зависимости, настройки ruff/black
├── uv.lock
├── local.env                  локальные переменные окружения (НЕ в git, создать вручную)
├── compose-nginx-db.yml       docker compose: app_flask + db + pgadmin + nginx
├── docker_manager.sh          хелпер: создание docker-сети, остановка контейнеров
├── git_manager.sh
├── nginx/
│   ├── Docker-nginx
│   ├── nginx.conf             TLS + reverse proxy на 172.20.1.50:5000
│   ├── cert/                  certificate.pem / private_key.pem (НЕ в git)
│   └── web/default/
└── flaskblog/                 <- пакет приложения
    ├── __init__.py            create_app(), db, bcrypt, login_manager
    ├── run.py                 точка входа: app = create_app(debug_mode=True)
    ├── config.py              класс Config, load_dotenv(../local.env)
    ├── models.py              User, Post
    ├── DockerFlask            Dockerfile приложения
    ├── dock_flask.env         env для контейнера (НЕ в git, создать вручную)
    ├── logger/config_log.py   ConfigLogger + dictConfig
    ├── new_articles/
    │   ├── articles.yaml      метаданные статей
    │   ├── schema_art.py      загрузка YAML, чтение HTML и рендер Markdown
    │   └── routesArticles.py  список и показ статей
    ├── templates/content_art/ HTML- и Markdown-файлы статей
    ├── main/, users/, errors/ остальные блюпринты
    ├── templates/, static/
    └── log/                   каталог логов (в git нет; создаётся на старте
                               относительно cwd, см. п. 6.5)
```

---

## 2. Настройка окружения

### 2.1 Виртуальное окружение и зависимости

```bash
cd ~/0_26_MY_pro_one/flask-blog-1

uv sync                 # создаст .venv и установит зависимости по uv.lock
source .venv/bin/activate
```

Альтернатива без uv:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r reqs_all.txt      # полный пин-лист
# или: pip install -r reqs_top.txt
```

Важно: проект **не устанавливается** как пакет (в `pyproject.toml` нет `[build-system]`,
в `site-packages` нет ни `flask_blog_1`, ни `.pth` на корень). Поэтому пакет `flaskblog`
импортируется только когда корень проекта попадает в `sys.path` — то есть когда cwd = корень
проекта, либо через `PYTHONPATH`. Отсюда следует раздел 4.

### 2.2 Файл `local.env`

`flaskblog/config.py:5-6` читает env-файл по пути `<корень проекта>/local.env`:

```python
env_path: Path = Path(__file__).resolve().parent.parent / "local.env"
load_dotenv(env_path)
```

Файл в `.gitignore` (`*.env`), поэтому его нужно создать вручную. Минимальный рабочий набор:

```dotenv
# --- Flask ---
SECRET_KEY=change-me-to-a-long-random-string

# --- PostgreSQL ---
DB_USER=flask_user
DB_PASSWORD=flask_password
DB_HOST=127.0.0.1
DB_PORT=9032
DB_NAME=flask_blog

# ЕДИНСТВЕННЫЙ источник строки подключения (config.py:20)
DATABASE_URI=postgresql+psycopg2://flask_user:flask_password@127.0.0.1:9032/flask_blog

# --- Логи ---
LOG_DIR=./log
LOG_FILE=FLASK.log
```

### 2.3 Таблица переменных

| Переменная | Где читается | Обязательна | Комментарий |
|---|---|---|---|
| `SECRET_KEY` | `config.py:10` | да | сессии, CSRF (Flask-WTF). Без него формы/логин упадут |
| `DATABASE_URI` | `config.py:20` | да | полный DSN, например `postgresql+psycopg2://user:pass@host:port/db` |
| `DB_USER` | `config.py:13` | для compose | пробрасывается в `POSTGRES_USER` |
| `DB_PASSWORD` | `config.py:14` | для compose | `POSTGRES_PASSWORD` |
| `DB_HOST` | `config.py:15` | нет | сейчас в DSN не используется (строка 19 закомментирована) |
| `DB_PORT` | `config.py:16` | нет | то же |
| `DB_NAME` | `config.py:17` | для compose | `POSTGRES_DB` |
| `LOG_DIR` | `config.py:23` | **да** | если `None` — падение на старте, см. раздел 6.2 |
| `LOG_FILE` | `config.py:24` | **да** | имя файла лога, напр. `FLASK.log` |
| `PGADMIN_EMAIL` | `compose-nginx-db.yml:31` | для compose | логин pgAdmin |
| `PGADMIN_PASSWORD` | `compose-nginx-db.yml:32` | для compose | пароль pgAdmin |

`DB_USER` / `DB_PASSWORD` / `DB_NAME` / `PGADMIN_*` compose подставляет из окружения оболочки
или из `.env` рядом с compose-файлом — это **не** тот же файл, что `local.env`.

---

## 3. База данных

Схема (`flaskblog/models.py`): `User` (id, username, email, image_file, password, posts) и
`Post` (id, title, date_posted, content, user_id → user.id).

Миграций (Alembic/Flask-Migrate) в проекте нет. Таблицы создаются HTTP-роутом
`flaskblog/main/routesMain.py:30-35` через `db.create_all()`:

```
GET http://127.0.0.1:5000/createDB
```

Быстрый локальный Postgres для разработки:

```bash
docker run -d --name pg_flask_dev \
  -e POSTGRES_USER=flask_user \
  -e POSTGRES_PASSWORD=flask_password \
  -e POSTGRES_DB=flask_blog \
  -p 9032:5432 postgres:16
```

Порт `9032` выбран для совпадения с публикацией порта в `compose-nginx-db.yml:48`.

Если Postgres не нужен (быстрая проверка кода/шаблонов), подойдёт SQLite — достаточно
подменить `DATABASE_URI` в `local.env`:

```dotenv
DATABASE_URI=sqlite:////home/max/0_26_MY_pro_one/flask-blog-1/instance/blog.db
```

Каталог `instance/` уже в `.gitignore`; создать его перед первым запуском (`mkdir -p instance`).

### 3.1 Добавление статьи

Метаданные находятся в `flaskblog/new_articles/articles.yaml`. Для новой статьи нужно:

1. добавить запись с уникальным целочисленным `art_id`, автором, языком, заголовком и `file_name`;
2. положить соответствующий файл в `flaskblog/templates/content_art/`;
3. перезапустить приложение, потому что YAML загружается при импорте модуля.

Поддерживаемые форматы тела:

- `.html` — содержимое возвращается без преобразования;
- `.md` и `.markdown` — преобразуются библиотекой `markdown` с расширениями
  `fenced_code` и `tables`.

Результат выводится через `{{ art.content|safe }}`, поэтому HTML и Markdown-файлы должны
считаться доверенным содержимым репозитория.

---

## 4. Локальный запуск

Все команды — **из корня проекта** с активированным venv.

```bash
cd ~/0_26_MY_pro_one/flask-blog-1
source .venv/bin/activate
```

### Вариант A — как модуль (рекомендуется)

```bash
python -m flaskblog.run
```

`sys.path[0]` = cwd = корень проекта → `from flaskblog import create_app` резолвится.

### Вариант B — через PYTHONPATH

```bash
PYTHONPATH=. python flaskblog/run.py
```

### Вариант C — waitress напрямую

```bash
waitress-serve --host=0.0.0.0 --port=5000 flaskblog.run:app
```

### Вариант D — gunicorn

```bash
gunicorn -w 1 -b 0.0.0.0:5000 flaskblog.run:app
```

После старта: <http://127.0.0.1:5000/>, первый заход — `/createDB` для создания таблиц.

Доступные маршруты:

| Маршрут | Файл |
|---|---|
| `/`, `/home` | `flaskblog/main/routesMain.py:12-13` |
| `/about` | `flaskblog/main/routesMain.py:19` |
| `/createDB`, `/createDB/<int:post_id>` | `flaskblog/main/routesMain.py:30-32` |
| `/register`, `/login`, `/logout`, `/account` | `flaskblog/users/routesUsers.py:20,41,61,68` |
| `/art_home`, `/art/<author>/<art_id>` | `flaskblog/new_articles/routesArticles.py:11,20` |

### Как запускать НЕ надо

```bash
python flaskblog/run.py          # ModuleNotFoundError: No module named 'flaskblog'
```

Python помещает в `sys.path[0]` каталог самого скрипта (`.../flask-blog-1/flaskblog`), а не
корень проекта. Внутри `flaskblog/` нет вложенного пакета `flaskblog`, поэтому импорт
в `flaskblog/run.py:4` падает. Комментарии `run:app` в `flaskblog/run.py:14-15` устарели —
корректный таргет `flaskblog.run:app` (строки 16-17).

---

## 5. Запуск в Docker

### 5.1 Что описано в compose

`compose-nginx-db.yml` — 4 сервиса во внешней сети `app_net_new` (172.20.0.0/16):

| Сервис | Контейнер | IP | Порты хоста |
|---|---|---|---|
| `app_flask` | `app_flask` | 172.20.1.50 | — (только через nginx) |
| `nginx` | `nginx_flask` | 172.20.1.1 | `1443:443` |
| `db` | `postgresql_db_flask` | 172.20.1.2 | `9032:5432` |
| `pgadmin` | `pgadmin_flask` | 172.20.1.3 | — (через `/pgadmin`) |

Команда приложения: `gunicorn --bind 0.0.0.0:5000 flaskblog.run:app`
(`compose-nginx-db.yml:11`), рабочий каталог `/flaskblog` (`flaskblog/DockerFlask:5`),
код копируется в `/flaskblog/flaskblog` (`flaskblog/DockerFlask:11`) — то есть в контейнере
пакет тоже лежит внутри корня проекта, поэтому таргет `flaskblog.run:app` корректен.
Зависимости ставятся через `uv sync --locked --no-dev --no-install-project`
(`flaskblog/DockerFlask:8-9`) в `/flaskblog/.venv`, который добавлен в `PATH` (строка 13).

Замечания по файлу compose:

- ключ `version: "3.7"` (строка 1) для Docker Compose v2 устарел — выдаётся предупреждение,
  на работу не влияет;
- `app_flask` объявлен через `depends_on: nginx` (строки 20-21), то есть порядок старта
  обратный логике проксирования и не гарантирует готовность БД. При холодном старте
  первое обращение к БД может упасть — повторить запрос после инициализации Postgres.

### 5.2 Подготовка перед `up`

1. Внешняя сеть (объявлена `external: true`, `compose-nginx-db.yml:70-73`):

   ```bash
   ./docker_manager.sh net-create
   # эквивалент:
   # docker network create -d bridge --subnet=172.20.0.0/16 \
   #   --ip-range=172.20.0.0/16 --gateway=172.20.0.1 app_net_new
   ```

2. Env-файл контейнера `flaskblog/dock_flask.env` (`compose-nginx-db.yml:17-18`).
   Внутри контейнера БД доступна по имени/адресу сервиса, а логи пишутся в `/flaskblog/log`
   (том `./flaskblog/log_app:/flaskblog/log`, строка 16):

   ```dotenv
   SECRET_KEY=change-me
   DATABASE_URI=postgresql+psycopg2://flask_user:flask_password@172.20.1.2:5432/flask_blog
   DB_USER=flask_user
   DB_PASSWORD=flask_password
   DB_HOST=172.20.1.2
   DB_PORT=5432
   DB_NAME=flask_blog
   LOG_DIR=/flaskblog/log
   LOG_FILE=FLASK.log
   ```

   Учтите: `flaskblog/config.py` всё равно вызовет `load_dotenv` для `/flaskblog/local.env`
   (файла в образе нет — это не ошибка, `load_dotenv` молча пропускает), а реальные значения
   придут из `env_file`.

3. Переменные для самого compose (подстановка `${...}` в YAML) — положить в `.env`
   рядом с `compose-nginx-db.yml` или экспортировать в оболочке:

   ```dotenv
   DB_USER=flask_user
   DB_PASSWORD=flask_password
   DB_NAME=flask_blog
   PGADMIN_EMAIL=admin@example.com
   PGADMIN_PASSWORD=admin
   ```

4. TLS-сертификаты для nginx (`nginx/Docker-nginx:12-13`, в git не хранятся):

   ```bash
   mkdir -p nginx/cert
   openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
     -keyout nginx/cert/private_key.pem \
     -out nginx/cert/certificate.pem \
     -subj "/CN=localhost"
   ```

### 5.3 Запуск

```bash
docker compose -f compose-nginx-db.yml build
docker compose -f compose-nginx-db.yml up -d
docker compose -f compose-nginx-db.yml logs -f app_flask
```

Доступ: <https://localhost:1443/> (self-signed → предупреждение браузера),
pgAdmin: <https://localhost:1443/pgadmin>, Postgres с хоста: `127.0.0.1:9032`.

Остановка:

```bash
docker compose -f compose-nginx-db.yml down
# либо точечно:
./docker_manager.sh cont-stop
```

---

## 6. Известные проблемы и их обход

### 6.1 `ModuleNotFoundError: No module named 'flaskblog'`

Причина и решение — раздел 4. Кратко: запускать `python -m flaskblog.run` из корня проекта.

### 6.2 `TypeError: stat: path should be string ... not NoneType`

```
flaskblog/logger/config_log.py:20  ->  os.path.exists(pathDir)
```

`LOG_DIR` не задан → `Config.LOG_DIR is None` → `ConfigLogger.pathLoggerDir = None`.
Лечится строкой `LOG_DIR=./log` в `local.env` / `dock_flask.env`.

### 6.3 `RuntimeError: Either 'SQLALCHEMY_DATABASE_URI' or 'SQLALCHEMY_BINDS' must be set`

Возникает в `flaskblog/__init__.py:26` (`db.init_app(app)`), если не задан `DATABASE_URI`.
Обратите внимание: `DB_USER`/`DB_PASSWORD`/`DB_HOST`/`DB_PORT`/`DB_NAME` **сами по себе
не собирают DSN** — строка сборки закомментирована в `flaskblog/config.py:19`, используется
только `DATABASE_URI` (строка 20).

### 6.4 `LOG_DIR` не может быть вложенным путём

`ConfigLogger.__createLogDir` (`flaskblog/logger/config_log.py:18-21`) использует `os.mkdir`,
который не создаёт промежуточные каталоги. Значения вида `./log_app/flask` упадут с
`FileNotFoundError`. Варианты: использовать одноуровневый путь либо заменить на
`os.makedirs(pathDir, exist_ok=True)`.

### 6.5 Относительный `LOG_DIR` зависит от cwd

`LOG_DIR=./log` разворачивается относительно рабочего каталога процесса, а не пакета.
При запуске из корня логи окажутся в `flask-blog-1/log`, а не в `flaskblog/log`.
Для предсказуемости лучше абсолютный путь (в контейнере — `/flaskblog/log`).

### 6.6 Порядок импортов в `__init__.py`

`flaskblog/__init__.py:6-7` инициализирует логгер до объявления `db`/`bcrypt`, поэтому
ошибки конфигурации логирования всегда проявляются как падение импорта пакета,
а не как ошибка внутри `create_app()`.

### 6.7 Нет миграций

`db.create_all()` вызывается только из `/createDB` и не изменяет уже существующие таблицы.
При правках `models.py` нужно либо пересоздавать таблицы вручную, либо подключать
Flask-Migrate.

### 6.8 `debug_mode=True` в точке входа

`flaskblog/run.py:6` включает Flask-debug безусловно. Для production вынести флаг
в переменную окружения либо использовать отдельный WSGI-модуль.

---

## 7. Проверка работоспособности

```bash
# 1) импорт пакета и конфиг (не поднимая сервер)
python -c "from flaskblog import create_app; app = create_app(); print(app.url_map)"

# 2) доступность БД
python -c "
from flaskblog import create_app, db
app = create_app()
with app.app_context():
    db.create_all(); print('DB OK:', app.config['SQLALCHEMY_DATABASE_URI'])
"

# 3) сервер (блокирующая команда)
python -m flaskblog.run

# 4) в другом терминале
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:5000/
```

Ожидаемый результат п.1 — список из 13 правил (`/`, `/home`, `/about`, `/createDB`,
`/createDB/`, `/createDB/<int:post_id>`, `/register`, `/login`, `/logout`, `/account`,
`/art_home`, `/art/<string:author>/<int:art_id>`, `/static/<path:filename>`),
п.4 — HTTP `200`.

---

## 8. Линтеры и формат кода

Настройки в `pyproject.toml`: `line-length = 120`, ruff игнорирует `F401`, `E402`, `F541`.

```bash
uv run ruff check .
uv run ruff format .     # либо: uv run black .
```

Инструменты в основные зависимости не входят — устанавливать отдельно
(`uv tool install ruff`, `uv tool install black`) или добавить в dev-группу.
