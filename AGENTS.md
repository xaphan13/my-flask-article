# AGENTS.md — flask-blog-1

Instructional context for AI coding agents working in this repository.
Harness-agnostic; `QWEN.md` is the Qwen Code copy of the same guidance — **keep both in sync.**

🇷🇺 Русская версия: [AGENTS.ru.md](AGENTS.ru.md)
User-facing docs: [README.md](README.md) · Setup report: [`docs/setup-and-run.md`](docs/setup-and-run.md)

## Project overview

A server-rendered blog / article site built on **Flask 3.1** using the application-factory
pattern. It combines two content models:

1. **Database-backed users & posts** — `User` / `Post` via Flask-SQLAlchemy on PostgreSQL,
   with registration, login, and profile-picture upload.
2. **File-backed articles** — technical articles stored as static Jinja HTML files in
   `flaskblog/templates/content_art/`, described by Pydantic models in
   `flaskblog/new_articles/schema_art.py`. This is the site's actual landing content
   (`/` redirects to `/art_home`).

**Stack**

| Concern | Choice |
|---|---|
| Language | Python 3.12 (`.python-version`) |
| Package manager | `uv` (`uv.lock` is authoritative) |
| Web framework | Flask 3.1.2 + Blueprints |
| ORM | Flask-SQLAlchemy 3.1.1 → PostgreSQL (`psycopg2-binary`) |
| Auth | Flask-Login + Flask-Bcrypt |
| Forms | Flask-WTF / WTForms (+ `email-validator`) |
| Validation/schemas | Pydantic 2.12 |
| WSGI server | `waitress` locally, `gunicorn` in Docker |
| Reverse proxy | nginx with TLS (Docker only) |
| Images | Pillow (profile-picture thumbnails) |
| Logging | custom `ConfigLogger` wrapper over `logging.config.dictConfig` |

**No test suite and no migration framework exist in this project.**

### Architecture

`flaskblog/__init__.py` exposes `create_app(config_class=Config, debug_mode=False)`. It
instantiates extensions at module level (`db`, `bcrypt`, `login_manager`), then binds them
inside the factory and registers four blueprints:

| Blueprint | Module | Routes |
|---|---|---|
| `art_main` | `new_articles/routesArticles.py` | `/art_home`, `/art/<author>/<art_id>` |
| `main` | `main/routesMain.py` | `/`, `/home`, `/about`, `/createDB[/<post_id>]` |
| `users` | `users/routesUsers.py` | `/register`, `/login`, `/logout`, `/account` |
| `errors` | `errors/handlers.py` | app-wide 403 / 404 / 500 handlers |

```
flask-blog-1/                   <- project root; ALWAYS the cwd for running anything
├── pyproject.toml              deps + ruff/black config
├── uv.lock
├── local.env                   local env vars — NOT in git, create manually
├── compose-nginx-db.yml        app_flask + nginx + db + pgadmin
├── docker_manager.sh           net-create | cont-stop helpers
├── git_manager.sh              br | st | brst | commit helpers
├── docs/setup-and-run.md       detailed setup report (Russian) — read this first
├── nginx/                      Docker-nginx, nginx.conf, cert/ (certs not in git)
└── flaskblog/                  application package
    ├── __init__.py             create_app(), db, bcrypt, login_manager
    ├── run.py                  entry point: app = create_app(debug_mode=True)
    ├── config.py               Config class; load_dotenv(<root>/local.env)
    ├── models.py               User, Post
    ├── DockerFlask             application Dockerfile
    ├── dock_flask.env          container env — NOT in git, create manually
    ├── logger/config_log.py    ConfigLogger + dictConfig
    ├── main/ users/ new_articles/ errors/   blueprints
    ├── templates/ static/
    └── log/                    log output (cwd-relative, see Gotchas)
```

## Building and running

`docs/setup-and-run.md` is the authoritative, verified reference — consult it for env-var
tables, Docker preparation steps, and troubleshooting. Summary below.

### Setup

```bash
cd ~/0_26_MY_pro_one/flask-blog-1
uv sync                      # creates .venv from uv.lock
source .venv/bin/activate
```

Then create `local.env` at the project root (it is gitignored). Required keys:

```dotenv
SECRET_KEY=<long-random-string>
DATABASE_URI=postgresql+psycopg2://flask_user:flask_password@127.0.0.1:9032/flask_blog
LOG_DIR=./log
LOG_FILE=FLASK.log
```

