#!/usr/bin/env node
/* Portão de runtime do contador de resposta (v3.1 §3.3): DOM das barras nos cartões de estado, contador
 * nacional ao lado do medidor com frase C18, cobertura de 27 UFs em defesa-civil.html, navegação sem a galeria. */
const { JSDOM } = require("jsdom"); const { inlinePageJs } = require("./_inline_js"); const fs = require("fs"), path = require("path"); const raiz = path.join(__dirname, "..");
const falhas = [];
function render(pagina) {
  const html = inlinePageJs(fs.readFileSync(path.join(raiz, pagina), "utf-8"), raiz);
  return new JSDOM(html, { url: "https://localhost/", runScripts: "dangerously", beforeParse(w) {
    global.window = w; global.document = w.document; w.d3 = require("d3");
    try { w.eval(fs.readFileSync(path.join(raiz, "assets", "mapas.js"), "utf-8")); } catch (e) {}
    class Chart { constructor(el, cfg) { w.__charts = (w.__charts || []).concat([cfg.type]); } } Chart.defaults = { font: {}, color: "", plugins: { legend: { labels: {} }, tooltip: {} }, elements: {} }; w.Chart = Chart;
    w.fetch = rel => { try { const t = fs.readFileSync(path.join(raiz, String(rel)), "utf-8"); return Promise.resolve({ ok: true, json: () => Promise.resolve(JSON.parse(t)) }); } catch (e) { return Promise.resolve({ ok: false }); } };
  } });
}
(async () => {
  const por = JSON.parse(fs.readFileSync(path.join(raiz, "data", "resposta", "por_uf.json"), "utf-8"));
  const ix = render("index.html"); await new Promise(r => setTimeout(r, 2500)); const d = ix.window.document;
  // 15/09/2026: a resposta é um ÍNDICE 0–100 (100 × fração da população em município sob decreto), com a mesma arte do medidor
  const indNac = por.nacional.indice.toFixed(1).replace(".", ",");
  if (d.getElementById("respNum").textContent !== indNac) falhas.push(`índice nacional de resposta na página (${d.getElementById("respNum").textContent}) ≠ por_uf.json (${indNac})`);
  if (!new RegExp(String(por.nacional.n_municipios).replace(/\B(?=(\d{3})+(?!\d))/g, "\\.") + " municípios").test(d.getElementById("respBadge").textContent)) falhas.push("pílula da resposta sem a contagem de municípios");
  if (!d.querySelector("#contadorResposta .gauge-fill.gauge-fill--resposta") || d.querySelector("#contadorResposta .resp-fill")) falhas.push("resposta não usa a arte única do medidor (.gauge-fill--resposta)");
  // 15/09: a frase C18 saiu da face do contador e passou à ficha "Como ler o MARÉ". 16/09 (handover da voz
  // editorial): o ARTIGO de lei sai da narrativa — o fato que a C18 protege (no período eleitoral as
  // voluntárias param, as por decreto continuam) continua obrigatório, agora sem citar o dispositivo.
  if (!/transferências voluntárias ficam suspensas/.test(d.getElementById("conteudo").textContent)) falhas.push("frase C18 (defeso) ausente na inicial");
  if (d.querySelectorAll(".tile .tile-bar--resposta .tile-fill--resposta").length !== 27) falhas.push("cartões de estado sem a segunda barra (resposta) na arte única");
  const rs = [...d.querySelectorAll(".tile")].find(t => t.dataset.uf === "RS"); rs.click(); await new Promise(r => setTimeout(r, 300));
  const det = d.getElementById("detail").textContent; const m = det.match(/(\d+) de (\d+) municípios · (\d+)% da população/);
  if (!m || +m[1] !== por.uf.RS.n_municipios) falhas.push("barra de resposta do cartão RS ≠ por_uf.json");
  if (!d.querySelector("#detail .gauge-mini.gauge-zone--resposta .gauge-fill--resposta")) falhas.push("cartão RS: resposta sem o medidor na arte única");
  if (/nota\s*[-−]\s*decret|contradi[çc][ãa]o/i.test(det)) falhas.push("cartão combina antecipação e resposta (C17)");
  if (d.querySelector('a[href="mapas-e-graficos.html"]')) falhas.push("navegação ainda aponta para a galeria");
  const respArquivo = JSON.parse(fs.readFileSync(path.join(raiz, "data", "resposta", "por_uf.json"), "utf-8"));
  if (Object.keys(respArquivo.uf || {}).length !== 27) falhas.push("defesa-civil: RESP.uf sem 27 UFs");
  // 21/09/2026 (pedido editorial): #resposta saiu de defesa-civil.html por completo — a frase C18
  // continua verificada na home (linha acima), que é onde ela mora agora.
  if (falhas.length) { console.log("✗ RUNTIME (resposta):"); falhas.forEach(f => console.log("   -", f)); process.exit(1); }
  console.log("✓ RUNTIME (resposta) OK — contador nacional, barras nos 27 cartões, cartão do estado, cobertura de 27 UFs e frase C18.");
})();
