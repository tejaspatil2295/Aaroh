// Drives the installed app's WebView (debug build) over raw Chrome DevTools Protocol and signs in to the live server.
// Playwright's connectOverCDP needs browser-level APIs that Android WebView does not expose, so this talks CDP directly.
const fs = require("fs");

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function connect() {
  for (let i = 0; i < 30; i++) {
    try {
      const pages = await (await fetch("http://localhost:9222/json")).json();
      const page = pages.find((p) => p.type === "page" && p.webSocketDebuggerUrl);
      if (page) return { page, ws: new WebSocket(page.webSocketDebuggerUrl) };
    } catch {}
    await sleep(2000);
  }
  throw new Error("no debuggable WebView page found");
}

(async () => {
  const { page, ws } = await connect();
  console.log("app page:", page.url);
  await new Promise((r, j) => { ws.onopen = r; ws.onerror = j; });
  let id = 0;
  const pending = new Map();
  const errors = [];
  ws.onmessage = (m) => {
    const msg = JSON.parse(m.data);
    if (msg.id && pending.has(msg.id)) { pending.get(msg.id)(msg); pending.delete(msg.id); }
    if (msg.method === "Runtime.exceptionThrown") errors.push(msg.params.exceptionDetails.exception?.description || msg.params.exceptionDetails.text);
  };
  const send = (method, params = {}) => new Promise((r) => { const i = ++id; pending.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
  const evaluate = async (expr) => {
    const res = await send("Runtime.evaluate", { expression: expr, awaitPromise: true, returnByValue: true });
    if (res.result?.exceptionDetails) throw new Error(res.result.exceptionDetails.text + " in: " + expr.slice(0, 80));
    return res.result?.result?.value;
  };
  const waitFor = async (expr, label, timeout = 90000) => {
    const t0 = Date.now();
    while (Date.now() - t0 < timeout) { if (await evaluate(expr)) return; await sleep(1000); }
    throw new Error(`timed out waiting for ${label}`);
  };
  const shot = async (file) => { const r = await send("Page.captureScreenshot", { format: "png" }); fs.writeFileSync(file, Buffer.from(r.result.data, "base64")); };
  await send("Runtime.enable");
  await send("Page.enable");

  await waitFor(`!!document.querySelector("input[type=email]")`, "login form");
  const server = await evaluate(`document.querySelector("input[type=url]")?.value`);
  console.log("server prefilled:", server);
  if (server !== process.env.URL) throw new Error(`expected server ${process.env.URL}, got ${server}`);
  const setVal = (sel, v) => `(() => { const el = document.querySelector(${JSON.stringify(sel)}); const set = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set; set.call(el, ${JSON.stringify(v)}); el.dispatchEvent(new Event("input", { bubbles: true })); return true; })()`;
  await evaluate(setVal("input[type=email]", "demo@aaroh.app"));
  await evaluate(setVal("input[type=password]", "Aaroh@2026"));
  await shot("android-1-login.png");
  await evaluate(`document.querySelector("button[type=submit]").click(), true`);
  await waitFor(`!location.pathname.startsWith("/login")`, "sign-in redirect");
  await waitFor(`/Good (morning|afternoon|evening)/.test(document.body.innerText)`, "dashboard greeting");
  await sleep(3000);
  console.log("signed in, now at", await evaluate("location.pathname"));
  await shot("android-2-dashboard.png");
  const stored = await evaluate(`!Object.keys(localStorage).some((k) => /refresh|token/i.test(k))`);
  console.log("refresh token kept out of localStorage:", stored);

  await evaluate(`history.pushState({}, "", "/finance"); dispatchEvent(new PopStateEvent("popstate")); true`);
  await waitFor(`/Spent|Income/.test(document.body.innerText)`, "money screen");
  await sleep(3000);
  console.log("money screen text:", (await evaluate("document.body.innerText")).replace(/\s+/g, " ").slice(0, 200));
  await shot("android-3-money.png");
  if (errors.length) throw new Error("page errors: " + errors.join(" | "));
  console.log("ANDROID DEVICE TEST PASSED");
  ws.close();
  process.exit(0);
})().catch((e) => { console.error(e); process.exit(1); });
