#!/usr/bin/env node
/* Verificador de runtime da página Defesa civil (defesa-civil.html).
 *
 * Renderiza a página com jsdom, d3 real, Chart simulado e `fetch` servindo `data/` do disco, e
 * confere o RESULTADO — não o código que o produz. Mesmo padrão de `scripts/verificar_runtime.js`.
 *
 * REESCRITO EM 01/10/2026, com a página. O portão anterior cobria sete mapas que não existem mais
 * (verificação municipal em doze categorias, cobertura e natureza por UF, risco × instrumento) e
 * testava títulos-fato que saíram. Um portão que cobra a página de ontem não protege a de hoje: ele
 * reprovava por ausência de figura removida de propósito, e não dizia nada sobre as que entraram.
 *
 * O QUE ELE EXISTE PARA BARRAR
 * ----------------------------
 *   (a) **Dois números para a mesma pergunta.** Aconteceu nesta página, hoje: o conjunto dos
 *       municípios que decretaram era montado no script da página, casando por NOME, e dava 770,
 *       enquanto o contador do topo, lendo o consolidado `resposta/municipios_decretados.json`,
 *       dizia 734. Os testes abaixo exigem que cada contador do topo seja IGUAL à contagem do mapa
 *       que está logo embaixo dele, e que as duas saiam do mesmo arquivo.
 *   (b) **Mapa vazio em silêncio.** Casar alerta por nome em vez de código IBGE já deixou os
 *       municípios do Cemaden fora do mapa sem nenhuma mensagem de erro. Cada mapa tem a sua
 *       contagem esperada calculada aqui, do dado, nunca escrita à mão.
 *   (c) **A volta do que a editoria mandou sair.** Os blocos de auditoria e os mapas de preparação
 *       foram para `dados-abertos/` e para a METODOLOGIA; "Cadastro Nacional" saiu do site porque é
 *       o nome de outro cadastro, que cria dever que a lista da Casa Civil não cria.
 *
 * Uso: node scripts/verificar_runtime_mapas.js
 */
const fs = require("fs");
const path = require("path");
const { JSDOM, VirtualConsole } = require("jsdom");
const { inlinePageJs } = require("./_inline_js");

const raiz = path.join(__dirname, "..");
const ler = p => JSON.parse(fs.readFileSync(path.join(raiz, p), "utf-8"));

const ALERTAS = ler("data/alertas/vigentes.json");
const DECRETADOS = ler("data/resposta/municipios_decretados.json");
const CADASTRO = ler("data/cadastro_prioritarios_federal.json");
const REF = ler("data/municipios_ibge_referencia.json");

/* As contagens ESPERADAS saem do dado, e com a mesma regra que a página usa: ponto só existe onde
   há coordenada no arquivo de referência. Escrever o número à mão aqui seria trocar um portão por
   um carimbo. */
const TEM_COORD = new Set(REF.map(m => String(m.codigo_ibge).padStart(7, "0")));
const codsAlerta = Object.keys(ALERTAS.municipios || {});
const comCemaden = codsAlerta.filter(c => (ALERTAS.municipios[c].cemaden || []).length);
const decretados = Object.values(DECRETADOS.municipios || {}).filter(m => m.decreto);
const reconhecidos = decretados.filter(m => m.reconhecido);
const cruzados = decretados.filter(m => codsAlerta.indexOf(m.ibge) >= 0);
const comCoord = l => l.filter(m => TEM_COORD.has(m.ibge || m)).length;
const N = {
  cemaden: comCoord(comCemaden),
  decretados: comCoord(decretados),
  reconhecidos: comCoord(reconhecidos),
  cruzados: comCoord(cruzados),
  cadastro: comCoord(Object.keys(CADASTRO.municipios || {})),
};

const erros = [];
const vc = new VirtualConsole();
vc.on("jsdomError", e => erros.push(e.detail && e.detail.stack ? e.detail.stack.split("\n")[0] : e.message));

