// Renders the AAROH launcher icons and splash screens into the Android project.
import { createRequire } from "node:module";
const { chromium } = createRequire(import.meta.url)("playwright");
const RES = "android/app/src/main/res";
const glyph = (s) => `<path d="M${18*s/64} ${46*s/64} ${32*s/64} ${16*s/64}l${14*s/64} ${30*s/64}" fill="none" stroke="#fff" stroke-width="${5*s/64}" stroke-linecap="round" stroke-linejoin="round"/><path d="M${24*s/64} ${36*s/64}h${16*s/64}" stroke="#fff" stroke-width="${5*s/64}" stroke-linecap="round"/>`;
const full = (s, round) => `<svg xmlns="http://www.w3.org/2000/svg" width="${s}" height="${s}" viewBox="0 0 ${s} ${s}">${round ? `<circle cx="${s/2}" cy="${s/2}" r="${s/2}" fill="#5b5bd6"/>` : `<rect width="${s}" height="${s}" rx="${s*0.22}" fill="#5b5bd6"/>`}${glyph(s)}</svg>`;
// adaptive foreground: glyph within central 66% safe zone of 108dp canvas
const fg = (s) => { const inner = s * 0.5; const off = (s - inner) / 2; return `<svg xmlns="http://www.w3.org/2000/svg" width="${s}" height="${s}"><g transform="translate(${off},${off})">${glyph(inner)}</g></svg>`; };
const splash = (w, h) => { const s = Math.min(w, h) * 0.22; return `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}"><rect width="${w}" height="${h}" fill="#0b0b0f"/><g transform="translate(${(w-s)/2},${(h-s)/2})"><rect width="${s}" height="${s}" rx="${s*0.22}" fill="#5b5bd6"/>${glyph(s)}</g></svg>`; };
const b = await chromium.launch(); const p = await b.newPage();
const render = async (svg, w, h, path, transparent = false) => { await p.setViewportSize({ width: Math.round(w), height: Math.round(h) }); await p.setContent(`<html><body style="margin:0;background:transparent">${svg}</body></html>`); await p.screenshot({ path, omitBackground: transparent }); };
const dens = { mdpi: 1, hdpi: 1.5, xhdpi: 2, xxhdpi: 3, xxxhdpi: 4 };
for (const [d, m] of Object.entries(dens)) {
  await render(full(48*m), 48*m, 48*m, `${RES}/mipmap-${d}/ic_launcher.png`, true);
  await render(full(48*m, true), 48*m, 48*m, `${RES}/mipmap-${d}/ic_launcher_round.png`, true);
  await render(fg(108*m), 108*m, 108*m, `${RES}/mipmap-${d}/ic_launcher_foreground.png`, true);
  await render(splash(320*m, 480*m), 320*m, 480*m, `${RES}/drawable-port-${d}/splash.png`);
  await render(splash(480*m, 320*m), 480*m, 320*m, `${RES}/drawable-land-${d}/splash.png`);
}
await render(splash(480, 800), 480, 800, `${RES}/drawable/splash.png`);
await b.close();
console.log("icons written");
