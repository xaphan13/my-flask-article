# 03 — Логика и работа кода

> Актуально для ветки `new-frontend`, HEAD `b12f62c` (актуализировано 2026-08-31).
> Описание потока основано на текущем коде;
> приложение и тесты для этой редакции документации не запускались. Архитектурный контекст:
> [02_architecture.md](02_architecture.md).

## 1. Жизненный цикл приложения

### 1.1 Порядок инициализации — и почему он важен

Инициализация происходит **на этапе импорта пакета**, ещё до вызова `create_app()`.
Это нетипично для Flask и определяет, в каком виде проявляются сбои конфигурации.

```
python -m flaskblog.run
  │
  ├─ (1) import flaskblog.run
  │        └─ from flaskblog import create_app  →  import flaskblog
  │
  ├─ (2) flaskblog/__init__.py, строки 1-4: импорт Flask, Bcrypt, LoginManager, SQLAlchemy
  │
  ├─ (3) строка 6: from flaskblog.logger.config_log import ConfigLogger
  │        └─ config_log.py импортирует flaskblog.config
  │             └─ config.py: load_dotenv(<корень>/local.env)  ← ЧТЕНИЕ ОКРУЖЕНИЯ
  │             └─ class Config: атрибуты вычисляются ЗДЕСЬ, один раз
  │        └─ формируется словарь logging_config с путём
  │           f"{ConfigLogger.pathLoggerDir}/{ConfigLogger.nameFileLogger}"
  │
  ├─ (4) строка 7: logFC = ConfigLogger.getLogger("FileStdout", "ClientHTTPS")
  │        └─ isSetting == False → settingLogger()
  │             ├─ __createLogDir(LOG_DIR)   os.mkdir, НЕ makedirs
  │             │    LOG_DIR is None      → TypeError ЗДЕСЬ, на импорте
  │             │    вложенный путь       → FileNotFoundError ЗДЕСЬ
  │             ├─ logging.config.dictConfig(logging_config)  ← файл лога открывается
  │             └─ isSetting = True        повторные вызовы бесплатны
  │
  ├─ (5) строки 12-19: db = SQLAlchemy(); bcrypt = Bcrypt(); login_manager = LoginManager()
  │        login_manager.login_view = 'users.login'
  │        login_manager.login_message = "Нужно авторизоваться или зарегистрироваться"
  │
  ├─ (6) run.py: app = create_app(debug_mode=True)   ← см. §1.2
  │
  └─ (7) под __main__: waitress.serve(TransLogger(app), host='0.0.0.0', port=5000)
           При запуске через gunicorn/waitress-serve шаг (7) не выполняется:
           WSGI-сервер забирает готовый объект app
```

**Практический вывод для отладки.** Логгер настраивается на шаге (4), а `db` появляется
только на шаге (5). Поэтому ошибка в `LOG_DIR` — это падение на импорте `flaskblog`
с трейсбеком внутри `config_log.py`, вообще без упоминания `create_app`. Ошибка в
`DATABASE_URI` — падение позже, внутри `create_app`.

### 1.2 Сборка приложения в `create_app()`

`flaskblog/__init__.py`, строки 21-42:

```
create_app(config_class=Config, debug_mode=False)
  ├─ app = Flask(__name__)                 __name__ == 'flaskblog' → templates/ и static/
  │                                        ищутся внутри пакета
  ├─ app.config.from_object(config_class)   переносятся только UPPERCASE-атрибуты
  ├─ app.config['DEBUG'] = debug_mode
  │
  ├─ logFC.info(... весь app.config ...)   ⚠ ПЕЧАТАЕТ SECRET_KEY В ЛОГ (проверено)
  │                                        и в файл, и в stdout, на каждый старт
  │
  ├─ db.init_app(app)                       БЕЗ SQLALCHEMY_DATABASE_URI →
  │                                         RuntimeError: Either 'SQLALCHEMY_DATABASE_URI'
  │                                         or 'SQLALCHEMY_BINDS' must be set. (проверено)
  ├─ bcrypt.init_app(app)
  ├─ login_manager.init_app(app)
  │
  ├─ import + register_blueprint(art_main)   импорты ВНУТРИ функции — так разрывается
  ├─ import + register_blueprint(users)      циклическая зависимость
  ├─ import + register_blueprint(main)       models ↔ flaskblog
  ├─ import + register_blueprint(errors)
  │
  ├─ logFC.warning("...start 'main()'")      маркер старта в логе
  └─ return app
```

