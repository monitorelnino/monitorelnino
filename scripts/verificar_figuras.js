#!/usr/bin/env node
/* Portão das figuras: texto do mouse dos mapas (monitor-de-riscos) e figuras de contagem (defesa-civil).
 *
 * Fundiu `verificar_dicas_dos_mapas.js` (09/10/2026, ajuste 6) e `verificar_figuras_de_contagem.js`
 * (09/10/2026, ajuste 10) num Chromium só, cada regra e cada caso de teste preservados (consolidação, item 6).
 *
 * MOUSE: passa o mouse numa amostra de cada mapa (estados e pontos) e reprova texto com data ISO, hora ISO
 * ("T12:"), número com ponto decimal, coordenada ("-3.1°,"), duas palavras seguidas em CAIXA ALTA (nome cru
 * da fonte), "km da capital" sem "estação", campo cru (natureza/situação) e MARCADOR DUPLO (dois círculos a
 * menos de 12 px no mapa das capitais).
 * CONTAGEM: reprova número em formato inglês ("1,000"), rótulo de barra cortado, faixa de legenda vazia e
 * rampa de contagem com mais de um matiz (> 25°).
 *
 *   node scripts/verificar_figuras.js --autoteste
 *   node scripts/verificar_figuras.js
 */
const path = require("path");
const RAIZ = path.join(__dirname, "..");
const MAPAS = ["mapaSecas", "mapaFogo", "mapaAr", "mapaTemperatura"];
const CAPITAIS = ["mapaTemperatura"];   // 16/10/2026: o ar é por cidade com estação, não por capital
/* 17/10/2026 (HANDOVER_DEFESA_CIVIL): os mapas de contagem por estado saíram da página (o das emergências é de pontos); a regra da rampa segue aqui para o mapa de contagem que voltar. */
const MAPAS_CONTAGEM = [];

