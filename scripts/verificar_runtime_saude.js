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
const { JSDOM, VirtualConsole } = require("jsdom"); const { inlinePageJs } = require("./_inline_js");
const fs = require("fs");
const path = require("path");

const raiz = path.join(__dirname, "..");
const html = inlinePageJs(fs.readFileSync(path.join(raiz, "saude.html"), "utf-8"), raiz);
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
  const SUF = JSON.parse(fs.readFileSync(path.join(raiz, "data", "saude_uf.json"), "utf-8"));
  teste("zero erros de runtime", erros.length === 0);
  erros.slice(0, 4).forEach(e => console.log("     ", e));
  for (const id of ["mapaStatus", "mapaRiscoSan", "mapaDengue", "mapaCalor"]) {
    teste(`${id}: 27 estados desenhados`, q(id) && q(id).querySelectorAll("path").length === 27);
    teste(`${id}: legenda preenchida`, q(id.replace("mapa", "leg")) && q(id.replace("mapa", "leg")).children.length >= 1);
  }
  // 13/09/2026 (auditoria de visualizações, consolidação): boxEmerg só aparece quando há
  // ocorrência (SSIN.emergencias.length > 0) — hoje é sempre 0, então o esperado é oculto,
  // não um mapa cinza redundante com o contador de boxRespostaSanitaria.
  teste("boxEmerg: oculto enquanto não há emergência registrada (contador em boxRespostaSanitaria cobre o zero)", q("boxEmerg") && q("boxEmerg").hidden === true);
  const nNV = Object.values(SUF.uf).filter(u => u.status === "NAO_VERIFICADO").length;
  teste(`contagem de UFs não verificadas renderizada = arquivo (${nNV})`, (q("contagemUF").textContent || "").includes(nNV + " de 27"));
  // 'O que a União publicou' migrou para pesquisadores.html em 13/09/2026 (proposta de
  // enxugamento, Manus AI) — teste de renderização correspondente removido daqui.
  teste("tabela das 27 UFs", d.querySelectorAll("#tblUF tbody tr").length === 27);
  // 13/09/2026 (proposta de enxugamento, Manus AI): seletor de estado logo após o título
  try {
    const sel = q("selEstadoSaude");
    teste("seletor de estado: 27 opções (+ 1 em branco)", sel && sel.options.length === 28);
    sel.value = "SC";
    sel.dispatchEvent(new dom.window.Event("change", { bubbles: true }));
    const perfil = q("perfilEstadoSaude");
    teste("perfil do estado: aparece ao selecionar, com 4 cartões", perfil && !perfil.hidden && perfil.querySelectorAll(".cartao").length === 4);
    sel.value = ""; sel.dispatchEvent(new dom.window.Event("change", { bubbles: true }));
    teste("perfil do estado: some ao limpar a seleção", perfil.hidden === true);
  } catch (e) { teste("seletor de estado", false); }
  // 14/09/2026: seletor de doença do comparador/mapa — chikungunya sem arquivo chik_* deve virar lacuna declarada, nunca gráfico inventado
  try {
    const sd = q("selDoencaDesf");
    teste("seletor de doença: dengue e chikungunya", sd && [...sd.options].map(o => o.value).join(",") === "dengue,chikungunya");
    const temChik = fs.existsSync(path.join(raiz, "data", "saude_desfechos", "chik_serie_painel.json"));
    sd.value = "chikungunya"; sd.dispatchEvent(new dom.window.Event("change", { bubbles: true }));
    const opSem = q("selComparadorDengue").querySelector('option[value="semanal"]');
    teste("chikungunya: opção 'semanal por capitais' some (sem série por capitais)", opSem && opSem.hidden === true);
    if (!temChik) {
      teste("chikungunya sem coleta: legenda declara lacuna, mapa sem pontos", /ainda não coletada/.test(q("legDesfAcum").textContent) && q("mapaDesf").querySelectorAll("circle").length === 0);
    } else {
      teste("chikungunya coletada: mapa com pontos do painel", q("mapaDesf").querySelectorAll("circle").length > 0);
    }
    sd.value = "dengue"; sd.dispatchEvent(new dom.window.Event("change", { bubbles: true }));
    teste("volta para dengue: mapa do painel redesenhado com pontos", q("mapaDesf").querySelectorAll("circle").length > 0 && opSem.hidden === false);
  } catch (e) { teste("seletor de doença", false); console.log("     ", e && e.message); }
  // 14/09/2026: figura respiratória SRAG | SG — sem arquivo, lacuna declarada visível (SVG) e canvas escondido; nunca moldura vazia
  try {
    const si = q("selIndicadorSRAG");
    teste("seletor respiratório: srag e sg", si && [...si.options].map(o => o.value).join(",") === "srag,sg");
    const temSRAG = fs.existsSync(path.join(raiz, "data", "saude_desfechos", "srag_serie.json"));
    const temSG = fs.existsSync(path.join(raiz, "data", "saude_desfechos", "sg_serie.json"));
    const estado = () => ({svg: !q("svgSRAGLacuna").hidden, cv: !q("cSRAG").hidden, txt: q("svgSRAGLacuna").textContent});
    let e0 = estado();
    teste("SRAG: " + (temSRAG ? "canvas visível com dado" : "lacuna declarada visível"), temSRAG ? (e0.cv && !e0.svg) : (e0.svg && !e0.cv && /SRAG.*lacuna declarada/.test(e0.txt)));
    si.value = "sg"; si.dispatchEvent(new dom.window.Event("change", { bubbles: true })); let e1 = estado();
    teste("SG: " + (temSG ? "canvas visível com dado" : "lacuna declarada visível"), temSG ? (e1.cv && !e1.svg) : (e1.svg && !e1.cv && /síndrome gripal.*lacuna declarada/.test(e1.txt)));
    si.value = "srag"; si.dispatchEvent(new dom.window.Event("change", { bubbles: true })); let e2 = estado();
    teste("volta para SRAG: estado idêntico ao inicial", e2.cv === e0.cv && e2.svg === e0.svg);
    // 14/09/2026: figura de DDA — mesmo componente e renderizador da respiratória; sem dda_serie.json, lacuna declarada visível
    const temDDA = fs.existsSync(path.join(raiz, "data", "saude_desfechos", "dda_serie.json"));
    const eD = {svg: !q("svgDDALacuna").hidden, cv: !q("cDDA").hidden, txt: q("svgDDALacuna").textContent};
    teste("DDA: " + (temDDA ? "canvas visível com dado" : "lacuna declarada visível"), temDDA ? (eD.cv && !eD.svg) : (eD.svg && !eD.cv && /DDA.*lacuna declarada/.test(eD.txt)));
    teste("DDA: legenda nunca fala em nowcasting (a fonte não estima)", !/nowcasting/.test(q("legDDA").textContent));
  } catch (e) { teste("seletor respiratório", false); console.log("     ", e && e.message); }
  // 13/09/2026 (proposta de enxugamento, Manus AI): quadrante 'Defesa civil × saúde' retirado —
  // teste de renderização correspondente removido daqui.
  // gesto: tooltip ao passar o mouse num estado
  try {
    const p = q("mapaStatus").querySelector("path");
    p.dispatchEvent(new dom.window.MouseEvent("mouseenter", { clientX: 100, clientY: 100, bubbles: true }));
    teste("gesto: tooltip abre ao passar o mouse", q("mapTooltip").style.display === "block" && q("mapTooltip").innerHTML.length > 10);
  } catch (e) { teste("gesto: tooltip", false); }
  // crédito por figura: UMA linha .fonte-figura ao pé do cartão
  const caixas = [...d.querySelectorAll(".figura")].filter(c => c.querySelector("svg, canvas"));
  const semCredito = caixas.filter(c => !c.querySelector(".fonte-figura"));
  teste(`toda figura tem crédito de fonte (${caixas.length - semCredito.length}/${caixas.length})`, semCredito.length === 0);
  teste("Monitor Saúde: mapa com 27 UFs, legenda com contagens e tabela alternativa completa", (() => {
    return d.querySelectorAll("#mapaMonitor path").length === 27 && /não verificado/.test(q("legMonitor").textContent)
      && d.querySelectorAll("#tblMonitor tbody tr").length === 27;
  })());
  // 14/09/2026 (v0.2): medidor MARÉ · Saúde com a mesma anatomia do medidor da home; alvo = média das UFs verificadas;
  // legenda diz "não é um número nacional"; contagem de não verificadas preenchida; badge de faixa presente.
  teste("MARÉ · Saúde: medidor idêntico ao da home, alvo = média das verificadas, 'não é um número nacional'", (() => {
    const fill = q("gaugeSaudeFill"), num = q("gaugeSaudeNum"), nota = q("gaugeSaudeNota"), nv = q("gaugeSaudeNV");
    if (!fill || !num || !nota || !nv) return false;
    const mon = JSON.parse(fs.readFileSync(path.join(raiz, "data", "monitor_saude.json"), "utf8"));
    const media = mon.resumo && mon.resumo.media_das_verificadas;
    return Math.abs(parseFloat(fill.dataset.alvo) - media) < 0.05 && /não é um número nacional/.test(nota.textContent)
      && nv.textContent.trim() === String(mon.resumo.nao_verificadas) && fill.closest(".gauge-track") !== null
      && d.querySelectorAll("#metadeSaude .gtick").length === 3 && !!q("faixaSaude");
  })());
  teste("figuras: nenhum parágrafo ou nota dentro de cartão (decisão editorial 04/09/2026)", caixas.every(c => c.querySelectorAll(":scope > .note, :scope > .hint, :scope > p:not(.figura-sub):not(.figura-cat):not(.figura-leitura)").length === 0));
  // linguagem: "não localizamos" só como lacuna de coleta ("Não localizamos coleta"), nunca sobre instrumento não verificado
  const texto = d.body.textContent;
  const naoLocIndevido = /não localizamos (?!coleta)/i.test(texto);
  teste("linguagem: 'não localizamos' só para lacuna de coleta", !naoLocIndevido);
  teste("crédito InfoDengue visível na página", texto.includes("InfoDengue (Fiocruz/FGV)"));
  // nav canônica com Saúde ativa
  const ativa = d.querySelector(".mainnav .ativa");
  teste("nav: 'MARÉ Saúde' é o item ativo", ativa && ativa.textContent.trim() === "MARÉ Saúde");

  // ── padrão único de mapas (03/09/2026): siglas das 27 UFs em todo mapa; legendas canônicas ──
  const mapasSvg = [...d.querySelectorAll('svg[id^="map"], svg[id^="mapa"]')].filter(s => s.querySelector("path.uf-path") || s.querySelector("path"));
  teste(`padrão de mapas: ${mapasSvg.length} mapa(s) com siglas das 27 UFs`, mapasSvg.length > 0 && mapasSvg.every(s => s.querySelectorAll("g.siglas text").length === 27));
  const legendas = [...d.querySelectorAll(".map-legend")].filter(l => l.children.length);
  teste(`padrão de legendas: ${legendas.length} legenda(s) no formato canônico`, legendas.every(l => [...l.children].every(c => c.tagName === "SPAN" && (c.classList.contains("escala") || (c.firstElementChild && c.firstElementChild.tagName === "I" && /background:/.test(c.firstElementChild.getAttribute("style") || ""))) && c.textContent.trim().length > 0)));
  console.log(falhas.length ? `\n✗ ${falhas.length} verificação(ões) falharam.` : "\n✓ RUNTIME (saúde) OK — mapas, cartões, tooltip, créditos e lacunas declaradas.");
  process.exit(falhas.length ? 1 : 0);
}, 900);
