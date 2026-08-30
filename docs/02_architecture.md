# 02 — Архитектура и паттерны

> Актуально для ветки `new-frontend`, HEAD `b12f62c` (актуализировано 2026-08-31). Карта файлов: [01_project_structure.md](01_project_structure.md).
> Пошаговая логика выполнения: [03_execution_flow.md](03_execution_flow.md).

## 1. Высокоуровневая архитектура

**Тип: монолит, server-side rendering, модульная организация через блюпринты Flask.**
Один WSGI-процесс, синхронная обработка, без внутренних сетевых вызовов между компонентами.
Клиенту отдаётся готовый HTML; JSON-API нет ни одного маршрута.

Слоистость выражена частично и не является строгой:

```
    HTTP/TLS
        │
   ┌────▼──────────────────────────────────────────────┐
   │ nginx  (только в Docker)                          │  nginx/nginx.conf
   │ TLS-терминация :443, reverse proxy, /pgadmin      │
   └────┬──────────────────────────────────────────────┘
        │ HTTP → 172.20.1.50:5000
   ┌────▼──────────────────────────────────────────────┐
   │ WSGI-сервер: gunicorn (Docker) | waitress (local) │  flaskblog/run.py
   │ + paste TransLogger (access-лог, только waitress) │
   └────┬──────────────────────────────────────────────┘
        │
   ┌────▼──────────────────────────────────────────────┐
   │ Flask-приложение (объект собран create_app())     │  flaskblog/__init__.py
   │                                                   │
   │  ┌── ПРЕЗЕНТАЦИЯ ─────────────────────────────┐   │
   │  │ Jinja: 2 независимые иерархии наследования │   │  flaskblog/templates/
   │  └────────────────────────────────────────────┘   │
   │  ┌── МАРШРУТЫ / КОНТРОЛЛЕРЫ ──────────────────┐   │
   │  │ art_main | main | users | errors           │   │  flaskblog/*/routes*.py
   │  └────────────────────────────────────────────┘   │
   │  ┌── ВАЛИДАЦИЯ ───────────────────────────────┐   │
   │  │ WTForms (HTML-формы) │ Pydantic (статьи)   │   │  forms_users.py / schema_art.py
   │  └────────────────────────────────────────────┘   │
   │  ┌── ДОСТУП К ДАННЫМ ─────────────────────────┐   │
   │  │ ORM-модели  │  чтение файлов статей        │   │  models.py / schema_art.py
   │  └────────────────────────────────────────────┘   │
   │                                                   │
   │  ПОПЕРЕЧНЫЕ: ConfigLogger, Config, Flask-Login    │
   └────┬──────────────────────────────────────────────┘
        │ psycopg2
   ┌────▼──────────────┐        ┌──────────────────────┐
   │ PostgreSQL 16     │        │ Файлы статей на диске│
   │ таблицы user/post │        │ templates/content_art│
   └───────────────────┘        └──────────────────────┘
```

**Ключевая архитектурная особенность:** сервисный слой отсутствует. Бизнес-логика живёт
непосредственно в обработчиках маршрутов, которые напрямую обращаются и к `db.session`,
и к файловой системе. Для текущего небольшого объёма проекта это осознанно приемлемо, но именно это
блокирует юнит-тестирование (см. [04](04_code_quality.md) §3).

> **О СУБД в этом документе.** Далее PostgreSQL упоминается как целевая конфигурация
> (сервис `db` в `compose-nginx-db.yml`, `psycopg2-binary` в зависимостях). Фактическое
> локальное окружение на момент проверки работает на SQLite: `local.env` задаёт
> `DATABASE_URI=sqlite:///site.db`. Код от диалекта не зависит — переключение выполняется
> одной переменной. Подробнее: [01](01_project_structure.md) §3.0.

### 1.1 Два независимых контура данных

Это главное, что нужно понять о системе: контуры не пересекаются нигде.