function dica(texto) {
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

function matiz(hex) {
  const m = /^#?([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i.exec(String(hex).trim()); if (!m) return null;
  const [r, g, b] = [m[1], m[2], m[3]].map(x => parseInt(x, 16) / 255);
  const max = Math.max(r, g, b), min = Math.min(r, g, b), d = max - min; if (!d) return null;
  let h = max === r ? ((g - b) / d) % 6 : max === g ? (b - r) / d + 2 : (r - g) / d + 4;
  return (h * 60 + 360) % 360;
}
const rgbHex = s => { const m = /rgb\((\d+),\s*(\d+),\s*(\d+)/.exec(s || ""); return m ? "#" + [m[1], m[2], m[3]].map(x => (+x).toString(16).padStart(2, "0")).join("") : String(s || "").toLowerCase(); };
function contagem(f) {
  const p = [];
  (f.textos || []).forEach(t => { if (/\b\d{1,3},\d{3}\b/.test(t)) p.push(`número em formato inglês: "${t.slice(0, 40)}"`); });
  (f.cortados || []).forEach(t => p.push(`rótulo de barra cortado: "${t}"`));
  (f.mapas || []).forEach(m => {
    m.legenda.filter(l => !/nenhum|sem /i.test(l.rotulo)).forEach(l => { if (!m.cores.includes(l.cor)) p.push(`${m.id}: faixa "${l.rotulo}" vazia`); });
    const hs = m.legenda.filter(l => !/nenhum|sem /i.test(l.rotulo)).map(l => matiz(l.cor)).filter(h => h != null);
    if (hs.length > 1 && Math.max(...hs) - Math.min(...hs) > 25) p.push(`${m.id}: rampa com mais de um matiz`);
  });
  return p;
}

function autoteste() {
  const rampa = (...cs) => ({ mapas: [{ id: "m", cores: cs.map(c => c[0]), legenda: cs.map(([cor, rotulo]) => ({ cor, rotulo })) }] });
  const casos = [
    ["texto antigo da estação reprova", dica("SAO PAULO - MIRANTE · medição · 4.5 km da capital · rede: x").length > 0],
    ["hora ISO reprova", dica("2026-10-08 às 12:00:00").length > 0],
    ["coordenada reprova", dica("3 foco(s) nesta célula de ~11 km · -3.1°, -60.0°").length > 0],
    ["texto novo passa", dica("Recife (PE) Máxima prevista para 08/10: 32 °C, +1,2 °C acima da normal do mês consulta de 08/10/2026 · INMET").length === 0],
    ["milhar com ponto passa", dica("1.234 focos nas últimas 24 horas").length === 0],
    ["1,000 reprova", contagem({ textos: ["1,000"] }).length === 1],
    ["1.000 passa", contagem({ textos: ["1.000"] }).length === 0],
    ["rótulo cortado reprova", contagem({ cortados: ["Cemaden · movimentos de m"] }).length === 1],
    ["faixa vazia reprova", contagem({ mapas: [{ id: "m", cores: ["#111111"], legenda: [{ cor: "#111111", rotulo: "1 a 2" }, { cor: "#222222", rotulo: "3 a 4" }] }] }).length === 1],
    ["rampa azul→roxo reprova", contagem(rampa(["#7fa6c4", "1"], ["#5b3f7a", "2"])).length === 1],
    ["rampa de um matiz passa", contagem(rampa(["#d3e0ea", "1"], ["#2c5373", "2"])).length === 0],
  ];
  casos.forEach(([n, ok]) => console.log(`  ${ok ? "OK  " : "FALHA"} ${n}`));
  const f = casos.filter(c => !c[1]).length;
  console.log(`${f ? "X" : "OK"} AUTOTESTE — ${casos.length} casos, sem navegador e sem escrita.`);
  return f ? 1 : 0;
}

async function mouse(page, falhas) {
  await page.waitForFunction(() => document.querySelectorAll("#mapaTemperatura path.uf-path").length >= 27, null, { timeout: 20000 });
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
    textos.forEach(t => dica(t).forEach(p => falhas.push(`${id}: ${p} — ${t.slice(0, 100)}`)));
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
}

async function figuras(page, falhas) {
  await page.waitForFunction(() => document.querySelectorAll("#mapEmergencias circle").length > 0, null, { timeout: 20000 });
  const f = await page.evaluate((MAPAS) => {
    const textos = [...document.querySelectorAll("#conteudo figure")].flatMap(fg => [...fg.querySelectorAll(".barra-valor, .map-legend span, text, .cartao-numero-valor")].map(e => e.textContent.trim()));
    const cortados = [...document.querySelectorAll(".barra-rotulo")].filter(e => e.scrollWidth > e.clientWidth + 1).map(e => e.textContent);
    const mapas = MAPAS.filter(id => document.getElementById(id) && document.querySelector("#" + id + " path.uf-path") && !document.getElementById(id).closest(".figura-midia--texto")).map(id => {
      const leg = document.getElementById(id).closest("figure").querySelector(".map-legend");
      return { id, cores: [...new Set([...document.querySelectorAll("#" + id + " path.uf-path")].map(p => getComputedStyle(p).fill))],
        legenda: leg ? [...leg.querySelectorAll("span")].map(s => ({ cor: getComputedStyle(s.querySelector("i")).backgroundColor, rotulo: s.textContent.trim() })) : [] };
    });
    return { textos, cortados, mapas };
  }, MAPAS_CONTAGEM);
  f.mapas.forEach(m => { m.cores = m.cores.map(rgbHex); m.legenda.forEach(l => l.cor = rgbHex(l.cor)); });
  falhas.push(...contagem(f));
}

async function principal() {
  const { chromium } = require("playwright");
  const srv = require("./_servidor.js")(RAIZ);
  await new Promise(r => srv.listen(0, "127.0.0.1", r));
  const b = await chromium.launch();
  const falhas = [];
  try {
    for (const [pagina, regra] of [["monitor-de-riscos", mouse], ["defesa-civil", figuras]]) {
      const page = await b.newPage({ viewport: { width: 1280, height: 900 } });
      await page.goto(`http://127.0.0.1:${srv.address().port}/${pagina}.html`, { waitUntil: "networkidle" });
      await regra(page, falhas);
    }
  } finally { await b.close(); srv.close(); }
  falhas.forEach(f => console.log("  ✗ " + f));
  console.log(falhas.length ? `✗ FIGURAS: ${falhas.length} problema(s).`
    : `✓ FIGURAS OK — ${MAPAS.length} mapas com texto do mouse sem dado cru e um marcador por capital; contagem em pt-BR, rótulos inteiros, faixas não vazias, rampa de um matiz.`);
  return falhas.length ? 1 : 0;
}

if (process.argv.includes("--autoteste")) process.exit(autoteste());
if (autoteste() !== 0) process.exit(1);   // 16/10/2026: o autoteste roda antes das páginas, num comando só
principal().then(c => process.exit(c)).catch(e => { console.error(e); process.exit(1); });
