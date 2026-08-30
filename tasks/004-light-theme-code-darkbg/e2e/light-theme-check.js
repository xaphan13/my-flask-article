// Playwright-проверка светлой/тёмной тем после правок frontend-dev (задание 004).
// Один скрипт: проверяет body, pre code.hljs, инлайн code, селектор hljs, хедер, data-bs-theme.

const { chromium } = require("playwright");

const URL = "http://127.0.0.1:5000/art/aaa/1787935323";

function fmt(rgb) {
  return rgb || "(empty)";
}

async function runOne(page, themeName, results) {
  await page.goto(URL, { waitUntil: "networkidle" });

  // data-bs-theme сразу после networkidle (до полного рендера body)
  const bsTheme = await page.evaluate(
    () => document.documentElement.getAttribute("data-bs-theme")
  );
  results.push(`[${themeName}] data-bs-theme на <html> после networkidle = ${bsTheme}`);

  // 1. body фон
  const bodyBg = await page.evaluate(
    () => getComputedStyle(document.body).backgroundColor
  );
  results.push(`[${themeName}] body.backgroundColor = ${fmt(bodyBg)}`);

  // 2. pre code.hljs фон
  const preHljsBg = await page.evaluate(() => {
    const el = document.querySelector("pre code.hljs");
    return el ? getComputedStyle(el).backgroundColor : "(no pre.hljs)";
  });
  results.push(`[${themeName}] pre code.hljs.backgroundColor = ${fmt(preHljsBg)}`);

  // 3. инлайн code (не внутри pre)
  const inlineCode = await page.evaluate(() => {
    const all = Array.from(document.querySelectorAll("code"));
    const inline = all.find((c) => !c.closest("pre"));
    if (!inline) return { bg: "(no inline code)", color: "(no inline code)" };
    const cs = getComputedStyle(inline);
    return { bg: cs.backgroundColor, color: cs.color };
  });
  results.push(
    `[${themeName}] inline code.backgroundColor = ${fmt(inlineCode.bg)}`
  );
  results.push(
    `[${themeName}] inline code.color = ${fmt(inlineCode.color)}`
  );

  // 4. селектор темы hljs (только светлая — там нас интересует смена)
  if (themeName === "light") {
    // baseline фон (vs2015)
    const baselineBg = await page.evaluate(() => {
      const el = document.querySelector("pre code.hljs");
      return el ? getComputedStyle(el).backgroundColor : "(no pre.hljs)";
    });
    results.push(`[light] baseline pre.hljs фон (vs2015) = ${fmt(baselineBg)}`);

    // есть ли селектор
    const selectorExists = await page.evaluate(
      () => !!document.querySelector("#hljs-theme-select")
    );
    results.push(`[light] #hljs-theme-select существует = ${selectorExists}`);

    // получить доступные опции
    const options = await page.evaluate(() => {
      const sel = document.querySelector("#hljs-theme-select");
      if (!sel) return [];
      return Array.from(sel.options).map((o) => ({
        value: o.value,
        disabled: o.disabled,
        selected: o.selected,
      }));
    });
    results.push(`[light] опции селектора: ${JSON.stringify(options)}`);

    // выбрать monokai
    await page.selectOption("#hljs-theme-select", "monokai");
    await page.waitForTimeout(300);
    const monokaiBg = await page.evaluate(() => {
      const el = document.querySelector("pre code.hljs");
      return el ? getComputedStyle(el).backgroundColor : "(no pre.hljs)";
    });
    results.push(
      `[light] после выбора monokai pre.hljs фон = ${fmt(monokaiBg)}`
    );

    // вернуть vs2015
    await page.selectOption("#hljs-theme-select", "vs2015");
    await page.waitForTimeout(300);
    const restoredBg = await page.evaluate(() => {
      const el = document.querySelector("pre code.hljs");
      return el ? getComputedStyle(el).backgroundColor : "(no pre.hljs)";
    });
    results.push(`[light] после возврата vs2015 pre.hljs фон = ${fmt(restoredBg)}`);
  }

  // 5. тёмная тема — токены
  const tokenColor = await page.evaluate(() => {
    const kw = document.querySelector(".hljs-keyword");
    return kw ? getComputedStyle(kw).color : "(no .hljs-keyword)";
  });
  results.push(`[${themeName}] .hljs-keyword.color = ${fmt(tokenColor)}`);

  // 6. хедер (только светлая)
  if (themeName === "light") {
    const headerBg = await page.evaluate(() => {
      const el =
        document.querySelector(".backcolor-header") ||
        document.querySelector(".site-header") ||
        document.querySelector("header") ||
        document.querySelector("nav");
      if (!el) return "(no header)";
      const cs = getComputedStyle(el);
      return { bg: cs.backgroundColor, tag: el.tagName, cls: el.className };
    });
    results.push(
      `[light] header = ${JSON.stringify(headerBg)}`
    );
  }

  // bonus: список подключённых hljs-стилей (link href) — какой реально активен
  const hljsLinks = await page.evaluate(() => {
    return Array.from(document.querySelectorAll('link[rel="stylesheet"]'))
      .map((l) => l.href)
      .filter((h) => /hljs/i.test(h));
  });
  results.push(`[${themeName}] подключённые hljs-стили: ${JSON.stringify(hljsLinks)}`);
}

(async () => {
  const browser = await chromium.launch();
  const lines = [];
  lines.push(`URL: ${URL}`);
  lines.push(`Дата: ${new Date().toISOString()}`);

  // --- LIGHT ---
  const ctxLight = await browser.newContext({
    viewport: { width: 1280, height: 800 },
  });
  await ctxLight.addInitScript(() =>
    localStorage.setItem("theme", "light")
  );
  const pLight = await ctxLight.newPage();
  const lightResults = [];
  await runOne(pLight, "light", lightResults);
  await ctxLight.close();

  // --- DARK ---
  const ctxDark = await browser.newContext({
    viewport: { width: 1280, height: 800 },
  });
  await ctxDark.addInitScript(() => localStorage.setItem("theme", "dark"));
  const pDark = await ctxDark.newPage();
  const darkResults = [];
  await runOne(pDark, "dark", darkResults);
  await ctxDark.close();

  await browser.close();

  lines.push("");
  lines.push("===== LIGHT =====");
  lightResults.forEach((l) => lines.push(l));
  lines.push("");
  lines.push("===== DARK =====");
  darkResults.forEach((l) => lines.push(l));

  console.log(lines.join("\n"));
})().catch((e) => {
  console.error("FAIL:", e);
  process.exit(1);
});