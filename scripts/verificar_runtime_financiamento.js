#!/usr/bin/env node
/* Verificador de runtime da página de Saúde e El Niño (financiamento.html, v2.2.4 — §9.6).
 * DOM, gesto de tooltip, crédito por figura, nav e lacunas declaradas.
 * Padrão de scripts/verificar_runtime_sinais.js.
 * Uso: node scripts/verificar_runtime_saude.js
 *
 * (cabeçalho herdado:
 * (financiamento.html, criada em 01/09/2026 — METODOLOGIA §23).
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
const html = fs.readFileSync(path.join(raiz, "financiamento.html"), "utf-8");
const erros = [];
const vc = new VirtualConsole();
vc.on("jsdomError", e => erros.push(e.detail && e.detail.stack ? e.detail.stack.split("\n")[0] : e.message));

const graficos = [];  // toda instância de Chart criada pela página

const dom = new JSDOM(html, {
  url: "https://localhost/", runScripts: "dangerously", virtualConsole: vc,
  beforeParse(w) {
    global.window = w; global.document = w.document; global.navigator = w.navigator;
    w.d3 = require("d3");
    // módulo único de mapas (o <script src> externo não é carregado pelo jsdom sem resources)
    w.eval(fs.readFileSync(path.join(raiz, "assets", "mapas.js"), "utf-8"));
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
  const ROTAS = JSON.parse(fs.readFileSync(path.join(raiz, "data", "financiamento", "rotas.json"), "utf-8")).rotas;
  const TR = JSON.parse(fs.readFileSync(path.join(raiz, "data", "transferencias.json"), "utf-8"));
  teste("zero erros de runtime", erros.length === 0); erros.slice(0, 4).forEach(e => console.log("     ", e));
  teste("bloco 1: rede com 8 rotas, 3 nós de origem/destino e arestas coloridas", q("redeRotas").querySelectorAll("g.nos g[role=img]").length === 8 && q("redeRotas").querySelectorAll("g.nos rect").length === 11 && q("redeRotas").querySelectorAll("path.aresta").length >= 16);
  teste("bloco 1: rede reage ao gesto (tooltip ao passar o mouse numa rota)", (() => { const g = q("redeRotas").querySelector("g.nos g[role=img]"); g.dispatchEvent(new dom.window.MouseEvent("mouseenter", {bubbles: true, clientX: 10, clientY: 10})); return q("mapTooltip").style.display === "block" && /chave/.test(q("mapTooltip").innerHTML); })());
  teste("bloco 1: 8 cartões de rota em texto (dobrável), na ordem e nas cores do modelo", q("rotasCards").children.length === 8 && [...q("rotasCards").children].every((c, i) => c.getAttribute("style").includes(ROTAS[i].cor)));
  teste("bloco 2: faixa do defeso desenhada", q("svgSerie").querySelector("rect") && q("svgSerie").textContent.includes("04/07–25/10"));
  for (const id of ["mapaFundo", "mapaHab", "mapDinheiro"]) teste(`${id}: 27 estados`, q(id).querySelectorAll("path").length === 27);
  teste("mapa do dinheiro: um círculo por repasse do Prepara RS", q("mapDinheiro").querySelectorAll("circle:not(.rec)").length === TR.repasses_rs.filter(r => r.lat).length);
  teste("totais RS preenchidos", q("dinTotalRS").textContent.startsWith("R$") && /^\d+$/.test(q("dinNumRS").textContent));
  teste("seletor de rota com 8 opções e mapa reage à troca", (() => { const s = q("selRota"); if (s.options.length !== 8) return false; s.value = "r3"; s.dispatchEvent(new dom.window.Event("change")); return q("mapaHab").querySelectorAll("path").length === 27; })());
  teste("tabela de resposta: 27 UFs", d.querySelectorAll("#tblResposta tbody tr").length === 27);
  teste("bloco 5: painel publicado (313) renderizado", (q("notaPainel").textContent || "").includes("313") && d.querySelectorAll("#painelResumo table tbody tr").length > 10);
  teste("bloco 6: 5 programas permanentes", q("programasCards").children.length === 5);
  teste("bloco 7: compromissos listados", d.querySelectorAll("#tblCompromissos tbody tr").length >= 4);
  teste("bloco 8: fontes de monitoramento populadas", q("fontesMonit").children.length > 0);
  const caixas = [...d.querySelectorAll(".map-box, .chart-box")].filter(c => c.querySelector("svg, canvas, table, ul"));
  const semCredito = caixas.filter(c => !c.querySelector(".fonte-figura") && !c.closest("#rotasCards") && !c.closest("#programasCards") && !c.closest("#comoler"));
  teste(`toda figura tem crédito de fonte (${caixas.length - semCredito.length}/${caixas.length})`, semCredito.length === 0);
  teste("cada cartão tem exatamente 1 parágrafo-nota visível", caixas.every(c => c.querySelectorAll(":scope > .note").length === 1));
  try { const p = q("mapaFundo").querySelector("path"); p.dispatchEvent(new dom.window.MouseEvent("mouseenter", { clientX: 100, clientY: 100, bubbles: true })); teste("gesto: tooltip", q("mapTooltip").style.display === "block"); } catch (e) { teste("gesto: tooltip", false); }
  // E10: nenhum nome de parlamentar / campo de autor na página renderizada
  const html = d.documentElement.outerHTML;
  teste("E10: nenhum campo de autor de emenda na página", !/nomeAutor|codigoAutor|autor_emenda/i.test(html));
  // resposta nunca somada a preparação (função estrutural)
  const soma = dom.window.somaPreparacao({r1: 10, r2: 10, r3: 1000, r4: 1000, r5: 10, r6: 10, r7: 10, rE: 10});
  teste("somaPreparacao ignora r3 e r4 (resposta)", soma === 60);
  const ativa = d.querySelector(".mainnav .ativa");
  teste("nav: 'Financiamento' é o item ativo", ativa && ativa.textContent.trim() === "Financiamento");

  // ── padrão único de mapas (03/09/2026): siglas das 27 UFs em todo mapa; legendas canônicas ──
  const mapasSvg = [...d.querySelectorAll('svg[id^="map"], svg[id^="mapa"]')].filter(s => s.querySelector("path.uf-path") || s.querySelector("path"));
  teste(`padrão de mapas: ${mapasSvg.length} mapa(s) com siglas das 27 UFs`, mapasSvg.length > 0 && mapasSvg.every(s => s.querySelectorAll("g.siglas text").length === 27));
  const legendas = [...d.querySelectorAll(".map-legend")].filter(l => l.children.length);
  teste(`padrão de legendas: ${legendas.length} legenda(s) no formato canônico`, legendas.every(l => [...l.children].every(c => c.tagName === "SPAN" && (c.classList.contains("escala") || (c.firstElementChild && c.firstElementChild.tagName === "I" && /background:/.test(c.firstElementChild.getAttribute("style") || ""))) && c.textContent.trim().length > 0)));
  console.log(falhas.length ? `\n✗ ${falhas.length} verificação(ões) falharam.` : "\n✓ RUNTIME (financiamento) OK — rotas, faixa do defeso, mapas, resposta, compromissos, fontes, E10 e soma de preparação.");
  process.exit(falhas.length ? 1 : 0);
}, 1200);
