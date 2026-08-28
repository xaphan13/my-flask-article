**FastAPI Application**

Подробный анализ архитектуры и Code Review

*Март 2026  •  Профессиональный разбор*

| 🏗 Архитектура | 📋 27 файлов | 🐍 Python \+ FastAPI |
| :---: | :---: | :---: |

# **1\. Общее описание проекта**

Репозиторий представляет собой учебно-демонстрационное FastAPI-приложение, цель которого — показать различные способы извлечения и валидации входных параметров HTTP-запросов. Помимо основной темы «параметры запросов», проект демонстрирует работу с базами данных через SQLAlchemy (async), систему зависимостей FastAPI (Depends), Pydantic v2-валидацию, Docker-инфраструктуру и production-запуск через Gunicorn \+ Uvicorn.

## **1.1 Стек технологий**

| Категория | Технология | Роль |
| :---- | :---- | :---- |
| Backend | FastAPI \+ Uvicorn / Gunicorn | HTTP-сервер |
| ORM | SQLAlchemy 2.x (async) | Работа с БД |
| Валидация | Pydantic v2 | Схемы / модели |
| Миграции | Alembic | Версионирование БД |
| Конфигурация | pydantic-settings \+ .env | Настройки приложения |
| БД (prod) | PostgreSQL 16 | Основная СУБД |
| БД (dev) | SQLite (aiosqlite) | Локальная разработка |
| Инфраструктура | Docker Compose \+ Nginx \+ Redis | Контейнеризация |
| Логирование | logging / RotatingFileHandler | Файловые логи |

## **1.2 Ключевые образовательные цели проекта**

* Четыре способа объявления параметров запроса в FastAPI: «старый» стиль (Field=…), Annotated-стиль, через dependency-классы, через dependency-функции

* Pydantic v2: Field, AfterValidator, field\_validator, ConfigDict

* Dependency Injection: простые функции, фабричные функции, dependency-классы (callable \+ метод .as\_dependency)

* SQLAlchemy async: AsyncEngine, async\_sessionmaker, AsyncSession, get\_async\_session как FastAPI dependency

* SQLAlchemy модели: простые таблицы, Mixin-паттерн, many-to-many через association-таблицу

* Gunicorn \+ UvicornWorker: production-конфигурация, кастомный логгер

* Alembic: конфигурация миграций, black-форматирование revisions

* Docker: postgres \+ pgadmin \+ adminer \+ nginx \+ redis

# **2\. Иерархия проекта и описание файлов**

## **2.1 Корневой уровень**

| Файл | Назначение |
| :---- | :---- |
| **docker-compose.yml** | Dev-инфраструктура: PostgreSQL, Adminer (порт 8080), pgAdmin (порт 5050). Простейший набор для локальной разработки без сети. |
| **nginx\_pg\_admin.yml** | Production-инфраструктура: PostgreSQL 16 с именованными томами, pgAdmin, Redis, Nginx — все в изолированной сети app\_net\_new (172.20.0.0/24). |

## **2.2 fastapi-application/ — корень приложения**

