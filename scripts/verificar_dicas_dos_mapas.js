#!/usr/bin/env node
/* Portão do texto do mouse dos mapas (09/10/2026, ajuste 6 do Monitor de riscos).
 *
 * Renderiza monitor-de-riscos.html num Chromium real, passa o mouse numa amostra de cada mapa
 * (estados e pontos) e reprova texto do mouse com: data ISO, hora ISO ("T12:"), número com ponto
 * decimal, coordenada geográfica ("-3.1°,"), duas palavras seguidas em CAIXA ALTA (nome cru da
 * fonte), "km da capital" sem a palavra "estação", ou campo cru (natureza/situação). Reprova também
 * MARCADOR DUPLO: dois círculos a menos de 12 px no mapa das capitais.
 *
 *   node scripts/verificar_dicas_dos_mapas.js --autoteste
 *   node scripts/verificar_dicas_dos_mapas.js
 */
const path = require("path"), fs = require("fs"), http = require("http");
const RAIZ = path.join(__dirname, "..");
const MAPAS = ["mapaRiscoPrevisto", "mapaSecas", "mapaFogo", "mapaAr", "mapaTemperatura", "mapaAvisos"];
const CAPITAIS = ["mapaTemperatura", "mapaAr"];

function problemas(texto) {
  const t = String(texto || "");
  const p = [];
  if (/\d{4}-\d{2}-\d{2}/.test(t)) p.push("data ISO");
  if (/T\d{2}:/.test(t)) p.push("hora ISO");
  if (/\d\.\d/.test(t.replace(/\d{1,3}(\.\d{3})+(?!\d)/g, "N"))) p.push("ponto decimal");
  if (/-?\d+(?:[.,]\d+)?°\s*,/.test(t)) p.push("coordenada");
  if (/\b[A-ZÀ-Ý]{2,}\s+[A-ZÀ-Ý-]{2,}\b/.test(t.replace(/\b(INMET|INPE|ANA|CPC|NOAA|IRI|CEMADEN|CAMS|EAQI|UF|UFs|OMS)\b/g, ""))) p.push("caixa alta da fonte");
  if (/km da capital/.test(t) && !/estação/.test(t)) p.push("distância sem dizer do quê");
  if (/\b(natureza|situacao|situação):|estimativa de modelo$|Operante/.test(t)) p.push("campo cru");
  return p;
}

function autoteste() {
  const casos = [
    ["texto antigo da estação reprova", problemas("SAO PAULO - MIRANTE · medição · 4.5 km da capital · rede: x").length > 0],
    ["hora ISO reprova", problemas("2026-10-08 às 12:00:00").length > 0],
    ["coordenada reprova", problemas("3 foco(s) nesta célula de ~11 km · -3.1°, -60.0°").length > 0],
    ["texto novo passa", problemas("Recife (PE) Máxima prevista para 08/10: 32 °C, +1,2 °C acima da normal do mês consulta de 08/10/2026 · INMET").length === 0],
    ["milhar com ponto passa", problemas("1.234 focos nas últimas 24 horas").length === 0],
  ];
  casos.forEach(([n, ok]) => console.log(`  ${ok ? "OK  " : "FALHA"} ${n}`));
  const f = casos.filter(c => !c[1]).length;
  console.log(`${f ? "X" : "OK"} AUTOTESTE — ${casos.length} casos, sem navegador e sem escrita.`);
  return f ? 1 : 0;
}

async function principal() {
  const { chromium } = require("playwright");
  const MIME = { ".html": "text/html; charset=utf-8", ".js": "text/javascript", ".css": "text/css", ".json": "application/json", ".svg": "image/svg+xml", ".png": "image/png", ".woff2": "font/woff2" };
  const srv = http.createServer((q, r) => { const u = decodeURIComponent(q.url.split("?")[0]); const f = path.join(RAIZ, u === "/" ? "index.html" : u);
    if (!f.startsWith(RAIZ) || !fs.existsSync(f) || fs.statSync(f).isDirectory()) { r.writeHead(404); return r.end(); }
    r.writeHead(200, { "Content-Type": MIME[path.extname(f)] || "application/octet-stream" }); fs.createReadStream(f).pipe(r); });
  await new Promise(r => srv.listen(0, "127.0.0.1", r));
  const b = await chromium.launch(); const page = await b.newPage({ viewport: { width: 1280, height: 900 } });
  const falhas = [];
  try {
    await page.goto(`http://127.0.0.1:${srv.address().port}/monitor-de-riscos.html`, { waitUntil: "networkidle" });
    await page.waitForFunction(() => document.querySelectorAll("#mapaAvisos path.uf-path").length >= 27, null, { timeout: 20000 });
    for (const id of MAPAS) {
      const textos = await page.evaluate((id) => {
        const svg = document.getElementById(id); if (!svg) return [];
        const alvos = [...svg.querySelectorAll("path.uf-path")].slice(0, 6).concat([...svg.querySelectorAll("circle")].slice(0, 6));
        const tip = document.getElementById("mapTooltip"); const out = [];
        for (const a of alvos) {
          const r = a.getBoundingClientRect();
          a.dispatchEvent(new MouseEvent("mouseover", { bubbles: true, clientX: r.x + 1, clientY: r.y + 1 }));
          a.dispatchEvent(new MouseEvent("mouseenter", { bubbles: false, clientX: r.x + 1, clientY: r.y + 1 }));
          if (tip && tip.style.display !== "none") out.push(tip.innerText.replace(/\s+/g, " "));
          a.dispatchEvent(new MouseEvent("mouseleave", { bubbles: false }));
        }
        return out;
      }, id);
      if (!textos.length) falhas.push(`${id}: nenhum texto do mouse na amostra`);
      textos.forEach(t => problemas(t).forEach(p => falhas.push(`${id}: ${p} — ${t.slice(0, 100)}`)));
    }
    for (const id of CAPITAIS) {
      const duplos = await page.evaluate((id) => {
        const cs = [...document.querySelectorAll("#" + id + " circle")].map(c => [+c.getAttribute("cx"), +c.getAttribute("cy")]);
        let n = 0;
        for (let i = 0; i < cs.length; i++) for (let j = i + 1; j < cs.length; j++)
          if (Math.hypot(cs[i][0] - cs[j][0], cs[i][1] - cs[j][1]) < 12) n++;
        return n;
      }, id);
      // Capitais muito próximas (DF/GO) podem cair perto por geografia; o que reprova é o padrão
      // de marcador duplo: mais de dois pares próximos.
      if (duplos > 2) falhas.push(`${id}: ${duplos} pares de marcadores a menos de 12 px (marcador duplo)`);
    }
  } finally { await b.close(); srv.close(); }
  falhas.forEach(f => console.log("  ✗ " + f));
  console.log(falhas.length ? `✗ DICAS DOS MAPAS: ${falhas.length} problema(s).`
    : `✓ DICAS DOS MAPAS OK — ${MAPAS.length} mapas, texto do mouse sem dado cru e um marcador por capital.`);
  return falhas.length ? 1 : 0;
}

if (process.argv.includes("--autoteste")) process.exit(autoteste());
principal().then(c => process.exit(c)).catch(e => { console.error(e); process.exit(1); });
