# flask-blog-1

A server-rendered blog / technical-article site built on **Flask 3.1** using the
application-factory pattern.

🇷🇺 Русская версия: [README.ru.md](README.ru.md)

The site deliberately combines **two independent content models**:

1. **File-backed articles** — technical articles stored as static Jinja HTML files in
   `flaskblog/templates/content_art/`, described by Pydantic models in
   `flaskblog/new_articles/schema_art.py`. This is the site's actual landing content:
   `/` redirects to `/art_home`.
2. **Database-backed users & posts** — `User` / `Post` via Flask-SQLAlchemy on PostgreSQL,
   with registration, login and profile-picture upload.

> The UI language, flash messages and article content are in **Russian**.

## Features

- Article index and per-article pages rendered from static HTML fragments (4 articles ship
  with the repo: Python and Rust topics).
- User registration / login / logout on Flask-Login + Flask-Bcrypt password hashing.
- Account page with avatar upload, thumbnailed by Pillow into `static/profile_pics/`.
- Light / dark theme switching via `static/art_css/` + `scripts.js`.
- Custom `ConfigLogger` wrapper over `logging.config.dictConfig` with console / file /
  combined logger presets.
- App-wide 403 / 404 / 500 error handlers.
- Full Docker deployment: gunicorn behind nginx with TLS, PostgreSQL 16 and pgAdmin.

## Stack

| Concern | Choice |
|---|---|
| Language | Python 3.12 (`.python-version`) |
| Package manager | `uv` (`uv.lock` is authoritative) |
| Web framework | Flask 3.1.2 + Blueprints |
| ORM | Flask-SQLAlchemy 3.1.1 → PostgreSQL (`psycopg2-binary`) |
| Auth | Flask-Login + Flask-Bcrypt |
| Forms | Flask-WTF / WTForms (+ `email-validator`) |
| Validation / schemas | Pydantic 2.12 |
| WSGI server | `waitress` locally, `gunicorn` in Docker |
| Reverse proxy | nginx with TLS (Docker only) |
| Images | Pillow |

## Requirements