`DB_USER` / `DB_PASSWORD` / `DB_NAME` are consumed by **docker compose**, not by the DSN.

### Run locally

```bash
python -m flaskblog.run                                        # preferred
PYTHONPATH=. python flaskblog/run.py                           # equivalent
waitress-serve --host=0.0.0.0 --port=5000 flaskblog.run:app    # WSGI target
gunicorn -w 1 -b 0.0.0.0:5000 flaskblog.run:app
```

Then hit `http://127.0.0.1:5000/createDB` once to create tables.

**Never run `python flaskblog/run.py`** — Python puts `flaskblog/` (not the project root) on
`sys.path[0]`, so `from flaskblog import create_app` raises `ModuleNotFoundError`. The
project is not installed as a package (there is no `[build-system]` in `pyproject.toml`),
so imports only resolve when the project root is on `sys.path`.

### Run in Docker

```bash
./docker_manager.sh net-create                       # external net app_net_new, 172.20.0.0/16
docker compose -f compose-nginx-db.yml build
docker compose -f compose-nginx-db.yml up -d
docker compose -f compose-nginx-db.yml logs -f app_flask
./docker_manager.sh cont-stop                        # stop all four containers
```

Requires `flaskblog/dock_flask.env`, a `.env` beside the compose file, and self-signed certs
in `nginx/cert/` — all gitignored; see `docs/setup-and-run.md` §5.2. Serves on
<https://localhost:1443/>; pgAdmin at `/pgadmin`; Postgres exposed on `127.0.0.1:9032`.

### Lint and format

```bash
uv run ruff check .
uv run ruff format .     # or: uv run black .
```

Ruff and black are **not** declared dependencies — install them as tools
(`uv tool install ruff`) or add a dev group.

### Verification

There is no test suite, so verify changes by exercising the app:

```bash
python -c "from flaskblog import create_app; print(len(list(create_app().url_map.iter_rules())))"   # expect 13
python -m flaskblog.run                                                                            # then curl /
```

13 rules = 12 application routes + Flask's own `static`.

Do not claim a change is verified without actually running something. If you cannot verify,
say so explicitly.

## Development conventions

### Code style

- Line length **120**, 4-space indent (`pyproject.toml` configures both ruff and black).
- Ruff intentionally ignores `F401` (unused imports), `E402` (imports not at top), and
  `F541` (f-string without placeholders). These are load-bearing exemptions — the codebase
  deliberately imports the logger before other imports, and re-exports names.
- Heavy decorative comment banners (`# ====`, `# ----`, `#***`) separate logical sections.
  Match the local style when editing a file; do not strip them.
- Russian is used for UI strings, flash messages, docstrings, and article content. Keep new
  user-facing text and comments consistent with the surrounding file's language.

### Blueprint module pattern

Every route module follows the same opening sequence — preserve it:

```python
from flask import render_template, Blueprint
from flaskblog.logger.config_log import ConfigLogger
logFC = ConfigLogger.getLogger("FileStdout", "ClientHTTPS")   # import-order exemption (E402)
from flaskblog import db
```

Logger names come from `logging_config["loggers"]` in `logger/config_log.py`:
`"Stdout"` (console), `"OnlyFile"` (file), `"FileStdout"` (both). Route handlers log with
`logFC.info(...)`. Blueprint objects are module-level and named after the blueprint
(`main`, `users`, `errors`, `art_main`); cross-blueprint redirects use the endpoint form
`url_for('art_main.art_home')`.

### Templates

Two independent layout hierarchies — pick the right parent:

- `layout.html` — auth/informational pages (`about`, `login`, `register`, `account`,
  `errors/*`). Includes `includes/_flash_msg.html`, so flash messages only render here.
- `new_art/art_base.html` — article pages (`art_home`, `art_author`), with a sidebar and its
  own `new_art/includes/_art_*.html` partials. Does **not** render flash messages.

Both share the footer macro `includes/_footer_macro.html::footer_new(current_user)`.
Article bodies live in `templates/content_art/artN.html` and are read at request time by
`read_html()`, then injected via `art.content`. Static assets are under
`static/art_css/` (`base.css`, `light-theme.css`, `dark-theme.css`, `scripts.js`) and
`static/profile_pics/`.

### Data model & schemas

- SQLAlchemy models use the classic `db.Column` declarative style (not 2.0
  `Mapped[]`/`mapped_column`). `User.__init__` is overridden with keyword defaults.
