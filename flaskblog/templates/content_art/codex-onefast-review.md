# Технический разбор репозитория `one-fastApi`

## 1) Назначение проекта

`one-fastApi` — это учебно-демонстрационный FastAPI-проект, который сочетает сразу несколько направлений:

1. Демонстрация разных способов извлечения и валидации параметров запроса в FastAPI (`Path`, `Query`, `Header`, `Cookie`, `Depends`, классы зависимостей, функции зависимостей, `Annotated`).
2. Демонстрация работы с асинхронной БД через SQLAlchemy 2.0 (`AsyncEngine`, `AsyncSession`) и Pydantic-схемами.
3. Примеры простых CRUD-операций (`users`) и более сложных связей many-to-many через association table (`orders` ↔ `products`).
4. Подготовка к запуску как через `uvicorn` (dev), так и через `gunicorn + uvicorn worker` (production-like).

Итог: это не «узкоспециализированный боевой сервис», а репозиторий-шаблон/песочница с рабочими примерами API, DI-паттернов и ORM-слоя.

---

## 2) Иерархия проекта (по смысловым блокам)

- `fastapi-application/`
  - `main.py` — основной entrypoint приложения на uvicorn.
  - `main_gunicorn.py` — entrypoint для запуска через кастомную обертку Gunicorn.
  - `create_fastapi.py` — фабрика FastAPI-приложения + lifecycle (`lifespan`).
  - `core/`
    - `config.py` — pydantic-settings конфиг (API префиксы, DB, gunicorn, logging).
    - `gunicorn/` — конфиг и интеграция логирования для Gunicorn.
  - `api/` — учебные роуты по dependency injection и извлечению параметров.
  - `example_sql/` — пример ORM-моделей `User/Post`, CRUD и роуты.
  - `ex_order_product/` — пример `Order/Product` со связью many-to-many.
  - `db_core/` — базовые DB-компоненты: engine/session manager, базовый ORM класс, типы.
  - `utils/docs.py` — кастомные `/docs` и `/redoc`.
  - `alembic/` + `alembic.ini` — миграции БД.
- Инфраструктура в корне:
  - `pyproject.toml` — зависимости и форматтер/линтер настройки.
  - `docker-compose.yml`, `nginx_pg_admin.yml`, `nginx/` — окружение PostgreSQL + админки + nginx.
  - `Makefile` — команды запуска/миграций.
  - `Install-run.md` — краткая инструкция запуска.

---

## 3) Как работает код (сквозной сценарий)

1. Запуск (`main.py`):
   - собирается `main_app = create_app(custom_docs_url=False)`;
   - подключаются роутеры: `api`, `users`, `orders`;
   - `uvicorn.run("main:main_app", ...)` стартует HTTP-сервер.

2. Инициализация приложения (`create_fastapi.py`):
   - создается `FastAPI` с `ORJSONResponse`;
   - lifecycle через `lifespan`:
     - на startup пишется лог с DB URL;
     - на shutdown освобождается SQLAlchemy engine (`engine_dispose`).

3. Конфиг (`core/config.py`):
   - читается из env-файлов (`two.env`, `.env`) с префиксом `APP__`;
   - типизированные блоки: `run`, `api`, `db`, `gunicorn`, `logging_gunicorn`.

4. База данных (`db_core/db_async.py`):
   - создается `AsyncEngine` и `async_sessionmaker`;
   - для SQLite включается `PRAGMA foreign_keys=ON` на connect;
   - dependency `CurrentSession` внедряется в роуты FastAPI.

5. API-модули:
   - `api/` — демонстрирует dependency-injection подходы;
   - `example_sql/` — реальный CRUD для `User`;
   - `ex_order_product/` — запросы с фильтрацией, сортировкой, joinedload для связей.

6. ORM-модели:
   - `db_core/model_base.py` автоматически строит имена таблиц из CamelCase;
   - `example_sql/models/*` и `ex_order_product/*` определяют схему и связи.

---

## 4) Ответственность ключевых файлов

- Точка входа и сборка приложения:
  - `fastapi-application/main.py`
  - `fastapi-application/create_fastapi.py`
  - `fastapi-application/main_gunicorn.py`

- Конфигурация и логирование:
  - `fastapi-application/core/config.py`
  - `fastapi-application/config_log.py`
  - `fastapi-application/core/gunicorn/*`

- Слой API:
  - `fastapi-application/api/*` — DI/параметры запроса;
  - `fastapi-application/example_sql/router_users.py` — API пользователей;
  - `fastapi-application/ex_order_product/router_order_one.py` — API заказов.

