#!/usr/bin/env node
/* 14/09/2026 — canário do site publicado num Chromium real (Playwright), contra o domínio: os NOSSOS scripts executam sob a CSP
 * servida (script-src por caminho, sem 'self'); o script que o Netlify injeta (/.netlify/scripts/hud) é o ÚNICO bloqueado;
 * a home preenche o medidor; nenhum erro de JS nosso. Credencial: PREVIA_BASIC_AUTH (user:senha) quando o domínio está com senha.
 * Uso: node scripts/verificar_publicado_navegador.js [--base URL] */
const { chromium } = require("playwright");
const args = process.argv.slice(2); const i = args.indexOf("--base");
const BASE = (i >= 0 ? args[i + 1] : "https://monitorelnino.com.br").replace(/\/$/, "");
const PAGINAS = ["index.html", "saude.html", "defesa-civil.html", "financiamento.html", "prefeituras.html"];
const falhas = []; const ok = (n, c, x = "") => { console.log((c ? "  ✓ " : "  ✗ ") + n + (x ? " · " + x : "")); if (!c) falhas.push(n); };
(async () => {
  const cred = process.env.PREVIA_BASIC_AUTH ? { username: process.env.PREVIA_BASIC_AUTH.split(":")[0], password: process.env.PREVIA_BASIC_AUTH.split(":").slice(1).join(":") } : undefined;
  const browser = await chromium.launch(); const ctx = await browser.newContext({ httpCredentials: cred, viewport: { width: 1280, height: 900 } });
  // o véu do navegador (acesso.js) pede senha por prompt: respondemos com a mesma senha do Basic-Auth
  for (const pg of PAGINAS) {
    const page = await ctx.newPage(); const console_ = []; const csp = [];
    page.on("dialog", d => d.accept(cred ? cred.password : "").catch(() => {}));   // véu do navegador: responde uma única vez
    page.on("console", m => { if (m.type() === "error") console_.push(m.text()); });
    page.on("requestfailed", r => { if (/Content Security Policy|blocked/i.test(r.failure() ? r.failure().errorText : "")) csp.push(r.url()); });
    try { await page.goto(`${BASE}/${pg}`, { waitUntil: "networkidle", timeout: 45000 }); } catch (e) { ok(`${pg}: carregou`, false, e.message.split("\n")[0]); await page.close(); continue; }
    const temMapas = await page.evaluate(() => typeof window.MonitorMapas !== "undefined");
    ok(`${pg}: nossos scripts executam sob a CSP (MonitorMapas presente)`, temMapas);
    const cspErrosNossos = console_.filter(t => /Content Security Policy/i.test(t) && !/\.netlify\/scripts\/hud/.test(t));
    ok(`${pg}: nenhuma violação de CSP nos nossos scripts`, cspErrosNossos.length === 0, cspErrosNossos.slice(0, 2).join(" | "));
    const outros = console_.filter(t => !/Content Security Policy/i.test(t) && !/vlibras/i.test(t));
    ok(`${pg}: sem erro de JS`, outros.length === 0, outros.slice(0, 2).join(" | "));
    if (pg === "index.html") { const g = await page.evaluate(() => (document.getElementById("gaugeNum") || {}).textContent || ""); ok("home: medidor preenchido", /\d/.test(g), g); }
    await page.close();
  }
  await browser.close();
  console.log(falhas.length ? `\n✗ NAVEGADOR (publicado): ${falhas.length} falha(s).` : "\n✓ NAVEGADOR (publicado) OK — scripts próprios executam sob a CSP; injeção do Netlify é a única bloqueada; medidor preenchido.");
  process.exit(falhas.length ? 1 : 0);
})().catch(e => { console.error("✗ erro:", e.message); process.exit(1); });