Побочный эффект импорта блюпринтов: при импорте `routesArticles` подтягивается
`schema_art`, который на уровне модуля создаёт все объекты `ArticleLang`, словарь
`art_dict_file` и **вычисляет `get_path_dir()`** как значение по
умолчанию у `read_html`. Каталог статей фиксируется именно здесь и навсегда.

Ни `before_request`, ни `after_request`, ни `teardown_appcontext` в проекте не
регистрируются. Единственный teardown — встроенный в Flask-SQLAlchemy: он закрывает
сессию по завершении контекста приложения.

### 1.3 Инициализация схемы БД

Миграций нет. Таблицы создаёт обращение к `/createDB`, где вызывается `db.create_all()`.
Это идемпотентная операция для *создания*, но она **не изменяет** существующие таблицы:
после правки `flaskblog/models.py` нужно либо удалять таблицы вручную, либо вводить
Flask-Migrate.

### 1.4 Завершение работы

Graceful shutdown не реализован: обработчиков `SIGTERM`/`SIGINT` нет, `atexit`-хуков нет.
Останов сводится к штатному поведению компонентов: WSGI-сервер дорабатывает текущие
запросы, Flask-SQLAlchemy закрывает сессии, `logging` сбрасывает буферы обработчиков.
В Docker останов выполняется скриптом `./docker_manager.sh cont-stop` (последовательные
`docker stop`), политика `restart: always` поднимет контейнеры обратно при перезапуске
демона.

## 2. Маршруты и обработка запроса

### 2.1 Полная карта маршрутов

Получено из `app.url_map` — 13 правил, из них 12 прикладных:

| URL | Endpoint | Методы | Авторизация | Обработчик |
|---|---|---|---|---|
| `/` | `main.home` | GET | нет | `main/routesMain.py` |
| `/home` | `main.home` | GET | нет | тот же |
| `/about` | `main.about` | GET | нет | `main/routesMain.py` |
| `/createDB` | `main.createDB` | GET | **нет** ⚠ | `main/routesMain.py` |
| `/createDB/` | `main.createDB` | GET | **нет** ⚠ | тот же |
| `/createDB/<int:post_id>` | `main.createDB` | GET | **нет** ⚠ | тот же |
| `/art_home` | `art_main.art_home` | GET | нет | `new_articles/routesArticles.py` |
| `/art/<string:author>/<int:art_id>` | `art_main.art_author` | GET | нет | там же |
| `/register` | `users.register` | GET, POST | нет | `users/routesUsers.py` |
| `/login` | `users.login` | GET, POST | нет | там же |
| `/logout` | `users.logout` | GET | нет | там же |
| `/account` | `users.account` | GET, POST | `@login_required` | там же |
| `/static/<path:filename>` | `static` | GET | нет | встроенный Flask |

Фактические ответы (прогон `test_client`):

```
/                    → 302 → /art_home
/art_home            → 200
/about               → 200
/art/Max/1           → 200
/art/anybody-else/1  → 200   ← <author> не проверяется, любая строка даёт ту же статью
/art/Max/999         → 404   ← исправлено заданием 001 (было 500, KeyError)
/login               → 200
/nope                → 404
```

### 2.2 Middleware

Собственных middleware в проекте нет — ни WSGI-обёрток, ни хуков `before_request`.
Всё, что стоит на пути запроса, приходит извне:

