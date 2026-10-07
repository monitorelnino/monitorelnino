#!/usr/bin/env node
/* Verificador de runtime da página de sinais oficiais de risco
 * (monitor-de-riscos.html, criada em 01/09/2026 — METODOLOGIA §23).
 * Mesmo padrão de scripts/verificar_runtime_mapas.js: jsdom + d3 reais,
 * Chart simulado, fetch local. Cobre os 4 mapas, os 4 gráficos, os cartões
 * do ciclo, a tabela de fontes e — o que é próprio desta página — a
 * PROVENIÊNCIA VISÍVEL: nenhuma figura pode ficar sem crédito de fonte, e
 * toda fonte não coletada precisa aparecer como lacuna declarada.
 * Uso: node scripts/verificar_runtime_sinais.js
 */
const SINAIS = require("../data/sinais_risco.json");
const MARE = require("../data/indice.json");
const { JSDOM, VirtualConsole } = require("jsdom"); const { inlinePageJs } = require("./_inline_js");
const fs = require("fs");
const path = require("path");

const raiz = path.join(__dirname, "..");
const html = inlinePageJs(fs.readFileSync(path.join(raiz, "monitor-de-riscos.html"), "utf-8"), raiz);
const erros = [];
const vc = new VirtualConsole();
vc.on("jsdomError", e => erros.push(e.detail && e.detail.stack ? e.detail.stack.split("\n")[0] : e.message));

const graficos = [];  // toda instância de Chart criada pela página