const html = inlinePageJs(fs.readFileSync(path.join(raiz, "defesa-civil.html"), "utf-8"), raiz);
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
      try {
        const txt = fs.readFileSync(path.join(raiz, rel.split("?")[0]), "utf-8");
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
  const circulos = id => (q(id) ? q(id).querySelectorAll("circle").length : -1);
  const txt = id => ((q(id) || {}).textContent || "").trim();
  const numero = id => Number(txt(id).replace(/\./g, "").replace(/[^\d-]/g, ""));

  teste("zero erros de runtime", erros.length === 0);
  erros.slice(0, 4).forEach(e => console.log("     ", e));

  // ── cada mapa com os 27 territórios, e cada lista com a contagem que o dado tem ───────────
  /* 02/10/2026 (handover "a cadeia do aviso ao recurso"): a página deixou de desenhar PONTO por
     município — ponto satura o país e não responde "e a minha cidade?". Os mapas passaram a ser por
     ESTADO, e a resposta municipal passou para a lista embutida com busca. Os testes acompanham: no
     lugar de contar círculos, eles contam territórios no mapa e conferem a CONTAGEM QUE A LISTA
     DECLARA ao leitor — que é o número que ele lê. */
  const SEM_ATUALIZACAO = /Sem atualiza[çc][ãa]o desde/i;
  const declaraVencido = id => SEM_ATUALIZACAO.test(
    ((d.getElementById(id) || {}).textContent || ""));
  const contadorDeAlerta = (id, esperado, rotulo) => {
    if (declaraVencido(id)) {
      teste(`${rotulo}: coleta vencida, e a página declara a ausência`, true);
      return;
    }
    teste(rotulo, numero(id) === esperado);
  };

  const territorios = id => (q(id) ? q(id).querySelectorAll("path.uf-path").length : -1);
  const MAPAS = ["mapAlertas", "mapCemaden", "mapDecretosUF", "mapRiscoEnchente",
                 "mapRiscoSemiarido", "mapRiscoFogo"];
  /* Com a coleta de alertas vencida, a seção do Cemaden não desenha — é a regra das 24 horas em
     `defesa-civil.js`, e o mapa ausente é a consequência correta dela. Os outros cinco continuam
     cobrados, porque não dependem de alerta. */
  const vencido = declaraVencido("topoCemaden") || declaraVencido("topoInmet");
  /* 09/10/2026 (ajuste 10): abaixo de LIMIAR_CEMADEN municípios o cartão do Cemaden vira texto
     ("{n} municípios em {UFs}" + lista por estado) — sem mapa, por regra do código. */
  const cemadenEmTexto = !!d.querySelector("#boxCemaden .figura-midia--texto");
  if (cemadenEmTexto) teste("Cemaden abaixo do limiar: cartão em texto, com a contagem e a lista por estado",
    /municípios? em |Nenhum município/.test(d.querySelector("#boxCemaden .figura-midia").textContent));
  const mapasCobrados = (vencido ? MAPAS.filter(id => id !== "mapCemaden" && id !== "mapAlertas")
                                 : MAPAS).filter(id => !(cemadenEmTexto && id === "mapCemaden"));
  teste(`os ${mapasCobrados.length} mapas têm os 27 territórios`
        + (vencido ? " (Cemaden e alertas fora: coleta vencida e declarada)" : ""),
    mapasCobrados.every(id => territorios(id) === 27));
  teste("nenhum mapa desta página desenha ponto por município",
    mapasCobrados.every(id => circulos(id) === 0));

  /* A contagem declarada na lista embutida: é o texto que o leitor lê depois de abrir "Ver em
     lista", e tem de ser o número do dado — não o teto de linhas que a tabela monta. */
  const contaDaLista = caixa => {
    const el = d.querySelector("#" + caixa + " .busca-mun-conta");
    if (!el) return -1;
    const m = (el.textContent || "").replace(/\./g, "").match(/(\d+)/);
    return m ? Number(m[1]) : -1;
  };
  teste(`lista dos decretos declara ${N.decretados} municípios`,
    contaDaLista("boxDecretosUF") === N.decretados);
  if (vencido) {
    teste("lista do Cemaden: coleta vencida, e a página declara a ausência", true);
  } else {
    teste(`lista do Cemaden declara ${N.cemaden} municípios`,
      contaDaLista("boxCemaden") === N.cemaden);
  }
  teste(`lista do cadastro da Casa Civil declara ${N.cadastro} municípios`,
    contaDaLista("boxRiscoEnchente") === N.cadastro);

  /* 04/10/2026 — A COLETA VENCIDA NÃO BLOQUEIA A PUBLICAÇÃO.
   *
   * `assets/js/defesa-civil.js` tem a regra das 24 horas (LIMITE_ALERTA_HORAS): alerta com mais de
   * um dia não é declarado como vigente; no lugar do número, a página escreve "Sem atualização
   * desde <carimbo>". A regra é certa e fica.
   *
   * O que estava errado era este portão cobrar o NÚMERO em todo caso: às 09:57 UTC de 04/10 o
   * arquivo de alertas completou 24h02 e a publicação morreu aqui — com a página fazendo
   * exatamente o que devia. Dado velho é assunto do coletor e do portão de frescor, não motivo
   * para o site inteiro não publicar.
   *
   * Então: quando a página declara a ausência de atualização, o portão exige ESSA declaração; o
   * número só é cobrado quando a coleta está dentro da janela. A trava que importa continua
   * inteira — o que nunca se aceita é número de alerta vencido apresentado como vigente.
   */
  // ── um número, uma fonte: o topo é igual ao mapa de baixo ──────────────────────────────────
  contadorDeAlerta("topoCemaden", (ALERTAS.resumo || {}).municipios_cemaden,
    "contador do Cemaden = resumo do arquivo de alertas");
  contadorDeAlerta("topoInmet", (ALERTAS.resumo || {}).municipios_inmet,
    "contador do Inmet = resumo do arquivo de alertas");
  teste("contador do cruzamento = decreto no ciclo e alerta agora",
    numero("topoCruzamento") === cruzados.length);
  teste("contador de quem decretou = municípios com decreto no consolidado",
    numero("topoDecretaram") === decretados.length);
  teste("contador de reconhecidos = municípios reconhecidos no consolidado",
    numero("topoReconhecidos") === reconhecidos.length);
  /* A população vem ARREDONDADA em milhões, por decisão da editoria ("nunca o número inteiro"):
     o teste confere o arredondamento, e não a igualdade ao habitante. */
  const popConsolidado = ler("data/resposta/por_uf.json").nacional.pop_sob_decreto;
  const popNaTela = Number((txt("topoPopulacao").match(/([\d,]+)/) || [])[1].replace(",", "."));
  teste("contador de população = consolidado arredondado em milhões",
    Math.abs(popNaTela - popConsolidado / 1e6) <= 0.05);
  teste("nenhum contador do topo ficou em travessão",
    ["topoCemaden", "topoInmet", "topoCruzamento", "topoDecretaram", "topoPopulacao", "topoReconhecidos"]
      .every(i => txt(i) && txt(i) !== "—"));

  // ── tooltip ────────────────────────────────────────────────────────────────────────────────
  // `path.uf-path`, não `path`: com a atmosfera, o PRIMEIRO path do SVG é a malha de 5° que ela
  // insere como primeiro filho, e essa malha não tem — nem deve ter — ouvinte de mouse. Quem
  // carrega o tooltip é o território.
  const hover = d.querySelector("#mapDecretosUF path.uf-path");
  if (!hover) { teste("mapa de decretos tem o território das UFs para o tooltip", false); }
  else {
    hover.dispatchEvent(new dom.window.MouseEvent("mouseenter", { clientX: 100, clientY: 100, bubbles: true }));
    teste("tooltip de mapa exibe conteúdo",
      q("mapTooltip").style.display === "block" && q("mapTooltip").innerHTML.length > 10);
  }

  // ── busca por município em todo cartão (pedido da editoria, 01/10/2026) ────────────────────
  const campos = [...d.querySelectorAll(".busca-mun input")];
  const cartoes = [...d.querySelectorAll("#conteudo .cartao-mapa")];
  teste(`busca por município em todos os ${cartoes.length} cartões`, campos.length === cartoes.length);
  teste("todo campo de busca tem rótulo associado e visível",
    campos.every(i => {
      const l = d.querySelector('label[for="' + i.id + '"]');
      return l && l.textContent.trim().length > 0 && !l.classList.contains("sr-only");
    }));
  teste("toda contagem de resultado é anunciada a leitor de tela",
    [...d.querySelectorAll(".busca-mun-conta")].every(p => p.getAttribute("aria-live") === "polite")
    && d.querySelectorAll(".busca-mun-conta").length === campos.length);
  /* Filtrar tem de FILTRAR: um campo que não liga em nada é pior que campo nenhum, porque promete
     resposta e devolve a lista inteira. */
  /* 02/10/2026: o cartão dos decretos passou a ser `#boxDecretosUF` — o mapa por estado com a lista
     municipal embutida —, no lugar dos três mapas de pontos. E o teste passa a FALHAR em vez de
     estourar quando o cartão não existe: `querySelector` devolve `null`, e chamar método em `null`
     derrubava o portão inteiro com TypeError, escondendo todas as verificações seguintes. */
  const cartaoDec = d.querySelector("#boxDecretosUF details.cartao-mapa-dados");
  if (!cartaoDec) {
    teste("digitar no campo filtra a lista", false);
  } else {
    const antes = cartaoDec.querySelectorAll("tbody tr").length;
    const campoDec = cartaoDec.querySelector("input");
    campoDec.value = "zzzzzz-nao-existe";
    campoDec.dispatchEvent(new dom.window.Event("input"));
    const depois = cartaoDec.querySelectorAll("tbody tr").length;
    teste("digitar no campo filtra a lista", antes > 1 && depois === 1
      && /nenhum município/.test(cartaoDec.querySelector("tbody").textContent));
  }

  // ── harmonização dos mapas (padrão único) ─────────────────────────────────────────────────
  const mapasSvg = [...d.querySelectorAll('#conteudo svg[id^="map"]')].filter(s => s.querySelector("path"));
  teste(`padrão de mapas: ${mapasSvg.length} mapa(s) com as 27 siglas de UF`,
    mapasSvg.length === (cemadenEmTexto ? 5 : 6) && mapasSvg.every(s => s.querySelectorAll("g.siglas text").length === 27));
  const legendas = [...d.querySelectorAll(".map-legend")].filter(l => l.children.length);
  teste(`padrão de legendas: ${legendas.length} legenda(s) no formato <span><i></i>rótulo</span>`,
    legendas.every(l => [...l.children].every(c => c.tagName === "SPAN"
      && (c.classList.contains("escala") || (c.firstElementChild && c.firstElementChild.tagName === "I"))
      && /background:/.test((c.firstElementChild || {}).getAttribute && c.firstElementChild.getAttribute("style") || "")
      && c.textContent.trim().length > 0)));
  teste("nenhuma legenda sobrescreve o alinhamento padrão",
    [...d.querySelectorAll(".map-legend")].every(el => !/justify-content/.test(el.getAttribute("style") || "")));
  teste("nenhum ícone de legenda usa borda tracejada (use hachura)",
    [...d.querySelectorAll(".map-legend i")].every(el => !/dashed/.test(el.getAttribute("style") || "")));
  teste("nenhum item de legenda passa de 40 caracteres",
    [...d.querySelectorAll(".map-legend > span:not(.escala)")].every(s => s.textContent.length <= 40));

  // ── decisão editorial de 04/09/2026: figura só com título, legenda e crédito ───────────────
  teste("nenhum parágrafo ou nota dentro de cartão de mapa",
    [...d.querySelectorAll("#conteudo .figura")].every(c =>
      ![...c.querySelectorAll(".note, .hint, p")].some(e => !e.closest("details")
        && !e.classList.contains("figura-titulo") && !e.classList.contains("figura-sub")
        && !e.classList.contains("figura-leitura") && !e.classList.contains("cartao-mapa-familia")
        && !e.classList.contains("cartao-mapa-boletim"))));
  teste("toda figura tem crédito de fonte",
    d.querySelectorAll("#conteudo .figura").length === d.querySelectorAll("#conteudo .fonte-figura").length);

  // ── o que a editoria mandou sair não volta ─────────────────────────────────────────────────
  const foiEmbora = ["log", "fontes", "painel-amostral", "boxVerificacao", "boxCoberturaNatureza",
                     "mapPoints", "mapNiveis", "mapCobertura", "mapNatureza", "tblBody"];
  const voltou = foiEmbora.filter(id => q(id));
  teste("material de auditoria e mapas de preparação continuam fora da página (01/10/2026)",
    voltou.length === 0);
  if (voltou.length) console.log("      voltaram:", voltou.join(", "));
  /* "Cadastro Nacional" é o nome do cadastro do art. 3º-A da Lei 12.340 — voluntário, com
     deslizamento, e que GERA O DEVER de plano de contingência. A lista desta página é a da Casa
     Civil, que não cria esse dever. Usar um nome pelo outro afirma obrigação inexistente. */
  const visivel = d.getElementById("conteudo").textContent;
  teste('o nome "Cadastro Nacional" não aparece na página (é outro cadastro)',
    !/Cadastro Nacional/i.test(visivel));
  teste("o cadastro é nomeado pela fonte certa (Casa Civil)",
    /suscet[íi]veis a enxurradas e inunda[çc][õo]es/i.test(visivel) && /Casa Civil/i.test(visivel));

  if (falhas.length) { console.error(`\n✗ ${falhas.length} verificação(ões) falharam.`); process.exit(1); }
  console.log("\n✓ RUNTIME (Defesa civil) OK — todas as verificações passaram.");
  process.exit(0);
}, 900);
