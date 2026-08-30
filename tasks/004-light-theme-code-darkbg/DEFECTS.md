# Реестр дефектов задачи 003 — доводка подсветки кода

## DEF-001: Базовый цвет блочного кода в светлой теме — rgb(0,0,0) вместо ожидаемого rgb(57,58,52)

- Status: REJECTED
- Severity: LOW
- Found by: qa
- Task: доводка подсветки кода (закрытая задача 003)

Steps to reproduce:
1. Сервер уже поднят: `pgrep -af flaskblog.run` → PID 239242. Если мёртв — запустить из корня `python -m flaskblog.run` в фоне и дождаться `curl http://127.0.0.1:5000/art_home` → 200.
2. Playwright (глобальный), скрипт одним вызовом для обеих тем:
   ```bash
   NODE_PATH=$(npm root -g) node tasks/current/e2e/hljs-colors.js
   ```
   Скрипт: `goto http://127.0.0.1:5000/art/aaa/1787935323` (waitUntil networkidle) → `probe()` считывает getComputedStyle первого `pre code.hljs` (color, backgroundColor) и токенов `.hljs-keyword`/`.hljs-string` из блока с индексом 4; затем `addInitScript(() => localStorage.setItem('theme','light'))` + `reload` (networkidle) → повтор `probe()`.
3. Сырой вывод — `tasks/current/e2e/hljs-colors-check.txt`.

Expected: базовый цвет `pre code.hljs` в светлой теме — rgb(57, 58, 52) (#393a34, тема vs); фактический «зелёный/розовый» из base.css не должен проступать (это в тёмной ожидание rgb(30,255,30), в светлой — rgb(214,51,132)).
Actual: фактический базовый цвет в светлой теме — rgb(0, 0, 0). Тема `vs` (highlight.js) по дефолту использует чёрный текст на белом фоне, а не #393a34 (#393a34 — это цвет темы `vs`, но в канонической поставке highlight.js стиль `pre code.hljs` окрашивается именно в #000). Фон rgb(255,255,255), токены расписаны (kw rgb(0,0,255), str rgb(163,21,21)), инлайн-код rgb(214,51,132) — всё корректно. Тёмная тема — полностью PASS (color rgb(220,220,220), bg rgb(30,30,30), инлайн rgb(30,255,30), токены различаются).
Screenshot: tasks/current/screenshots/code-highlight-light.png (уже снят после правки)

History:
- qa: opened
- оркестратор: REJECTED — дефекта нет. rgb(0,0,0) — канонический базовый цвет темы `vs` из поставки highlight.js (`.hljs{color:black;background:white}`); именно он даёт «как в VSCode» светлую палитру, запрошенную пользователем. Ожидание rgb(57,58,52) в спецификации прогона было ошибочным (оркестратора), код работает как задумано: тёмная — vs2015 rgb(220,220,220)/rgb(30,30,30), светлая — vs rgb(0,0,0)/rgb(255,255,255), токены расписаны темой в обеих темах, инлайн-код сохранил авторские цвета. Исправление не требуется.