| Уровень | Компонент | Функция |
|---|---|---|
| WSGI, только локально | `paste.translogger.TransLogger` в `flaskblog/run.py` | access-лог в формате Apache. При запуске через gunicorn отсутствует |
| Прокси, только Docker | `nginx` | TLS, `proxy_set_header Host` / `X-Forwarded-For`, `client_max_body_size 1000M` |
| Расширение | Flask-Login | загрузка `current_user` из cookie, редирект неавторизованных |
| Расширение | Flask-WTF | проверка CSRF-токена при валидации формы |
| Расширение | Flask-SQLAlchemy | сессия на время запроса и её закрытие |

Важное следствие отсутствия `ProxyFix`: `X-Forwarded-For` от nginx приходит, но Flask его
не учитывает — `request.remote_addr` всегда будет IP прокси. Для rate limiting или
аудита по IP потребуется добавить `werkzeug.middleware.proxy_fix.ProxyFix`.

## 3. Ключевые процессы: пошаговый разбор

### 3.1 Отображение списка статей — `art_home`

`../flaskblog/new_articles/routes_articles.py`:

```python
@art_main.route("/art_home")
def art_home():
    title_list = [x.dict(exclude_unset=True, exclude={"content"}) for x in art_dict_file.values()]
    logFC.info(f"new_art : '/art' = {title_list}")
    return render_template("new_art/art_home.html", title_list=title_list)
```

1. Итерация по `art_dict_file` — словарю, собранному при импорте `schema_art`.
2. `model_dump(exclude={"content"})` сериализует каждую `ArticleLang` в `dict`,
    убирая тело статьи. Фактический результат (проверено):
   `{'author', 'lang', 'art_id', 'title', 'file_name'}`. (Ранее использовался
   `.dict()` — API Pydantic v1 с предупреждением `PydanticDeprecatedSince20`;
   переведён на `model_dump()`.)
3. Весь список логируется на уровне INFO — то есть содержимое индекса пишется в файл
   при каждом заходе на главную.
4. Шаблон `new_art/art_home.html` строит ссылки через
   `url_for('art_main.art_author', author=art.author, art_id=art.art_id)`.

Обращений к диску и к БД в этом обработчике нет.

### 3.2 Чтение статьи — `art_author`

```python
@art_main.route("/art/<string:author>/<int:art_id>")
def art_author(author, art_id):
    logFC.info(f"art_author : '/art/<string:author>/<int:art_id>' = {author} - {art_id}")
    art = get_art(art_id)
    if art is None:
        abort(404)
    if not _is_complete(art):
        abort(404)
    content_dir = get_path_dir()
    if not os.path.exists(os.path.join(content_dir, art.file_name)):
        abort(404)
    content = render_article(art.file_name, content_dir)
    art_for_template = art.model_copy(update={"content": content})
    return render_template(
        "new_art/art_author.html", lang=art_for_template.lang, art=art_for_template
    )
```

1. **`author` игнорируется** — используется только в логе. Поиск идёт исключительно по
   `art_id`, поэтому разные значения автора ведут к одной статье с тем же идентификатором.
2. `get_art(art_id)` + `abort(404)` при отсутствии записи — исправлено заданием 001
   (раньше было прямое индексирование `art_dict_file[art_id]` с `KeyError` → 500).
   Дополнительно 404 отдаётся для неполных записей и отсутствующих файлов.
3. `render_article(art.file_name)` сначала читает файл из каталога, зафиксированного при
   импорте. Для `.md` и `.markdown` содержимое преобразуется функцией `markdown()` с
   расширениями `fenced_code` и `tables`; остальные расширения, включая `.html`,
   возвращаются без преобразования. Кэша нет — чтение и Markdown-рендеринг выполняются на
   каждый запрос.
4. `art_for_template = art.model_copy(update={"content": content})` — в шаблон уходит
   **копия** записи: общие объекты `art_dict_file` не мутируются (ранее `art.content =`
   менял модуль-level состояние; исправлено в задании 002).
