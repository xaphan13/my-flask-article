# ADVERSARIAL_REVIEW.md — Управление статьями

Прогон выполнен 2026-08-28 против локально поднятого `python -m flaskblog.run` (БД SQLite).
Бэкап: `/tmp/articles.yaml.adv-backup`; md5 контента: `/tmp/content_md5_backup`.
Сервер погашен (`pkill -f flaskblog.run`), состояние восстановлено (yaml — 4 записи,
content_art — 4 файла).

## ADV-001: Path-traversal и абсолютные пути в `file_name` отклоняются

- Session: Управление статьями | final
- Suggested severity: LOW (работает как задумано)

What I did:
```
POST /art_manage/meta
  file_name=../../../etc/passwd
  file_name=/etc/passwd
  file_name=art/../gemini-pro-fastapi-1.md
  file_name=%2e%2e%2f%2e%2e%2fetc%2fpasswd  (URL-encoded)
  file_name=""                              (пустая строка)
  file_name="  gemini-pro-fastapi-1.md  "  (лидирующие/хвостовые пробелы)
  file_name="Gemini-PRO-FastAPI-1.MD"      (другой регистр)
  file_name=<10000 'a's>                   (очень длинная строка)
```

Expected: каждое имя, не совпадающее с одним из файлов на диске в content_art,
отклоняется флэш-сообщением «Недопустимое имя файла», yaml не меняется.
Actual: всё перечисленное вернуло 302 на `/art_manage`, флэш
`<div class="alert alert-danger">Недопустимое имя файла: …</div>`,
`articles.yaml` остался прежним (4 записи). Защита держится проверкой
`file_name not in disk_files and file_name not in registry_by_file`.

Screenshot: tasks/current/screenshots/adv-manage-light.png (видна плашка
«Нет новых файлов для добавления» как побочный эффект прогона).

Disposition: REJECTED - подтверждение корректной работы, а не дефект: критерий 7 задания требует именно отклонения таких file_name (302 + flash, yaml без изменений), что и наблюдается

## ADV-002: `meta` без обновляемых полей обнуляет существующие author/lang/title

- Session: Управление статьями | final
- Suggested severity: MEDIUM

What I did:
```
# Сначала восстановил оригинальные мета
POST /art_manage/meta  file_name=codex-onefast-review.md  title=""  author=""  lang=""
```

Expected: не изменять ранее заполненные мета-поля, если они не переданы в форме.
Actual: маршрут использует `request.form.get(…).strip()` и слепо подставляет
пустые строки в `ArticleLang.model_copy(update={"author":author,"lang":lang,"title":title})` —
author='', lang='', title='' записаны в yaml. После этого:
- `/art/Max/1787932545` → 404 (статья стала неполной, дизайн-решение 6).
- `/art_home` пуст (т.к. других полных записей нет).
- на `/art_manage` запись помечена «неполная».
Шаблон `art_manage.html` подставляет в `value` исходные значения, но любой
«голый» POST (даже случайный по сгенерированной форме, если поля очистят) —
необратимый data-loss. Конкретный сценарий: пользователь в строке таблицы
чистит поле title и нажимает OK — author/lang тоже зануляются.

Логирование во Flask-логе: информационных следов нет (только
`articles.yaml saved: N entries`).

Disposition: REJECTED - работает как задумано: по контракту POST /art_manage/meta записывает именно переданные значения трёх полей (форма на manage-странице шлёт их все с префиллом); очистка меты - штатный способ перевести статью в неполные (решение 6), обратимая операция - мета восстанавливается той же формой, yaml под контролем git

## ADV-003: POST `/art_manage/meta` и `/art_manage/add_all` без CSRF-токена

- Session: Управление статьями | final
- Suggested severity: MEDIUM

What I did:
```
# Залогиненный пользователь (cookie сессии валидная), без CSRF-токена
POST /art_manage/meta     file_name=codex-onefast-review.md  title=Foo
POST /art_manage/add_all
```

Expected: для защиты от CSRF нужен валидный CSRF-токен (как в
`/login`, `/register`, `/account` — там `FlaskForm.validate_on_submit` отбрасывает
запрос без csrf_token).
Actual: оба POST принимаются и модифицируют реестр без CSRF-токена.
`validate_on_submit`/CSRF здесь не задействованы (поля читаются
напрямую через `request.form.get`). Доступ к `/art_manage/*` всё равно только
через `@login_required`, поэтому анонимные атаки не работают, но залогиненного
пользователя можно CSRF-формой на чужом сайте заставить добавить/обнулить запись.

