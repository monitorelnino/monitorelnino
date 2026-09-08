#!/usr/bin/env node
/* Portão de figuras (04/09/2026, decisão editorial): mapas e gráficos trazem SÓ título,
 * legenda e crédito de uma linha. Nenhum parágrafo, nota, dica ou <details> dentro de
 * .map-box / .chart-box — nem estático no HTML, nem criado pelo JavaScript depois de renderizar.
 * Verifica as cinco páginas com figuras após a execução dos scripts (jsdom + d3 + fetch local).
 * Uso: node scripts/verificar_figuras.js
 */
const { JSDOM, VirtualConsole } = require("jsdom"); const { inlinePageJs } = require("./_inline_js");
const fs = require("fs"), path = require("path");
const raiz = path.join(__dirname, "..");
const PAGINAS = ["index.html", "pesquisadores.html", "calendario-eleitoral.html", "defesa-civil.html", "sinais-de-risco.html", "saude.html", "financiamento.html", "proteja-se.html", "imprensa.html"];
const PROIBIDOS = "p, details, .note, .hint, summary";
// Componente único (07/09/2026): .figura-titulo · .figura-sub · .figura-midia · .map-legend · .figura-leitura (opcional) · .fonte-figura
const falhas = [];

function renderizar(pagina) {
  const html = inlinePageJs(fs.readFileSync(path.join(raiz, pagina), "utf-8"), raiz);
  const vc = new VirtualConsole();
  const dom = new JSDOM(html, {
    url: "https://localhost/", runScripts: "dangerously", virtualConsole: vc,
    beforeParse(w) {
      global.window = w; global.document = w.document; global.navigator = w.navigator;
      w.d3 = require("d3");
      try { w.eval(fs.readFileSync(path.join(raiz, "assets", "mapas.js"), "utf-8")); } catch (e) {}
      class Chart { constructor() {} } Chart.defaults = { font: {}, color: "", plugins: { legend: { labels: {} }, tooltip: {} }, elements: {} };
      w.Chart = Chart;
      w.fetch = (rel) => {
        try { const txt = fs.readFileSync(path.join(raiz, String(rel).replace(/^\.\//, "")), "utf-8");
              return Promise.resolve({ ok: true, json: () => Promise.resolve(JSON.parse(txt)), text: () => Promise.resolve(txt) }); }
        catch (e) { return Promise.resolve({ ok: false }); }
      };
    }
  });
  return dom;
}

(async () => {
  for (const pagina of PAGINAS) {
    const dom = renderizar(pagina);
    await new Promise(r => setTimeout(r, 1500));
    const d = dom.window.document;
    const caixas = d.querySelectorAll(".figura");
    caixas.forEach(c => {
      const id = c.id || (c.querySelector(".figura-titulo") || {}).textContent || "(sem id)";
      // <details> com <table> dentro é alternativa de dados (acessibilidade), não explicação — permitido.
      const ruins = Array.from(c.querySelectorAll(PROIBIDOS)).filter(e => {
        const det = e.tagName === "DETAILS" ? e : e.closest("details");
        if (det && (det.querySelector("table") || det.dataset.alternativa === "dados")) return false;
        if (e.classList.contains("figura-sub") || e.classList.contains("figura-cat") || e.classList.contains("figura-leitura")) return false;   // partes do componente
        return true;
      });
      if (ruins.length) {
        const amostra = Array.from(ruins).slice(0, 2).map(e => e.tagName.toLowerCase() + ": " + e.textContent.trim().replace(/\s+/g, " ").slice(0, 70));
        falhas.push(`${pagina} › ${String(id).trim().slice(0, 50)}: ${ruins.length} elemento(s) proibido(s) — ${amostra.join(" | ")}`);
      }
      // 07/09/2026 (revisão de UX): toda figura de dado tem título, subtítulo padronizado (≤ 140 caracteres, com "·") e crédito "Fonte(s): … · dd/mm/aaaa" ou "sem coleta"
      const subs = c.querySelectorAll(".figura-sub");
      if (!c.querySelector(".figura-titulo")) falhas.push(`${pagina} › ${String(id).trim().slice(0, 50)}: figura sem título`);
      if (subs.length > 1) falhas.push(`${pagina} › ${String(id).trim().slice(0, 50)}: ${subs.length} subtítulos (máximo 1)`);
      subs.forEach(e => { const s = e.textContent.trim(); if (s.length > 140 || !s.includes("·")) falhas.push(`${pagina} › ${String(id).trim().slice(0, 50)}: subtítulo fora do padrão (≤ 140 caracteres, separado por "·") — "${s.slice(0, 60)}"`); });
      if (!subs.length) falhas.push(`${pagina} › ${String(id).trim().slice(0, 50)}: figura sem subtítulo (período · variável · unidade)`);
      if (!c.querySelector(".fonte-figura")) falhas.push(`${pagina} › ${String(id).trim().slice(0, 50)}: figura sem crédito de fonte`);
      const cred = c.querySelectorAll(".fonte-figura");
      if (cred.length > 1) falhas.push(`${pagina} › ${String(id).trim().slice(0, 50)}: ${cred.length} créditos (máximo 1)`);
      cred.forEach(e => {
        const t = e.textContent.trim();
        if (t.length > 160) falhas.push(`${pagina} › ${String(id).trim().slice(0, 50)}: crédito longo demais (${t.length} caracteres) — "${t.slice(0, 60)}…"`);
        // formato único (07/09/2026): "Fonte: órgão · documento · Atualização: dd/mm/aaaa" ou "… · Atualização: sem coleta até o corte"
        if (!/^Fonte: .+ · Atualização: (\d{2}\/\d{2}\/\d{4}|sem coleta até o corte)$/.test(t)) falhas.push(`${pagina} › ${String(id).trim().slice(0, 50)}: crédito fora do formato "Fonte: … · Atualização: dd/mm/aaaa" — "${t.slice(0, 80)}"`);
        if (/por que|confira|enquanto isso|lacuna declarada|contrariaria|regra de prova|aguard/i.test(t))
          falhas.push(`${pagina} › ${String(id).trim().slice(0, 50)}: crédito com explicação — "${t.slice(0, 80)}"`);
      });
    });
    d.querySelectorAll(".cartao .fonte-figura, .contador-zone .fonte-figura, #prazos .fonte-figura").forEach(e => { const t = e.textContent.trim();
      if (!/^Fonte: .+ · Atualização: (\d{2}\/\d{2}\/\d{4}|sem coleta até o corte)$/.test(t)) falhas.push(`${pagina} › crédito de cartão fora do formato único — "${t.slice(0, 80)}"`); });
    console.log(`  ${pagina}: ${caixas.length} figura(s) verificada(s)`);
  }
  if (falhas.length) {
    console.log("✗ FIGURAS: cartões com texto além de título, legenda e crédito:");
    falhas.forEach(f => console.log("   - " + f));
    process.exit(1);
  }
  console.log("✓ FIGURAS OK — toda .figura traz título, subtítulo, mídia, legenda e crédito no formato único (Fonte: … · Atualização: dd/mm/aaaa).");
})();