const dom = new JSDOM(html, {
  // A URL É A DA PÁGINA, de propósito: `assets/catalogo.js` descobre qual arquivo de conteúdo
  // pedir pelo `location.pathname`, e com "/" ele pedia `conteudo/index.json` — o portão
  // renderizava a página com o texto de RESERVA do HTML e conferia outra coisa que não a que vai
  // ao ar. É a mesma lição que o inlinador aprendeu em 05/10/2026, no outro extremo do caminho.
  url: "https://localhost/monitor-de-riscos.html", runScripts: "dangerously", virtualConsole: vc,
  beforeParse(w) {
    global.window = w; global.document = w.document; global.navigator = w.navigator;
    w.d3 = require("d3");
    // módulo único de mapas (o <script src> externo não é carregado pelo jsdom sem resources)
    w.eval(fs.readFileSync(path.join(raiz, "assets", "mapas.js"), "utf-8"));
    class Chart { constructor(ctx, cfg) { graficos.push({ ctx, cfg }); } }
    Chart.defaults = { font: {}, color: "" };
    w.Chart = Chart;
    w.fetch = (rel) => {
      const p = path.join(raiz, String(rel).replace(/^\//, "").split("?")[0]);
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

  teste("zero erros de runtime", erros.length === 0);
  erros.slice(0, 4).forEach(e => console.log("     ", e));

  // --- mapas: os quatro desenham as 27 UFs, coletados ou não ---
  // 24/09/2026: mapaAvisos e mapaCemaden saíram desta página — avisos e alertas moram na
  // Defesa civil, com granularidade municipal (verificar_runtime_defesa_civil.js cobre lá).
  // Entraram mapaTemperatura e mapaAr, por capital.
  // 27/09/2026: mapaTipoRisco saiu desta página — o risco projetado passou para o cartão de cada
  // estado na inicial (coberto em verificar_runtime.js). E temperatura e ar deixaram de PINTAR a
  // UF: a medida é de um ponto (a capital), então o mapa desenha um ponto. O contorno das 27 UFs
  // continua lá como base, mas a cor agora vive nos círculos.
  for (const id of ["mapaSecas", "mapaFogo"]) {
    teste(`${id}: 27 estados desenhados`, q(id) && q(id).querySelectorAll("g.ufs path").length === 27);
    teste(`${id}: legenda preenchida`, q(id.replace("mapa", "leg")) && q(id.replace("mapa", "leg")).children.length >= 2);
  }
  for (const [id, classe] of [["mapaTemperatura", "pontosTemp"], ["mapaAr", "pontosAr"]]) {
    teste(`${id}: contorno das 27 UFs como base`, q(id) && q(id).querySelectorAll("g.ufs path").length === 27);
    teste(`${id}: um ponto por capital com dado, e não pintura por UF`, (() => {
      const pts = q(id) && q(id).querySelectorAll(`g.${classe} circle`);
      // O que este teste quer dizer é "todas as UFs têm o MESMO preenchimento" — ou seja, o
      // estado não é pintado pelo dado. Contar `path` solto passou a incluir a malha de
      // coordenadas da atmosfera, que é fill="none", e dois valores distintos reprovavam um
      // mapa que estava certo.
      const fundos = new Set([...q(id).querySelectorAll("g.ufs path")].map(x => x.getAttribute("fill")));
      return pts && pts.length > 0 && pts.length <= 27 && fundos.size === 1;
    })());
    teste(`${id}: legenda preenchida`, q(id.replace("mapa", "leg")) && q(id.replace("mapa", "leg")).children.length >= 2);
  }

  // 27/09/2026: o risco projetado saiu desta página. O que resta conferir aqui é que ele NÃO
  // voltou por engano — o dado segue no registro e é exibido na inicial.
  teste("risco projetado não é mais desenhado nesta página", !q("mapaTipoRisco") && !q("tblTipoRisco"));

  // --- gráficos: os dois derivados do registro sempre existem;
  //     os dois dependentes de coleta existem OU exibem lacuna declarada ---
  teste("gráfico de estados por tipo de risco também saiu", !graficos.some(g => g.ctx && g.ctx.id === "cTipos"));
  // 15/09/2026: o cruzamento risco × estágio (cCruz) mudou para o fim da página inicial — testado em verificar_runtime.js.
  teste("cruzamento risco × estágio não fica mais nesta página (mora na inicial)", !q("cCruz") && !graficos.some(g => g.ctx && g.ctx.id === "cCruz"));
  // 30/09/2026: a figura do Pacífico neste painel passa a ser o RONI — o ONI e a anomalia mensal
  // saíram da página por decisão da editoria e vivem na METODOLOGIA. A cobrança não some: muda
  // de alvo junto com a página, e continua exigindo a figura dentro do painel e o resumo cheio.
  teste("RONI: figura dentro do painel 'Situação atual'", (() => { const s = q("situacao"); return !!(s && s.querySelector("#boxRoni")); })());

  // ===== O topo "Situação atual" e os dois gráficos do Pacífico (07/10/2026, parte 1) =========
  // O que estes testes guardam é o que o handover pediu e a conformidade não alcança sozinha: a
  // régua de força fora do topo, os anos do título saindo do DADO, a lista de episódios igual à
  // calculada pelo critério da NOAA/CPC, e nenhum número do topo sem fonte e data.
  const contrato = require("../layout/contratos/monitor-de-riscos.json");

  // --- a régua de força saiu, e com ela os três quadros com ícone ---
  teste("os três quadros com ícone saíram do topo",
    !q("stHaElNino") && !q("stForca") && !q("stChance") && !d.querySelector(".situacao--fichas"));

  // --- vocabulário proibido POR SEÇÃO, do contrato. "Chuva forte", na legenda dos mapas de "Os
  //     riscos no Brasil", é outra coisa e continua valendo: a regra é de seção, não de página ---
  Object.entries(contrato.secoes_texto_proibido || {}).forEach(([seletor, regra]) => {
    if (seletor.startsWith("_")) return;
    const secao = d.querySelector(seletor);
    if (!secao) { teste(`seção ${seletor} existe para o vocabulário por seção`, false); return; }
    // A exceção declarada: "muito forte" ENTRE ASPAS e atribuído à NOAA/CPC. Qualquer outra
    // ocorrência conta. Tirar os trechos citados antes de procurar é o que separa as duas.
    const texto = secao.textContent.replace(/[“"][^”"]*[”"]/g, " ");
    (regra.palavras || []).forEach(palavra => {
      const achou = new RegExp("\\b" + palavra.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "\\b", "i").test(texto);
      teste(`${seletor}: sem ${JSON.stringify(palavra)} fora de citação`, !achou);
    });
  });

  // --- os quatro cartões de número do topo: valor preenchido, e fonte com órgão e data ---
  const cartoes = contrato.numeros_esperados && contrato.numeros_esperados.cartoes || [];
  teste(`topo: ${cartoes.length} cartão(ões) de número no componente do site`,
    cartoes.length > 0 && cartoes.every(c => {
      const el = d.querySelector(`[data-cartao="${c}"]`);
      return el && el.classList.contains("cartao-numero") && el.closest(".grade-numeros");
    }));
  cartoes.forEach(c => {
    const el = d.querySelector(`[data-cartao="${c}"]`);
    const valor = el && el.querySelector(".cartao-numero-valor");
    const fonte = el && el.querySelector(".cartao-numero-fonte");
    const v = valor ? valor.textContent.trim() : "";
    // Travessão e vazio são o que `layout/regras.json` reprova em cartão de número, e aqui vale
    // sobre o cartão RENDERIZADO, que é onde o leitor o encontra.
    teste(`cartão '${c}': valor sem travessão e sem vazio`, v !== "" && v !== "—" && v !== "-");
    teste(`cartão '${c}': fonte com órgão e data`,
      !!(fonte && fonte.textContent.trim() && /\d{2}\/\d{2}\/\d{4}/.test(fonte.textContent)));
  });

  // --- os dois gráficos: SVG desenhado, nunca canvas escalado, e letra de 12 px ---
  for (const wrap of ["wrapRoni", "wrapEpisodios"]) {
    const coletada = SINAIS.fontes["noaa_roni"].status === "coletado";
    const svg = q(wrap) && q(wrap).querySelector("svg");
    const temLacuna = q(wrap) && q(wrap).querySelector(".lacuna");
    teste(`${wrap}: ${coletada ? "gráfico desenhado" : "lacuna declarada"}`, coletada ? !!svg : !!temLacuna);
    teste(`${wrap}: nunca gráfico e lacuna ao mesmo tempo`, !(svg && temLacuna));
    if (!svg) continue;
    teste(`${wrap}: o gráfico é SVG, e não canvas`, !q(wrap).querySelector("canvas"));
    teste(`${wrap}: mídia rotulada para leitor de tela`,
      svg.getAttribute("role") === "img" && (svg.getAttribute("aria-label") || "").length > 10);
    // Só os DOIS limiares oficiais da NOAA/CPC, e nenhuma faixa de força no fundo.
    teste(`${wrap}: duas linhas tracejadas de limiar, e nada além`, svg.querySelectorAll("line.lim").length === 2);
    teste(`${wrap}: nenhuma cor em hexadecimal no desenho`, !/#[0-9a-fA-F]{3,8}\b/.test(svg.outerHTML));
    teste(`${wrap}: todo valor tem rótulo ao passar o mouse`, svg.querySelectorAll("title").length > 0);
  }

  // --- o título do gráfico 1 traz os ANOS DO DADO ---
  const serieRoni = ((SINAIS.enos.roni || {}).serie || []);
  if (serieRoni.length) {
    const anoIni = serieRoni[0].ano, anoFim = serieRoni[serieRoni.length - 1].ano;
    const tit = (q("roniTitulo") || {}).textContent || "";
    teste(`título do gráfico 1 traz ${anoIni}–${anoFim}, do próprio dado`,
      tit.includes(String(anoIni)) && tit.includes(String(anoFim)));
  }

  // --- a lista de episódios do gráfico 2 é a CALCULADA pelo critério, nunca escrita à mão ---
  // O critério é o da NOAA/CPC: cinco ou mais médias trimestrais consecutivas acima de +0,5 °C.
  // Este cálculo é independente do da página, de propósito: ele existe para discordar dela.
  const CENTRO = {DJF:0,JFM:1,FMA:2,MAM:3,AMJ:4,MJJ:5,JJA:6,JAS:7,ASO:8,SON:9,OND:10,NDJ:11};
  const ord = p => p.ano * 12 + CENTRO[String(p.trimestre).toUpperCase()];
  const ordenada = serieRoni.filter(p => CENTRO[String(p.trimestre).toUpperCase()] !== undefined)
    .slice().sort((a, b) => ord(a) - ord(b));
  const trechos = [];
  let corrente = [];
  ordenada.forEach(pt => {
    const contiguo = !corrente.length || ord(pt) === ord(corrente[corrente.length - 1]) + 1;
    if (pt.anomalia > 0.5 && contiguo) { corrente.push(pt); return; }
    if (corrente.length) trechos.push(corrente);
    corrente = pt.anomalia > 0.5 ? [pt] : [];
  });
  if (corrente.length) trechos.push(corrente);
  const derradeiro = ordenada[ordenada.length - 1];
  const emCurso = trechos.find(t => t[t.length - 1] === derradeiro) || null;
  const esperados = trechos.filter(t => t !== emCurso && t.length >= 5)
    .map(t => t[0].ano + "–" + String(t[0].ano + 1).slice(2));
  if (emCurso) esperados.push(String(emCurso[0].ano));
  const naLegenda = [...d.querySelectorAll("#legEpisodios span")].map(x => x.textContent.trim());
  teste(`gráfico 2: episódios calculados do dado (${esperados.join(", ")})`,
    esperados.length > 0 && esperados.every(e => naLegenda.includes(e))
    && naLegenda.every(e => esperados.includes(e)));
  // 07/10/2026: a lista saiu do TÍTULO e foi para a NOTA — no título ela ocupava cinco linhas
  // numa coluna da grade de dois e desalinhava a dupla em 70 px, e com a série desde 1950 ela
  // cresce para dezenas de episódios. A cobrança não some: muda de alvo junto com a página.
  // Quem nomeia cada episódio é a LEGENDA, item a item (conferida acima), e a frase de leitura
  // sob o gráfico, com o valor de cada um. Nem o título nem a nota carregam a lista: as duas
  // reservam altura para a dupla alinhar, e lista que cresce com o dado estoura a reserva.
  const fechados = esperados.filter(e => e.includes("–"));
  const leituraEp = (q("episodiosLeitura") || {}).textContent || "";
  teste("gráfico 2: a leitura dá o valor de cada episódio e do ciclo em curso",
    esperados.every(e => leituraEp.includes(e.slice(0, 4))));
  const tituloEp = (q("episodiosTitulo") || {}).textContent || "";
  teste("gráfico 2: o título nomeia o ciclo em curso e não cresce com a lista",
    (!emCurso || tituloEp.includes(String(emCurso[0].ano)))
    && !fechados.some(e => tituloEp.includes(e)));
  teste("gráfico 2: uma linha por episódio, mais o ciclo em curso",
    q("wrapEpisodios") && q("wrapEpisodios").querySelectorAll("polyline").length === esperados.length);

  // --- a anomalia mensal saiu da página, e o dado dela continua coletado ---
  teste("a anomalia mensal do Niño 3.4 saiu da página", !q("boxAnomalia") && !q("wrapAnomalia"));
  teste("o dado da anomalia mensal continua no registro",
    !!(SINAIS.enos.nino34_mensal && (SINAIS.enos.nino34_mensal.serie || []).length));

  // --- cartões do estado do ciclo removidos em 13/09/2026 (unificados em 'Situação atual', pedido
  //     de Patricia): três dos quatro duplicavam valores já no painel; verificação virou parte do
  //     bloco de crédito abaixo (id 'situacao').

  // --- PROVENIÊNCIA VISÍVEL: regra própria desta página ---
  const creditos = [...d.querySelectorAll("[data-credito]")];
  const figuras = ["boxSecas", "boxTemperatura", "boxAr", "boxFogo", "boxRoni", "boxEpisodios", "boxRiscoPrevisto", "boxAvisos"]   // 24/09/2026: boxAvisos e boxCemaden foram para defesa-civil.html; entraram boxTemperatura e boxAr   // boxTipos fundido em boxTipoRisco (figura dupla) em 15/09/2026;   // boxCruz foi para a página inicial em 15/09/2026   // ids a partir de 1 (auditoria 07/09/2026); boxPlume retirado em 13/09/2026 (sem cobertura); cartaoCiclo1-4 retirados em 13/09/2026 (unificados em 'situacao')
  const semCredito = figuras.filter(id => !q(id) || !q(id).querySelector("[data-credito]"));
  teste(`toda figura tem crédito de fonte (${creditos.length} créditos)`, semCredito.length === 0);
  if (semCredito.length) console.log("      sem crédito:", semCredito.join(", "));

  const orgaosCitados = creditos.map(p => p.dataset.credito);
  const fonteDesconhecida = orgaosCitados.filter(f => !SINAIS.fontes[f]);
  teste("todo crédito aponta para fonte do catálogo", fonteDesconhecida.length === 0);

  const coletadasSemData = creditos.filter(p => SINAIS.fontes[p.dataset.credito].status === "coletado"
    && !/Atualização: \d{2}\/\d{2}\/\d{4}/.test(p.textContent));
  teste("crédito de fonte coletada traz a data de consulta", coletadasSemData.length === 0);

  const esperaSemTeto = creditos.filter(p => SINAIS.fontes[p.dataset.credito].status !== "coletado"
    && !/Não localizamos|sem coleta até o corte/.test(p.textContent));   // 04/09/2026: crédito de uma linha
  teste("fonte em espera usa a linguagem-teto do projeto", esperaSemTeto.length === 0);

  // --- tabela de fontes: uma linha por fonte catalogada ---
  const nFontes = Object.keys(SINAIS.fontes).length;
  // v3.1 §7: a tabela das oito fontes vive em pesquisadores.html

  // --- tooltip funciona no gesto do usuário (lição de 30/08: teste o gesto) ---
  // 30/09/2026: os mapas ganharam uma ATMOSFERA (fundo e malha de coordenadas), e a malha é um
  // <path> a mais dentro do SVG. Contar `path` solto passou a contar a decoração junto, e
  // apontar `path` solto passou a apontar a malha em vez da UF. O alvo correto sempre foi o
  // grupo das UFs; agora está escrito assim.
  const alvo = d.querySelector("#mapaSecas g.ufs path");
  alvo.dispatchEvent(new dom.window.MouseEvent("mouseenter", { clientX: 100, clientY: 100, bubbles: true }));
  teste("tooltip de mapa exibe conteúdo no mouseenter",
    q("mapTooltip").style.display === "block" && q("mapTooltip").innerHTML.length > 10);
  alvo.dispatchEvent(new dom.window.MouseEvent("mouseleave", { bubbles: true }));
  teste("tooltip some no mouseleave", q("mapTooltip").style.display === "none");
  alvo.dispatchEvent(new dom.window.FocusEvent("focus", { bubbles: true }));
  teste("tooltip abre também por teclado (foco)", q("mapTooltip").style.display === "block");

  // --- nenhuma pontuação vazando para esta página ---
  const texto = d.body.textContent;
  // 16/09/2026 (handover da voz editorial, §3): as duas ressalvas saíram do subtítulo e do corpo e passaram
  // a morar UMA vez, na nota "O que esta página não diz". Os testes seguem exigindo que ambas estejam na
  // página — só mudou a redação e o lugar.
  // 30/09/2026 (decisão da editoria): a frase "são sinais reproduzidos dos órgãos, que não entram
  // na nota" saiu da página — a abertura aprovada não recebe acréscimo. A cobrança de TEXTO cai
  // junto, porque portão que não tem como ser cumprido vira ruído. A garantia em si não cai: ela é
  // de método (METODOLOGIA §23, peso zero), e passa a ser conferida onde é FATO e não frase —
  // nenhuma fonte desta página pode aparecer no índice.
  const fontesDaPagina = Object.keys(SINAIS.fontes || {});
  const vazou = fontesDaPagina.filter(f => JSON.stringify(MARE).includes('"' + f + '"'));
  teste("nenhuma fonte de sinal entra no índice (peso zero, §23)", vazou.length === 0);
  if (vazou.length) console.log("      vazou para o índice:", vazou.join(", "));


  // ── padrão único de mapas (03/09/2026): siglas das 27 UFs em todo mapa; legendas canônicas ──
  const mapasSvg = [...d.querySelectorAll('svg[id^="map"], svg[id^="mapa"]')].filter(s => s.querySelector("path.uf-path") || s.querySelector("path"));
  teste(`padrão de mapas: ${mapasSvg.length} mapa(s) com siglas das 27 UFs`, mapasSvg.length > 0 && mapasSvg.every(s => s.querySelectorAll("g.siglas text").length === 27));
  const legendas = [...d.querySelectorAll(".map-legend")].filter(l => l.children.length);
  teste(`padrão de legendas: ${legendas.length} legenda(s) no formato canônico`, legendas.every(l => [...l.children].every(c => c.tagName === "SPAN" && (c.classList.contains("escala") || (c.firstElementChild && c.firstElementChild.tagName === "I" && /background:/.test(c.firstElementChild.getAttribute("style") || ""))) && c.textContent.trim().length > 0)));
  if (falhas.length) {
    console.log(`\n✗ RUNTIME (sinais de risco): ${falhas.length} falha(s). Publicação bloqueada.`);
    process.exit(1);
  }
  console.log("\n✓ RUNTIME (sinais de risco) OK — mapas, gráficos, cartões, proveniência visível e lacunas declaradas.");
}, 900);
