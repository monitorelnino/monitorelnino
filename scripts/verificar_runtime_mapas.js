#!/usr/bin/env node
/* Verificador de runtime da página Defesa civil (defesa-civil.html; ex-mapas e gráficos),
 * separada de index.html em 31/08/2026. Mesmo padrão de scripts/verificar_runtime.js
 * (jsdom + d3 reais, Chart simulado, fetch local), cobrindo os 7 mapas, a tabela
 * risco×instrumento e os totais que migraram para cá.
 * Uso: node scripts/verificar_runtime_mapas.js
 */
const N_PONTOS = require("../data/pontos_mapa.json").length;
const CONSIST = require("../data/consist.json");
const ATOS_RESPOSTA = require("../data/atos_resposta.json");
const MUNICIPIOS = require("../data/municipios.json");
const { JSDOM, VirtualConsole } = require("jsdom"); const { inlinePageJs } = require("./_inline_js");
const fs = require("fs");
const path = require("path");

const raiz = path.join(__dirname, "..");
const html = inlinePageJs(fs.readFileSync(path.join(raiz, "defesa-civil.html"), "utf-8"), raiz);
const erros = [];
const vc = new VirtualConsole();
vc.on("jsdomError", e => erros.push(e.detail && e.detail.stack ? e.detail.stack.split("\n")[0] : e.message));

const dom = new JSDOM(html, {
  url: "https://localhost/", runScripts: "dangerously", virtualConsole: vc,
  beforeParse(w) {
    global.window = w; global.document = w.document; global.navigator = w.navigator;
    w.d3 = require("d3");
    // módulo único de mapas (o <script src> externo não é carregado pelo jsdom sem resources)
    w.eval(fs.readFileSync(path.join(raiz, "assets", "mapas.js"), "utf-8"));
    class Chart { constructor() {} } Chart.defaults = { font: {}, color: "" };
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
      erros.push("unhandledrejection: " + (e.reason && e.reason.message || e.reason)));
  },
});