Disposition: REJECTED - вне рамок задания: раздел «Вне рамок» явно исключает всё, кроме @login_required, по разграничению доступа; CSRFProtect - глобальное изменение фабрики приложения (затронуло бы все формы), подлежит отдельному заданию. Замечание передано пользователю в отчёте

## ADV-004: Конкурентные POST add_all + meta — атомарная запись, без частичного yaml

- Session: Управление статьями | final
- Suggested severity: LOW (работает как задумано, закреплено в «Принятых решениях»)

What I did:

1. Сценарий A — 5 параллельных `POST /art_manage/add_all`, когда 2 файла
   нераспределены (`gemPro-book1-g.md`, `FastAPI_CodeReview.docx.md`).

```
$ parallel 5x add_all
count: 4
IDs: [5, 1787932545, 1787933599, 1787933600]
files: [..., 'FastAPI_CodeReview.docx.md', 'gemPro-book1-g.md']
id dups: []   file dups: []
```

2. Сценарий B — параллельный `add_all` + `meta` на один файл.

3. Сценарий C — два параллельных `meta` на один и тот же `file_name`
   с разными title: `TitleA1` vs `TitleA2`.

Expected: не должно возникать дубликатов art_id, дубликатов file_name,
битого yaml, потери записей; частичный файл недопустим.
Actual: `save_articles` всегда идёт через `tempfile.mkstemp` + `os.replace` —
уникальные tmp-имена на каждый процесс, атомарный rename, частичного файла не
бывает. В каждом из трёх сценариев: нет дублей по art_id, нет дублей по
file_name, итоговый yaml валиден (`yaml.safe_load` без исключений). В сценарии C
побеждает последний writer (`title=TitleA2`) — это ожидаемо по решению 2.
В сценарии A 5 процессов пришли с пустым `_last_stat`-кэшем; только первый
запрос фактически добавляет записи; остальные четыре перечитывают
обновлённый yaml и видят «нечего добавлять».

Замечание о поведении `_allocate_art_id`: при первом сохранении двумя
процессами в одну и ту же секунду оба получат одинаковый
`int(time.time())` — но текущая логика всё равно работает, потому что каждый
процесс сохраняет только СВОЙ инкремент и tmp+rename атомарен; маловероятная
коллизия art_id теоретически возможна при двух независимых запросах за
1 секунду с 0 нераспределёнными файлами (тогда оба уйдут в «ничего не
добавлять» и не сохраняют). На практике за время прогона коллизию получить
не удалось.

Disposition: REJECTED - работает как задумано: раздел «Риски» REQUIREMENTS.md фиксирует «последний атомарный write побеждает, частичного файла не бывает» - наблюдаемое поведение точно этому соответствует

## ADV-005: Битый yaml — публичные маршруты остаются 200, ошибка видна только на manage

- Session: Управление статьями | final
- Suggested severity: LOW (работает как задумано, закреплено в «Принятых решениях»)

What I did: последовательно клал в `articles.yaml`:
1. пустой файл (`>`);
2. `articles: this-is-not-a-list`;
3. запись без обязательного поля `lang`;
4. запись с нечисловым `art_id: "not-a-number"`;
5. две записи с одинаковым `art_id=10`;
6. реально битый YAML с лидирующими пробелами, ломающими `mapping values`;
7. запись с лишними `extra_field`, `injection: "<script>…</script>"`, дубль `lang`.

Expected: ошибка логируется, на `manage`-странице показано
«последнее рабочее состояние», `/art_home` и `/art/<author>/<id>` возвращают
200 на старом кэше, после починки yaml всё восстанавливается без перезапуска.

Actual:
- `/art_home` = 200, `/art/Max/5` = 200, `/art_manage` = 200 во всех семи
  вариантах; никаких 500.
- На manage-странице видна красная плашка
  `alert alert-danger` с текстом ошибки (например,
  `mapping values are not allowed here … line 4, column 13`,
  `1 validation error for ArticleLang`,
  `argument after ** must be a mapping, not str`).
- В логе `FileStdout.ClientHTTPS` строка
  `ERROR: Failed to parse articles.yaml: …`.
- После возврата валидного yaml — следующий запрос перечитал файл по
  `(st_mtime_ns, st_size)`, ошибка ушла, статьи снова видны.
