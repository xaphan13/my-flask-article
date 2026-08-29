// K6 retest with clean context for dark
const { chromium } = require("playwright");
const fs = require("fs");

(async () => {
  const browser = await chromium.launch();

  // === K6 dark: fresh context, init script dark ===
  {
    const ctx = await browser.newContext({ viewport: { width: 1280, height: 800 } });
    await ctx.addInitScript(() => localStorage.setItem("theme", "dark"));
    const page = await ctx.newPage();
    await page.goto("http://127.0.0.1:5000/art/aaa/1787935323", { waitUntil: "networkidle" });
    const info = await page.evaluate(() => {
      const light = document.getElementById("hljs-theme-light");
      const dark = document.getElementById("hljs-theme-dark");
      const bs = document.documentElement.getAttribute("data-bs-theme");
      const hljsCount = document.querySelectorAll(".hljs").length;
      return {
        bs,
        lightExists: !!light, lightDisabled: light ? light.disabled : null,
        darkExists: !!dark, darkDisabled: dark ? dark.disabled : null,
        hljsCount,
      };
    });
    console.log("K6 fresh dark /art/aaa/1787935323:", JSON.stringify(info));
    await ctx.close();
  }

  // === K6 light: fresh context, init script light ===
  {
    const ctx = await browser.newContext({ viewport: { width: 1280, height: 800 } });
    await ctx.addInitScript(() => localStorage.setItem("theme", "light"));
    const page = await ctx.newPage();
    await page.goto("http://127.0.0.1:5000/art/aaa/1787935323", { waitUntil: "networkidle" });
    const info = await page.evaluate(() => {
      const light = document.getElementById("hljs-theme-light");
      const dark = document.getElementById("hljs-theme-dark");
      const bs = document.documentElement.getAttribute("data-bs-theme");
      const hljsCount = document.querySelectorAll(".hljs").length;
      return {
        bs,
        lightExists: !!light, lightDisabled: light ? light.disabled : null,
        darkExists: !!dark, darkDisabled: dark ? dark.disabled : null,
        hljsCount,
      };
    });
    console.log("K6 fresh light /art/aaa/1787935323:", JSON.stringify(info));
    await ctx.close();
  }

  await browser.close();
})();
