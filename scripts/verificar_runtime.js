#!/usr/bin/env node
/* Verificador de runtime do Monitor El Niño Brasil.
 * Executa index.html num navegador simulado (jsdom + d3 reais, Chart simulado),
 * com fetch local para data/*.json, e valida a renderização e o fluxo do cidadão.
 * Requer: npm i jsdom d3   ·   Uso: node scripts/verificar_runtime.js
 */
const N_PONTOS = require("../data/pontos_mapa.json").length;
const INDICE = require("../data/indice.json");
const INDICE_META = require("../data/meta.json");
const { JSDOM, VirtualConsole } = require("jsdom");
const fs = require("fs");
const path = require("path");

const raiz = path.join(__dirname, "..");
const html = fs.readFileSync(path.join(raiz, "index.html"), "utf-8");
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
    // Correção C3 da auditoria de 29/08/2026 (limitação registrada em
    // 27/08/2026, fechada nesta versão): o listener de "unhandledrejection"
    // acima captura exceções lançadas no fluxo async de __load()/__init(),
    // que antes eram engolidas silenciosamente e faziam o portão falhar só
    // por ausência de conteúdo, sem mensagem — a causa exata do incidente do
    // timelineData/MEDIA_NACIONAL, localizado à época por bisseção manual.
    // Validado por teste negativo em 29/08/2026: ReferenceError assíncrono
    // proposital acusado com mensagem clara (ver CHANGELOG v2.2.3).
  },
});

