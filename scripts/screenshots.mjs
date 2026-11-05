// Screenshots and a QA click-through in headless Microsoft Edge (adapted from the startup-runway project).
// Needs: web/out built (cd web; npm run build), Python (local web server), Node 22+.
// Run from the repo root:
//   node scripts/screenshots.mjs before|after   comparison shots into docs/screenshots/redesign/
//   node scripts/screenshots.mjs compare        side-by-side images and web/public/og.png (after `after`)
//   node scripts/screenshots.mjs qa             checks (PASS/FAIL) and the regular shots in docs/screenshots/
//   node scripts/screenshots.mjs qa https://... the same checks against the live site (no local server)
//
// Edge is driven through its DevTools protocol (a WebSocket built into Node): no extra packages.
// Selectors the script relies on (keep them when the page changes): #period, buttons named
// "Previous month" / "Next month", .vrow, dialog.drill, #drill-title, "Close details", #ai-title,
// #bridge-title, #list-title, #summary-title, .info-btn, .info-pop.
import { spawn } from "node:child_process";
import { mkdirSync, writeFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { tmpdir } from "node:os";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const mode = process.argv[2] ?? "qa";
const live = (process.argv[3] ?? "").replace(/\/$/, "");
const SITE = live || "http://localhost:8766";
const shots = join(root, "docs", "screenshots", live ? "live" : mode === "qa" ? "" : "redesign");
const EDGE = "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const PORT = 9335;
const wait = (ms) => new Promise((r) => setTimeout(r, ms));

const server = live ? null : spawn("python", ["-m", "http.server", "8766", "--directory", join(root, "web", "out")], { stdio: "ignore" });
const edge = spawn(EDGE, ["--headless=new", "--disable-gpu", "--hide-scrollbars", `--remote-debugging-port=${PORT}`,
  `--user-data-dir=${join(tmpdir(), "variance-edge-profile")}`, "about:blank"], { stdio: "ignore" });

let ws, nextId = 0;
const pending = new Map();
const siteErrors = [];
function send(method, params = {}) {
  return new Promise((resolve, reject) => {
    const id = ++nextId;
    pending.set(id, (m) => (m.error ? reject(new Error(`${method}: ${m.error.message}`)) : resolve(m.result)));
    ws.send(JSON.stringify({ id, method, params }));
  });
}
const js = async (expr) => (await send("Runtime.evaluate", { expression: expr, awaitPromise: true, returnByValue: true })).result.value;

async function connect() {
  for (let i = 0; i < 50; i++) {
    try {
      const page = (await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json()).find((p) => p.type === "page");
      if (page) {
        ws = new WebSocket(page.webSocketDebuggerUrl);
        await new Promise((r) => (ws.onopen = r));
        ws.onmessage = (e) => {
          const m = JSON.parse(e.data);
          if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); }
          // Only errors from the site's own scripts count (Edge injects a script of its own that can throw).
          if (m.method === "Runtime.exceptionThrown") {
            const d = m.params.exceptionDetails;
            if ((d.url || d.stackTrace?.callFrames?.[0]?.url || "").startsWith(SITE)) siteErrors.push(d.exception?.description ?? d.text);
          }
          if (m.method === "Runtime.consoleAPICalled" && m.params.type === "error")
            siteErrors.push(m.params.args.map((a) => a.value ?? a.description).join(" "));
        };
        return;
      }
    } catch {}
    await wait(200);
  }
  throw new Error("Could not connect to Edge");
}

let current = { width: 1440, mobile: false };
// The theme is stored before the page loads, so it works with both the old and the new theme script.
async function open(theme, width, mobile = false) {
  current = { width, mobile };
  await send("Emulation.setDeviceMetricsOverride", { width, height: mobile ? 900 : 1600, deviceScaleFactor: 1, mobile });
  await send("Emulation.setTouchEmulationEnabled", { enabled: mobile, maxTouchPoints: 5 });
  await send("Page.navigate", { url: SITE + "/" });
  await wait(300);
  await js(`localStorage.setItem("theme", ${JSON.stringify(theme)})`);
  await send("Page.navigate", { url: SITE + "/" });
  for (let i = 0; i < 150; i++) {
    if (await js("document.readyState === 'complete' && !!document.getElementById('period')")) break;
    await wait(100);
  }
  await wait(1200);   // hydrate, measure charts, finish the one-time chart animation
}