| Файл | Назначение |
| :---- | :---- |
| **main.py** | Точка входа. Создаёт FastAPI-приложение, подключает все роутеры (API, SQL-примеры, orders), запускает uvicorn в режиме reload. |
| **main\_gunicorn.py** | Production-запуск через Gunicorn с UvicornWorker. Читает настройки из settings.gunicorn. |
| **create\_fastapi.py** | Фабрика FastAPI-приложения. Настраивает lifespan (startup/shutdown), ORJSONResponse по умолчанию, опциональные кастомные docs-маршруты. |
| **base\_dir\_path.py** | Вычисляет BASE\_DIR (папка файла) и DIR\_CWD (рабочая директория). Используется повсеместно. |
| **config\_log.py** | Настройка логирования через dictConfig. Три именованных логгера: OnlyFile, FileStdout, Stdout. Экспортирует logF (в файл) и logFC (файл \+ консоль). |
| **alembic.ini** | Конфигурация Alembic. Включён post-write hook black для форматирования миграций. URL пока placeholder (driver://...). |

## **2.3 core/ — конфигурация и production-сервер**

| Файл | Назначение |
| :---- | :---- |
| **core/config.py** | Центральный конфиг на pydantic-settings. Модели: GunicornConfig, LoggingConfigGunicorn, RunConfig, ApiV1Prefix, ApiPrefix, DatabaseConfig, Settings. Читает two.env (SQLite) или one.env (Postgres), затем .env. Поддерживает вложенные env-переменные (APP\_\_DB\_\_URL). |
| **core/gunicorn/gunicorn\_app.py** | Обёртка BaseApplication — передаёт FastAPI-приложение и опции в Gunicorn. |
| **core/gunicorn/gunicorn\_log.py** | Кастомный GunicornLogger: форматирует access и error логи по шаблону из settings. |
| **core/gunicorn/gunicorn\_opt.py** | Функция get\_app\_options — собирает словарь опций Gunicorn (bind, workers, loglevel, timeout, worker\_class). |

## **2.4 db\_core/ — база данных**

| Файл | Назначение |
| :---- | :---- |
| **db\_core/db\_async.py** | AsyncDbManager: создаёт AsyncEngine, async\_sessionmaker. get\_async\_session — генератор-dependency с rollback при исключении. CurrentSession — Annotated-тип для инъекции в роуты. SQLite-прагма FOREIGN\_KEYS=ON через event listener. |
| **db\_core/model\_base.py** | Base-класс (DeclarativeBase): автоматически генерирует \_\_tablename\_\_ через camel\_case\_to\_snake\_case \+ суффикс 's'. Хранит naming\_convention для FK, IX, UQ, CK, PK. |
| **db\_core/case\_converter.py** | camel\_case\_to\_snake\_case — конвертирует имя Python-класса в snake\_case для имени таблицы. Корректно обрабатывает аббревиатуры (SomeSDK → some\_sdk). |
| **db\_core/type\_for\_models.py** | Переиспользуемые аннотированные типы для моделей: int\_primary\_key, time\_stamp\_utc (с server\_default=now()), str\_len\_50, str\_len\_100. |
| **db\_core/\_\_init\_\_.py** | Реэкспортирует Base и все модели (User, Post, Order, Product, OrderProductAssociation) для удобного импорта Alembic. |

## **2.5 api/ — маршруты и примеры зависимостей**

| Файл | Назначение |
| :---- | :---- |
| **api/\_\_init\_\_.py** | Корневой router\_api (prefix /api) \+ router\_api\_v1 (prefix /v1). Собирает dep\_examples и param\_extract. |
| **api/dependencies/func\_deps.py** | Функции-зависимости: get\_x\_foo\_bar, get\_header\_dependency (фабрика), get\_great\_helper (вложенные Depends). |
| **api/dependencies/cls\_deps.py** | Классовые зависимости: PathReaderDependency (метод .as\_dependency — Generator), HeaderAccessDependency (callable \_\_call\_\_, валидация токена). |
| **api/dependencies/helper.py** | GreatHelper (обычный \_\_init\_\_) и GreatService (параметры через Header-аннотации — FastAPI dependency injection в конструктор). |
| **api/dependencies/dep\_examp\_simple.py** | 4 маршрута, показывающих Header напрямую, через функцию, через несколько зависимостей одновременно. |
| **api/dependencies/dep\_examp\_cls.py** | 5 маршрутов с классовыми зависимостями: создание в роуте, как Depends, GreatService, PathReader, HeaderAccess. |

## **2.6 api/my\_routes\_dep/ — четыре способа извлечения параметров**

| Файл | Назначение |
| :---- | :---- |
| **my\_param\_fast\_cls.py** | СПОСОБ 1 — «старый» FastAPI-стиль: параметры задаются как default=Path(...), Query(...). Роут /fastapi\_class\_old/my\_items/{item\_id}. |
| **my\_param\_fast\_ann.py** | СПОСОБ 2 — Annotated-стиль: Annotated\[int, Path(...)\]. Тип явно виден IDE. Роут /fastapi\_class\_annotated/my\_items/{item\_id}. |
| **my\_param\_dep\_cls.py** | СПОСОБ 3 — dependency-классы: PathData, QueryData, HeaderData, CookieData каждый через Depends(). Роут /depends\_class\_annotated/my\_items/{item\_id}. |
| **my\_param\_dep\_func.py** | СПОСОБ 4 — dependency-функции: get\_item\_id, get\_param\_id и т.д. каждая через Depends(). Роут /depends\_function\_annotated/my\_items/{item\_id}. |
| **dep\_cls\_schema.py** | Классы PathData, QueryData, HeaderData, CookieData — каждый принимает один параметр через Annotated в \_\_init\_\_, используются для СПОСОБА 3\. |
| **dep\_func\_schema.py** | Функции get\_item\_id / get\_param\_id / get\_user\_id / get\_number\_req — используются для СПОСОБА 4\. |
| **pydantic\_schema.py** | Response-модели RespFieldStyle (Field=... стиль) и RespAnnotated (Annotated-стиль). |
| **pydantic\_validator.py** | Response-модели с продвинутой валидацией: RespAfterValid (AfterValidator, type alias) и RespDecorValid (@field\_validator декораторы). |

## **2.7 example\_sql/ и ex\_order\_product/ — SQL примеры**

| Файл | Назначение |
| :---- | :---- |
| **example\_sql/models/model\_user\_post.py** | Модели User (никнейм, имя, посты) и Post (заголовок, контент, FK на users.id). One-to-many с cascade delete. |
| **example\_sql/models/model\_id\_pk\_mixin.py** | Mixin IntIdPkMixin: добавляет id: Mapped\[int\] primary key с индексом. Используется в TestUser. |
| **example\_sql/models/model\_user\_mix.py** | TestUser — пример использования Mixin \+ Base: name, age, number. |
| **example\_sql/crud/crud\_users.py** | CRUD для User: get\_all\_users (SELECT \+ ORDER BY), create\_user (add \+ commit \+ refresh). |
| **example\_sql/router\_users.py** | Два маршрута: GET /users/get\_all\_users и POST /users/create\_user. Принимают CurrentSession через Depends. |
| **ex\_order\_product/model\_order\_product.py** | Many-to-many: Order ↔ Product через OrderProductAssociation. Содержит count, unit\_price. UniqueConstraint на (order\_id, product\_id). |
| **ex\_order\_product/router\_order\_one.py** | 5 маршрутов: add\_order, insert\_order, get\_order\_filter\_by, get\_order\_where, get\_all\_orders, get\_all\_join (joinedload). |
| **ex\_order\_product/schema\_order\_product.py** | Все Pydantic-схемы для Order/Product/Association: Create, Update, Get, Response \+ вложенные схемы с relationship-данными. |

# **3\. Как работает код: поток запроса**

## **3.1 Запуск приложения**

При запуске через python main.py или uvicorn main:main\_app вызывается create\_app(), которая:

* Создаёт FastAPI-экземпляр с ORJSONResponse и lifespan-контекстным менеджером

* В lifespan (startup) логирует URL базы данных, предупреждает если используется SQLite

* В lifespan (shutdown) вызывает db\_manager.engine\_dispose() — закрывает пул соединений

* Подключаются три набора роутеров: router\_api, r\_users\_sql, r\_order\_one

## **3.2 Обработка HTTP-запроса (пример СПОСОБ 4\)**

Запрос: GET /api/v1/depends\_function\_annotated/my\_items/5?param\_id=100

| Шаг | Компонент | Действие |
| ----- | :---- | :---- |
| **1** | Router | main\_app → router\_api (/api) → router\_api\_v1 (/v1) → router\_param\_extract → router\_param\_dep\_func (/depends\_function\_annotated) |
| **2** | FastAPI DI | Вычисляет дерево зависимостей: get\_item\_id(item\_id=5), get\_param\_id(param\_id=100), get\_user\_id(user\_id=None), get\_number\_req(number\_req=1) |
| **3** | Pydantic | Конвертирует строки URL в нужные типы: '5' → int 5, '100' → int 100\. Применяет ge=1 к item\_id. |
| **4** | Route handler | depends\_function\_annotated() получает готовые значения, логирует, устанавливает X-Custom-Header и cookies в Response. |
| **5** | Response model | Возвращаемый dict сериализуется через RespDecorValid: проверяется диапазон query (1-1000), порт (1024-65535), path \> 0\. |
| **6** | ORJSONResponse | Финальная сериализация в JSON через orjson (быстрее стандартного json). |

## **3.3 Поток работы с базой данных**

Запрос: POST /users/create\_user

* FastAPI вызывает Depends(db\_manager.get\_async\_session)

* AsyncDbManager.get\_async\_session() открывает async with session\_factory() as session

* Генератор yield session передаёт сессию в router-функцию

* crud\_users.create\_user(): создаёт объект User, session.add(), await session.commit(), await session.refresh()

* При исключении: except → await session.rollback() → raise

* После завершения роута: генератор завершается, сессия закрывается автоматически

# **4\. Code Review**

## **4.1 Итоговая оценка**

| Общая оценка | 7.5 / 10 | Хорошая учебная база |
| :---: | :---: | :---: |

## **4.2 Критические и важные замечания**

| Серьёзность | Место | Проблема | Рекомендация |
| :---- | :---- | :---- | :---- |
| 🔴 КРИТИЧНО | alembic.ini | sqlalchemy.url \= driver://user:pass@localhost/dbname — placeholder не заменён. Alembic не будет работать без правильного URL. | Заменить на env\_variable через env\_db\_url или подключить через env.py с settings.db.url |
| 🔴 КРИТИЧНО | schema\_order\_product.pyOrderResp | Поле promocode: str — не Optional\[str\]. Order.promocode в модели Mapped\[str\_len\_50 | None\], т.е. может быть NULL. Это приведёт к ValidationError при None. | Изменить на promocode: str | None \= None |
| 🔴 КРИТИЧНО | router\_order\_one.pyget\_all\_join | Жёсткое обращение result\_scalars\_all\[0\] и \[1\] без проверки наличия записей вызовет IndexError если в БД менее 2 заказов. | Добавить проверку: if len(result\_scalars\_all) \< 2: raise HTTPException(...) |
| 🟠 ВАЖНО | db\_core/db\_async.py | create\_async\_engine вызывается при импорте модуля с жёстко переданным str(settings.db.url). Нет возможности подменить в тестах. | Использовать lazy initialization или передавать URL через фабричную функцию |
| 🟠 ВАЖНО | config\_log.py | ConfigLogger.setting\_path\_logger() вызывается при импорте модуля (глобальный side effect). Это нарушает тестируемость и порядок инициализации. | Перенести вызов в lifespan или в main(), использовать явную инициализацию |
| 🟠 ВАЖНО | pydantic\_validator.pyRespDecorValid | validate\_query\_safe: if 1 \<= v \<= 1000 — когда v is None (поле Optional), будет TypeError. Нет обработки None-случая. | Добавить: if v is None: return None перед проверкой диапазона |
| 🟠 ВАЖНО | router\_order\_one.pyget\_all\_orders | OrderGetAllOrderbyQuery — параметр без Depends(). FastAPI не сможет автоматически распарсить Enum из query string без явного Query() или Depends(). | Добавить: params: OrderGetAllOrderbyQuery \= Query(...) |
| 🟡 УЛУЧШЕНИЕ | db\_core/db\_async.py | pool\_size=50, max\_overflow=10 в AsyncDbManager — значения по умолчанию не совпадают с defaults в DatabaseConfig (pool\_size=50 там, 5 здесь). | Убрать defaults из AsyncDbManager.\_\_init\_\_, всегда передавать из settings |
| 🟡 УЛУЧШЕНИЕ | api/dependencies/cls\_deps.pyPathReaderDependency | Комментарий \# self.\_foobar \= '' закомментирован в cleanup после yield. Возможна утечка state между запросами если объект переиспользуется. | Раскомментировать cleanup или документировать намеренность |
| 🟡 УЛУЧШЕНИЕ | example\_sql/models/model\_user\_mix.py | TestUser используется только как демонстрация Mixin. Не подключён ни к одному роутеру и не экспортируется из db\_core/\_\_init\_\_.py. Alembic создаст лишнюю таблицу. | Добавить в \_\_init\_\_.py или удалить если не нужен |
| 🟡 УЛУЧШЕНИЕ | core/config.py | two.env читается первым (SQLite), one.env (Postgres) закомментирован. При переключении нужно редактировать код. | Использовать один .env с флагом DB\_TYPE или USE\_SQLITE=true |
| 🟢 ХОРОШО | db\_core/db\_async.py | Корректная обработка rollback в get\_async\_session через try/except/raise. Сессия не утекает. | — |
| 🟢 ХОРОШО | db\_core/model\_base.py | Naming convention для всех constraint-типов — отличная практика, упрощает Alembic миграции. | — |
| 🟢 ХОРОШО | core/config.py | Использование pydantic-settings с env\_nested\_delimiter — современный и надёжный подход. | — |
| 🟢 ХОРОШО | api/dependencies/ | Демонстрация всех ключевых паттернов FastAPI DI — educational value высокий. | — |

## **4.3 Архитектурные наблюдения**

### **Структура проекта**

✅  Хорошее разделение слоёв: api (routes) → crud → models → schemas. Следует принципу single responsibility.

✅  db\_core/ вынесен отдельно — правильно, логика БД не смешана с бизнес-логикой.

⚠️  example\_sql/ и ex\_order\_product/ — оба являются 'примерами', но имеют разную глубину структуры. Лучше унифицировать.

❌  Нет разделения на services-слой. CRUD и бизнес-логика смешаны в роутах (router\_order\_one.py). При росте проекта это проблема.

### **Конфигурация и окружение**

⚠️  Два docker-compose файла с дублированием конфигурации postgres. Лучше использовать override-паттерн: docker-compose.yml \+ docker-compose.prod.yml.

⚠️  nginx\_pg\_admin.yml не содержит сервис FastAPI-приложения — неполная production-конфигурация.

❌  В docker-compose.yml нет volumes для PostgreSQL — данные теряются при docker-compose down.

### **Типизация и Pydantic**

✅  Грамотное использование Annotated для типизации параметров — повышает читаемость и поддержку IDE.

✅  type aliases (PathID, QueryID, PortNumber) в pydantic\_validator.py — переиспользуемые типы с валидацией.

⚠️  ConfigDict(frozen=True) в RespAfterValid делает модель immutable — хорошая практика для response-моделей, но может удивить при дебаге.

### **Логирование**

⚠️  logF и logFC — экспортируются как глобальные переменные. При использовании в многопоточном/async-контексте нет проблем с logging, но подход не масштабируется.

⚠️  Закомментированные блоки uvicorn-логгеров в config\_log.py. Лучше удалить или документировать.

## **4.4 Сводная таблица метрик**

| Метрика | Оценка | Комментарий |
| :---- | :---- | :---- |
| Читаемость кода | ⭐⭐⭐⭐⭐ | Отличные аннотации типов, понятные имена |
| Структура проекта | ⭐⭐⭐⭐ | Хорошее разделение, нет services-слоя |
| Обработка ошибок | ⭐⭐⭐ | Частичная: rollback есть, IndexError возможен |
| Тестируемость | ⭐⭐ | Нет тестов, globals при импорте мешают |
| Безопасность | ⭐⭐⭐ | Базовая проверка токена, нет rate limit |
| Production-готовность | ⭐⭐⭐ | Gunicorn есть, Docker неполный, нет healthcheck |
| Документация (code) | ⭐⭐⭐⭐ | Хорошие комментарии на русском в учебных файлах |
| Образовательная ценность | ⭐⭐⭐⭐⭐ | Отличный набор паттернов FastAPI/SQLAlchemy |

# **5\. Приоритизированные рекомендации**

## **Немедленно (блокеры)**

* Исправить alembic.ini: подключить env.py для чтения settings.db.url

* Исправить OrderResp.promocode → Optional\[str\]

* Добавить guard в get\_all\_join перед \[0\] и \[1\]

* Исправить validate\_query\_safe: обработать v is None

## **Краткосрочно (улучшения качества)**

* Добавить volumes в docker-compose.yml для PostgreSQL

* Добавить FastAPI-сервис в nginx\_pg\_admin.yml

* Перенести инициализацию логгера и db\_manager из module-level в lifespan/factory

* Унифицировать структуру example\_sql/ и ex\_order\_product/

* Добавить хотя бы минимальный pytest с httpx.AsyncClient

## **Долгосрочно (архитектура)**

* Выделить services-слой между router и crud

* Добавить healthcheck endpoint (/health) для Docker

* Рассмотреть Dependency Injection контейнер (например, dishka) для управления зависимостями

* Добавить rate limiting (slowapi) для production

* Покрыть тестами минимум 70% кода

| 💡 Вывод Проект является качественной учебной базой с хорошей демонстрацией современных паттернов FastAPI и SQLAlchemy. Код читаемый, типизация продуманная. Для production-использования необходимо устранить критические баги (особенно в схемах и Alembic), добавить тесты и полноценную Docker-инфраструктуру. |
| :---- |

