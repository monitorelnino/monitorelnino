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
  for (const id of ["mapaStatus", "mapaRiscoSan", "mapaDengue", "mapaCalor", "mapaMonitor"]) {
    teste(`${id}: 27 estados desenhados`, q(id) && q(id).querySelectorAll("path").length === 27);
    teste(`${id}: legenda preenchida`, q(id.replace("mapa", "leg")) && q(id.replace("mapa", "leg")).children.length >= 1);
  }
  // 15/09/2026 (MARÉ Saúde espelha o MARÉ · Defesa civil): dois medidores no topo, ficha "Como ler", cartões por estado com detalhe em <dialog>,
  // uma seção por desfecho (dengue, chikungunya, calor, respiratórias, diarreicas) — nenhum desfecho em acordeão, nenhum seletor de doença.
  const nNV = Object.values(SUF.uf).filter(u => u.status === "NAO_VERIFICADO").length;
  teste(`contagem de UFs não verificadas renderizada = arquivo (${nNV})`, (q("contagemUF").textContent || "").includes(nNV + " de 27"));
  teste("tabela das 27 UFs", d.querySelectorAll("#tblUF tbody tr").length === 27);
  teste("mapas do painel (dengue e chikungunya): 27 estados e legenda", ["mapaDesf", "mapaChik"].every(id => q(id).querySelectorAll("path").length === 27) && q("legDesfMapa").children.length >= 1 && q("legChikMapa").children.length >= 1);
  teste("dengue nas capitais: 27 pontos dentro do mapa (coordenadas pela malha IBGE)", (() => { const c = [...d.querySelectorAll("#mapaDengue circle")]; return c.length === 27 && c.every(x => +x.getAttribute("cx") > 0 && +x.getAttribute("cx") < 480 && +x.getAttribute("cy") > 0 && +x.getAttribute("cy") < 460); })());
  teste("sem acordeão escondendo desfecho, sem seletor de doença", !q("outrosDesfechos") && !q("selDoencaDesf") && !q("boxEmerg") && !q("boxRespostaSanitaria"));
  teste("seções próprias: dengue, chikungunya, calor, respiratórias, diarreicas, na ordem, antes dos estados", (() => { const ids = [...d.querySelectorAll("main > .panel, main > .hero")].map(e => e.id); const pos = k => ids.indexOf(k); return pos("heroSaude") < pos("dengue") && pos("dengue") < pos("chikungunya") && pos("chikungunya") < pos("calor") && pos("calor") < pos("respiratorias") && pos("respiratorias") < pos("diarreicas") && pos("diarreicas") < pos("estados") && pos("estados") < pos("estadual"); })());
  const MSAUDE = JSON.parse(fs.readFileSync(path.join(raiz, "data", "monitor_saude.json"), "utf8"));
  teste("medidor de resposta sanitária: índice do dado (MSAUDE.resposta.indice), arte única, contagem na pílula", q("rsNum").textContent === MSAUDE.resposta.indice.toFixed(1).replace(".", ",") && !!d.querySelector("#contadorRespostaSaude .gauge-fill--resposta") && new RegExp(MSAUDE.resposta.emergencias + " emergência").test(q("rsBadge").textContent));
  teste("interpretação da resposta fora do medidor, com contagem e milhões", /emergência\(s\) sanitária\(s\) declarada\(s\) desde 29\/06\/2026/.test(q("interpRespostaSaude").textContent));
  teste("cartões por estado: 27, com face de três linhas e barra de resposta na arte única", d.querySelectorAll("#regionsSaude .tile").length === 27 && [...d.querySelectorAll("#regionsSaude .tile .tile-face")].every(f => f.querySelectorAll("span").length === 3) && d.querySelectorAll("#regionsSaude .tile .tile-fill--resposta").length === 27);
  teste("cartões por estado: micro-barra do índice só nos verificados", d.querySelectorAll("#regionsSaude .tile .tile-bar:not(.tile-bar--resposta)").length === MSAUDE.resumo.verificadas);
  try {
    const go = [...d.querySelectorAll("#regionsSaude .tile")].find(t => t.dataset.uf === "GO"); go.click();
    const det = q("detailSaudeConteudo").textContent;
    teste("detalhe do estado (GO): instrumento, componentes, resposta, risco e dengue na capital", /Instrumento estadual de saúde/.test(det) && /Componentes/.test(det) && /Resposta sanitária/.test(det) && /Risco sanitário projetado/.test(det) && /Dengue na capital/.test(det) && q("detailSaude").open === true);
    const nv = [...d.querySelectorAll("#regionsSaude .tile")].find(t => t.dataset.uf === Object.keys(SUF.uf).find(u => SUF.uf[u].status === "NAO_VERIFICADO")); if (nv) { nv.click(); teste("detalhe de UF não verificada: declara a bateria não executada, sem número", /bateria de busca de saúde não foi executada/.test(q("detailSaudeConteudo").textContent)); }
    q("linkComoLerSaude").click();
    teste("ficha 'Como ler o MARÉ · Saúde' abre no mesmo dialog, com O que conta / não conta / emergências / sem plano localizado / casos", (() => {
      // 16/09/2026 (handover da voz editorial, §5.3): a ficha foi reescrita — as seções passam a ser
      // "O que conta", "O que não conta", "Emergências declaradas", "Um estado sem plano localizado" e
      // "Sobre os casos". O teste segue exigindo que TODAS estejam no mesmo dialog, só com os rótulos novos.
      const t = q("detailSaudeConteudo").textContent;
      return /O que conta\./.test(t) && /O que não conta\./.test(t) && /Emergências declaradas\./.test(t)
        && /sem plano localizado/.test(t) && /Sobre os casos\./.test(t);
    })());
  } catch (e) { teste("cartões/detalhe (" + e.message + ")", false); }
  // chikungunya em seção própria: com arquivo, pontos no mapa; sem arquivo, lacuna declarada
  try {
    const temChik = fs.existsSync(path.join(raiz, "data", "saude_desfechos", "chik_serie_painel.json"));
    const opSem = q("selComparadorChik").querySelector('option[value="semanal"]');
    teste("chikungunya: sem opção 'semanal por capitais' (sem série por capitais)", !opSem);
    if (!temChik) teste("chikungunya sem coleta: legenda declara lacuna, mapa sem pontos", /ainda não coletada/.test(q("legChikSerie").textContent) && q("mapaChik").querySelectorAll("circle").length === 0);
    else teste("chikungunya coletada: mapa com pontos do painel", q("mapaChik").querySelectorAll("circle").length > 0);
    teste("dengue: mapa do painel com pontos e comparador com opção por capitais", q("mapaDesf").querySelectorAll("circle").length > 0 && !!q("selComparadorDengue").querySelector('option[value="semanal"]'));
  } catch (e) { teste("seções de doença", false); console.log("     ", e && e.message); }
  // 14/09/2026: figura respiratória SRAG | SG — sem arquivo, lacuna declarada visível (SVG) e canvas escondido; nunca moldura vazia
  try {
    // 15/09/2026: SRAG e SG em figuras próprias, lado a lado, sem seletor
    teste("respiratórias: duas figuras (SRAG e SG) lado a lado, sem seletor", !q("selIndicadorSRAG") && !!q("boxSRAG") && !!q("boxSG"));
    const temSRAG = fs.existsSync(path.join(raiz, "data", "saude_desfechos", "srag_serie.json"));
    const temSG = fs.existsSync(path.join(raiz, "data", "saude_desfechos", "sg_serie.json"));
    const e0 = {svg: !q("svgSRAGLacuna").hidden, cv: !q("cSRAG").hidden, txt: q("svgSRAGLacuna").textContent};
    teste("SRAG: " + (temSRAG ? "canvas visível com dado" : "lacuna declarada visível"), temSRAG ? (e0.cv && !e0.svg) : (e0.svg && !e0.cv && /SRAG.*lacuna declarada/.test(e0.txt)));
    const e1 = {svg: !q("svgSGLacuna").hidden, cv: !q("cSG").hidden, txt: q("svgSGLacuna").textContent};
    teste("SG: " + (temSG ? "canvas visível com dado" : "lacuna declarada visível"), temSG ? (e1.cv && !e1.svg) : (e1.svg && !e1.cv && /síndrome gripal.*lacuna declarada/.test(e1.txt)));
    teste("lado a lado: dengue com três figuras numa linha; item 'O que cada estado publicou' com três mapas numa linha", d.querySelectorAll("#dengue .grade-figuras--3 > .figura").length === 3 && d.querySelectorAll("#estadual .grade-figuras--3 > .figura").length === 3);
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
  // 15/09/2026 (§2.10): títulos-fato de Saúde vêm do dado
  try {
    const SUFd = JSON.parse(fs.readFileSync(path.join(raiz, "data", "saude_uf.json"), "utf8")); const UFS = Object.keys(SUFd.uf); const st = u => (SUFd.uf[u] || {}).status || "NAO_VERIFICADO";
    const c = k => UFS.filter(u => k.includes(st(u))).length;
    // 23/09/2026 (governança editorial §12, §32.8): boxMonitor pinta PRONTIDÃO SANITÁRIA; o título-fato
    // anterior contava estados por status de instrumento, que é o objeto da figura seguinte, e saía
    // quase igual ao dela. O princípio que este portão guarda continua o mesmo — o título vem do dado,
    // nunca digitado —, e a contagem agora sai do agregado autoritativo em monitor_saude.json.
    const MSd = JSON.parse(fs.readFileSync(path.join(raiz, "data", "monitor_saude.json"), "utf8"));
    teste("saúde: título-fato da prontidão com a contagem do dado", new RegExp(`^Prontidão sanitária por estado: ${MSd.resumo.verificadas} de ${UFS.length} estados verificados$`).test(q("boxMonitor").querySelector(".figura-titulo").textContent));
    teste("saúde: título-fato do status com as contagens do dado", new RegExp(`^Plano de saúde por estado: ${c(["NOVO"])} para o ciclo, ${c(["VIG","READ"])} de todo ano, ${c(["NAO_VERIFICADO"])} não verificados$`).test(q("boxStatus").querySelector(".figura-titulo").textContent));
    const DESFd = JSON.parse(fs.readFileSync(path.join(raiz, "data", "saude_desfechos", "serie_painel.json"), "utf8")); const M = DESFd.municipios; const se = Object.values(M).map(m => m.ultima_se).sort().pop();
    const alto = Object.values(M).filter(m => m.ultima_se === se && (m.nivel_ultima_se === 3 || m.nivel_ultima_se === 4)).length;
    teste("saúde: dengue — municípios em alerta laranja/vermelho na última semana, do dado", new RegExp(`^Dengue: ${alto} ${alto === 1 ? "município" : "municípios"} em alerta laranja ou vermelho na semana SE ${se.split("-")[1]} de 2026`).test(q("boxDesfMapa").querySelector(".figura-titulo").textContent));
    teste("saúde: interpretação fixa do InfoDengue fora da figura", /InfoDengue/.test(q("interpObservado").textContent));
  } catch (e) { teste("saúde: títulos-fato (" + e.message + ")", false); }
  console.log(falhas.length ? `\n✗ ${falhas.length} verificação(ões) falharam.` : "\n✓ RUNTIME (saúde) OK — mapas, cartões, tooltip, créditos e lacunas declaradas.");
  process.exit(falhas.length ? 1 : 0);
}, 900);
