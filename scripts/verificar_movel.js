#!/usr/bin/env node
/* Portão móvel (v3.1 §14.3): cada página a 390 px de largura num Chromium real (Playwright), com os dados
 * servidos localmente; falha se houver rolagem horizontal (scrollWidth > innerWidth) ou erro de JS.
 * Gera capturas em /tmp/capturas_390/ (não versionadas). */
const { chromium } = require("playwright"); const http = require("http"), fs = require("fs"), path = require("path");
const RAIZ = path.join(__dirname, ".."); const PAGINAS = fs.readdirSync(RAIZ).filter(f => f.endsWith(".html"));
const MIME = { ".html": "text/html; charset=utf-8", ".js": "text/javascript", ".css": "text/css", ".json": "application/json", ".svg": "image/svg+xml", ".xml": "application/xml", ".png": "image/png", ".pdf": "application/pdf" };
const srv = http.createServer((req, res) => { const u = decodeURIComponent(req.url.split("?")[0]); const f = path.join(RAIZ, u === "/" ? "index.html" : u);
  if (!f.startsWith(RAIZ) || !fs.existsSync(f) || fs.statSync(f).isDirectory()) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { "Content-Type": MIME[path.extname(f)] || "application/octet-stream" }); fs.createReadStream(f).pipe(res); });
(async () => {
  await new Promise(r => srv.listen(0, "127.0.0.1", r)); const porta = srv.address().port; const falhas = [];
  const b = await chromium.launch(); const ctx = await b.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1 });
  fs.mkdirSync("/tmp/capturas_390", { recursive: true });
  for (const p of PAGINAS) {
    const page = await ctx.newPage(); const erros = [];
    page.on("pageerror", e => erros.push(e.message));
    await page.route(/vlibras\.gov\.br|fonts\.g|netlify/, r => r.abort());
    try { await page.goto(`http://127.0.0.1:${porta}/${p}`, { waitUntil: "networkidle", timeout: 30000 }); } catch (e) { falhas.push(`${p}: não carregou (${e.message.split("\n")[0]})`); await page.close(); continue; }
    await page.waitForTimeout(1200);
    const m = await page.evaluate(() => ({ sw: document.documentElement.scrollWidth, iw: window.innerWidth, bw: document.body.scrollWidth }));
    if (m.sw > m.iw + 1 || m.bw > m.iw + 1) falhas.push(`${p}: rolagem horizontal a 390 px (scrollWidth ${Math.max(m.sw, m.bw)} > ${m.iw})`);
    const errosReais = erros.filter(e => !/jsPDF|VLibras|fonts/i.test(e));
    if (errosReais.length) falhas.push(`${p}: erro JS — ${errosReais[0].slice(0, 100)}`);
    await page.screenshot({ path: `/tmp/capturas_390/${p.replace(".html", "")}.png`, fullPage: false });
    await page.close();
  }
  await b.close(); srv.close();
  if (falhas.length) { console.log("✗ MÓVEL (390 px):"); falhas.forEach(f => console.log("   -", f)); process.exit(1); }
  console.log(`✓ MÓVEL OK — ${PAGINAS.length} páginas a 390 px sem rolagem horizontal nem erro de JS (capturas em /tmp/capturas_390).`);
})();