| | Контур статей (основной) | Контур пользователей |
|---|---|---|
| Источник данных | `articles.yaml` + файлы `.html`/`.md`/`.markdown` | PostgreSQL |
| Точки входа | `/art_home`, `/art/<author>/<art_id>` | `/register`, `/login`, `/logout`, `/account` |
| Модель | Pydantic `ArticleLang` | SQLAlchemy `User`, `Post` |
| База шаблонов | `layout.html` (единая для всего сайта) | `layout.html` |
| Нужна ли БД | нет | да |
| Влияние авторизации | только вид шапки | доступ к `/account` |

Модель `Post` — мост, который так и не был построен: она объявлена, связана с `User` через
`db.relationship`, но ни один маршрут её не читает и не пишет.

## 2. Применённые паттерны проектирования

### 2.1 Application Factory + отложенная инициализация расширений

Канонический для Flask паттерн, реализован корректно. `flaskblog/__init__.py`:

```python
db = SQLAlchemy()  # 1. синглтоны создаются на уровне модуля, без app
bcrypt = Bcrypt()
login_manager = LoginManager()


def create_app(config_class=Config, debug_mode=False):
    app = Flask(__name__)
    app.config.from_object(config_class)  # 2. конфиг из класса
    app.config["DEBUG"] = debug_mode
    db.init_app(app)  # 3. привязка расширений к экземпляру
    ...
    from flaskblog.new_articles.routes_articles import art_main  # 4. импорт внутри

    app.register_blueprint(art_main)  # фабрики
```

Что этот паттерн даёт здесь:

- **Разрыв циклического импорта.** `flaskblog/models.py` импортирует `db` из `flaskblog`,
  а `flaskblog` регистрирует блюпринты, которые импортируют `models`. Импорты внутри тела
  функции (шаг 4) — единственная причина, по которой цикл не возникает. Переносить эти
  импорты на верхний уровень модуля нельзя.
- **Возможность нескольких конфигураций.** Сигнатура `create_app(config_class=Config)`
  уже готова для тестового конфига, но эта возможность не задействована — тестов нет.

### 2.2 Blueprint как модуль (вертикальная нарезка)

Четыре блюпринта, каждый объявлен на уровне своего модуля и назван так же, как переменная:

| Блюпринт | Модуль | Ответственность |
|---|---|---|
| `art_main` | `../flaskblog/new_articles/routes_articles.py` | публикация статей |
| `main` | `../flaskblog/main/routes_main.py` | навигация, `/about`, создание схемы БД |
| `users` | `../flaskblog/users/routes_users.py` | аутентификация и профиль |
| `errors` | `flaskblog/errors/handlers.py` | app-wide обработчики HTTP-ошибок |

Нарезка вертикальная: `users/` содержит и маршруты, и формы. Связи между блюпринтами —
только через endpoint-имена в `url_for('art_main.art_home')`; прямых импортов между
маршрутными модулями нет. Порядок регистрации в `create_app()` (`art_main` первым)
на разрешение URL не влияет — пересечений правил нет.

Обработчики ошибок используют `@errors.app_errorhandler`, а не `@errors.errorhandler`:
регистрация глобальная, действует для всего приложения, а блюпринт служит лишь контейнером.

### 2.3 Конфигурация через класс + внешний `.env`

`flaskblog/config.py` — плоский класс с атрибутами уровня класса, читающий `os.environ`
**в момент импорта**:

```python
env_path: Path = Path(__file__).resolve().parent.parent / "local.env"
load_dotenv(env_path)


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URI")
    LOG_DIR = os.environ.get("LOG_DIR")
    ...
```

Следствия, которые нужно учитывать:

- Путь к `local.env` вычисляется от `__file__`, а не от cwd — это единственная
  cwd-независимая часть конфигурации.
- Значения фиксируются один раз при импорте. Подмена `os.environ` после импорта
  `flaskblog.config` не действует; тестовый конфиг придётся передавать через
  `config_class`, а не через окружение.
- Иерархии конфигов (`DevConfig` / `ProdConfig` / `TestConfig`) нет — один класс на все среды,
  а режим отладки прокидывается отдельным аргументом `debug_mode`.

### 2.4 Singleton через статический класс — `ConfigLogger`

