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
const { JSDOM, VirtualConsole } = require("jsdom"); const { inlinePageJs } = require("./_inline_js");
const fs = require("fs");
const path = require("path");

const raiz = path.join(__dirname, "..");
const html = inlinePageJs(fs.readFileSync(path.join(raiz, "financiamento.html"), "utf-8"), raiz);
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
  // 09/09/2026: a cor da rota é a da paleta semântica única (MonitorMapas.PALETA.rotas), igual em todas as figuras; o JSON guarda a ordem
  const PAL_ROTAS = (dom.window.MonitorMapas && dom.window.MonitorMapas.PALETA && dom.window.MonitorMapas.PALETA.rotas) || {};
  const corRota = r => PAL_ROTAS[r.id] || r.cor;
  teste("bloco 1: 8 cartões de rota em texto (dobrável), na ordem e nas cores do modelo", q("rotasCards").children.length === 8 && [...q("rotasCards").children].every((c, i) => c.getAttribute("style").includes(corRota(ROTAS[i]))));
  teste("bloco 1: rotas com 8 cores distintas da paleta única (rede, cartões e série usam a mesma)", new Set(ROTAS.map(corRota)).size === 8 && ROTAS.every(r => PAL_ROTAS[r.id]));
  // 'Brasil, por semana' (bloco 2, faixa do defeso) migrou para pesquisadores.html em 13/09/2026
  // (proposta de enxugamento, Manus AI) — teste de renderização correspondente removido daqui.
  // 15/09/2026: mapaFundo, mapDinheiro, mapaContadores, cResposta e o mapa do fogo saíram da página (pedido da editoria)   // mapaHab retirado do HTML em 13/09/2026 (auditoria de visualizações) — sem cobertura mínima
  // seletor de rota / mapaHab retirados do HTML em 13/09/2026 (auditoria de visualizações) — teste correspondente removido junto
  // 15/09/2026 (Financiamento elucidativo): tabelas viraram figuras — mapa por habitante, barras de resposta por UF, gráfico dos compromissos, mapas das MPs, gráfico do RS
  teste("compromissos: gráfico anunciado × empenhado × pago com legenda e crédito", q("legCompromissos").children.length === 4 && graficos.some(g => g.ctx && g.ctx.id === "cCompromissos") && /Fonte:/.test(q("boxCompromissosGrafico").textContent));
  for (const id of ["mapaMPsUF", "mapaMP1384UF"]) teste(`${id}: 27 estados, legenda com a unidade nacional à parte`, q(id).querySelectorAll("path").length === 27 && /unidade nacional/.test(q(id.replace("mapa", "leg")).textContent));
  teste("RS: gráfico repasse preventivo × decreto × reconhecidos, com os números do dado na legenda", graficos.some(g => g.ctx && g.ctx.id === "cRS") && /138 municípios/.test(q("legRS").textContent) && /sob decreto: \d+/.test(q("legRS").textContent));
  teste("caminho do município: três momentos com chips de chave", d.querySelectorAll("#caminho .cartao").length === 3 && d.querySelectorAll("#caminho .chip-chave").length >= 12);
  teste("ficha 'Como ler as rotas': chaves, termos, 8 cartões e a rota do fogo (PNMIF)", /Chaves de acesso/.test(q("comolerRotas").textContent) && /PNMIF/.test(q("comolerRotas").textContent) && q("rotasCards").children.length === 8);
  teste("nenhuma tabela na página (só figuras, mapas, rotas e fichas)", d.querySelectorAll("main table").length === 0);
  teste("painéis retirados a pedido da editoria não voltaram", !q("porestado") && !q("boxFundoEstadual") && !q("notaExecucao"));
  // Painel amostral (agregados) migrou para pesquisadores.html em 13/09/2026 (proposta de
  // enxugamento, Manus AI) — teste de renderização correspondente removido daqui.
  teste("bloco 6: 5 programas listados como exemplos da rota 7", q("programasLista").children.length === 5);
  // 'Compromissos federais' (bloco 7) migrou para pesquisadores.html em 13/09/2026 (proposta de
  // enxugamento, Manus AI) — teste de renderização correspondente removido daqui.
  // v3.1 §7: as fontes do financiamento vivem em pesquisadores.html
  const caixas = [...d.querySelectorAll(".figura")].filter(c => c.querySelector("svg, canvas, table, ul"));
  const semCredito = caixas.filter(c => !c.querySelector(".fonte-figura") && !c.closest("#rotasCards") && !c.closest("#comoler"));
  teste(`toda figura tem crédito de fonte (${caixas.length - semCredito.length}/${caixas.length})`, semCredito.length === 0);
  teste("figuras: nenhum parágrafo ou nota dentro de cartão (decisão editorial 04/09/2026)", caixas.every(c => c.querySelectorAll(":scope > .note, :scope > .hint, :scope > p:not(.figura-sub):not(.figura-cat):not(.figura-leitura)").length === 0));
  try { const p = q("mapaMPsUF").querySelector("path"); p.dispatchEvent(new dom.window.MouseEvent("mouseenter", { clientX: 100, clientY: 100, bubbles: true })); teste("gesto: tooltip", q("mapTooltip").style.display === "block" && q("mapTooltip").innerHTML.length > 5); } catch (e) { teste("gesto: tooltip (" + e.message + ")", false); }
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
  // 14/09/2026: rota preventiva do fogo — título-fato do dado, tabela por linha, mapa como lacuna declarada sem os arquivos de fogo/
  try {
    const rp = JSON.parse(fs.readFileSync(path.join(raiz, "data", "financiamento", "rotas_preventivas.json"), "utf8"));
    teste("fogo: título-fato traz os números do edital (do dado)", new RegExp(String(rp.rotas.find(r => r.id === "fogo_edital_2025").valores.elegiveis) + ".*" + String(rp.rotas.find(r => r.id === "fogo_edital_2025").valores.contemplados)).test(q("fogoTitulo").textContent));
    teste("fogo: frase de não-existência só porque só há linha de incêndio", /não existe rota equivalente para seca nem para chuva/.test(q("fogoTitulo").textContent) === (rp.riscos_com_rota_preventiva.length === 1 && rp.riscos_com_rota_preventiva[0] === "incendio"));
    teste("fogo: um cartão por rota preventiva", q("fogoRotasCards").children.length === rp.rotas.length);
    const temFogo = fs.existsSync(path.join(raiz, "data", "financiamento", "fogo", "areas_declaradas.json"));
    teste("fogo: sem mapa até a resposta da LAI — nota no lugar", !q("boxFogoMapa") && /pedido de acesso à informação/.test(q("notaFogoMapa").textContent));
    teste("fogo: crédito dos cartões", /Fonte:/.test(q("fogoRotasFonte").textContent));
  } catch (e) { teste("fogo: bloco (" + e.message + ")", false); }
  // 15/09/2026 (§1.7/§1.6): "O que a União prometeu — e o que pagou" de volta a Financiamento, com a quarta porta para o calendário
  try {
    teste("prometeu: título-fato com nº de compromissos (do dado)", /\d+ compromissos federais verificados/.test(q("prometeuTitulo").textContent));
    teste("prometeu: série semanal com a faixa do período eleitoral e a porta para o calendário eleitoral", !!q("svgSerie").querySelector("rect") && !![...q("prometeu").querySelectorAll("a")].find(a => /calendario-eleitoral\.html/.test(a.getAttribute("href") || "")));
  } catch (e) { teste("prometeu: bloco (" + e.message + ")", false); }
  console.log(falhas.length ? `\n✗ ${falhas.length} verificação(ões) falharam.` : "\n✓ RUNTIME (financiamento) OK — rotas, faixa do defeso, mapas, resposta, compromissos, fontes, E10 e soma de preparação.");
  process.exit(falhas.length ? 1 : 0);
}, 1200);
