// K3, K4, K5, K6, K10 console + /account alt - all in one Playwright run
const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");

const SHOTS = "tasks/current/screenshots";
const LOG = "tasks/current/e2e/qa_playwright.txt";
const APP = "http://127.0.0.1:5000";

const out = [];
const log = (m) => { out.push(m); console.log(m); };

(async () => {
  const browser = await chromium.launch();

  // ========== K3: mobile menu expand on /art_home (375x812) ==========
  {
    const ctx = await browser.newContext({ viewport: { width: 375, height: 812 } });
    const page = await ctx.newPage();
    const consoleErrs = [];
    page.on("pageerror", e => consoleErrs.push("pageerror: " + e.message));
    page.on("console", msg => { if (msg.type() === "error") consoleErrs.push("console.error: " + msg.text()); });
    const net404 = [];
    page.on("response", r => { if (r.status() === 404) net404.push(r.url()); });

    await page.goto(APP + "/art_home", { waitUntil: "networkidle" });
    // default theme
    log("K3 initial data-bs-theme: " + await page.evaluate(() => document.documentElement.getAttribute("data-bs-theme")));

    // click toggler
    const toggler = page.locator(".navbar-toggler").first();
    await toggler.click();
    // give collapse a moment
    await page.waitForTimeout(400);
    const collapse = page.locator("#navbarToggle");
    const hasShow = await collapse.evaluate(el => el.classList.contains("show"));
    log("K3 #navbarToggle has .show after click: " + hasShow);
    await page.screenshot({ path: path.join(SHOTS, "qa_mobile_375_expanded.png"), fullPage: false });

    log("K3 console errors (mobile /art_home): " + JSON.stringify(consoleErrs));
    log("K3 network 404s (mobile /art_home): " + JSON.stringify(net404));
    await ctx.close();
  }

  // ========== K4: theme toggle (dark default) + persist ==========
  {
    const ctx = await browser.newContext({ viewport: { width: 1280, height: 800 } });
    const page = await ctx.newPage();
    await page.goto(APP + "/art_home", { waitUntil: "networkidle" });
    log("K4 default data-bs-theme: " + await page.evaluate(() => document.documentElement.getAttribute("data-bs-theme")));
    log("K4 default localStorage.theme: " + await page.evaluate(() => localStorage.getItem("theme")));

    // click theme toggle
    const toggle = page.locator("#theme-toggle").first();
    if (await toggle.count() > 0) {
      await toggle.click();
      await page.waitForTimeout(200);
      log("K4 after first click data-bs-theme: " + await page.evaluate(() => document.documentElement.getAttribute("data-bs-theme")));
      log("K4 after first click localStorage.theme: " + await page.evaluate(() => localStorage.getItem("theme")));

      // reload, expect persistence
      await page.reload({ waitUntil: "networkidle" });
      log("K4 after reload data-bs-theme: " + await page.evaluate(() => document.documentElement.getAttribute("data-bs-theme")));
      log("K4 after reload localStorage.theme: " + await page.evaluate(() => localStorage.getItem("theme")));

      // click back
      await page.locator("#theme-toggle").first().click();
      await page.waitForTimeout(200);
      log("K4 after second click data-bs-theme: " + await page.evaluate(() => document.documentElement.getAttribute("data-bs-theme")));
      log("K4 after second click localStorage.theme: " + await page.evaluate(() => localStorage.getItem("theme")));
    } else {
      log("K4 ERROR: #theme-toggle not found");
    }
    await ctx.close();
  }

  // ========== K5: dark screenshots (4 pages) ==========
  {
    const ctx = await browser.newContext({ viewport: { width: 1280, height: 800 } });
    await ctx.addInitScript(() => localStorage.setItem("theme", "dark"));
    const page = await ctx.newPage();
    const pages = [
      { url: "/art_home",            file: "qa_home_dark.png" },
      { url: "/art/aaa/1787935323",  file: "qa_art5_dark.png" },
      { url: "/login",               file: "qa_login_dark.png" },
      { url: "/about",               file: "qa_about_dark.png" },
    ];
    for (const p of pages) {
      const consoleErrs = [];
      page.removeAllListeners("pageerror");
      page.removeAllListeners("console");
      page.on("pageerror", e => consoleErrs.push("pageerror: " + e.message));
      page.on("console", msg => { if (msg.type() === "error") consoleErrs.push("console.error: " + msg.text()); });
      const net404 = [];
      page.removeAllListeners("response");
      page.on("response", r => { if (r.status() === 404) net404.push(r.url()); });

      await page.goto(APP + p.url, { waitUntil: "networkidle" });
      const bs = await page.evaluate(() => document.documentElement.getAttribute("data-bs-theme"));
      const bg = await page.evaluate(() => getComputedStyle(document.body).backgroundColor);
      log(`K5 dark ${p.url}: data-bs-theme=${bs} bodyBg=${bg} consoleErrs=${JSON.stringify(consoleErrs)} net404=${JSON.stringify(net404)}`);
      await page.screenshot({ path: path.join(SHOTS, p.file), fullPage: true });
    }
    await ctx.close();
  }

  // ========== K6: light screenshots (4 pages) + code highlight check ==========
  {
    const ctx = await browser.newContext({ viewport: { width: 1280, height: 800 } });
    await ctx.addInitScript(() => localStorage.setItem("theme", "light"));
    const page = await ctx.newPage();
    const pages = [
      { url: "/art_home",            file: "qa_home_light.png" },
      { url: "/art/aaa/1787935323",  file: "qa_art5_light.png" },
      { url: "/login",               file: "qa_login_light.png" },
      { url: "/about",               file: "qa_about_light.png" },
    ];
    for (const p of pages) {
      const consoleErrs = [];
      page.removeAllListeners("pageerror");
      page.removeAllListeners("console");
      page.on("pageerror", e => consoleErrs.push("pageerror: " + e.message));
      page.on("console", msg => { if (msg.type() === "error") consoleErrs.push("console.error: " + msg.text()); });

      await page.goto(APP + p.url, { waitUntil: "networkidle" });
      const bs = await page.evaluate(() => document.documentElement.getAttribute("data-bs-theme"));
      const bg = await page.evaluate(() => getComputedStyle(document.body).backgroundColor);
      log(`K6 light ${p.url}: data-bs-theme=${bs} bodyBg=${bg} consoleErrs=${JSON.stringify(consoleErrs)}`);

      // highlight.js link state on /art/aaa/1787935323
      if (p.url === "/art/aaa/1787935323") {
        const hljsInfo = await page.evaluate(() => {
          const light = document.getElementById("hljs-theme-light");
          const dark = document.getElementById("hljs-theme-dark");
          const hljsEls = document.querySelectorAll(".hljs").length;
          return {
            lightExists: !!light,
            lightDisabled: light ? light.disabled : null,
            darkExists: !!dark,
            darkDisabled: dark ? dark.disabled : null,
            hljsElems: hljsEls,
          };
        });
        log("K6 light /art/aaa/1787935323 hljs: " + JSON.stringify(hljsInfo));
      }
      await page.screenshot({ path: path.join(SHOTS, p.file), fullPage: true });
    }
    // also: switch back to dark, check hljs links inverted
    await page.evaluate(() => localStorage.setItem("theme", "dark"));
    await page.goto(APP + "/art/aaa/1787935323", { waitUntil: "networkidle" });
    const hljsDark = await page.evaluate(() => {
      const light = document.getElementById("hljs-theme-light");
      const dark = document.getElementById("hljs-theme-dark");
      const hljsEls = document.querySelectorAll(".hljs").length;
      return {
        lightDisabled: light ? light.disabled : null,
        darkDisabled: dark ? dark.disabled : null,
        hljsElems: hljsEls,
      };
    });
    log("K6 dark /art/aaa/1787935323 hljs: " + JSON.stringify(hljsDark));

    await ctx.close();
  }

  // ========== K10: console on /art_home (both themes) ==========
  {
    for (const theme of ["dark", "light"]) {
      const ctx = await browser.newContext({ viewport: { width: 1280, height: 800 } });
      await ctx.addInitScript((t) => localStorage.setItem("theme", t), theme);
      const page = await ctx.newPage();
      const errs = [];
      page.on("pageerror", e => errs.push("pageerror: " + e.message));
      page.on("console", m => { if (m.type() === "error") errs.push("console.error: " + m.text()); });
      const net404 = [];
      page.on("response", r => { if (r.status() === 404) net404.push(r.url()); });
      await page.goto(APP + "/art_home", { waitUntil: "networkidle" });
      log(`K10 /art_home ${theme} errs: ${JSON.stringify(errs)} net404: ${JSON.stringify(net404)}`);

      const errs2 = [];
      page.removeAllListeners("pageerror");
      page.removeAllListeners("console");
      page.on("pageerror", e => errs2.push("pageerror: " + e.message));
      page.on("console", m => { if (m.type() === "error") errs2.push("console.error: " + m.text()); });
      const net404b = [];
      page.removeAllListeners("response");
      page.on("response", r => { if (r.status() === 404) net404b.push(r.url()); });
      await page.goto(APP + "/art/aaa/1787935323", { waitUntil: "networkidle" });
      log(`K10 /art/aaa/1787935323 ${theme} errs: ${JSON.stringify(errs2)} net404: ${JSON.stringify(net404b)}`);
      await ctx.close();
    }
  }

  await browser.close();
  fs.writeFileSync(LOG, out.join("\n") + "\n");
})();