async function shoot(file, selector) {
  let clip;
  if (selector) {
    clip = await js(`(() => { const r = (${selector}).getBoundingClientRect();
      return { x: r.x + scrollX - 8, y: r.y + scrollY - 8, width: r.width + 16, height: r.height + 16, scale: 1 }; })()`);
  } else {
    const h = await js("document.documentElement.scrollHeight");
    await send("Emulation.setDeviceMetricsOverride", { width: current.width, height: h, deviceScaleFactor: 1, mobile: current.mobile });
    await wait(800);
    clip = { x: 0, y: 0, width: await js("document.documentElement.clientWidth"), height: await js("document.documentElement.scrollHeight"), scale: 1 };
  }
  const { data } = await send("Page.captureScreenshot", { format: "png", clip, captureBeyondViewport: !selector ? false : true });
  writeFileSync(join(shots, file), Buffer.from(data, "base64"));
  console.log(`  saved ${join("docs", "screenshots", live ? "live" : mode === "qa" ? "" : "redesign", file)}`);
}
// The drill-down is a full-height dialog: photograph the viewport with it open.
async function shootViewport(file) {
  const { data } = await send("Page.captureScreenshot", { format: "png" });
  writeFileSync(join(shots, file), Buffer.from(data, "base64"));
  console.log(`  saved ${join("docs", "screenshots", live ? "live" : mode === "qa" ? "" : "redesign", file)}`);
}
const key = async (k, code, vk) => {
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: k, code, windowsVirtualKeyCode: vk, ...(k === "Enter" ? { text: "\r" } : {}) });
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: k, code, windowsVirtualKeyCode: vk });
};
const pickMonth = (value) => js(`(() => { const s = document.getElementById('period');
  Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, 'value').set.call(s, ${JSON.stringify(value)});
  s.dispatchEvent(new Event('change', { bubbles: true })); })()`);
const AI_CARD = "document.getElementById('ai-title').closest('section')";

let failed = false;
const report = (ok, text) => { console.log(`  ${ok ? "PASS" : "FAIL"}  ${text}`); failed ||= !ok; };

