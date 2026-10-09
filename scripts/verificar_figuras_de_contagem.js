#!/usr/bin/env node
/* Portão das figuras de contagem da Defesa civil (09/10/2026, ajuste 10).
 *
 * Renderiza defesa-civil.html num Chromium real e reprova:
 *   - número em formato inglês em figura ("1,000");
 *   - rótulo de barra cortado (largura de rolagem maior que a visível);
 *   - legenda de série única nas figuras de barras (legenda que só repete o título);
 *   - mapa de contagem com faixa vazia (item de legenda sem nenhum estado com aquela cor);
 *   - rampa de contagem com mais de um matiz (variação de matiz > 25° entre as faixas).
 *
 *   node scripts/verificar_figuras_de_contagem.js --autoteste
 *   node scripts/verificar_figuras_de_contagem.js
 */
const path = require("path"), fs = require("fs"), http = require("http");
const RAIZ = path.join(__dirname, "..");
const MAPAS = ["mapAlertas", "mapCemaden", "mapDecretosUF", "mapRiscoEnchente", "mapRiscoSemiarido", "mapRiscoFogo"];

function matiz(hex) {
  const m = /^#?([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i.exec(String(hex).trim()); if (!m) return null;
  const [r, g, b] = [m[1], m[2], m[3]].map(x => parseInt(x, 16) / 255);
  const max = Math.max(r, g, b), min = Math.min(r, g, b), d = max - min; if (!d) return null;
  let h = max === r ? ((g - b) / d) % 6 : max === g ? (b - r) / d + 2 : (r - g) / d + 4;
  return (h * 60 + 360) % 360;
}
const rgbHex = s => { const m = /rgb\((\d+),\s*(\d+),\s*(\d+)/.exec(s || ""); return m ? "#" + [m[1], m[2], m[3]].map(x => (+x).toString(16).padStart(2, "0")).join("") : String(s || "").toLowerCase(); };
function problemas(f) {
  const p = [];
  (f.textos || []).forEach(t => { if (/\b\d{1,3},\d{3}\b/.test(t)) p.push(`número em formato inglês: "${t.slice(0, 40)}"`); });
  (f.cortados || []).forEach(t => p.push(`rótulo de barra cortado: "${t}"`));
  (f.legendasUnicas || []).forEach(id => p.push(`legenda de série única em ${id}`));
  (f.mapas || []).forEach(m => {
    m.legenda.filter(l => !/nenhum|sem /i.test(l.rotulo)).forEach(l => { if (!m.cores.includes(l.cor)) p.push(`${m.id}: faixa "${l.rotulo}" vazia`); });
    const hs = m.legenda.filter(l => !/nenhum|sem /i.test(l.rotulo)).map(l => matiz(l.cor)).filter(h => h != null);
    if (hs.length > 1 && Math.max(...hs) - Math.min(...hs) > 25) p.push(`${m.id}: rampa com mais de um matiz`);
  });
  return p;
}
function autoteste() {
  const casos = [
    ["1,000 reprova", problemas({ textos: ["1,000"] }).length === 1],
    ["1.000 passa", problemas({ textos: ["1.000"] }).length === 0],
    ["rótulo cortado reprova", problemas({ cortados: ["Cemaden · movimentos de m"] }).length === 1],
    ["faixa vazia reprova", problemas({ mapas: [{ id: "m", cores: ["#111111"], legenda: [{ cor: "#111111", rotulo: "1 a 2" }, { cor: "#222222", rotulo: "3 a 4" }] }] }).length === 1],
    ["rampa azul→roxo reprova", problemas({ mapas: [{ id: "m", cores: ["#7fa6c4", "#5b3f7a"], legenda: [{ cor: "#7fa6c4", rotulo: "1" }, { cor: "#5b3f7a", rotulo: "2" }] }] }).length === 1],
    ["rampa de um matiz passa", problemas({ mapas: [{ id: "m", cores: ["#d3e0ea", "#2c5373"], legenda: [{ cor: "#d3e0ea", rotulo: "1" }, { cor: "#2c5373", rotulo: "2" }] }] }).length === 0],
  ];
  casos.forEach(([n, ok]) => console.log(`  ${ok ? "OK  " : "FALHA"} ${n}`));
  const f = casos.filter(c => !c[1]).length;
  console.log(`${f ? "X" : "OK"} AUTOTESTE — ${casos.length} casos, sem navegador e sem escrita.`);
  return f ? 1 : 0;
}
async function principal() {
  const { chromium } = require("playwright");
  const MIME = { ".html": "text/html; charset=utf-8", ".js": "text/javascript", ".css": "text/css", ".json": "application/json", ".svg": "image/svg+xml", ".png": "image/png" };
  const srv = http.createServer((q, r) => { const u = decodeURIComponent(q.url.split("?")[0]); const f = path.join(RAIZ, u === "/" ? "index.html" : u);
    if (!f.startsWith(RAIZ) || !fs.existsSync(f) || fs.statSync(f).isDirectory()) { r.writeHead(404); return r.end(); }
    r.writeHead(200, { "Content-Type": MIME[path.extname(f)] || "application/octet-stream" }); fs.createReadStream(f).pipe(r); });
  await new Promise(r => srv.listen(0, "127.0.0.1", r));
  const b = await chromium.launch(); const page = await b.newPage({ viewport: { width: 1280, height: 900 } });
  let falhas = [];
  try {
    await page.goto(`http://127.0.0.1:${srv.address().port}/defesa-civil.html`, { waitUntil: "networkidle" });
    await page.waitForFunction(() => document.querySelectorAll("#mapRiscoFogo path.uf-path").length >= 27, null, { timeout: 20000 });
    const f = await page.evaluate((MAPAS) => {
      const textos = [...document.querySelectorAll("#conteudo figure")].flatMap(fg => [...fg.querySelectorAll(".barra-valor, .map-legend span, text, .cartao-numero-valor")].map(e => e.textContent.trim()));
      const cortados = [...document.querySelectorAll(".barra-rotulo")].filter(e => e.scrollWidth > e.clientWidth + 1).map(e => e.textContent);
      const legendasUnicas = ["boxAlertasTipo", "boxDecretosTipo"].filter(id => { const l = document.querySelector("#" + id + " .map-legend"); return l && l.querySelectorAll("span").length === 1; });
      const mapas = MAPAS.filter(id => document.getElementById(id) && document.querySelector("#" + id + " path.uf-path") && !document.getElementById(id).closest(".figura-midia--texto")).map(id => {
        const leg = document.getElementById(id).closest("figure").querySelector(".map-legend");
        return { id, cores: [...new Set([...document.querySelectorAll("#" + id + " path.uf-path")].map(p => getComputedStyle(p).fill))],
          legenda: leg ? [...leg.querySelectorAll("span")].map(s => ({ cor: getComputedStyle(s.querySelector("i")).backgroundColor, rotulo: s.textContent.trim() })) : [] };
      });
      return { textos, cortados, legendasUnicas, mapas };
    }, MAPAS);
    f.mapas.forEach(m => { m.cores = m.cores.map(rgbHex); m.legenda.forEach(l => l.cor = rgbHex(l.cor)); });
    falhas = problemas(f);
  } finally { await b.close(); srv.close(); }
  falhas.forEach(x => console.log("  ✗ " + x));
  console.log(falhas.length ? `✗ FIGURAS DE CONTAGEM: ${falhas.length} problema(s).` : "✓ FIGURAS DE CONTAGEM OK — números em pt-BR, rótulos inteiros, sem legenda de série única, faixas não vazias, rampa de um matiz.");
  return falhas.length ? 1 : 0;
}
if (process.argv.includes("--autoteste")) process.exit(autoteste());
principal().then(c => process.exit(c)).catch(e => { console.error(e); process.exit(1); });