5. Шаблон выводит `{{ body_html|safe }}` — экранирование отключено сознательно. Для
   HTML-файлов это доверенная разметка из репозитория; для Markdown это HTML, созданный
   библиотекой `markdown`. Встроенная HTML-разметка внутри Markdown также проходит без
   дополнительной очистки, поэтому файлы `content_art/` считаются доверенным контентом.

### 3.3 Регистрация — `register`

```
POST /register
 1. current_user.is_authenticated → redirect на art_main.art_home
 2. RegistrationForm() из request.form
 3. form.validate_on_submit():
      ├─ CSRF-токен (Flask-WTF)
      ├─ username: DataRequired, Length(2..20)
      ├─ email:    DataRequired, Email()
      ├─ password: только DataRequired  ⚠ ни минимальной длины, ни сложности
      ├─ confirm_password: EqualTo('password')
      ├─ validate_username → SELECT ... WHERE username = ?   (уникальность)
      └─ validate_email    → SELECT ... WHERE email = ?       (уникальность)
 4. bcrypt.generate_password_hash(password).decode('utf-8')   → 60 символов
 5. logFC.info(f"register = {user}")   → в лог уходит __repr__: username + email
 6. db.session.add(user); db.session.commit()
 7. flash('Your account has been created! ...', 'success')
 8. redirect(url_for('users.login'))   → login.html на базе layout.html, flash виден
```

Проверка уникальности на уровне формы и `unique=True` на уровне БД образуют состояние
гонки (TOCTOU): два одновременных запроса могут пройти шаг 3 и столкнуться на шаге 6,
где `IntegrityError` не перехвачен и даст 500. Правильная защита — `try/except
IntegrityError` с `db.session.rollback()`.

### 3.4 Вход и выход

`login` разобран в [02_architecture.md](02_architecture.md) §3.2. Две особенности реализации:

- **Open redirect.** `next_page = request.args.get('next')` подставляется в `redirect()`
  без проверки, что это относительный путь. Ссылка `/login?next=https://evil.example`
  после успешного входа увезёт пользователя на внешний домен.
- **Ответ одинаков для «нет такого e-mail» и «неверный пароль»** — это правильно,
  перечисление аккаунтов через сообщение об ошибке невозможно. Но при отсутствующем
  пользователе `bcrypt.check_password_hash` не вызывается, поэтому время ответа
  различается — остаётся тайминговый канал.

`logout` — три строки: `logout_user()` и редирект. Маршрут доступен по **GET и без
CSRF-защиты**, то есть сторонний сайт может разлогинить пользователя картинкой
`<img src="https://site/logout">`. Помимо этого, `logout` не помечен `@login_required`,
но для анонимного пользователя вызов безвреден.

### 3.5 Обновление профиля — `account`

Один обработчик обслуживает и GET, и POST, разделяя ветки через `validate_on_submit()`
и `request.method == 'GET'` (предзаполнение полей). Загрузка файла:

```python
def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)  # расширение от КЛИЕНТА
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(current_app.root_path, "static/profile_pics", picture_fn)
    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)
    return picture_fn
```

Шаг за шагом, с оценкой рисков:

1. Имя генерируется случайно — path traversal через имя файла исключён, это сделано верно.
2. **Расширение берётся из присланного имени файла.** `FileAllowed(['jpg','png'])` тоже
   проверяет только имя. Реальный тип содержимого не верифицируется (`Image.verify()`
   не вызывается); защищает лишь то, что Pillow не сможет открыть не-изображение.
3. Ограничения на размер загрузки нет: `MAX_CONTENT_LENGTH` не задан, а nginx разрешает
   `client_max_body_size 1000M`. Декомпрессионная бомба или очень большой JPEG будут
   разжаты в память рабочего процесса.
