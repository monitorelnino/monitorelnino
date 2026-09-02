#!/usr/bin/env node
/* Verificador de runtime da página de Saúde e El Niño (saude.html, v2.2.4 — §9.6).
 * DOM, gesto de tooltip, crédito por figura, nav e lacunas declaradas.
 * Padrão de scripts/verificar_runtime_sinais.js.
 * Uso: node scripts/verificar_runtime_saude.js
 *
 * (cabeçalho herdado:
 * (saude.html, criada em 01/09/2026 — METODOLOGIA §23).
 * Mesmo padrão de scripts/verificar_runtime_mapas.js: jsdom + d3 reais,
 * Chart simulado, fetch local. Cobre os 4 mapas, os 4 gráficos, os cartões
 * do ciclo, a tabela de fontes e — o que é próprio desta página — a
 * PROVENIÊNCIA VISÍVEL: nenhuma figura pode ficar sem crédito de fonte, e
 * toda fonte não coletada precisa aparecer como lacuna declarada.
 * Uso: node scripts/verificar_runtime_sinais.js
 */
const { JSDOM, VirtualConsole } = require("jsdom");
const fs = require("fs");
const path = require("path");

const raiz = path.join(__dirname, "..");
const html = fs.readFileSync(path.join(raiz, "saude.html"), "utf-8");
const erros = [];
const vc = new VirtualConsole();
vc.on("jsdomError", e => erros.push(e.detail && e.detail.stack ? e.detail.stack.split("\n")[0] : e.message));

const graficos = [];  // toda instância de Chart criada pela página

const dom = new JSDOM(html, {
  url: "https://localhost/", runScripts: "dangerously", virtualConsole: vc,
  beforeParse(w) {
    global.window = w; global.document = w.document; global.navigator = w.navigator;
    w.d3 = require("d3");
    class Chart { constructor(ctx, cfg) { graficos.push({ ctx, cfg }); } }
    Chart.defaults = { font: {}, color: "" };
    w.Chart = Chart;
    w.fetch = (rel) => {
      const p = path.join(raiz, rel);
      try {
        const txt = fs.readFileSync(p, "utf-8");
        return Promise.resolve({ ok: true, json: () => Promise.resolve(JSON.parse(txt)) });
      } catch (e) { return Promise.resolve({ ok: false }); }
    };
    w.addEventListener("error", e => erros.push("onerror: " + e.message));
    w.addEventListener("unhandledrejection", e =>
      erros.push("unhandledrejection: " + ((e.reason && e.reason.message) || e.reason)));
  },
});

setTimeout(() => {
  const d = dom.window.document, q = id => d.getElementById(id);
  const falhas = [];
  const teste = (nome, cond) => { console.log((cond ? "  ✓ " : "  ✗ ") + nome); if (!cond) falhas.push(nome); };
  const SUF = JSON.parse(fs.readFileSync(path.join(raiz, "data", "saude_uf.json"), "utf-8"));
  teste("zero erros de runtime", erros.length === 0);
  erros.slice(0, 4).forEach(e => console.log("     ", e));
  for (const id of ["mapaStatus", "mapaRiscoSan", "mapaDengue", "mapaCalor", "mapaEmerg"]) {
    teste(`${id}: 27 estados desenhados`, q(id) && q(id).querySelectorAll("path").length === 27);
    teste(`${id}: legenda preenchida`, q(id.replace("mapa", "leg")) && q(id.replace("mapa", "leg")).children.length >= 1);
  }
  const nNV = Object.values(SUF.uf).filter(u => u.status === "NAO_VERIFICADO").length;
  teste(`contagem de UFs não verificadas renderizada = arquivo (${nNV})`, (q("contagemUF").textContent || "").includes(nNV + " de 27"));
  teste("cartões federais renderizados", q("cartoesFederal") && q("cartoesFederal").children.length >= 4);
  teste("tabela das 27 UFs", d.querySelectorAll("#tblUF tbody tr").length === 27);
  teste("quadrantes: 5 blocos e soma 27", q("quadrantes").children.length === 5 &&
    [...q("quadrantes").querySelectorAll("strong")].reduce((s, e) => s + Number(e.textContent), 0) === 27);
  // gesto: tooltip ao passar o mouse num estado
  try {
    const p = q("mapaStatus").querySelector("path");
    p.dispatchEvent(new dom.window.MouseEvent("mouseenter", { clientX: 100, clientY: 100, bubbles: true }));
    teste("gesto: tooltip abre ao passar o mouse", q("mapTooltip").style.display === "block" && q("mapTooltip").innerHTML.length > 10);
  } catch (e) { teste("gesto: tooltip", false); }
  // crédito por figura (dentro do parágrafo-nota único)
  const caixas = [...d.querySelectorAll(".map-box, .chart-box")].filter(c => c.querySelector("svg, canvas, #quadrantes"));
  const semCredito = caixas.filter(c => !c.querySelector(".fonte-figura"));
  teste(`toda figura tem crédito de fonte (${caixas.length - semCredito.length}/${caixas.length})`, semCredito.length === 0);
  teste("cada cartão tem exatamente 1 parágrafo-nota visível", caixas.every(c => c.querySelectorAll(":scope > .note").length === 1));
  // linguagem: "não localizamos" só como lacuna de coleta ("Não localizamos coleta"), nunca sobre instrumento não verificado
  const texto = d.body.textContent;
  const naoLocIndevido = /não localizamos (?!coleta)/i.test(texto);
  teste("linguagem: 'não localizamos' só para lacuna de coleta", !naoLocIndevido);
  teste("crédito InfoDengue visível na página", texto.includes("InfoDengue (Fiocruz/FGV)"));
  // nav canônica com Saúde ativa
  const ativa = d.querySelector(".mainnav .ativa");
  teste("nav: 'Saúde' é o item ativo", ativa && ativa.textContent.trim() === "Saúde");
  console.log(falhas.length ? `\n✗ ${falhas.length} verificação(ões) falharam.` : "\n✓ RUNTIME (saúde) OK — mapas, cartões, quadrantes, tooltip, créditos e lacunas declaradas.");
  process.exit(falhas.length ? 1 : 0);
}, 900);