- Слой данных:
  - `fastapi-application/db_core/db_async.py` — engine/session/dependency;
  - `fastapi-application/db_core/model_base.py` — базовый DeclarativeBase;
  - `fastapi-application/db_core/type_for_models.py` — переиспользуемые типы колонок;
  - `fastapi-application/example_sql/models/*`, `fastapi-application/ex_order_product/*`.

- Миграции:
  - `fastapi-application/alembic/env.py`
  - `fastapi-application/alembic/versions/*`

- Инфраструктура/запуск:
  - `pyproject.toml`, `Makefile`, `docker-compose.yml`, `nginx_pg_admin.yml`, `Install-run.md`.

---

## 5) Code Review

Ниже — практическое ревью с приоритизацией.

### ✅ Сильные стороны

1. Хорошая модульность: API, DB-core, конфиг, gunicorn и миграции разнесены по пакетам.
2. Используются современные подходы FastAPI + Pydantic v2 + SQLAlchemy 2.0 async.
3. Есть типизация и response-модели почти во всех роутингах.
4. Продемонстрированы разные стили DI, полезно для обучения и масштабирования.
5. Предусмотрен lifecycle shutdown с `engine.dispose()`.

### ⚠️ Замечания высокого приоритета

1. **Смешение демонстрационного и боевого кода в одном приложении**
   - Роуты-демо DI и прикладные CRUD роуты подключаются вместе.
   - Риск: сложно поддерживать API-контракты и документацию в production.
   - Рекомендация: разделить на `apps/demo` и `apps/service` или фичефлаги.

2. **В `router_order_one.get_all_orders` сравнивается enum-объект со строками**
   - Сейчас: `if params == "time"` / `elif params == "promocode"`.
   - Надежнее и чище: `if params is OrderGetAllOrderbyQuery.time` и т.д.

3. **`OrderResp.promocode: str` конфликтует с nullable полем БД**
   - В модели `Order.promocode` допускается `None`, а response-схема требует `str`.
   - Возможны ошибки сериализации при `NULL` в БД.
   - Рекомендация: сделать `promocode: str | None`.

4. **HTTP-код для «не найдено» выбран как 409**
   - В `get_order_filter_by`/`get_order_where` используется `409 CONFLICT`.
   - Семантически корректнее `404 NOT FOUND`.

### ⚠️ Замечания среднего приоритета

1. **`Makefile` содержит перепутанные команды `up/down`**
   - `up` вызывает `docker-compose ... build`, а `down` — `docker-compose ... up`.
   - Это вероятная опечатка.

2. **Имена и стиль неоднородны**
   - Примеры: `r_users_sql`, `r_order_one`, `router_param_fast_cls_old`.
   - Лучше ввести единый нейминг-конвеншн (например `router_*`).

3. **Логгер по умолчанию пишет в файл, но uvicorn/gunicorn логгеры частично закомментированы**
   - Для эксплуатации полезно унифицировать формат и сделать предсказуемую маршрутизацию логов.

4. **Валидация `query` в `RespDecorValid` не обрабатывает `None`**
   - Сейчас условие `if 1 <= v <= 1000` для `v=None` вызовет TypeError.
   - Нужно первым условием обрабатывать `None`.

### ℹ️ Низкий приоритет / улучшения

1. Добавить тесты (`pytest`, `httpx`, фикстуры БД).
2. Добавить OpenAPI-описания (summary/description/responses/examples).
3. Свести комментарии к «почему», а не «что» (уменьшить избыточность).
4. Добавить pre-commit (ruff/black/isort/mypy).
5. Явно разделить environment-файлы для `dev/stage/prod`.

---

## 6) Рекомендованный план улучшений

1. Исправить схемы/валидацию и HTTP-коды (быстрые безопасные фиксы).
2. Починить `Makefile` и унифицировать запуск/миграции.
3. Вынести demo-роуты в отдельный модуль или отдельный app.
4. Добавить минимум smoke-тестов на ключевые endpoints.
5. Довести логирование и конфиг до production-friendly стандарта.

---

## 7) Вывод

Проект уже полезен как «живой справочник» по FastAPI dependency injection и async SQLAlchemy. При этом, чтобы сделать его production-ready, важно отделить учебные примеры от бизнес-эндпоинтов, синхронизировать схемы данных и response-модели, улучшить семантику ошибок и добавить базовый набор автотестов.
