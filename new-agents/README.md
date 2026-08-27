# flask-blog-1 — агентный режим

Блог/сайт технических статей с серверным рендерингом на **Flask 3.1**, построенный по
паттерну «фабрика приложения», с внедрённым **агентным режимом**: задания по развитию
проекта выполняет команда агентов Qwen Code — оркестратор плюс субагенты на разных
моделях.

Сайт намеренно совмещает **две независимые модели контента**:

1. **Статьи из файлов** — технические статьи хранятся как статические Jinja-HTML файлы в
   `flaskblog/templates/content_art/` и описываются Pydantic-моделями в
   `flaskblog/new_articles/schema_art.py`. Именно это — основной контент сайта:
   `/` перенаправляет на `/art_home`.
2. **Пользователи и посты в БД** — `User` / `Post` через Flask-SQLAlchemy на PostgreSQL,
   с регистрацией, входом и загрузкой аватара.

> Язык интерфейса, flash-сообщений и содержимого статей — **русский**.

## Агентный режим

Проект развивается командой агентов Qwen Code по одному заданию за раз:

| Файл | Назначение |
|---|---|
| [QWEN.md](QWEN.md) | контекст проекта + инструкции оркестратора (главная сессия, glm-5.3) |
| [AGENTS.md](AGENTS.md) | контекст проекта + правила команды, процесс дефектов |
| [REQUIREMENTS.md](REQUIREMENTS.md) | **текущее задание** команды; после выполнения заменяется новым |
| `.qwen/agents/` | субагенты: frontend-dev, backend-dev, qa, adversary |
| `.qwen/settings.json` | настройки проекта (`tools.approvalMode: auto-edit`) |

Схема работы: пользователь кладёт задание в `REQUIREMENTS.md` и запускает Qwen Code в
корне проекта. Главная сессия (glm-5.3) по `QWEN.md` действует как оркестратор: пишет
план, делегирует разработку субагентам, проверяет доказательства, отправляет qa
проверить работу запуском и curl-сценариями, adversary — враждебный прогон; дефекты
фиксируются в `DEFECTS.md`, находки — в `ADVERSARIAL_REVIEW.md`. Когда все критерии
успеха подтверждены, задание закрыто — в `REQUIREMENTS.md` кладётся следующее.

Модели команды (объявлены в `~/.qwen/settings.json`, authType `openai`):

| Роль | Модель |
|---|---|
| оркестратор (главная сессия) | glm-5.3 |
| frontend-dev | nordrouter/minimax/minimax-m3 |
| backend-dev | nordrouter/moonshotai/kimi-k2.7-code |
| qa, adversary | nordrouter/minimax/minimax-m3 |

Комплект переносим: чтобы внедрить агентный режим в другой проект, скопируйте эти файлы
и `.qwen/`, а затем адаптируйте проектный контекст в `README.md`, `QWEN.md`, `AGENTS.md`
под новый проект. `REQUIREMENTS.md` каждый раз получает задание нового проекта.

## Возможности

- Список статей и страницы отдельных статей, собираемые из статических HTML-фрагментов
  (темы по Python и Rust; поддерживаются `.html`, `.md`, `.markdown`).
- Регистрация / вход / выход пользователей на Flask-Login с хешированием паролей
  Flask-Bcrypt.
- Страница аккаунта с загрузкой аватара, который Pillow уменьшает в миниатюру.
- Переключение светлой и тёмной темы через `static/art_css/` + `scripts.js`.
- Своя обёртка `ConfigLogger` над `logging.config.dictConfig`.
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

## Быстрый старт (локально)

```bash
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

## Запуск агентного режима

1. Убедитесь, что модели субагентов объявлены в `~/.qwen/settings.json`
   (`nordrouter/minimax/minimax-m3`, `nordrouter/moonshotai/kimi-k2.7-code`), а главная
   сессия работает на `glm-5.3`.
2. Поднимите приложение и БД (см. «Быстрый старт» или Docker ниже) — агентам нужен
   работающий URL для проверок.
3. Запустите `qwen-code` в корне проекта. `QWEN.md` превратит главную сессию в
   оркестратора; субагенты подхватятся из `.qwen/agents/`.
4. Дайте команду:

   > Выполни текущее задание из REQUIREMENTS.md и не останавливайся, пока все критерии
   > успеха не будут подтверждены доказательствами.

Пока команда работает: дефекты появляются в `DEFECTS.md`, находки adversary — в
`ADVERSARIAL_REVIEW.md`, доказательства — в `screenshots/`, сценарии проверок — в `e2e/`.

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

## Маршруты

Регистрируются 13 URL-правил (12 маршрутов приложения плюс встроенный `static`):

| Методы | Маршрут | Эндпоинт | Назначение |
|---|---|---|---|
| GET | `/`, `/home` | `main.home` | перенаправляет на `/art_home` |
| GET | `/art_home` | `art_main.art_home` | список статей — главная страница |
| GET | `/art/<author>/<art_id>` | `art_main.art_author` | отдельная статья |
| GET | `/about` | `main.about` | страница «о проекте» |
| GET | `/createDB`, `/createDB/`, `/createDB/<post_id>` | `main.createDB` | вызывает `db.create_all()` |
| GET, POST | `/register` | `users.register` | регистрация |
| GET, POST | `/login` | `users.login` | вход |
| GET | `/logout` | `users.logout` | выход |
| GET, POST | `/account` | `users.account` | профиль и загрузка аватара |

## Запуск в Docker

```bash
./docker_manager.sh net-create                       # внешняя сеть app_net_new
docker compose -f compose-nginx-db.yml build
docker compose -f compose-nginx-db.yml up -d
./docker_manager.sh cont-stop                        # остановить все четыре контейнера
```

Требуются `flaskblog/dock_flask.env`, `.env` рядом с compose-файлом и self-signed
сертификаты в `nginx/cert/` — всё в `.gitignore`; см. [`docs/setup-and-run.md`](docs/setup-and-run.md) §5.2.
Доступ: <https://localhost:1443/>; pgAdmin на `/pgadmin`; Postgres на `127.0.0.1:9032`.

## Модель данных

```python
User(id, username, email, image_file, password) -> posts
Post(id, title, date_posted, content, user_id)
```

Статьи — Pydantic-модели `ArticleLang` с полями `author`, `lang`, `art_id`, `title`,
`file_name`, `content`. Метаданные — в `flaskblog/new_articles/articles.yaml`, тела — в
`flaskblog/templates/content_art/`. Добавление статьи: файл `art.html`/`art.md` в
`content_art/` + запись в `articles.yaml` с уникальным `art_id`.

## Линтеры и проверка изменений

```bash
uv run ruff check .
python -c "from flaskblog import create_app; print(len(list(create_app().url_map.iter_rules())))"   # 13
python -m flaskblog.run                                                                            # затем curl /
```

Тестов и миграций нет — подробные соглашения, грабли и правила для агентов см. в
[AGENTS.md](AGENTS.md).
