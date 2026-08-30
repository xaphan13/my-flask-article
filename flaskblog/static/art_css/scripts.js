/* Скрипты сайта. Без глобальных функций и inline-обработчиков:
   - переключатель темы на addEventListener;
   - селектор тёмной темы подсветки hljs (15 вариантов), хранится в localStorage;
   - hljs.highlightAll() только при наличии <pre><code>;
   - синхронизация активной таблицы стилей hljs с темой сайта и выбором пользователя.
   Тема сайта восстанавливается инлайн-скриптом в <head> до загрузки стилей,
   здесь мы только реагируем на клики и поддерживаем синхронизацию.
   Принцип: активная hljs-таблица переключается ДО вызова highlightAll(), поэтому
   классы .hljs на токенах появляются уже после синхронизации — без вспышки цвета. */

(function () {
  'use strict';

  // === Тема сайта ============================================================
  // Значения: 'dark' | 'light'. Хранятся в localStorage['theme'] — формат ключа
  // и значений сохранён, чтобы у уже приходивших посетителей выбор не сбрасывался.

  var STORAGE_KEY = 'theme';
  var VALID = ['dark', 'light'];

  // === Тема подсветки кода ===================================================
  // Список тёмных тем жёстко задан: id должен совпадать с id подключённых в <head>
  // ссылок hljs-theme-<id> и со value <option> в селекторе. Невалидное значение
  // в localStorage откатывается к дефолту — пользовательский ввод из URL/руками
  // не должен ломать подсветку.

  var HLJS_STORAGE_KEY = 'hljs-theme';
  var HLJS_DEFAULT = 'vs2015';
  var HLJS_DARK_THEMES = [
    'vs2015',
    'github-dark',
    'github-dark-dimmed',
    'atom-one-dark',
    'monokai',
    'monokai-sublime',
    'nord',
    'paraiso-dark',
    'stackoverflow-dark',
    'tokyo-night-dark',
    'gradient-dark',
    'night-owl',
    'obsidian',
    'shades-of-purple',
    'ir-black'
  ];

  function readTheme() {
    try {
      var t = localStorage.getItem(STORAGE_KEY);
      return VALID.indexOf(t) >= 0 ? t : 'dark';
    } catch (e) {
      return 'dark';
    }
  }

  function writeTheme(t) {
    try { localStorage.setItem(STORAGE_KEY, t); } catch (e) {}
  }

  function readHljsTheme() {
    try {
      var t = localStorage.getItem(HLJS_STORAGE_KEY);
      return HLJS_DARK_THEMES.indexOf(t) >= 0 ? t : HLJS_DEFAULT;
    } catch (e) {
      return HLJS_DEFAULT;
    }
  }

  function writeHljsTheme(t) {
    try { localStorage.setItem(HLJS_STORAGE_KEY, t); } catch (e) {}
  }

  // Синхронизирует активную таблицу стилей highlight.js с выбранной тёмной темой.
  // Код всегда на тёмном фоне в обеих темах сайта: ссылка светлой темы (vs)
  // всегда disabled, активна ровно одна тёмная ссылка — выбранный пользователем id
  // (или дефолт, если id из localStorage невалиден).
  // Список тёмных ссылок получаем через data-атрибут, чтобы не перечислять id.
  function syncHighlightTheme() {
    var light = document.getElementById('hljs-theme-light');
    var darkLinks = document.querySelectorAll('link[data-hljs-dark]');
    if (!light || !darkLinks.length) return;

    var chosen = readHljsTheme();
    light.disabled = true;
    for (var i = 0; i < darkLinks.length; i++) {
      var link = darkLinks[i];
      var id = link.id.replace(/^hljs-theme-/, '');
      link.disabled = (id !== chosen);
    }
  }

  function applyTheme(t) {
    document.documentElement.setAttribute('data-bs-theme', t);
    syncHighlightTheme();
  }

  // === Подписки на события ===================================================

  function onThemeToggleClick(e) {
    e.preventDefault();
    var current = document.documentElement.getAttribute('data-bs-theme') || 'dark';
    var next = current === 'dark' ? 'light' : 'dark';
    applyTheme(next);
    writeTheme(next);
  }

  function initThemeToggle() {
    var btn = document.getElementById('theme-toggle');
    if (!btn) return;
    btn.addEventListener('click', onThemeToggleClick);
  }

  // Селектор тёмной темы hljs. Применяется мгновенно, если сайт в тёмной теме;
  // в светлой сохраняется в localStorage и подхватится при возврате в тёмную.
  // Повторный highlightAll() не нужен: классы .hljs уже стоят на токенах после
  // первого прохода в init(), а смена таблицы стилей меняет их фон/цвет на лету.
  function onHljsThemeChange(e) {
    var value = e.target.value;
    if (HLJS_DARK_THEMES.indexOf(value) < 0) value = HLJS_DEFAULT;
    writeHljsTheme(value);
    // Селектор работает в обеих темах сайта: код всегда на тёмном фоне,
    // выбор меняет активную hljs-таблицу независимо от темы.
    syncHighlightTheme();
  }

  function initHljsThemeSelect() {
    var sel = document.getElementById('hljs-theme-select');
    if (!sel) return;
    // Защита от рассинхрона: если в разметке появились option-ы, которых нет
    // в нашем списке, удаляем их — value из HTML не должно «протекать» в настройки.
    var known = HLJS_DARK_THEMES;
    var options = sel.querySelectorAll('option');
    for (var i = 0; i < options.length; i++) {
      if (known.indexOf(options[i].value) < 0) {
        options[i].parentNode.removeChild(options[i]);
      }
    }
    sel.value = readHljsTheme();
    sel.addEventListener('change', onHljsThemeChange);
  }

  // === Подсветка кода ========================================================

  function highlightAll() {
    if (typeof hljs === 'undefined') return;
    // Гоняем только при наличии <pre><code> — на страницах без кода нечего подсвечивать.
    if (!document.querySelector('pre code')) return;
    hljs.highlightAll();
  }

  // === Bootstrap collapse для мобильного меню ===============================
  // BS5 сам ведёт data-bs-toggle="collapse"; здесь ничего не требуется,
  // но оставлен якорь на случай, если потребуется делегирование.

  // === Точка входа ==========================================================

  function init() {
    // К моменту DOMContentLoaded инлайн-скрипт уже выставил data-bs-theme
    // (или стоит дефолтный «dark»). Подтянем состояние в одном месте и
    // синхронизируем hljs-таблицу до первого вызова highlightAll().
    var t = document.documentElement.getAttribute('data-bs-theme') || readTheme();
    applyTheme(t);
    initThemeToggle();
    initHljsThemeSelect();
    highlightAll();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();