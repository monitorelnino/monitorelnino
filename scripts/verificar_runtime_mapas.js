#!/usr/bin/env node
/* Verificador de runtime da página de mapas e gráficos (mapas-e-graficos.html),
 * separada de index.html em 31/08/2026. Mesmo padrão de scripts/verificar_runtime.js
 * (jsdom + d3 reais, Chart simulado, fetch local), cobrindo os 7 mapas, a tabela
 * risco×instrumento e os totais que migraram para cá.
 * Uso: node scripts/verificar_runtime_mapas.js
 */
const N_PONTOS = require("../data/pontos_mapa.json").length;
const CONSIST = require("../data/consist.json");
const ATOS_RESPOSTA = require("../data/atos_resposta.json");
const MUNICIPIOS = require("../data/municipios.json");
const { JSDOM, VirtualConsole } = require("jsdom");
const fs = require("fs");
const path = require("path");

const raiz = path.join(__dirname, "..");
const html = fs.readFileSync(path.join(raiz, "mapas-e-graficos.html"), "utf-8");
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
  teste("mapa consistência: 27 estados", q("mapConsistencia") && q("mapConsistencia").querySelectorAll("path").length === 27);
  // (financiamento — mapa do dinheiro, totais e fontes — migrou para financiamento.html, E9; testado em verificar_runtime_financiamento.js)
  teste("mapa de municípios prioritários: 2.095 pontos", q("mapPrioritarios") && q("mapPrioritarios").querySelectorAll("circle").length === 2095);

  const hover = d.querySelector("#mapCobertura path");
  hover.dispatchEvent(new dom.window.MouseEvent("mouseenter", { clientX: 100, clientY: 100, bubbles: true }));
  teste("tooltip de mapa exibe conteúdo", q("mapTooltip").style.display === "block" && q("mapTooltip").innerHTML.length > 10);

  // Tabela "risco × instrumento" gerada de CONSIST (achado de 31/08/2026 — a cópia
  // estática anterior tinha divergido de verdade: PE aparecia em 2 categorias ao
  // mesmo tempo). Confere: sem duplicata de UF, contagem por categoria bate com
  // CONSIST, e as 27 UFs aparecem exatamente uma vez cada, no total.
  const linhasTabela = Array.from(q("tblConsistencia").querySelectorAll("tr"))
    .filter(tr => !tr.querySelector('td[colspan]'));
  const ufsNaTabela = linhasTabela.map(tr => tr.querySelector("strong").textContent);
  teste("tabela risco×instrumento: 27 UFs, sem duplicata", ufsNaTabela.length === 27 && new Set(ufsNaTabela).size === 27);
  const contagemReal = {};
  Object.values(CONSIST).forEach(v => { contagemReal[v.cat] = (contagemReal[v.cat] || 0) + 1; });
  const cabecalhos = Array.from(q("tblConsistencia").querySelectorAll("tr"))
    .filter(tr => tr.querySelector('td[colspan]'))
    .map(tr => tr.textContent);
  const contagemNaoBate = cabecalhos.some(txt => {
    const m = txt.match(/· (\d+) estado/);
    return m && !Object.values(contagemReal).includes(+m[1]);
  });
  teste("tabela risco×instrumento: cabeçalhos batem com a contagem real de CONSIST", !contagemNaoBate);

  // Mapa de atos de resposta (decretos de emergência) — pedido de Patricia, 31/08/2026,
  // motivado pelo temporal de granizo em SC.
  const decretosMun = MUNICIPIOS.filter(m => m.categoria === "decreto").length;
  const totalEsperado = decretosMun + ATOS_RESPOSTA.eventos.length;
  const totalNaPagina = q("countAtosResposta").textContent;
  teste("mapa de atos de resposta: contador bate (decreto em municipios.json + atos_resposta.json)",
    totalNaPagina === String(totalEsperado));
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
  const MAPAS_COM_SIGLA = ["mapPoints", "mapCobertura", "mapNatureza", "mapConsistencia",
    "mapPrioritarios", "mapAtosResposta"];
  const semSiglaCompleta = MAPAS_COM_SIGLA.filter(id => q(id).querySelectorAll("text").length !== 27);
  teste("harmonização: todos os 7 mapas têm as 27 siglas de UF", semSiglaCompleta.length === 0);
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

  // Achado de Patricia, 31/08/2026 (quarta rodada): os mapas 5 e 6 tinham 2
  // parágrafos de introdução visíveis, contra 1 em todos os outros 13 cartões
  // da página (mapas e gráficos) — regra agora fixada: exatamente 1 parágrafo
  // visível por cartão; qualquer detalhe extra vai para dentro de <details>.
  const cartoesComParagrafosDemais = [...d.querySelectorAll(".map-box, .chart-box")]
    .map(c => ({
      titulo: c.querySelector(".map-card-h")?.textContent.slice(0, 40) || "?",
      n: [...c.querySelectorAll(".note")].filter(p => !p.closest("details")).length,
    }))
    .filter(c => c.n !== 1);
  teste("harmonização: todo cartão de mapa/gráfico tem exatamente 1 parágrafo visível",
    cartoesComParagrafosDemais.length === 0);


  // ── padrão único de mapas (03/09/2026): siglas das 27 UFs em todo mapa; legendas canônicas ──
  const mapasSvg = [...d.querySelectorAll('svg[id^="map"], svg[id^="mapa"]')].filter(s => s.querySelector("path.uf-path") || s.querySelector("path"));
  teste(`padrão de mapas: ${mapasSvg.length} mapa(s) com siglas das 27 UFs`, mapasSvg.length > 0 && mapasSvg.every(s => s.querySelectorAll("g.siglas text").length === 27));
  const legendas = [...d.querySelectorAll(".map-legend")].filter(l => l.children.length);
  teste(`padrão de legendas: ${legendas.length} legenda(s) no formato <span><i></i>rótulo</span>`, legendas.every(l => [...l.children].every(c => c.tagName === "SPAN" && (c.classList.contains("escala") || (c.firstElementChild && c.firstElementChild.tagName === "I")) && /background:/.test(c.firstElementChild.getAttribute("style") || "") && c.textContent.trim().length > 0)));
  if (falhas.length) { console.error(`\n✗ ${falhas.length} verificação(ões) falharam.`); process.exit(1); }
  console.log("\n✓ RUNTIME (mapas e gráficos) OK — todas as verificações passaram.");
  process.exit(0);
}, 600);
