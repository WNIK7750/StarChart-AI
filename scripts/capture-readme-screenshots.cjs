"use strict";

const fs = require("node:fs");
const path = require("node:path");
const { chromium } = require("playwright");

const root = path.resolve(__dirname, "..");
const baseUrl = (process.env.AI_NAV_SCREENSHOT_BASE_URL || "http://127.0.0.1:8088").replace(/\/$/, "");
const browserExecutable = process.env.AI_NAV_BROWSER_EXECUTABLE;
const outputDirectory = path.join(root, "docs", "assets", "screenshots", "readme");

async function main() {
  if (!browserExecutable || !fs.existsSync(browserExecutable)) {
    throw new Error("Set AI_NAV_BROWSER_EXECUTABLE to an installed Chromium-compatible browser.");
  }

  fs.mkdirSync(outputDirectory, { recursive: true });

  const browser = await chromium.launch({
    executablePath: browserExecutable,
    headless: true,
    args: ["--disable-gpu"],
  });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 1,
    locale: "zh-CN",
    reducedMotion: "reduce",
  });
  const page = await context.newPage();
  const issues = [];

  page.on("pageerror", (error) => issues.push({ type: "pageerror", text: error.message }));
  page.on("console", (message) => {
    if (["error", "warning"].includes(message.type())) {
      issues.push({ type: message.type(), text: message.text() });
    }
  });

  async function open(route, readySelector) {
    await page.goto(`${baseUrl}${route}`, { waitUntil: "networkidle" });
    await page.locator(readySelector).first().waitFor({ state: "visible", timeout: 15_000 });
    await page.waitForTimeout(250);
  }

  async function screenshot(name) {
    const target = path.join(outputDirectory, name);
    await page.screenshot({ path: target, fullPage: false, animations: "disabled" });
    return {
      file: path.relative(root, target).replaceAll("\\", "/"),
      url: page.url(),
      title: await page.title(),
    };
  }

  const captures = [];

  await open("/", "body");
  captures.push(await screenshot("home-desktop.png"));

  await open("/learn", ".km-title");
  captures.push(await screenshot("learning-map-desktop.png"));

  await open("/tools", "#searchInput");
  await page.locator("#searchInput").fill("代码");
  await page.locator("#searchForm button[type='submit']").click();
  await page.locator("#directory").waitFor({ state: "visible", timeout: 15_000 });
  await page.waitForTimeout(900);
  captures.push(await screenshot("tools-search-desktop.png"));

  await browser.close();

  process.stdout.write(`${JSON.stringify({ captures, issues }, null, 2)}\n`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
