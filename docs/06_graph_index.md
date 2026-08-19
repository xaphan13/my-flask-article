# 06 — Индекс кодовой базы и архитектура по измерениям

Дополнение к `02_architecture.md`. Там архитектура описана по чтению кода — здесь то же
приложение, но **измеренное** по графу вызовов: связность, когезия модулей, точки
концентрации зависимостей, метрики сложности. Плюс рабочая инструкция по самому индексу.

Состояние на момент снятия: ветка `prod-one`, HEAD `d5479d9`, 2026-08-19.
Часть наблюдений снята с рабочей копии, где есть незакоммиченные правки — см. раздел 4.

---

## 1. Индекс кодовой базы

Проект проиндексирован в граф `codebase-memory-mcp`.

| | |
|---|---|
| Имя проекта в индексе | `home-max-0_0_26_new_one-my-flask-article` |
| Корень | `/home/max/0_0_26_new_one/my-flask-article` |
| Узлов / рёбер | 571 / 926 |
| Типов рёбер | 14 |
| Режим индексации | `full` (включая similarity/semantic-рёбра) |
| Статус | `ready`, автообновление в фоне |

Индекс хранится **вне репозитория**, в `~/.cache/codebase-memory-mcp/`. В git не попадает
и на сборку не влияет. Пересоздать его можно в любой момент — это дешёвая производная от
кода, а не источник истины.

### 1.1. Распределение рёбер

```
DEFINES 598   USAGE 72   CONTAINS_FILE 69   CALLS 57   WRITES 29
IMPORTS 25    DECORATES 18   CONTAINS_FOLDER 16   DEFINES_METHOD 16
HANDLES 12    CONFIGURES 8   INHERITS 4   HAS_BRANCH 1   SIMILAR_TO 1
```

`CALLS` всего 57 при 598 `DEFINES` — соотношение, характерное для проекта, где почти вся
работа делегирована фреймворкам, а собственного кода-логики мало.

### 1.2. Покрытие: где графу нельзя доверять

Индексатор сообщает два класса неполноты. **Отсутствие файла в этих списках не является
гарантией полноты** — сигнал best-effort.

`parse_partial` — файл проиндексирован, но конструкции в указанных строках могли не попасть
в граф. Здесь надёжнее `grep`:

| Файл | Строки |
|---|---|
| `flaskblog/templates/content_art/art4.html` | 1–220 |
| `nginx/nginx.conf` | 1–29 |

`skipped` (не проиндексировано вовсе) — **пусто**, 0 файлов.

Исключено сознательно (`not_indexed`, 15 каталогов + 4 файла): `.git`, `.claude`, `.idea`,
`.venv`, все `__pycache__`, `log`, `log_app`, `instance`, `pg_db`, а также `*.jpg` в
`static/profile_pics/` (ignored-suffix) и `nginx/cert/*.pem` (по `nginx/cert/.gitignore`).
Это правила, а не сбои.

### 1.3. Ограничения индексатора на Flask

Несколько мест, где сводки графа выглядят пустыми — это свойство инструмента, а не кода:

- В таблице `packages` все `fan_in`/`fan_out` нулевые.
- В таблице `routes` не заполнена колонка handler, хотя связь route → обработчик в графе
  есть в виде 12 рёбер `HANDLES`.
- В `layers` присутствует строка с пустым именем пакета.

Причина — маршруты объявлены декораторами блюпринтов, и статически связать URL с функцией
индексатор может, а разложить это по сводным таблицам — нет.

### 1.4. Рабочие запросы

Обновить индекс после крупных внешних изменений (обычно не нужно — обновляется сам):

```
index_repository(repo_path=".", mode="full")
```

Проверить здоровье и покрытие:

```
index_status(project="home-max-0_0_26_new_one-my-flask-article")
check_index_coverage(project=..., paths=["flaskblog/config.py"])
```

Найти символ, затем прочитать его точный исходник:

```
search_graph(project=..., query="save picture thumbnail")
get_code_snippet(project=..., qualified_name="<полное имя из search_graph>")
```

Кто вызывает функцию и что вызывает она:

```
trace_path(project=..., function_name="create_app", direction="both", depth=3)
```

Радиус влияния незакоммиченных правок:

```
detect_changes(project=..., base_branch="master", direction="inbound")
```

Метрики сложности по всем функциям (Cypher):

```cypher
MATCH (f) WHERE (f:Function OR f:Method) AND f.complexity IS NOT NULL
RETURN f.qualified_name, f.complexity, f.cognitive, f.loop_depth,
       f.transitive_loop_depth, f.linear_scan_in_loop
ORDER BY f.complexity DESC LIMIT 25
```