- Python 3.12+
- [`uv`](https://docs.astral.sh/uv/)
- PostgreSQL — either your own instance, or the one from the Docker compose stack
- For the Docker path: Docker + Compose v2

## Quick start (local)

```bash
cd flask-blog-1
uv sync                      # creates .venv from uv.lock
source .venv/bin/activate
```

Create `local.env` in the project root (the file is gitignored):

```dotenv
SECRET_KEY=<long-random-string>
DATABASE_URI=postgresql+psycopg2://flask_user:flask_password@127.0.0.1:9032/flask_blog
LOG_DIR=./log
LOG_FILE=FLASK.log
```

Run the app:

```bash
python -m flaskblog.run                                        # preferred
waitress-serve --host=0.0.0.0 --port=5000 flaskblog.run:app    # WSGI target
gunicorn -w 1 -b 0.0.0.0:5000 flaskblog.run:app
```

Then open <http://127.0.0.1:5000/createDB> **once** to create the database tables, and
<http://127.0.0.1:5000/> for the site.

> ⚠️ **Always run from the project root, and never as `python flaskblog/run.py`.**
> Python would put `flaskblog/` on `sys.path[0]` instead of the project root, so
> `from flaskblog import create_app` fails with `ModuleNotFoundError`. The project is not
> installed as a package (there is no `[build-system]` in `pyproject.toml`). Article
> loading is also resolved relative to the current working directory.

## Configuration

All configuration is read from environment variables into `flaskblog/config.py`, which
loads `<project-root>/local.env` via `python-dotenv`.

| Variable | Consumed by | Required | Notes |
|---|---|---|---|
| `SECRET_KEY` | Flask sessions, CSRF | yes | any long random string |
| `DATABASE_URI` | SQLAlchemy | yes | the **only** source of the DSN |
| `LOG_DIR` | `ConfigLogger` | yes | must be a **single** level, e.g. `./log` |
| `LOG_FILE` | `ConfigLogger` | yes | e.g. `FLASK.log` |
| `DB_USER`, `DB_PASSWORD`, `DB_NAME` | docker compose → postgres | Docker only | not part of the DSN |
| `PGADMIN_EMAIL`, `PGADMIN_PASSWORD` | docker compose → pgadmin | Docker only | |

`DB_HOST` / `DB_PORT` are still read into `Config`, but the DSN assembly that used them is
commented out — setting them alone has no effect.

## Routes

13 URL rules are registered (12 application routes plus Flask's `static`):

| Methods | Route | Endpoint | Purpose |
|---|---|---|---|
| GET | `/`, `/home` | `main.home` | redirects to `/art_home` |
| GET | `/art_home` | `art_main.art_home` | article index — the landing page |
| GET | `/art/<author>/<art_id>` | `art_main.art_author` | a single article |
| GET | `/about` | `main.about` | about page (also demos all flash categories) |
| GET | `/createDB`, `/createDB/`, `/createDB/<post_id>` | `main.createDB` | runs `db.create_all()` |
| GET, POST | `/register` | `users.register` | registration |
| GET, POST | `/login` | `users.login` | login |
| GET | `/logout` | `users.logout` | logout |
| GET, POST | `/account` | `users.account` | profile and avatar upload |

Blueprints: `art_main`, `main`, `users`, `errors` — all registered in
`create_app()` in `flaskblog/__init__.py`.

## Run in Docker

```bash
./docker_manager.sh net-create                       # external net app_net_new, 172.20.0.0/16
docker compose -f compose-nginx-db.yml build
docker compose -f compose-nginx-db.yml up -d
docker compose -f compose-nginx-db.yml logs -f app_flask
./docker_manager.sh cont-stop                        # stop all four containers
```

Before the first build you must create three gitignored things (see
[`docs/setup-and-run.md`](docs/setup-and-run.md) §5.2):

- `flaskblog/dock_flask.env` — container environment
- `.env` next to the compose file — `DB_*` and `PGADMIN_*` values
- self-signed certificates in `nginx/cert/` (`certificate.pem`, `private_key.pem`)

| Service | Container | Reachable at |
|---|---|---|
| nginx (TLS) | `nginx_flask` | <https://localhost:1443/> |
| Flask + gunicorn | `app_flask` | internal only, `172.20.1.50:5000` |
| PostgreSQL 16 | `postgresql_db_flask` | `127.0.0.1:9032` |
| pgAdmin | `pgadmin_flask` | <https://localhost:1443/pgadmin> |

Container logs are bind-mounted to `flaskblog/log_app/`, and database files to `pg_db/`.
In containers prefer an absolute `LOG_DIR` such as `/flaskblog/log`.

## Project structure

```
flask-blog-1/                   <- project root; always the cwd for running anything
├── pyproject.toml              dependencies + ruff/black config
├── uv.lock
├── local.env                   local env vars — NOT in git, create manually
├── compose-nginx-db.yml        app_flask + nginx + db + pgadmin
├── docker_manager.sh           net-create | cont-stop helpers
├── git_manager.sh              br | st | brst | commit helpers
├── docs/setup-and-run.md       detailed setup + troubleshooting report (Russian)
├── nginx/                      Docker-nginx, nginx.conf, cert/ (certs not in git)
└── flaskblog/                  application package
    ├── __init__.py             create_app(), db, bcrypt, login_manager
    ├── run.py                  entry point: app = create_app(debug_mode=True)
    ├── config.py               Config class; load_dotenv(<root>/local.env)
    ├── models.py               User, Post
    ├── DockerFlask             application Dockerfile
    ├── logger/config_log.py    ConfigLogger + dictConfig
    ├── main/ users/ new_articles/ errors/   blueprints
    ├── templates/ static/
    └── log/                    log output (cwd-relative)
```

## Data model

```python
User(id, username, email, image_file, password) -> posts
Post(id, title, date_posted, content, user_id)
```

Articles are Pydantic `ArticleLang` models with the fields
`author`, `lang`, `art_id`, `title`, `file_name`, `content`.

**To add an article:**

1. Create `flaskblog/templates/content_art/<file>.html` with the article body.
2. Append an `ArticleLang(...)` entry to `art_files` in
   `flaskblog/new_articles/schema_art.py`.

`art_dict_file` is keyed by `art_id`, which is what `/art/<author>/<art_id>` looks up; the
body is read from disk at request time by `read_html()`.

## Lint and format

```bash
uv run ruff check .
uv run ruff format .     # or: uv run black .
```

Line length is 120. Ruff intentionally ignores `F401` (unused imports), `E402` (imports not
at top of file) and `F541` (f-string without placeholders) — the codebase deliberately
initialises the logger before other imports and re-exports names.

Ruff and black are **not** declared dependencies; install them as tools
(`uv tool install ruff`) or add a dev group.

## Verifying a change

There is no test suite, so changes are verified by exercising the app:

```bash
python -c "from flaskblog import create_app; print(len(list(create_app().url_map.iter_rules())))"   # 13
python -m flaskblog.run                                                                            # then curl /
```

## Known limitations

- **No test suite** and **no migration framework.** `db.create_all()` runs only from the
  `/createDB` route and will not alter existing tables — changing `models.py` requires
  recreating them manually or adding Flask-Migrate.
- **`run.py` hardcodes `debug_mode=True`**, and the Docker `gunicorn` command inherits it.
  This is a production concern, not an intended setting.
- **`/createDB` is unauthenticated** — any visitor can trigger `db.create_all()`.
- `compose-nginx-db.yml` still declares the obsolete `version: "3.7"` key, and `app_flask`
  has `depends_on: nginx` rather than `db`, so the first database call after a cold start
  may fail and need a retry.
- `nginx.conf` hardcodes `server_name xaphan.ru` and the certificate paths.

## Documentation

Everything under `docs/` is written in **Russian**. The numbered series 01–07 is meant to be
read in order; `setup-and-run.md` is the operational companion.

| Document | Contents |
|---|---|
| [`docs/01_project_structure.md`](docs/01_project_structure.md) | project map, file tree, external dependencies and their role, environment invariants, metrics |
| [`docs/02_architecture.md`](docs/02_architecture.md) | high-level architecture, design patterns in use, data flow, state / caching / configuration, deployment |
| [`docs/03_execution_flow.md`](docs/03_execution_flow.md) | application lifecycle, routes and request handling, key processes step by step, error handling, logging |
| [`docs/04_code_quality.md`](docs/04_code_quality.md) | quality assessment, readability and cohesion, testability as the main debt, defects by severity |
| [`docs/05_optimization_roadmap.md`](docs/05_optimization_roadmap.md) | proposed work order, architectural improvements, performance, refactoring queue, DX, priority table |
| [`docs/06_graph_index.md`](docs/06_graph_index.md) | the codebase graph index (coverage caveats, ready-made queries) and architecture as measured: coupling, cohesion, hotspots, complexity |
| [`docs/07_permissions.md`](docs/07_permissions.md) | Claude Code permissions: auto mode and its safety classifier, why it fails here, allow rules, diagnostics |
| [`docs/setup-and-run.md`](docs/setup-and-run.md) | the authoritative, verified setup and troubleshooting report, with full environment-variable tables |
| [`AGENTS.md`](AGENTS.md) / [`AGENTS.ru.md`](AGENTS.ru.md) | conventions and gotchas for AI coding agents |

> ⚠️ 01–05 and `setup-and-run.md` were written against an earlier commit. Where the working
> tree has since diverged — the DSN assembly in `config.py`, and env files actually being
> tracked by git — the verified deltas are recorded in
> [`docs/06_graph_index.md`](docs/06_graph_index.md) §4. Read that section before trusting the
> environment-variable tables here or in `setup-and-run.md`.