// 600ms: tempo empírico para o __init() assíncrono (fetch local + d3 + Chart
// simulado) terminar de popular o DOM antes de inspecioná-lo; não há um evento
// "pronto" explícito para aguardar, então o valor foi calibrado por tentativa.
setTimeout(() => {
  const d = dom.window.document, q = id => d.getElementById(id);
  const falhas = [];
  const teste = (nome, cond) => { console.log((cond ? "  ✓ " : "  ✗ ") + nome); if (!cond) falhas.push(nome); };

  teste("zero erros de runtime", erros.length === 0);
  erros.slice(0, 4).forEach(e => console.log("     ", e));
  teste(`tabela de auditoria: ${N_PONTOS} linhas`, q("tblBody") && q("tblBody").children.length === N_PONTOS);
  teste("seletor de UF populado", q("ufSelect") && q("ufSelect").children.length === 28);

  try {
    q("ufSelect").value = "SC";
    q("ufSelect").dispatchEvent(new dom.window.Event("change"));
    q("cidadeInput").value = "Blumenau";
    q("cidadeInput").dispatchEvent(new dom.window.Event("input"));
    const card = q("meuCard");
    teste("consulta municipal: card visível com contatos", !card.hidden && card.innerHTML.includes("199") && card.innerHTML.includes("mailto:"));
    teste("datalist com municípios de SC", q("listaMun").children.length === 295);
  } catch (e) { teste("fluxo da consulta municipal", false); }

  // ── v2.2.4 (§6): portão de linguagem — "não localizamos" só com verificação completa ──
  try {
    q("ufSelect").value = "MT";
    q("ufSelect").dispatchEvent(new dom.window.Event("change"));
    q("cidadeInput").value = "Sorriso"; // município sem registro no banco → nível padrão "não verificado"
    q("cidadeInput").dispatchEvent(new dom.window.Event("input"));
    const cardNV = q("meuCard").innerHTML;
    teste("medidor do herói: alvo da barra e número = média do índice (não o HTML)", (() => {
    const idx = JSON.parse(fs.readFileSync(path.join(raiz, "data", "indice.json"), "utf-8"));
    const tot = Object.keys(idx).filter(k => k.length === 2).map(k => idx[k].total); const media = Math.round(tot.reduce((a, b) => a + b, 0) / 27 * 10) / 10;
    const alvo = parseFloat(q("gaugeFill").dataset.alvo); const num = (q("gaugeNum").textContent || "").replace(",", ".");
    return Math.abs(alvo - media) < 0.05 && q("gaugeFill").style.width === alvo + "%";
  })());
  teste("linguagem: município não verificado diz 'Ainda não verificamos'", cardNV.includes("Ainda não verificamos"));
    teste("linguagem: município não verificado NÃO diz 'Não localizamos'", !/[Nn]ão localizamos/.test(cardNV));
  } catch (e) { teste("portão de linguagem v2.2.4", false); }

  try {
    const tile = d.querySelector('#regions .tile[data-uf="SC"]');
    tile.click();
    teste("detalhe do estado abre ao clique", !q("detail").hidden && q("detail").innerHTML.includes("Santa Catarina"));
  } catch (e) { teste("clique no estado", false); }

  // Botões de PDF: clicar de verdade e exigir que nenhum erro de runtime apareça.
  // Bug de produção achado em 31/08/2026 ao gerar uma amostra de PDFs para
  // conferência: "gerarPDFEstado is not defined" no clique (função local a
  // __init() chamada por onclick inline, que só enxerga escopo global). Este
  // portão nunca tinha clicado no botão, então nunca viu. Sem jsPDF (CDN não
  // carrega no jsdom) a função avisa e retorna — o que se testa aqui é que ela
  // EXISTE e é alcançável a partir do clique.
  const errosAntesPDF = erros.length;
  d.defaultView.alert = () => {};
  try { q("btnPDFEstado").click(); } catch (e) { erros.push("clique btnPDFEstado: " + e.message); }
  try { q("btnPDF").click(); } catch (e) { erros.push("clique btnPDF: " + e.message); }
  teste("botões de PDF (estado e município) são alcançáveis pelo clique, sem erro",
    erros.length === errosAntesPDF);

  // Relatório do cidadão (31/08/2026): um único template para estado e município.
  // Sem jsPDF no jsdom o PDF não é gerado, então aqui se confere o CONTRATO do
  // gerador no código-fonte: as seis seções na ordem certa, e nenhuma das
  // frases de auditor que Patricia mandou tirar (metodologia/componentes/
  // camada declarada ficam em METODOLOGIA.pdf, não no PDF do usuário).
  const fonte = fs.readFileSync(path.join(raiz, "index.html"), "utf-8");
  const ger = fonte.slice(fonte.indexOf("function gerarRelatorioCidadao("), fonte.indexOf("function gerarPDF(){"));
  const secoes = ["Em emergência, ligue", "Risco projetado para ", "O que já existe", "O que ainda falta", "Pedido de informação pronto", "Como se proteger", "Links úteis"];
  const posicoes = secoes.map(s => ger.indexOf("secao('" + s));
  teste("PDF do cidadão: as 7 seções existem, na ordem", posicoes.every((p, k) => p > 0 && (k === 0 || p > posicoes[k-1])));
  const jargao = ["posição ordinal", "pesos iguais", "peso aritmético", "camada declarada", "Confiança da verificação", "Pendências de verificação"];
  teste("PDF do cidadão: sem jargão de auditoria", !jargao.some(j => ger.includes(j)));
  // 31/08/2026: cartão e PDF diziam "nenhum decreto localizado" para Biguaçu enquanto o
  // mapa 6 mostrava o decreto de 30/08 — index.html não carregava atos_resposta.json.
  teste("PDF/cartão do cidadão: index.html carrega atos_resposta.json", /'atos_resposta'[,\]]/.test(fonte));
  teste("PDF do cidadão: mostra decretos de emergência do município", ger.includes("emergs.forEach"));
  try {
    q("ufSelect").value = "SC"; q("ufSelect").dispatchEvent(new dom.window.Event("change"));
    q("cidadeInput").value = "Biguaçu"; q("cidadeInput").dispatchEvent(new dom.window.Event("input"));
    teste("cartão de Biguaçu mostra o decreto de emergência de 30/08/2026", q("meuCard").innerHTML.includes("30/08/2026") && q("meuCard").innerHTML.includes("granizo"));
  } catch (e) { teste("cartão de Biguaçu (emergência)", false); }
  // Caixa "Prazos em curso" (31/08/2026): itens = marcos com vencimento e título curto,
  // vencendo daqui para a frente ou vencidos há até 60 dias — mesma regra da página.
  const prazos = JSON.parse(fs.readFileSync(path.join(raiz, "data", "prazos_uf.json"), "utf-8")).marcos;
  const _d = s => { const [dd, mm, aa] = s.split("/").map(Number); return new Date(aa, mm - 1, dd); };
  const _hoje = new Date(); _hoje.setHours(0, 0, 0, 0);
  const esperados = prazos.filter(m => m.vencimento && m.titulo_curto && Math.round((_d(m.vencimento) - _hoje) / 86400000) >= -60).length;
  teste(`prazos em curso: ${esperados} item(ns) renderizados a partir de prazos_uf.json`, q("prazosLista").querySelectorAll("li").length === esperados && esperados > 0);
  // Pedido de informação pronto (31/08/2026): presente no cartão da cidade e no detalhe do estado,
  // com linguagem probatória ("não localizou") e sem afirmação de inexistência.
  const pedidoCard = q("meuCard").querySelector(".pedido-texto"), pedidoUF = q("detail").querySelector(".pedido-texto");
  teste("pedido de informação pronto: cartão da cidade e detalhe do estado", !!pedidoCard && !!pedidoUF && /Lei nº 12\.527\/2011/.test(pedidoCard.value) && /Lei nº 12\.527\/2011/.test(pedidoUF.value));
  teste("pedido de informação: nunca afirma inexistência", ![pedidoCard, pedidoUF].some(p => p && /não existe|inexist/i.test(p.value)));
  teste("PDF do cidadão: estado e município usam o mesmo gerador",
    /function gerarPDFEstado\(uf\)\{ ?gerarRelatorioCidadao\(uf, null\)/.test(fonte) && /gerarRelatorioCidadao\(uf, cid \|\| null\)/.test(fonte));

  // Tooltip compartilhado (usado pela linha do tempo do herói desde que os mapas
  // saíram para mapas-e-graficos.html, 31/08/2026) — alvo de hover trocado de
  // #mapCobertura (mudou de página) para um tick da linha do tempo, que continua aqui.
  const hover = d.querySelector(".strip-tick");
  hover.dispatchEvent(new dom.window.MouseEvent("mouseenter", { clientX: 100, clientY: 100, bubbles: true }));
  teste("tooltip da linha do tempo exibe conteúdo", q("mapTooltip").style.display === "block" && q("mapTooltip").innerHTML.length > 10);

  // KPIs do topo: sempre calculados a partir dos dados carregados (nunca texto fixo) —
  // guarda-corpo contra o card ficar desatualizado silenciosamente (achado de 31/08/2026).
  const nLAC = Object.values(INDICE).filter(v => v.status_estadual === "LAC").length;
  teste("KPI 'estados sem plano' bate com o banco", q("kpiSemPlano").textContent === String(nLAC));
  teste("KPI 'registros estaduais' = 27", q("kpiRegistros").textContent === "27");
  teste("KPI 'capitais verificadas' é numérico e > 0", /^\d+$/.test(q("kpiCapitais").textContent) && +q("kpiCapitais").textContent > 0);
  teste("KPI 'programas federais' bate com a lista real", q("kpiFederais").textContent === String(q("fontesFederais").querySelectorAll("li").length));
  teste("KPI 'municípios sem plano' é numérico", /^[\d.]+$/.test(q("kpiMunSemPlano").textContent));

  // Medidor principal do herói: a barra de progresso precisa de fato preencher
  // (achado de 31/08/2026 — animarGauges() estava escopada só a #regions e nunca
  // tocava o medidor do herói, que ficava sempre visualmente vazio).
  const fillWidth = q("gaugeFill").style.width;
  teste("barra do medidor principal preenche de verdade", fillWidth !== "" && fillWidth !== "0%");

  // Metadados do cabeçalho: nunca mais um nome de arquivo inventado (achado de
  // Patricia, 31/08/2026 — "BD_El_Nino_2026_2027_Brasil.xlsx" não existia no
  // projeto); e a data de "última verificação" precisa vir de META, não de texto fixo.
  // Checagem sobre o CONTEÚDO RENDERIZADO (body, excluindo <script>/<style>, que
  // carregam o comentário-fonte da própria correção) — não o código-fonte bruto.
  const bodyClone = d.body.cloneNode(true);
  bodyClone.querySelectorAll("script, style").forEach(n => n.remove());
  teste("nenhum nome de arquivo .xlsx inventado na página renderizada", !/BD_El_Nino.*\.xlsx/i.test(bodyClone.innerHTML));
  teste("data de última verificação bate com META", q("metaUltimaVerif").textContent === INDICE_META.atualizado_em);
  teste("rodapé 'última atualização' bate com META", q("metaAtualizado").textContent === INDICE_META.atualizado_em);

  if (falhas.length) { console.error(`\n✗ ${falhas.length} verificação(ões) falharam.`); process.exit(1); }
  console.log("\n✓ RUNTIME OK — todas as verificações passaram.");
  process.exit(0);
}, 600);