`flaskblog/logger/config_log.py` реализует одноразовую инициализацию логирования вручную,
через классовый флаг вместо метакласса или модульной функции:

```python
class ConfigLogger:
    isSetting = False  # защита от повторной настройки

    @staticmethod
    def settingLogger():
        if not ConfigLogger.isSetting:
            ConfigLogger.__createLogDir(pathDir=ConfigLogger.pathLoggerDir)
            logging.config.dictConfig(logging_config)
            ConfigLogger.isSetting = True

    @staticmethod
    @dispatch(str, str)  # multipledispatch: перегрузка по числу аргументов
    def getLogger(nameBase, nameMod):
        if not ConfigLogger.isSetting:
            ConfigLogger.settingLogger()
        return logging.getLogger(nameBase + "." + nameMod)
```

Использование `multipledispatch` для перегрузки по арности — избыточно: то же достигается
значением по умолчанию. Флаг `isSetting` не потокобезопасен, но фактически безопасен,
поскольку первый вызов происходит на этапе импорта, до появления рабочих потоков.

### 2.5 Ленивое чтение шаблонов статей вместо репозитория

Роль репозитория для статей играет пара «реестр в памяти + функция чтения файла»:

```python
def get_articles() -> list[ArticleLang]:
    # mtime/size-кэш: перечитывает articles.yaml при изменении файла

def get_art(art_id: int) -> ArticleLang | None:
    # поиск записи по art_id

def read_html(name_html: str, name_dir: str = get_path_dir()) -> str: ...
def render_article(name_file: str, name_dir: str = get_path_dir()) -> str: ...
```

Индекс (метаданные) валидируется через `ArticleLang` при первом обращении и
перечитывается с диска при изменении `mtime`/`size` файла — перезапуск процесса не нужен
(задание 002; до этого реестр загружался при импорте и жил до перезапуска). Тело статьи
читается с диска на каждый запрос. `render_article()` возвращает HTML-файл без
изменений, а для `.md`/`.markdown` вызывает `markdown(..., extensions=["fenced_code",
"tables"])`. Абстракции репозитория нет — обработчик сам вызывает `render_article()`.
Запись реестра — `save_articles()`: атомарная замена `articles.yaml` через временный
файл; вызывается POST-формами `/art_manage`.

**Бывшее опасное место — устранено (задание 002).** Раньше обработчик мутировал общий
объект (`art.content = content` на модуль-level экземпляре `ArticleLang`); теперь в
шаблон уходит `art.model_copy(update={"content": content})`, и объекты реестра
остаются неизменяемыми.

### 2.6 Шаблонное наследование и макросы

Композиция представления построена на трёх механизмах Jinja:

- `{% extends %}` — **одна** база `layout.html` для всех страниц, включая статьи
  (вторая база `new_art/art_base.html` и её партиалы `_art_*.html` удалены при
  миграции на Bootstrap 5, задание 003).
- `{% include %}` — переиспользование `<head>`, шапки, сайдбара, flash-партиала
  и подключения скриптов; селектор тем hljs включается внутри `_header.html`.
- `{% macro %}` — два макроса: `includes/_footer_macro.html::footer_new(current_user)`
  и `includes/_form_macro.html::field_with_errors/file_field` (дедупликация форм,
  задание 003).

Следствие единой базы: `includes/_flash_msg.html` подключён в `layout.html`, поэтому
`flash()` виден на любой странице сайта, включая статьи.

### 2.7 Валидация: два несвязанных механизма

| Механизм | Где | Что валидирует | Поведение при ошибке |
|---|---|---|---|
| WTForms | `../flaskblog/users/forms_users.py` | пользовательский ввод форм: обязательность, длина, формат e-mail, совпадение паролей, уникальность в БД | ошибка в `form.errors`, страница перерисовывается |
| Pydantic | `flaskblog/new_articles/schema_art.py` | форма объектов статей — контент разработчика, не пользователя | `ValidationError` при перечитывании `articles.yaml`; сайт продолжает работать на последней рабочей версии, ошибка показывается в `/art_manage` и логе |