4. Обработка синхронная, внутри воркера — на время ресайза воркер занят.
5. **Старый аватар не удаляется** — каталог `static/profile_pics/` растёт неограниченно.
6. Изменения профиля и имя файла коммитятся, затем POST/redirect/GET предотвращает
   повторную отправку формы.

### 3.6 Создание схемы БД — `createDB`

```python
@main.route("/createDB")
@main.route("/createDB/")
@main.route("/createDB/<int:post_id>")
def createDB(post_id=999):
    page = request.args.get("id", 0, type=int)
    db.create_all()
    db.session.commit()
    logFC.info(f"'createDB' = {post_id} = {page}")
    return render_template("about.html", title="About")
```

Обработчик носит следы отладочного эксперимента и заслуживает отдельного внимания:

- **Ни авторизации, ни проверки прав, ни ограничения метода** — любой анонимный
  посетитель может дёрнуть DDL-операцию по GET.
- `post_id` и `page` не участвуют в логике, попадают только в лог. Три декоратора
  маршрута существуют ради демонстрации разбора URL.
- `db.session.commit()` после `create_all()` избыточен: DDL выполняется вне сессии.
- Возвращается `about.html` — то есть страница «О проекте» с заголовком «About», что
  никак не отражает выполненное действие.

## 4. Обработка ошибок

### 4.1 Что реализовано

`flaskblog/errors/handlers.py` — три обработчика, зарегистрированных глобально через
`@errors.app_errorhandler`:

| Код | Шаблон | Когда срабатывает |
|---|---|---|
| 404 | `templates/errors/404.html` | нет совпадения правила (проверено на `/nope`) |
| 403 | `templates/errors/403.html` | явный `abort(403)` — в коде не вызывается ни разу |
| 500 | `templates/errors/500.html` | необработанное исключение, **только при `DEBUG=False`** |

Шаблоны наследуют `layout.html`, поэтому страницы ошибок оформлены как остальной сайт
и русифицированы (задание 003).

**Обработчик 500 в рабочей конфигурации не задействован на сценарии с неизвестным
`art_id`.** Историческая проверка (до задания 001) на запросе `/art/Max/999` в трёх средах
показывала 500 из-за `KeyError`; теперь этот маршрут отдаёт 404, и приведённая ниже
механика актуальна только для прочих необработанных исключений:

| Среда | Поведение при необработанном исключении |
|---|---|
| `create_app(debug_mode=False)` + `test_client` | HTTP 500, отрисован `errors/500.html` |
| `create_app(debug_mode=True)` + `test_client` | исключение пробрасывается наружу |
| `python -m flaskblog.run` (waitress, `debug_mode=True`) | HTTP 500, тело 110 байт: `Internal Server Error … (generated by waitress)`; трейсбек уходит в stdout |

Механика: `debug_mode=True` включает `PROPAGATE_EXCEPTIONS`, поэтому Flask **не** вызывает
свой обработчик, а пробрасывает исключение в WSGI-сервер. Интерактивного отладчика
Werkzeug при этом не возникает — он подключается только через `app.run()`, которого здесь
нет. Итог: `flaskblog/run.py` жёстко задаёт `debug_mode=True`, ту же точку входа использует
Docker-команда `gunicorn flaskblog.run:app`, поэтому **фирменная страница `errors/500.html`
не показывается ни локально, ни в контейнере** — клиент получает служебную заглушку
WSGI-сервера. Раскрытия исходников в ответе нет, но трейсбек пишется в stdout,
а не через настроенный `ConfigLogger`.

### 4.2 Чего не хватает

- **Ни одного `try/except` во всём прикладном коде.** Проверено: конструкции
  `try` в `flaskblog/**/*.py` отсутствуют. Любая ошибка ввода-вывода, БД или
  расшифровки данных превращается в 500.
- **Обработчик 500 не логирует исключение.** Он принимает аргумент `error` и не
  использует его. При `DEBUG=False` трейсбек уйдёт в стандартный логгер Flask,
  который в `logging_config` не сконфигурирован, — то есть в кастомный файл лога
  ошибка не попадёт.
