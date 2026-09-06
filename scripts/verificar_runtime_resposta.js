#!/usr/bin/env node
/* Portão de runtime do contador de resposta (v3.1 §3.3): DOM das barras nos cartões de estado, contador
 * nacional ao lado do medidor com frase C18, dispersão e tabela em defesa-civil.html, navegação sem a galeria. */
const { JSDOM } = require("jsdom"); const fs = require("fs"), path = require("path"); const raiz = path.join(__dirname, "..");
const falhas = [];
function render(pagina) {
  const html = fs.readFileSync(path.join(raiz, pagina), "utf-8");
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
  if (d.getElementById("respNum").textContent.replace(/\./g, "") !== String(por.nacional.n_municipios)) falhas.push("contador nacional ≠ por_uf.json");
  if (!/art\. 73, VI/.test(d.getElementById("respC18").textContent)) falhas.push("frase C18 ausente no contador da inicial");
  if (d.querySelectorAll(".tile .tile-bar2").length !== 27) falhas.push("cartões de estado sem a segunda barra (resposta)");
  const rs = [...d.querySelectorAll(".tile")].find(t => t.dataset.uf === "RS"); rs.click(); await new Promise(r => setTimeout(r, 300));
  const det = d.getElementById("detail").textContent; const m = det.match(/(\d+) de (\d+) municípios · (\d+)% da população/);
  if (!m || +m[1] !== por.uf.RS.n_municipios) falhas.push("barra de resposta do cartão RS ≠ por_uf.json");
  if (/nota\s*[-−]\s*decret|contradi[çc][ãa]o/i.test(det)) falhas.push("cartão combina antecipação e resposta (C17)");
  if (d.querySelector('a[href="mapas-e-graficos.html"]')) falhas.push("navegação ainda aponta para a galeria");
  const dc = render("defesa-civil.html"); await new Promise(r => setTimeout(r, 2500)); const d2 = dc.window.document;
  if (!(dc.window.__charts || []).includes("scatter")) falhas.push("defesa-civil: dispersão antecipação × resposta não desenhada (C20)");
  if (d2.querySelectorAll("#tblDecRec tbody tr").length !== 27) falhas.push("defesa-civil: tabela decretado × reconhecido sem 27 UFs");
  if (!/art\. 73, VI/.test(d2.getElementById("resposta").textContent)) falhas.push("defesa-civil: frase C18 ausente na seção do contador");
  if (falhas.length) { console.log("✗ RUNTIME (resposta):"); falhas.forEach(f => console.log("   -", f)); process.exit(1); }
  console.log("✓ RUNTIME (resposta) OK — contador nacional, barras nos 27 cartões, cartão do estado, dispersão, tabela e frase C18.");
})();