Pydantic здесь не защищает границу системы: он работает с данными, зашитыми в код.
Наоборот, поступающие извне `<author>` и `<art_id>` не проверяются на прикладном уровне
вообще — `<int:art_id>` фильтруется только конвертером маршрута Werkzeug.

## 3. Поток данных

### 3.1 Чтение статьи (основной сценарий, БД не участвует)

```
GET /art/Max/1787932544
  │
  ├─ nginx (Docker): TLS, proxy_pass → 172.20.1.50:5000
  ├─ gunicorn/waitress → WSGI-вызов приложения
  │
  ├─ Werkzeug: сопоставление правила /art/<string:author>/<int:art_id>
  │    <int:art_id> — единственная фактическая проверка типа
  │
  ├─ art_main.art_author(author, art_id)          routes_articles.py
  │    ├─ logFC.info(...)                          → stdout + файл лога
  │    ├─ art = get_art(art_id)                    реестр в памяти (mtime-кэш)
  │    │    неизвестный/неполный id или нет файла → abort(404) (исправлено заданием 001, было 500)
  │    ├─ content = render_article(art.file_name)  ЧТЕНИЕ ДИСКА, каждый запрос
  │    │    ├─ .html → содержимое без преобразования
  │    │    └─ .md/.markdown → markdown(..., fenced_code + tables)
  │    │    каталог зафиксирован при импорте (см. 01 §4)
  │    └─ art_for_template = art.model_copy(...)    копия, объект реестра не мутируется
  │
  ├─ render_template('new_art/art_author.html', lang=art.lang, art=art)
  │    layout.html → _head/_header/_scripts + footer_new
  │    {{ art.content|safe }} — экранирование ОТКЛЮЧЕНО
  │
  └─ 200 text/html
```

Обращений к PostgreSQL в этом пути нет ни одного. `current_user` в шапке разрешается
Flask-Login из cookie сессии — и вот он-то один SELECT в `user` сделает, если пользователь
авторизован.

### 3.2 Вход пользователя (сценарий с БД)

```
POST /login  (email, password, remember, csrf_token)
  │
  ├─ users.login()                                 routes_users.py
  ├─ current_user.is_authenticated → если да, редирект на art_main.art_home
  ├─ LoginForm() ← request.form
  ├─ form.validate_on_submit()
  │    ├─ проверка CSRF-токена (Flask-WTF, SECRET_KEY)
  │    └─ DataRequired + Email()
  │
  ├─ User.query.filter_by(email=...).first()       SELECT → PostgreSQL
  ├─ bcrypt.check_password_hash(user.password, ...) сравнение хэша
  │
  ├─ успех: login_user(user, remember=...)          запись в session-cookie
  │    └─ redirect(request.args.get('next') или art_main.art_home)
  │         ⚠ next используется без валидации → open redirect
  └─ провал: flash(..., 'danger') + повторный рендер login.html (база layout.html,
             поэтому flash-сообщение будет видно)
```

### 3.3 Загрузка аватара

```
POST /account  (multipart: username, email, picture)
  ├─ @login_required → нет сессии: редирект на users.login + flash 'info'
  ├─ UpdateAccountForm(): FileAllowed(['jpg','png']) — проверка ПО ИМЕНИ файла
  ├─ save_picture(form.picture.data)                routes_users.py
  │    ├─ имя: secrets.token_hex(8) + расширение из имени, присланного клиентом
  │    ├─ Image.open(...).thumbnail((125,125))      Pillow, синхронно, в воркере
  │    └─ i.save(current_app.root_path/static/profile_pics/<name>)
  │         ⚠ старый файл аватара не удаляется
  ├─ current_user.image_file/username/email = ...
  ├─ db.session.commit()                            UPDATE → PostgreSQL
  └─ redirect(url_for('users.account'))             POST/redirect/GET
```

## 4. Состояние, кэширование, конфигурация

### 4.1 Состояние