Структура файлов, которые индексатор не разобрал полностью:

```cypher
MATCH (f:File) WHERE f.kind = "parse_partial" RETURN f.file_path, f.detail
```
(с параметром `graph="missed"`)

---

## 2. Архитектура по измерениям

### 2.1. Форма: плоская, два слоя

Классификация пакетов по графу вызовов:

| Пакет | Слой | Основание |
|---|---|---|
| `main`, `users`, `new_articles` | entry | только исходящие вызовы |
| `models` | internal | fan-in 1, fan-out 2 |
| `dict` (builtin) | core | fan-in 4 |
| `int` (builtin) | leaf | только входящие |

Блюпринты — вершины графа: внутри кода их не вызывает никто, только диспетчер Flask. Под
ними единственный слой `models`. Сервисного слоя, репозиториев, use-case'ов нет —
подтверждение того, что в `02_architecture.md` описано как «тонкий контроллер над ORM».

### 2.2. Связность: практически нулевая

Полный список межпакетных вызовов, с весами:

```
users        → models   1     ← единственная реальная связь внутри приложения
users        → dict     1
models       → dict     1
models       → int      1
new_articles → dict     1
main         → dict     1
```

Кроме `users → models` всё остальное — обращения к билтинам. Блюпринты не знают друг о
друге ничего.

Важное следствие: связь между ними существует **только через строковые имена эндпоинтов**
в `url_for` (`main.home` → `art_main.art_home`, `users.login` в `login_manager.login_view`).
Граф такие связи рёбрами не считает, и никакой другой механизм их тоже не проверяет.
Переименование эндпоинта не поймает ни линтер, ни типы, ни этот граф — только запуск.
Это самая хрупкая точка в архитектуре, и она невидима статически.

### 2.3. Точка концентрации — логгер

Топ по fan-in:

```
ConfigLogger.getLogger            6      ← самый востребованный символ проекта
git_manager.execute_command       5
docker_manager.execute_command    3
create_app                        2
save_picture                      1
ConfigLogger.settingLogger        1
ConfigLogger.__createLogDir       1
```

Самая связанная точка кодовой базы — не фабрика приложения и не модели, а `getLogger`.
Шесть модулей зависят от `flaskblog/logger/config_log.py`, который сам тянет `config.py` и
далее `local.env`.

Следствие для эксплуатации: **`logger/config_log.py` — единственный модуль, поломка которого
валит импорт всего приложения**, причём на этапе импорта, до создания app и до любых
обработчиков ошибок. Это прямая цена стиля «инициализировать логгер до остальных импортов»
(из-за него же в `pyproject.toml` заглушены `E402` и `F401`).

### 2.4. Когезия: девять изолированных островов

Leiden-разбиение по графу вызовов, cohesion 1.0 у каждого кластера (внутри плотно, между
ними пусто):

| # | Смысл | Члены | Размер |
|---|---|---|---|
| 3 | аутентификация | `login`, `load_user`, `LoginForm` | 6 |
| 13 | `git_manager.sh` | `execute_command`, `git--branch/status/commit` | 6 |
| 47 | `docker_manager.sh` | `execute_command`, `container--start/stop`, `network--create` | 4 |
| 16 | файловые статьи | `art_author`, `read_html`, `get_path_dir` | 3 |
| 30 | регистрация | `register`, `RegistrationForm`, `User` | 3 |
| 33 | аккаунт и аватар | `account`, `UpdateAccountForm`, `save_picture` | 3 |
| 50 | логгер | `getLogger`, `settingLogger`, `__createLogDir` | 3 |
| 5 | лента статей | `art_home` | 2 |
| 45 | `docker_manager.sh` | `rm-on-exit`, `container--file` | 2 |

Два вывода:

1. **Фактические модули совпадают с каталогами.** Обычно кластеризация вскрывает швы,
   идущие вразрез с раскладкой папок. Здесь нет: `users/`, `new_articles/`, `logger/` и есть
   настоящие модули. Раскладка проекта честная, рефакторинг по границам папок безопасен.
2. **Самый структурированный код в репозитории — не приложение, а shell-обвязка.**
   `git_manager` (6 членов) и `docker_manager` (4+2) имеют больше внутренних вызовов, чем
   любая часть Flask-приложения.

Кластер 16 (`art_author` + `read_html` + `get_path_dir`) изолирован полностью — это значит,
что починка cwd-зависимости в `get_path_dir()` затрагивает ровно три функции и ничего больше.

### 2.5. Алгоритмической сложности нет

По всем функциям и методам проекта:

```
максимум cyclomatic         1
максимум cognitive          1
loop_depth                  0 везде (единственное исключение: docker_manager.on-exit = 1)
transitive_loop_depth       0
linear_scan_in_loop         0
recursive                   нет ни одной
unguarded_recursion         нет
```

Ни вложенных петель, ни линейных сканов в цикле, ни рекурсии. Приложение целиком состоит из
I/O и склейки; вся реальная работа внутри Flask, SQLAlchemy, Pydantic и Pillow.

Практический вывод для `05_optimization_roadmap.md`: **объекта для оптимизации Python-логики
здесь нет.** Узкие места, когда появятся, будут в БД-запросах и в `read_html()`, читающем
файл с диска на каждый запрос, — не в вычислениях.

### 2.6. Подтверждение мёртвого кода

Граф независимо подтверждает то, что `01_project_structure.md` фиксирует по чтению:
у пакета `models` fan-in равен 1, и единственный входящий вызов идёт от `users`, то есть к
`User`. **Модель `Post` не упоминается ни в одном кластере и ни в одном хотспоте** — ни один
маршрут её не использует.

---

## 3. Маршруты по графу

12 URL-правил (плюс `static` от Flask = 13), совпадает с `03_execution_flow.md`:

```
/                              /home                /about
/art_home                      /art/<string:author>/<int:art_id>
/register                      /login               /logout        /account
/createDB                      /createDB/           /createDB/<int:post_id>
```

Метод в графе указан как `ANY` — индексатор не разбирает аргумент `methods=[...]` в
декораторе. Фактические методы см. в `03_execution_flow.md`.

---

## 4. Расхождения с 01–05, выявленные при проверке

Документы 01–05 писались по состоянию коммита. В рабочей копии есть незакоммиченные
правки, которые меняют выводы. Зафиксировано здесь, чтобы не потерялось.

### 4.1. Дефект B2 закрыт незакоммиченной правкой

`04_code_quality.md` §4 (B2) утверждает: Docker-контур не стартует, потому что в
`dock_flask.env` нет `DATABASE_URI`, а сборка DSN из `DB_*` в `config.py` закомментирована →
`SQLALCHEMY_DATABASE_URI` = `None` → `RuntimeError`.

В рабочей копии это **перевёрнуто** (`git diff flaskblog/config.py`):

```diff
-    # SQLALCHEMY_DATABASE_URI = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
-    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URI")
+    SQLALCHEMY_DATABASE_URI = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
+    # SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URI")
```

DSN теперь собирается из `DB_USER/PASSWORD/HOST/PORT/NAME`, которые в `dock_flask.env` есть.
**B2 в текущей рабочей копии не воспроизводится.**

Обратная сторона: для локального запуска теперь недостаточно `DATABASE_URI` — нужны все пять
`DB_*`. Таблица переменных в `setup-and-run.md` §Конфигурация и в `README.md` описывает
прежнюю схему и **устарела**. `DB_HOST`/`DB_PORT` из «читаются, но не влияют» стали
обязательными.

Второй незакоммиченный диф (`__init__.py`) — только смена метки в логе, `'create_app 5'` →
`'create_app 6'`, на поведение не влияет.

### 4.2. Секреты находятся в git — вопреки README и 01

`README.md` и `01_project_structure.md` утверждают, что `local.env` и
`flaskblog/dock_flask.env` в git не входят и создаются вручную. Проверено — это не так:

```
$ git ls-files | grep -E '\.env$'
.env
flaskblog/dock_flask.env
local.env
```

Все три файла **отслеживаются git**. В корневом `.gitignore` правила для env закомментированы:

```
# Environment
#*.env
#.env
```

То есть в истории репозитория лежат `SECRET_KEY`, `DB_PASSWORD` и учётные данные pgAdmin.
Это усиливает дефект B1 из `04_code_quality.md` (утечка `SECRET_KEY` в логи): ключ
скомпрометирован не только через логи, но и через саму историю коммитов, а значит смена
ключа требует ещё и вычистки истории.

Сертификаты, в отличие от env, игнорируются корректно — но не корневым файлом, а вложенным
`nginx/cert/.gitignore` с правилом `*.pem`.

---

## 5. Что этим документом не проверялось

- Шаблоны и статика как таковые: `art4.html` разобран индексатором лишь частично (см. 1.2),
  по нему граф неполон.
- Рёбра `SIMILAR_TO` (всего 1) и семантические связи не анализировались.
- Радиус влияния правок через `detect_changes` не снимался: `base_sha` совпадает с `head_sha`,
  а незакоммиченные изменения затрагивают два файла, разобранные вручную в §4.
- Метрики сложности сняты по узлам графа. Для файлов из `parse_partial` они могут быть
  занижены.
