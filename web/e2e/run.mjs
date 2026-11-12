// End-to-end smoke + critical journeys against a running web app and API.
// Usage: BASE_URL=http://localhost:5173 node e2e/run.mjs  (demo data must be seeded)
import { createRequire } from "node:module";
// Uses the project dependency if installed, else a globally installed Playwright (NODE_PATH).
const { chromium } = createRequire(import.meta.url)("playwright");
import fs from "node:fs";

const BASE = process.env.BASE_URL || "http://localhost:5173";
const OUT = process.env.SHOT_DIR || "e2e/screenshots";
fs.mkdirSync(OUT, { recursive: true });
const errors = [];
const results = [];
const step = async (name, fn) => {
  try {
    await fn();
    results.push(["PASS", name]);
  } catch (e) {
    results.push(["FAIL", name, e.message.split("\n")[0]]);
    await page.screenshot({ path: `${OUT}/FAIL-${name.replace(/\W+/g, "-")}.png` }).catch(() => {});
  }
};

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1360, height: 900 }, timezoneId: "Asia/Kolkata", deviceScaleFactor: Number(process.env.DSF || 1) });
const page = await ctx.newPage();
page.on("pageerror", (e) => errors.push(`pageerror: ${e.message}`));
page.on("console", (m) => m.type() === "error" && !/Failed to load resource/.test(m.text()) && errors.push(`console: ${m.text()}`));
page.on("response", (r) => r.url().includes("/api/") && r.status() >= 500 && errors.push(`HTTP ${r.status()} ${r.url()}`));
const shot = async (n) => { await page.waitForTimeout(1600); return page.screenshot({ path: `${OUT}/${n}.png`, fullPage: true }); };
const uniq = Date.now().toString(36);

await step("login with demo account", async () => {
  await page.goto(BASE);
  await page.getByLabel("Email").fill("demo@aaroh.app");
  await page.getByLabel("Password").fill("Aaroh@2026");
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.getByText("Productivity").first().waitFor({ timeout: 10000 });
  await shot("01-dashboard");
});

await step("session survives reload (refresh cookie)", async () => {
  await page.reload();
  await page.getByText("Productivity").first().waitFor({ timeout: 10000 });
});

await step("generate morning/evening briefing (offline mode label)", async () => {
  const btn = page.getByRole("button", { name: /Brief me|Review my day/ });
  if (await btn.count()) await btn.first().click();
  await page.getByText("Offline mode · rule-based").first().waitFor({ timeout: 10000 });
});

await step("create, find and complete a task", async () => {
  await page.goto(`${BASE}/tasks`);
  await page.getByRole("button", { name: "Task", exact: true }).click();
  await page.getByLabel("Title *").fill(`E2E task ${uniq}`);
  await page.getByLabel("Priority *").selectOption("urgent");
  await page.getByRole("button", { name: "Save" }).click();
  await page.getByText(`E2E task ${uniq}`).waitFor();
  await page.getByRole("button", { name: `Complete E2E task ${uniq}` }).click();
  await page.waitForTimeout(600);
  await page.getByPlaceholder("Search tasks").fill(uniq);
  await page.locator("select").first().selectOption("done");
  await page.getByText(`E2E task ${uniq}`).waitFor();
  await shot("02-tasks");
});

await step("smart plan preview", async () => {
  await page.locator("select").first().selectOption("open");
  await page.getByPlaceholder("Search tasks").fill("");
  await page.getByRole("button", { name: "Plan my day" }).click();
  await page.getByRole("button", { name: "Preview" }).click();
  await page.getByText(/available minutes planned/).waitFor();
  await shot("03-plan");
  await page.getByLabel("Close").click();
});

await step("calendar month view", async () => {
  await page.getByRole("tab", { name: "Calendar" }).click();
  await page.getByRole("tab", { name: "Month" }).click();
  await page.getByText("Mon", { exact: true }).waitFor();
  await shot("04-calendar");
});

await step("habits and goals tabs", async () => {
  await page.getByRole("tab", { name: "Habits" }).click();
  await page.getByText("Streak").waitFor();
  await page.getByRole("tab", { name: "Goals" }).click();
  await page.getByText("Reach 15% body fat").waitFor();
  await shot("05-goals");
});

await step("add an expense and see it in transactions", async () => {
  await page.goto(`${BASE}/finance`);
  await page.getByText("Where it went").waitFor();
  await shot("06-finance");
  await page.getByRole("button", { name: "Expense" }).click();
  await page.getByLabel("Amount (₹) *").fill("349");
  await page.getByLabel("Category *").selectOption("food_delivery");
  await page.getByLabel("Description").fill(`E2E biryani ${uniq}`);
  await page.getByRole("button", { name: "Add" }).click();
  await page.getByRole("tab", { name: "Transactions" }).click();
  await page.getByText(`E2E biryani ${uniq}`).waitFor();
});