| Вид состояния | Где хранится | Механизм | Замечание |
|---|---|---|---|
| Сессия пользователя | cookie на клиенте | подписанный cookie Flask + Flask-Login | server-side хранилища сессий нет |
| Постоянные данные | СУБД по `DATABASE_URI` (целевая PostgreSQL, фактически SQLite) | Flask-SQLAlchemy | схема создаётся только через `/createDB` |
| Индекс статей | память процесса | кэш `get_articles()` (mtime/size), перечитывается при изменении `articles.yaml` | перезапуск не нужен; при ошибке YAML — последняя рабочая версия |
| Тело статьи | файловая система | `render_article()` на каждый запрос | HTML возвращается как есть; Markdown преобразуется в HTML; кэша нет |
| Аватары | локальный диск контейнера/хоста | `static/profile_pics/` | НЕ в volume → теряются при пересборке контейнера |
| Тема оформления | `localStorage` браузера + `data-bs-theme` на `<html>` | `static/art_css/scripts.js` | на сервер не передаётся; восстановление инлайн-скриптом в `<head>` |
| Тема подсветки кода | `localStorage['hljs-theme']` | там же | 15 тёмных тем hljs, селектор в шапке |
| Flash-сообщения | сессия | `flash()` / `get_flashed_messages()` | видны на всех страницах — единая база `layout.html` |

Приложение почти stateless на уровне процесса — кроме кэша реестра статей
(`get_articles()`), который в multi-worker-конфигурации обновляется каждым воркером
независимо. Это делает горизонтальное масштабирование возможным без внешнего
session-store, но каталог `static/profile_pics/` придётся вынести в общее хранилище.

### 4.2 Кэширование

**Кэширования нет ни на одном уровне.** Ни `Flask-Caching`, ни Redis, ни `@lru_cache`,
ни HTTP-заголовков `Cache-Control` / `ETag`, ни кэша nginx (`proxy_cache` в
`nginx/nginx.conf` отсутствует). Каждый показ статьи — это `open()` + полное чтение файла.
Единственное неявное кэширование — встроенный кэш скомпилированных шаблонов Jinja
и статика, отдаваемая Flask с `Last-Modified`/`ETag` по умолчанию.

Это самая очевидная точка приложения усилий по производительности — см.
[05_optimization_roadmap.md](05_optimization_roadmap.md) §2.

### 4.3 Управление конфигурацией

Цепочка: `local.env` → `os.environ` → класс `Config` → `app.config`.

```
локально:  local.env  ──load_dotenv()──▶ os.environ ──▶ Config ──from_object──▶ app.config
Docker:    dock_flask.env ──env_file──▶ os.environ ──▶ Config ──from_object──▶ app.config
           .env (корень)  ──▶ подстановка ${...} в compose-nginx-db.yml (НЕ в приложение)
```

Три файла окружения с разными зонами ответственности — источник путаницы:

| Файл | Кто читает | Ключи |
|---|---|---|
| `local.env` | `flaskblog/config.py` через `load_dotenv()` | `SECRET_KEY`, `DATABASE_URI`, `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `LOG_DIR`, `LOG_FILE` |
| `flaskblog/dock_flask.env` | docker compose → окружение контейнера `app_flask` | `SECRET_KEY`, `DB_*`, `LOG_DIR`, `LOG_FILE` — **без `DATABASE_URI`** |
| `.env` в корне | сам docker compose для подстановки `${...}` | `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `PGADMIN_EMAIL`, `PGADMIN_PASSWORD` |

Все три gitignored (`*.env`), примеров `*.env.example` в репозитории нет — воспроизвести
окружение с нуля можно только по [setup-and-run.md](setup-and-run.md).

Из `DB_*` реально работает лишь то, что уходит в compose. Переменные `DB_HOST`/`DB_PORT`
в `Config` считываются, но не используются: строка сборки DSN закомментирована, а
`SQLALCHEMY_DATABASE_URI` берётся только из `DATABASE_URI`. Отсюда следует
критическая проблема Docker-контура, разобранная в [04](04_code_quality.md) §4.1.

### 4.4 Конфигурация логирования