- `ArticleLang` fields: `author`, `lang`, `art_id: int`, `title`, `file_name`, `content`.
- Article metadata is stored in `new_articles/articles.yaml`; adding an article means adding a record there and creating the matching `.html`, `.md`, or `.markdown` file in `templates/content_art/`. `art_dict_file` is loaded from YAML and keyed by `art_id`, which is what `/art/<author>/<art_id>` looks up.
- `schema_art.py` also contains the old `articles` / `articles_dict` pair with inline content from `arts_content.py`. Routes use the new file-backed dictionary; leave the old pair alone unless asked.

## Gotchas — verify against these before debugging

### Configuration and startup

- **`DATABASE_URI` is the only DSN source.** The `f"postgresql+psycopg2://..."` assembly
  from `DB_*` parts is commented out in `config.py`. Setting `DB_HOST`/`DB_PORT` alone does
  nothing; a missing `DATABASE_URI` fails at `db.init_app(app)`.
- **`LOG_DIR` is mandatory.** If unset, `Config.LOG_DIR is None` and
  `os.path.exists(None)` raises `TypeError` at *import* of `flaskblog`, not inside
  `create_app()` — because the logger is initialised before `db`/`bcrypt` are declared.
- **`LOG_DIR` must be a single level.** `ConfigLogger.__createLogDir` uses `os.mkdir`, not
  `os.makedirs`, so nested paths like `./log_app/flask` raise `FileNotFoundError`.
- **`run.py` hardcodes `debug_mode=True`**, which the Docker `gunicorn` command also picks
  up. Treat this as a known production concern.

### Working directory

- **Two cwd-relative behaviours.** A relative `LOG_DIR` resolves against the process cwd,
  and `schema_art.get_path_dir()` builds the article path from `os.getcwd()` +
  `flaskblog/templates/content_art`. Running from anywhere but the project root breaks
  article loading. Prefer absolute paths in containers (`/flaskblog/log`).
- **The article directory is frozen at import time.** `read_html(name_html, name_dir=get_path_dir())`
  evaluates its default argument once, when the module is imported — so `chdir` after import
  will not change where articles are read from. Pass `name_dir` explicitly to override.

### Articles

- **`author` in `/art/<author>/<art_id>` is decorative.** `art_author` looks the article up
  by `art_id` alone, so any author string returns the same article.
- **An unknown `art_id` raises `KeyError`** from `art_dict_file[art_id]`, surfacing as a 500
  rather than a 404.
- **`art.content = content` mutates the module-level `ArticleLang` instance** shared by all
  requests. It is re-read from disk on every request, so it is currently harmless — but do
  not add state to these objects assuming per-request isolation.

### Database

- **No migrations.** `db.create_all()` runs only from the `/createDB` route and will not
  alter existing tables. Changing `models.py` requires manual recreation or adding
  Flask-Migrate.
- **`/createDB` is unauthenticated** — any visitor can trigger `db.create_all()`.

### Deprecated APIs still in use

Do not "fix" these unless asked, but be aware they emit warnings:

- `art_home` calls `x.dict(...)` — the Pydantic v1 API, deprecated in Pydantic 2.12
  (`model_dump()` is the replacement).
- `models.py` uses `datetime.utcnow` as a column default — deprecated in Python 3.12.
- `load_user` uses `User.query.get()` — the legacy SQLAlchemy query API.

### Docker

- **Compose quirks:** `version: "3.7"` is deprecated under Compose v2, and `app_flask`
  declares `depends_on: nginx` rather than `db` — so the first DB call after a cold start
  may fail and need a retry.
- `nginx.conf` hardcodes `server_name xaphan.ru` and certificate paths under `/home/cert/`.
- `DockerFlask` runs `uv sync --locked --no-dev --no-install-project`, so `uv.lock` must be
  committed and current or the build fails.

## Git

Branch at time of writing: `alphaFlask`. Commit subjects are short and lowercase
(`new 26 start`, `restore theme`, `added psycopg2`). Match that terseness. Note that
`log/`, `instance/`, `pg_db/`, `*.env`, `.idea/`, and the nginx certs are gitignored —
never add them. Stage only files relevant to the change; several files are currently
modified in the working tree. `git_manager.sh` wraps the common commands
(`br`, `st`, `brst`, `commit`, `push_two`).