await step("investments: net worth, add a holding, update its value", async () => {
  await page.goto(`${BASE}/investments`);
  await page.getByText("Net worth over time").waitFor();
  await page.getByText("Allocation").waitFor();
  await shot("06b-investments");
  await page.getByRole("button", { name: "Investment", exact: true }).click();
  await page.getByLabel("Name *").fill(`E2E gold ${uniq}`);
  await page.getByLabel("Type *").selectOption("gold");
  await page.getByLabel("Total invested (₹) *").fill("10000");
  await page.getByLabel("Current value (₹) *").fill("12500");
  await page.getByRole("button", { name: "Add" }).click();
  await page.getByRole("tab", { name: "Holdings" }).click();
  await page.getByText(`E2E gold ${uniq}`).click();
  await page.getByLabel("Current value (₹) *").fill("13000");
  await page.locator("form").getByRole("button", { name: "Save" }).click();
  await page.getByText("+₹3,000").first().waitFor();
  await page.getByRole("tab", { name: "Loans" }).click();
  await page.getByText("Credit card balance").waitFor();
  await page.goto(`${BASE}/`);
  await page.getByText(/Net worth ₹/).waitFor();
});

await step("journal entry with search", async () => {
  await page.goto(`${BASE}/journal`);
  await page.getByRole("button", { name: "Entry" }).click();
  await page.getByLabel("Title").fill(`E2E reflection ${uniq}`);
  await page.getByLabel("What happened? What did you think or feel?").fill("Testing the journal end to end.");
  await page.getByRole("button", { name: "Save & add photos" }).click();
  await page.getByText("Photos").waitFor();
  await page.getByLabel("Close").click();
  await page.getByPlaceholder("Search your journal").fill(uniq);
  await page.getByText(`E2E reflection ${uniq}`).waitFor();
  await shot("07-journal");
});

await step("learning hub", async () => {
  await page.goto(`${BASE}/learning`);
  await page.getByText("Skill gaps").waitFor();
  await shot("08-learning");
  await page.getByRole("tab", { name: "Skills & roadmaps" }).click();
  await page.getByText("System Design").first().waitFor();
});

await step("fitness: log water, view progress", async () => {
  await page.goto(`${BASE}/fitness`);
  await page.getByRole("button", { name: "+250 ml" }).click();
  await page.waitForTimeout(500);
  await shot("09-fitness");
  await page.getByRole("tab", { name: "Progress" }).click();
  await page.getByText("Strength progress").waitFor();
  await shot("10-fitness-progress");
});

await step("work journal", async () => {
  await page.goto(`${BASE}/work`);
  await page.getByText("Implemented retry with exponential backoff").waitFor();
  await shot("11-work");
});

await step("side income", async () => {
  await page.goto(`${BASE}/side-income`);
  await page.getByText("1:1 UPSC mentorship").first().waitFor();
  await shot("12-side-income");
});

await step("AI companion chat (offline mode)", async () => {
  await page.goto(`${BASE}/companion`);
  await page.getByRole("button", { name: "Financial Coach" }).click();
  await page.getByLabel("Message").fill("Where is my money going?");
  await page.getByLabel("Send").click();
  await page.getByText("Money this month").waitFor({ timeout: 10000 });
  await shot("13-companion");
});

await step("settings: privacy toggle round-trip", async () => {
  await page.goto(`${BASE}/settings`);
  const sw = page.getByRole("switch", { name: "Personal journal" });
  const before = await sw.getAttribute("aria-checked");
  await sw.click();
  await page.waitForFunction((b) => document.querySelector('[aria-label="Personal journal"]')?.getAttribute("aria-checked") !== b, before);
  await sw.click();
  await shot("14-settings");
});

await step("dark theme + mobile layout", async () => {
  await page.getByRole("button", { name: "Dark" }).click();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(BASE);
  await page.getByText("Productivity").first().waitFor();
  await shot("15-mobile-dark");
  await page.getByRole("button", { name: "More" }).click();
  await shot("16-mobile-more");
  await page.getByRole("link", { name: "Fitness" }).click();
  await page.getByText("Quick log").waitFor();
  await page.getByRole("button", { name: "Light" }).count();
});

await step("sign out and register a fresh account", async () => {
  await page.setViewportSize({ width: 1360, height: 900 });
  await page.goto(`${BASE}/settings`);
  await page.getByRole("button", { name: "System" }).click();
  await page.getByRole("button", { name: "Sign out" }).click();
  await page.getByRole("button", { name: "Create an account" }).click();
  await page.getByLabel("Name").fill("Fresh User");
  await page.getByLabel("Email").fill(`fresh-${uniq}@example.com`);
  await page.getByLabel("Password").fill("fresh-pass-123");
  await page.getByRole("button", { name: "Create account" }).click();
  await page.getByText("Nothing due today").waitFor({ timeout: 10000 });
  await shot("17-fresh-account");
});

await browser.close();
for (const r of results) console.log(r.join("  "));
if (errors.length) console.log("\nErrors captured:\n" + [...new Set(errors)].join("\n"));
const failed = results.filter((r) => r[0] === "FAIL").length;
console.log(`\n${results.length - failed}/${results.length} journeys passed, ${new Set(errors).size} browser errors`);
process.exit(failed || errors.length ? 1 : 0);
