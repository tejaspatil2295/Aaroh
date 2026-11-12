// Attaches to the installed app's WebView (debug build) and signs in to the live server with the demo account.
const { chromium } = require("playwright");

(async () => {
  const browser = await chromium.connectOverCDP("http://localhost:9222");
  const page = browser.contexts()[0].pages()[0];
  console.log("app page:", page.url());
  const errors = [];
  page.on("pageerror", (e) => errors.push(String(e)));
  await page.waitForSelector("input[type=email]", { timeout: 60000 });
  const server = await page.inputValue("input[type=url]");
  console.log("server prefilled:", server);
  if (server !== process.env.URL) throw new Error(`expected server ${process.env.URL}, got ${server}`);
  await page.fill("input[type=email]", "demo@aaroh.app");
  await page.fill("input[type=password]", "Aaroh@2026");
  await page.click("button[type=submit]");
  await page.waitForFunction(() => !location.pathname.startsWith("/login"), null, { timeout: 90000 });
  await page.waitForSelector("text=/Good (morning|afternoon|evening)|Today/", { timeout: 60000 });
  await page.waitForTimeout(3000);
  console.log("signed in, now at", await page.evaluate(() => location.pathname));
  // Data actually loaded from the server
  await page.goto(page.url().replace(/\/[^/]*$/, "/tasks"));
  await page.waitForTimeout(4000);
  const body = await page.textContent("body");
  console.log("tasks screen text sample:", body.replace(/\s+/g, " ").slice(0, 300));
  await page.screenshot({ path: "android-2-tasks.png" });
  if (errors.length) throw new Error("page errors: " + errors.join(" | "));
  console.log("ANDROID DEVICE TEST PASSED");
  await browser.close();
})().catch((e) => { console.error(e); process.exit(1); });