try {
  mkdirSync(shots, { recursive: true });
  await wait(1500);
  await connect();
  await send("Page.enable");
  await send("Runtime.enable");

  if (mode === "before" || mode === "after") {
    for (const [name, theme, width, mobile] of [["desktop-light", "light", 1440, false], ["desktop-dark", "dark", 1440, false],
      ["mobile-375", "light", 375, true]]) {
      await open(theme, width, mobile);
      await shoot(`${name}-${mode}.png`);
    }
    await open("light", 1440);
    await shoot(`ai-quality-${mode}.png`, AI_CARD);
    await js("document.querySelectorAll('.vrow')[1].click()");   // 2010 raw materials: has the price/volume split
    await wait(600);
    await shootViewport(`drilldown-${mode}.png`);
    process.exit(0);
  }

  // Side-by-side BEFORE | AFTER images, and the Open Graph image cropped from the new desktop light shot.
  // Edge draws them from the PNGs, so no image library is needed.
  if (mode === "compare") {
    const { readFileSync } = await import("node:fs");
    const png = (f) => `data:image/png;base64,${readFileSync(join(shots, f)).toString("base64")}`;
    const size = (f) => { const b = readFileSync(join(shots, f)); return [b.readUInt32BE(16), b.readUInt32BE(20)]; };
    async function draw(html, width, height, file) {
      await send("Emulation.setDeviceMetricsOverride", { width, height, deviceScaleFactor: 1, mobile: false });
      const { frameTree } = await send("Page.getFrameTree");
      await send("Page.setDocumentContent", { frameId: frameTree.frame.id, html });
      await wait(500);
      const { data } = await send("Page.captureScreenshot", { format: "png", clip: { x: 0, y: 0, width, height, scale: 1 } });
      writeFileSync(join(shots, file), Buffer.from(data, "base64"));
      console.log(`  saved docs/screenshots/redesign/${file}`);
    }
    for (const name of ["desktop-light", "desktop-dark", "mobile-375", "drilldown", "ai-quality"]) {
      const [bw, bh] = size(`${name}-before.png`), [aw, ah] = size(`${name}-after.png`);
      const gap = 24, w = bw + aw + gap * 3, h = Math.max(bh, ah) + 64;
      await draw(`<body style="margin:0;background:#e7e5e1;font:600 14px system-ui;color:#1c1b19">
        <div style="display:flex;gap:${gap}px;padding:16px ${gap}px;align-items:flex-start">
        <div><div style="margin-bottom:8px">Before</div><img src="${png(`${name}-before.png`)}"></div>
        <div><div style="margin-bottom:8px">After</div><img src="${png(`${name}-after.png`)}"></div></div></body>`, w, h, `compare-${name}.png`);
    }
    // og.png: 1200 x 630 from the top of the 1440 px page, where the 1200 px content column starts at x = 120.
    await draw(`<body style="margin:0;overflow:hidden"><img style="display:block;margin-left:-120px" src="${png("desktop-light-after.png")}"></body>`,
      1200, 630, "og.png");
    writeFileSync(join(root, "web", "public", "og.png"), readFileSync(join(shots, "og.png")));
    console.log("  copied to web/public/og.png");
    process.exit(0);
  }

  // ---------------------------------------------------------------- QA (mode "qa")
  console.log("Figures, Sep 2026 (the default month):");
  await open("light", 1440);
  const text = () => js("document.body.innerText");
  const t = await text();
  for (const s of ["DKK 10,26m", "DKK 10,76m", "DKK 0,25m", "DKK 1,55m", "2,5 %", "14,4 %", "(fictional)", "Draft summary (Claude)"])
    report(t.toLowerCase().includes(s.toLowerCase()), `"${s}" visible`);   // labels may be upper-cased by CSS
  const sig = await js("document.querySelectorAll('.vrow').length");
  report(sig === 6 && t.includes("5 accounts + 1 price effect"), `significant variances: ${sig} rows, "5 accounts + 1 price effect"`);
  report(/Price effect DKK 0,37m unfavourable, partly offset by lower volume DKK 0,20m favourable/.test(t), "raw materials price 0,37m / volume 0,20m");
  const ai = await js(`${AI_CARD}.innerText`);
  const counts = ["Approved", "Edited", "Rejected"].map((l) => Number((ai.match(new RegExp(`${l}\\s+(\\d+)`, "i")) ?? [])[1]));
  report(counts.join("/") === "35/30/6" && counts.reduce((a, b) => a + b, 0) === 71, `AI panel counts ${counts.join(" + ")} = 71`);
  report(/16 of 18/.test(ai), 'AI panel shows "16 of 18"');

  let notReviewed = 0;
  for (const p of await js("[...document.getElementById('period').options].map(o => o.value)")) {
    await pickMonth(p);
    await wait(60);
    if ((await text()).toLowerCase().includes("not reviewed")) notReviewed++;
  }
  report(notReviewed === 0, `no "not reviewed" in any month (${notReviewed} months with it)`);

  console.log("Keyboard:");
  await open("light", 1440);
  const reached = [];
  const noRing = new Set();
  for (let i = 0; i < 40; i++) {
    await key("Tab", "Tab", 9);
    const f = await js(`(() => { const e = document.activeElement; if (e === document.body) return null; const cs = getComputedStyle(e);
      return { name: e.getAttribute('aria-label') || e.id || e.textContent.trim().slice(0, 30), cls: e.className,
        ring: cs.outlineStyle !== 'none' && parseFloat(cs.outlineWidth) >= 2, color: cs.outlineColor }; })()`);
    if (!f) continue;   // past the last stop, focus is on the page itself
    reached.push(f);
    if (!f.ring) noRing.add(f.name);
  }
  console.log(`  tab order: ${reached.slice(0, 18).map((f) => f.name).join(" > ")}`);
  const gotRow = reached.some((f) => String(f.cls).includes("vrow"));
  const gotBridge = reached.some((f) => /^(Revenue|Materials|Staff|Other opex)$/.test(f.name) || /filter/i.test(f.name));
  report(gotRow && gotBridge, `Tab reaches bridge filters (${gotBridge}) and variance rows (${gotRow})`);
  report(noRing.size === 0, "visible focus ring on every stop" + (noRing.size ? `; none on: ${[...noRing].join(", ")}` : ""));
  const accent = await js(`(() => { const d = document.createElement('div'); d.style.color = 'var(--accent)'; document.body.append(d);
    const c = getComputedStyle(d).color; d.remove(); return c; })()`);
  report(reached.every((f) => f.color === accent), `focus ring colour is the accent (${accent})`);

  // Drill-down by keyboard: Enter on a row opens the dialog, Esc closes it.
  await js("document.querySelector('.vrow').focus()");
  await key("Enter", "Enter", 13);
  await wait(400);
  const opened = await js("document.querySelector('dialog.drill').open && !!document.getElementById('drill-title')");
  await key("Escape", "Escape", 27);
  await wait(300);
  report(opened && !(await js("document.querySelector('dialog.drill').open")), "drill-down opens with Enter, closes with Esc");

  const infoCount = await js("document.querySelectorAll('.info-btn').length");
  if (infoCount) {
    await js("document.querySelector('.info-btn').focus()");
    await key("Enter", "Enter", 13);
    await wait(200);
    const popOpen = await js("!!document.querySelector('.info-pop')");
    await key("Escape", "Escape", 27);
    await wait(200);
    const back = await js("!document.querySelector('.info-pop') && document.activeElement.classList.contains('info-btn')");
    report(popOpen && back, `(i) popover opens with Enter, Esc closes it and returns focus (${infoCount} buttons)`);
    const unnamed = await js("[...document.querySelectorAll('.info-btn')].filter(b => !b.getAttribute('aria-label')).length");
    report(unnamed === 0, "every (i) button has a name");
  }

  console.log("Phone and motion:");
  await open("light", 375, true);
  const sw = await js("[document.documentElement.scrollWidth, document.documentElement.clientWidth]");
  report(sw[0] <= sw[1], `no horizontal scroll at 375 px (scrollWidth ${sw[0]}, clientWidth ${sw[1]})`);
  if (infoCount) {
    const inside = await js(`(async () => { document.querySelector('.info-btn').click(); await new Promise(r => setTimeout(r, 150));
      const r = document.querySelector('.info-pop').getBoundingClientRect(); return r.left >= 0 && r.right <= document.documentElement.clientWidth; })()`);
    report(inside, "375 px: an open popover stays inside the screen");
  }
  await send("Emulation.setEmulatedMedia", { features: [{ name: "prefers-reduced-motion", value: "reduce" }] });
  await open("light", 1440);
  const dur = await js("getComputedStyle(document.querySelector('.vrow')).transitionDuration");
  report(dur.split(",").every((d) => parseFloat(d) === 0), `reduced motion: row transition ${dur}`);
  await send("Emulation.setEmulatedMedia", { features: [] });

  if (!live) {
    console.log("Screenshots:");
    for (const theme of ["light", "dark"]) { await open(theme, 1440); await shoot(`desktop-${theme}.png`); }
    await open("light", 375, true);
    await shoot("mobile-375.png");
    await open("light", 1440);
    await shoot("ai-quality-panel.png", AI_CARD);
    await js("document.querySelectorAll('.vrow')[1].click()");
    await wait(600);
    await shootViewport("drilldown.png");
  }
  report(siteErrors.length === 0, "no console errors" + (siteErrors.length ? `: ${siteErrors.join(" | ")}` : ""));
} finally {
  ws?.close();
  edge.kill();
  server?.kill();
}
process.exit(failed ? 1 : 0);