- **Ошибки предметной области отображаются в неверные HTTP-коды.** Главный пример —
  неизвестный `art_id`: `KeyError` → 500 вместо 404 — **исправлен заданием 001**
  (теперь `get_art()` + `abort(404)`).
- **Нет откатов транзакций.** `db.session.commit()` вызывается без `try/except`
  и без `db.session.rollback()` в обработчике ошибки, поэтому `IntegrityError`
  оставляет сессию в сломанном состоянии до конца запроса.
- **`debug_mode=True` захардкожен** в `flaskblog/run.py` и наследуется Docker-командой
  gunicorn. В этом режиме 500 отдаёт интерактивный отладчик Werkzeug с исходниками
  и трейсбеком — недопустимо вне localhost.

## 5. Логирование

### 5.1 Как это устроено

Каждый маршрутный модуль начинается одинаково — этот блок обязателен к сохранению
при правках (порядок импортов защищён исключением `E402` в `pyproject.toml`):

```python
from flask import render_template, Blueprint
from flaskblog.logger.config_log import ConfigLogger

logFC = ConfigLogger.getLogger("FileStdout", "ClientHTTPS")  # логгер ДО прочих импортов
from flaskblog import db
```

Имя логгера строится как `f"{nameBase}.{nameMod}"`: базовое имя определяет набор
обработчиков (`Stdout` / `OnlyFile` / `FileStdout`), а `nameMod` служит меткой источника
и наследует обработчики родителя. Во всех модулях используется одна и та же пара
`("FileStdout", "ClientHTTPS")`, поэтому по имени логгера различить модули нельзя —
источник видно только по полям `%(module)s.%(funcName)s(%(lineno)d)` в форматтере.

Куда пишется:

- файл `{LOG_DIR}/{LOG_FILE}` через `RotatingFileHandler`, 1 МБ × 20 бэкапов (макс. ≈ 21 МБ);
- `stdout` через `StreamHandler`.

В Docker это означает двойную запись: и в смонтированный `/flaskblog/log`, и в поток
контейнера, который Docker пишет в свой json-лог. Ротация настроена только для файла.

### 5.2 Что фактически логируется

| Место | Уровень | Содержимое |
|---|---|---|
| `create_app` | INFO | **весь `app.config`, включая `SECRET_KEY`** (проверено) |
| `create_app` | WARNING | маркер старта `'***...***'start 'main()'` |
| `art_home` | INFO | полный список метаданных статей |
| `art_author` | INFO | `author` и `art_id` из URL |
| `read_html` | INFO | каталог и полный путь читаемого файла — на каждый запрос |
| `register` | INFO | `__repr__` пользователя: username + email |
| `about`, `createDB` | INFO | отладочные метки |

### 5.3 Проблемы логирования

1. **Утечка секрета.** `SECRET_KEY` в открытом виде попадает и в файл, и в stdout при
   каждом старте (подтверждено запуском). Компрометация `SECRET_KEY` = возможность
   подделать cookie сессии, то есть выдать себя за любого пользователя. Файл лога при этом
   в Docker смонтирован на хост, а stdout уходит в журнал Docker.
2. **PII в логах.** e-mail пользователя пишется при регистрации без маскирования.
3. **Уровень не настраивается.** `LOG_LEVEL` в окружении нет; уровни зашиты в
   `logging_config` (`DEBUG` у логгеров, `INFO` у обработчиков).
4. **Нет контекста запроса.** Ни идентификатора запроса, ни URL, ни IP, ни времени
   ответа. Форматтер даёт thread/process, но связать записи одного запроса нельзя.
5. **Логирование в горячем пути.** `read_html` пишет INFO-строку на каждое чтение файла —
   лишний синхронный ввод-вывод на каждый показ статьи.
6. **Ошибки не логируются вовсе** (см. §4.2), при том что успешные операции логируются
   подробно.