- Запись с «лишними» полями (`extra_field`, `injection`, дубль `lang`):
  Pydantic проглотил, ничего не упало, на `/art_home` отображается штатный
  заголовок.

Screenshot: tasks/current/screenshots/adv-manage-light.png

Disposition: REJECTED - работает как задумано: решения 3 и контракт (битый yaml -> предыдущее рабочее состояние, лог, ошибка на manage-странице) выполнены в точности; критерий 8 подтверждён

## ADV-006: `art_author` и `/art_home` правильно прячут «нет файла» и «неполную мету»

- Session: Управление статьями | final
- Suggested severity: LOW (работает как задумано — решение 6)

What I did:
```
mv flaskblog/templates/content_art/gemPro-book1-g.md /tmp/gemPro-book1-g.md.advtest
GET /art_manage
GET /art/Max/1787932546
mv /tmp/gemPro-book1-g.md.advtest flaskblog/templates/content_art/gemPro-book1-g.md
GET /art_manage
```

Expected: при отсутствии файла / неполной мете — `/art_manage` помечает
«нет файла» / «неполная» и дублирует в секции «Записи без файла»;
`/art/<author>/<id>` отдаёт 404; после возврата файла — всё чисто.

Actual:
- В секции «Все статьи» у строки id=1787932546 появляются оба бейджа
  `badge-danger «нет файла»` и `badge-warning «неполная»`.
- В отдельной секции «Записи без файла» — строка
  `<strong>#1787932546</strong> gemPro-book1-g.md gemPro-book1-g`.
- `/art/Max/1787932546` → 404 (также потому, что пустые author/lang).
- После восстановления файла: секция «Записи без файла» показывает «Пусто.`,
  ни одного `badge-danger` нигде. md5 всех файлов content_art совпадает с
  бэкапом.

Screenshot: tasks/current/screenshots/adv-manage-missing-file-light.png

Disposition: REJECTED - работает как задумано: 404 по прямой ссылке при отсутствии файла или полной меты - прямое требование контракта к art_author; manage-страница корректно отражает оба состояния

## ADV-007: Jinja autoescape защищает /art_home и /art/<id> от XSS

- Session: Управление статьями | final
- Suggested severity: LOW (работает как задумано)

What I did:
```
POST /art_manage/meta
  file_name=codex-onefast-review.md
  author=<script>alert('xss')</script>
  title=<img src=x onerror=alert(1)>
  lang=Python
```

Expected: опасные последовательности экранируются Jinja-автоэскейпом;
`/art_home` и страница статьи возвращают HTML, где `<` заменён на `&lt;`.
Actual: в сыром HTML-ответе:
- `&lt;img src=x onerror=alert(1)&gt;`
- `&lt;script&gt;alert(...)
Никакого исполняемого `<script>` или `<img onerror>` в выдаче не появилось;
`/art/Max/1787932545` отдаёт 200 и тот же экранированный текст. Защита держится
за счёт дефолтного `autoescape=True` у Flask/Jinja.

Disposition: REJECTED - подтверждение корректной работы (autoescape Jinja), дефекта нет

## ADV-008: Нет валидации длины полей — title/author принимают 10k–50k символов

- Session: Управление статьями | final
- Suggested severity: LOW

What I did:
```
POST /art_manage/meta  file_name=codex-onefast-review.md  author=<50000 'A's>
POST /art_manage/meta  file_name=codex-onefast-review.md  title=<10000 'A's>
```

Expected: Pydantic-схема `ArticleLang` не задаёт `max_length` ни для одного из
полей, WTForms-валидатора тоже нет — большие значения будут приняты.
Actual: оба POST вернули 302, `articles.yaml` сохранил соответствующие поля
(`author len: 50000`, `title len: 10000`). `/art_home` ответил 200
(ответ вырос с ~15K символов до неприличных размеров). Никаких следов
`400/422/MAX_FORM_MEMORY_SIZE` — `MAX_FORM_MEMORY_SIZE=500000` байт
(по умолчанию `flaskblog.config`) сработает только на ещё бо́льших payload'ах.

Disposition: REJECTED - вне рамок задания: лимиты длины полей и санитизация значений не входят в контракт; для личного сайта приемлемо, потенциальный кандидат в будущие улучшения

## ADV-009: Допускаются управляющие символы и Unicode (emoji) в title

- Session: Управление статьями | final
- Suggested severity: LOW