setTimeout(() => {
  const d = dom.window.document, q = id => d.getElementById(id);
  const falhas = [];
  const teste = (nome, cond) => { console.log((cond ? "  ✓ " : "  ✗ ") + nome); if (!cond) falhas.push(nome); };

  teste("zero erros de runtime", erros.length === 0);
  erros.slice(0, 4).forEach(e => console.log("     ", e));

  teste(`mapa fase 1: ${N_PONTOS} pontos`, q("mapPoints") && q("mapPoints").querySelectorAll("circle").length === N_PONTOS);
  teste("mapa cobertura: 27 estados", q("mapCobertura") && q("mapCobertura").querySelectorAll("path").length === 27);
  teste("mapa natureza: 27 estados", q("mapNatureza") && q("mapNatureza").querySelectorAll("path").length === 27);
  // mapConsistencia/tblConsistencia retirados de defesa-civil.html em 13/09/2026 (auditoria de
  // visualizações, consolidação) — versão principal do cruzamento risco×instrumento fica em
  // monitor-de-riscos.html (boxCruz); aqui sobrou um resumo compacto com link, testado abaixo.
  // (financiamento — mapa do dinheiro, totais e fontes — migrou para financiamento.html, E9; testado em verificar_runtime_financiamento.js)
  teste("mapa de municípios prioritários: 2.095 pontos", q("mapPrioritarios") && q("mapPrioritarios").querySelectorAll("circle").length === 2095);

  const hover = d.querySelector("#mapCobertura path");
  hover.dispatchEvent(new dom.window.MouseEvent("mouseenter", { clientX: 100, clientY: 100, bubbles: true }));
  teste("tooltip de mapa exibe conteúdo", q("mapTooltip").style.display === "block" && q("mapTooltip").innerHTML.length > 10);

  // Tabela "risco × instrumento" (tblConsistencia) retirada de defesa-civil.html em 13/09/2026 —
  // ver comentário acima. O resumo compacto (#riscoinstrumentoResumo) e o cruzamento completo que
  // ele linkava (index.html#boxCruz) saíram do site em 17/09/2026 (pedido da editoria).
  teste("Defesa Civil sem o resumo risco×instrumento (removido junto com o cruzamento)", !q("riscoinstrumentoResumo"));

  // Mapa de atos de resposta (decretos de emergência) — pedido de Patricia, 31/08/2026,
  // motivado pelo temporal de granizo em SC.
  const decretosMun = MUNICIPIOS.filter(m => m.categoria === "decreto").length;
  const totalEsperado = decretosMun + ATOS_RESPOSTA.eventos.length;
  // 04/09/2026: o contador em texto saiu do cartão (figuras só com título, legenda e crédito);
  // a contagem passa a ser conferida direto no mapa, abaixo.
  const pontosNoMapa = d.querySelectorAll("#mapAtosResposta circle").length;
  teste("mapa de atos de resposta: um círculo por evento, nenhum a mais nem a menos",
    pontosNoMapa === totalEsperado);
  const nomesSC = new Set(ATOS_RESPOSTA.eventos.filter(e => e.uf === "SC").map(e => e.nome));
  const esperados5 = ["Biguaçu", "Bom Jesus", "Florianópolis", "Ipuaçu", "Quilombo"];
  teste("mapa de atos de resposta: os 5 municípios de SC do temporal de 30/08 estão presentes",
    esperados5.every(n => nomesSC.has(n)));

  // Financiamento: totais derivados de transferencias.json, nunca texto fixo.

  // Harmonização visual entre os 7 mapas (achado de Patricia, 31/08/2026: os mapas
  // 5, 6 e 7 — municípios prioritários, atos de resposta, transferências — tinham
  // legendas fora do padrão dos mapas 1-4: sem siglas de UF, opacidade reduzida nos
  // pontos, legenda centralizada em vez de alinhada à esquerda). Todo mapa categórico
  // precisa ter as 27 siglas, e nenhuma legenda pode sobrescrever o alinhamento padrão.
  const MAPAS_COM_SIGLA = ["mapPoints", "mapCobertura", "mapNatureza",
    "mapPrioritarios", "mapAtosResposta"];   // mapConsistencia retirado em 13/09/2026 (auditoria de visualizações)
  const semSiglaCompleta = MAPAS_COM_SIGLA.filter(id => q(id).querySelectorAll("text").length !== 27);
  teste("harmonização: todos os 6 mapas têm as 27 siglas de UF", semSiglaCompleta.length === 0);
  const legendasDesalinhadas = [...d.querySelectorAll(".map-legend")]
    .filter(el => el.getAttribute("style") && /justify-content/.test(el.getAttribute("style")));
  teste("harmonização: nenhuma legenda de mapa sobrescreve o alinhamento padrão", legendasDesalinhadas.length === 0);

  // Achado de Patricia, 31/08/2026 (segunda rodada): o ícone de cor da legenda do
  // mapa 5 tinha preenchimento quase invisível (#E4DBC6, quase a cor de fundo do
  // cartão) com borda tracejada — visualmente quebrado, mesmo com o resto da
  // legenda já corrigido. O padrão certo, já estabelecido nos mapas 3 e 4, é
  // hachura de listras diagonais (repeating-linear-gradient) para "sem dado" —
  // nunca borda tracejada sobre preenchimento quase invisível.
  const iconesQuebrados = [...d.querySelectorAll(".map-legend i")]
    .filter(el => /dashed/.test(el.getAttribute("style") || ""));
  teste("harmonização: nenhum ícone de legenda usa borda tracejada sobre preenchimento (use hachura)",
    iconesQuebrados.length === 0);

  // Achado de Patricia, 31/08/2026 (terceira rodada): itens de legenda muito longos
  // (até 63 caracteres, contra 5-22 nas legendas mais compactas da página) faziam
  // cada item ocupar sua própria linha em vez de várias legendas cabendo lado a lado
  // — rótulos precisam ser nomes de categoria diretos, não frases descritivas com
  // parênteses explicativos (esses vão no tooltip, que já tem espaço de sobra).
  const itensLongos = [...d.querySelectorAll(".map-legend > span:not(.escala)")]
    .filter(s => s.textContent.length > 40);
  teste("harmonização: nenhum item de legenda passa de 40 caracteres",
    itensLongos.length === 0);

  // Decisão editorial de 04/09/2026: figuras trazem SÓ título, legenda e crédito de uma linha.
  // Nenhum parágrafo/nota dentro de cartão (o portão scripts/verificar_figuras.js cobre as 5 páginas;
  // aqui fica a guarda local desta página).
  const cartoesComParagrafo = [...d.querySelectorAll(".figura")]
    .filter(c => [...c.querySelectorAll(".note, .hint, p")].some(e => !e.closest("details") && !e.classList.contains("figura-titulo") && !e.classList.contains("figura-sub") && !e.classList.contains("figura-leitura")));
  teste("figuras: nenhum parágrafo ou nota dentro de cartão de mapa/gráfico", cartoesComParagrafo.length === 0);


  // ── padrão único de mapas (03/09/2026): siglas das 27 UFs em todo mapa; legendas canônicas ──
  const mapasSvg = [...d.querySelectorAll('svg[id^="map"], svg[id^="mapa"]')].filter(s => s.querySelector("path.uf-path") || s.querySelector("path"));
  teste(`padrão de mapas: ${mapasSvg.length} mapa(s) com siglas das 27 UFs`, mapasSvg.length > 0 && mapasSvg.every(s => s.querySelectorAll("g.siglas text").length === 27));
  const legendas = [...d.querySelectorAll(".map-legend")].filter(l => l.children.length);
  teste(`padrão de legendas: ${legendas.length} legenda(s) no formato <span><i></i>rótulo</span>`, legendas.every(l => [...l.children].every(c => c.tagName === "SPAN" && (c.classList.contains("escala") || (c.firstElementChild && c.firstElementChild.tagName === "I")) && /background:/.test(c.firstElementChild.getAttribute("style") || "") && c.textContent.trim().length > 0)));
  // 15/09/2026 (§2.9): títulos-fato das figuras de Defesa civil vêm do dado; interpretações fora das figuras
  try {
    const DATA = JSON.parse(fs.readFileSync(path.join(raiz, "data", "estados.json"), "utf8")), RESP = JSON.parse(fs.readFileSync(path.join(raiz, "data", "resposta", "por_uf.json"), "utf8"));
    const st = DATA.ufs.map(u => u.status); const c = k => st.filter(x => k.includes(x)).length;
    const tR = d.querySelector("#boxRegion .figura-titulo").textContent;
    teste("defesa civil (a): título-fato com as três contagens (somam 27)", new RegExp(`^${c(["NOVO"])} estados com plano para o ciclo; ${c(["READ","VIG"])} com plano de todo ano`).test(tR) && (c(["NOVO"]) + c(["READ","VIG"]) + c(["ELAB","LAC"])) === 27);
    teste("defesa civil (c): verificação com 5.571 e planos municipais localizados", /^5\.571 municípios no registro federal.*[1-9]\d* planos municipais localizados$/.test(d.querySelector("#boxVerificacao .figura-titulo").textContent));
    teste("defesa civil (f): mapa com nº de municípios do dado", new RegExp("^Decretos: " + String(RESP.nacional.n_municipios).replace(/\B(?=(\d{3})+(?!\d))/g, ".") + " municípios").test(d.querySelector("#boxAtosResposta .figura-titulo").textContent));
    // 15/09/2026: a figura da série semanal saiu da página — o fato (primeiro decreto e contagem no período eleitoral) migrou para interpDepois
    teste("defesa civil (g): primeiro decreto do dado e contagem no período eleitoral, fora de figura", new RegExp("Primeiro decreto do ciclo em " + RESP.nacional.primeiro_decreto + "; \\d").test(q("interpDepois").textContent));
    teste("defesa civil: interpretação fora da figura preenchida", /Por região:|Nenhum estado/.test(q("interpAntes").textContent));
  } catch (e) { teste("defesa civil: títulos-fato (" + e.message + ")", false); }
  // 15/09/2026: correção do portão — o teste que checava `falhas` rodava ANTES destes testes de
  // Defesa civil (bug pré-existente, §2.9): quaisquer falhas aqui nunca bloqueavam a publicação.
  // A checagem final agora cobre TODOS os testes acima, não só os anteriores a esta seção.
  if (falhas.length) { console.error(`\n✗ ${falhas.length} verificação(ões) falharam.`); process.exit(1); }
  console.log("\n✓ RUNTIME (mapas e gráficos) OK — todas as verificações passaram.");
  process.exit(0);
}, 600);