Отдельный от `Config` механизм: словарь `logging_config` захардкожен в конце
`flaskblog/logger/config_log.py`, а из окружения приходят только `LOG_DIR` и `LOG_FILE`.

| Логгер | Обработчики | Куда пишет |
|---|---|---|
| `Stdout` | `console1` | только консоль |
| `OnlyFile` | `rotating_file1` | только файл |
| `FileStdout` | `rotating_file1` + `console1` | и файл, и консоль |

`rotating_file1` — `RotatingFileHandler`, `maxBytes=1048576` (1 МБ), `backupCount=20`,
то есть верхняя граница объёма логов ≈ 21 МБ. Все прикладные модули используют
`FileStdout`, что в Docker даёт двойную запись: и в файл, и в поток контейнера.
Файл `flaskblog/logger/loggerSettings.json` — альтернативный конфиг, который код
не читает (проверено поиском по всем `.py`).

## 5. Развёртывание

### 5.1 Топология Docker

`compose-nginx-db.yml`, внешняя сеть `app_net_new` (`172.20.0.0/16`), статические адреса:

| Сервис | Контейнер | IP | Публикация | Volume |
|---|---|---|---|---|
| `nginx` | `nginx_flask` | 172.20.1.1 | `1443:443` | — |
| `app_flask` | `app_flask` | 172.20.1.50 | нет (только через nginx) | `./flaskblog/log_app:/flaskblog/log` |
| `db` | `postgresql_db_flask` | 172.20.1.2 | `9032:5432` | `./pg_db:/var/lib/postgresql/data/` |
| `pgadmin` | `pgadmin_flask` | 172.20.1.3 | нет (через `/pgadmin`) | — |

Особенности этой топологии:

- **Адресация статическими IP.** `nginx.conf` проксирует на литерал `172.20.1.50:5000`
  вместо DNS-имени сервиса. Сеть объявлена `external: true`, поэтому её нужно создать
  заранее: `./docker_manager.sh net-create`.
- **`depends_on: nginx` у `app_flask`** — зависимость объявлена от прокси, а не от `db`.
  Порядок старта относительно PostgreSQL не гарантирован, healthcheck'ов нет ни у одного
  сервиса, поэтому первое обращение к БД после холодного старта может упасть.
- **`version: "3.7"`** — ключ устарел и игнорируется Compose v2.
- **Монтирование логов работает согласованно:** `WORKDIR /flaskblog` + `LOG_DIR=./log`
  дают `/flaskblog/log`, который смонтирован в `./flaskblog/log_app` на хосте.
- **Аватары не персистентны:** `static/profile_pics/` не смонтирован, файлы живут
  внутри слоя контейнера и исчезают при пересборке.

### 5.2 Сборка образа приложения

`flaskblog/DockerFlask`:

```dockerfile
FROM python:3.12-slim
WORKDIR /flaskblog
COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv \
    && uv sync --locked --no-dev --no-install-project
COPY ./flaskblog /flaskblog/flaskblog
ENV PATH="/flaskblog/.venv/bin:$PATH"
```

Слои упорядочены правильно: зависимости устанавливаются до копирования кода, поэтому
изменение исходников не инвалидирует кэш `uv sync`. Флаг `--locked` требует, чтобы
`uv.lock` был закоммичен и соответствовал `pyproject.toml`, иначе сборка падает.

Что стоит знать про этот образ: сборка одноступенчатая (в образ попадает и `uv`),
пользователь остаётся `root`, `HEALTHCHECK` не объявлен, а команда запуска задана не в
`CMD`, а в `command` сервиса compose — `gunicorn --bind 0.0.0.0:5000 flaskblog.run:app`,
то есть с одним воркером по умолчанию и с `debug_mode=True`, зашитым в `flaskblog/run.py`.

### 5.3 Локальный запуск

Прокси и TLS не участвуют: `waitress` слушает `0.0.0.0:5000` напрямую, обёрнутый в
`TransLogger` для access-логов. Схема БД создаётся однократным заходом на
`http://127.0.0.1:5000/createDB`. Подробности и таблицы переменных —
в [setup-and-run.md](setup-and-run.md).