What I did:
```
POST /art_manage/meta
  file_name=codex-onefast-review.md
  title=Tab	here and bell\x07     (таб + \x07)
  title=Тест 🚀 статья 📚
```

Expected: всё проходит (нет санитизации), yaml использует `allow_unicode=True`.
Actual: оба варианта записаны, перечитаны через `yaml.safe_load` без потерь.
`\x07` сохранён как управляющий символ в yaml-эскейпе `\a`, `🚀`/`📚` сохранены
и рендерятся (страница статьи не загрузилась только потому, что author/lang к
этому моменту уже были пустыми — из ADV-002). В самом yaml экранирование
корректное.

Disposition: REJECTED - вне рамок задания: санитизация значений не входит в контракт; Unicode-контент корректно переживает цикл запись-чтение

## ADV-010: `add_all` с уже распределёнными файлами — корректный flash, без мутаций

- Session: Управление статьями | final
- Suggested severity: LOW (работает как задумано)

What I did:
```
POST /art_manage/add_all   (все 4 файла уже зарегистрированы)
```

Expected: 302 на manage, флэш «Нет новых файлов для добавления», yaml не
меняется.
Actual: на `/art_manage` после редиректа видна плашка
`<div class="alert alert-info">Нет новых файлов для добавления</div>`.
yaml — те же 4 записи, без следов мутаций.

Disposition: REJECTED - работает как задумано: штатный flash при пустом списке нераспределённых

## ADV-011: Неаутентифицированные GET/POST на manage-маршрутах перенаправляют на /login

- Session: Управление статьями | final
- Suggested severity: LOW (работает как задумано, `@login_required`)

What I did:
```
GET   /art_manage
POST  /art_manage/add_all
POST  /art_manage/meta
```
без cookie-jar.

Expected: 302 → `/login?next=…`.
Actual:
- `GET /art_manage`        → 302 → `…/login?next=%2Fart_manage`
- `POST /art_manage/add_all` → 302 → `…/login?next=%2Fart_manage%2Fadd_all`
- `POST /art_manage/meta`    → 302 → `…/login?next=%2Fart_manage%2Fmeta`

Disposition: REJECTED - работает как задумано: решение 8 (страница управления за @login_required) выполнено

## ADV-012: Прямой GET на POST-эндпоинтах даёт 405

- Session: Управление статьями | final
- Suggested severity: LOW (работает как задумано, Flask `methods=["POST"]`)

What I did:
```
GET /art_manage/add_all
GET /art_manage/meta?file_name=…&title=HackViaGet
```

Expected: 405 Method Not Allowed, никакого побочного эффекта.
Actual:
- `GET /art_manage/add_all` → 405, стандартная страница Flask
  «The method is not allowed for the requested URL».
- `GET /art_manage/meta?…`  → 405, yaml не изменился
  (`title` остался прежним).

Disposition: REJECTED - работает как задумано: стандартное поведение Flask для POST-маршрутов, побочных эффектов нет

## ADV-013: `add_all` игнорирует посторонние поля формы

- Session: Управление статьями | final
- Suggested severity: LOW (работает как задумано)

What I did:
```
POST /art_manage/add_all  extra=ignore  author=Bob
```

Expected: 302, в yaml попадают только 5 канонических полей
(`author`, `lang`, `art_id`, `title`, `file_name`); значения `extra`/`author`
из POST не подставляются новым записям.
Actual: в `articles.yaml` все 4 записи — по 5 полей, никакого `extra`,
`author` у созданных записей пустой (`""`). Тело `add_all` не читает `request.form`,
берёт только то, что обнаружено сканированием диска.

Disposition: REJECTED - работает как задумано: в yaml попадают только канонические 5 полей записи

## ADV-014: Реестр обнаруживает ручную правку yaml без перезапуска

- Session: Управление статьями | final
- Suggested severity: LOW (работает как задумано, критерий успеха №6)

What I did:
```
# sed -i 's/Репозиторий для Telegram-магазина-/Модифицировано вручную через yaml/'
GET /art_home
```

Expected: mtime-ключ меняется → кэш инвалидируется → следующий GET видит
новый title.
Actual: `/art_home` отдал `Модифицировано вручную через yaml` в первом же
запросе после правки; процесс сервера не перезапускался.

Disposition: REJECTED - подтверждение корректной работы: это и есть критерий успеха 6 (mtime-кэш перечитывает yaml без перезапуска)
