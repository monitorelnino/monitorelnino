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
 *       foram para `dados-abertos/` e para a METODOLOGIA; "Cadastro Nacional" só entra como
 *       indicação da União (§107): inscrição, que é o que cria dever, não tem fonte pública.
 *
 * Uso: node scripts/verificar_runtime_mapas.js
 */
const fs = require("fs");
const path = require("path");
const { renderizar } = require("./_inline_js");

const raiz = path.join(__dirname, "..");
const ler = p => JSON.parse(fs.readFileSync(path.join(raiz, p), "utf-8"));

const ALERTAS = ler("data/alertas/vigentes.json");
const DECRETADOS = ler("data/resposta/municipios_decretados.json");
const REF = ler("data/municipios_ibge_referencia.json");

/* As contagens ESPERADAS saem do dado, e com a mesma regra que a página usa: ponto só existe onde
   há coordenada no arquivo de referência. Escrever o número à mão aqui seria trocar um portão por
   um carimbo. */
const TEM_COORD = new Set(REF.map(m => String(m.codigo_ibge).padStart(7, "0")));
const codsAlerta = Object.keys(ALERTAS.municipios || {});
const comCemaden = codsAlerta.filter(c => (ALERTAS.municipios[c].cemaden || []).length);
const decretados = Object.values(DECRETADOS.municipios || {}).filter(m => m.decreto);
const reconhecidos = decretados.filter(m => m.reconhecido);
const comCoord = l => l.filter(m => TEM_COORD.has(m.ibge || m)).length;
const N = {
  cemaden: comCoord(comCemaden),
  decretados: comCoord(decretados),
  reconhecidos: comCoord(reconhecidos),
};


const { dom, erros, graficos } = renderizar("defesa-civil.html", raiz);

setTimeout(() => {
  const d = dom.window.document, q = id => d.getElementById(id);
  const falhas = [];
  const teste = (nome, cond) => { console.log((cond ? "  ✓ " : "  ✗ ") + nome); if (!cond) falhas.push(nome); };
  const circulos = id => (q(id) ? q(id).querySelectorAll("circle").length : -1);
  const txt = id => ((q(id) || {}).textContent || "").trim();
  const numero = id => Number(txt(id).replace(/\./g, "").replace(/[^\d-]/g, ""));

  teste("zero erros de runtime", erros.length === 0);
  erros.slice(0, 4).forEach(e => console.log("     ", e));

  // ── 17/10/2026 (HANDOVER_DEFESA_CIVIL): um mapa MUNICIPAL, um ponto por município com decreto ─
  /* A página voltou a desenhar ponto por município (figura principal, mapa de pontos na sede), com a
     lista nominal em "Ver em tabela". O que este portão cobra continua o mesmo: o número que o leitor
     lê é o do dado — pontos = municípios com decreto e com sede no arquivo de referência; lista
     declara o total; cada contador do topo é a contagem do consolidado. */
  const SEM_ATUALIZACAO = /Sem atualiza[çc][ãa]o desde/i;
  const declaraVencido = id => SEM_ATUALIZACAO.test(((d.getElementById(id) || {}).textContent || ""));
  const contadorDeAlerta = (id, esperado, rotulo) => {
    if (declaraVencido(id)) { teste(`${rotulo}: coleta vencida, e a página declara a ausência`, true); return; }
    teste(rotulo, numero(id) === esperado);
  };
  const vencido = declaraVencido("topoCemaden") || declaraVencido("topoInmet");
  const mapasCobrados = ["mapEmergencias"];
  teste("o mapa das emergências tem os 27 territórios", (q("mapEmergencias") || d).querySelectorAll("path.uf-path").length === 27);
  teste(`o mapa das emergências tem ${N.decretados} pontos (municípios com decreto e sede)`, circulos("mapEmergencias") === N.decretados);
  const BRANCO = dom.window.MonitorMapas.cor("branco");
  const reconhecidosNoMapa = q("mapEmergencias") ? [...q("mapEmergencias").querySelectorAll("circle")].filter(c => c.getAttribute("stroke") === BRANCO).length : -1;
  teste(`pontos cheios = ${N.reconhecidos} municípios reconhecidos`, reconhecidosNoMapa === N.reconhecidos);
  const contaDaLista = caixa => {
    const el = d.querySelector("#" + caixa + " .busca-mun-conta");
    const m = el ? (el.textContent || "").replace(/\./g, "").match(/(\d+)/) : null;
    return m ? Number(m[1]) : -1;
  };
  teste(`lista das emergências declara ${decretados.length} municípios`, contaDaLista("boxEmergencias") === decretados.length);
  contadorDeAlerta("topoCemaden", (ALERTAS.resumo || {}).municipios_cemaden, "contador do Cemaden = resumo do arquivo de alertas");
  contadorDeAlerta("topoInmet", (ALERTAS.resumo || {}).municipios_inmet, "contador do Inmet = resumo do arquivo de alertas");
  teste("contador de quem decretou = municípios com decreto no consolidado", numero("topoDecretaram") === decretados.length);
  teste("contador de reconhecidos = municípios reconhecidos no consolidado", numero("topoReconhecidos") === reconhecidos.length);
  /* A população vem ARREDONDADA em milhões, por decisão da editoria ("nunca o número inteiro"). */
  const popConsolidado = ler("data/resposta/por_uf.json").nacional.pop_sob_decreto;
  const popNaTela = Number(((txt("topoPopulacao").match(/([\d,]+)/) || [])[1] || "").replace(",", "."));
  teste("contador de população = consolidado arredondado em milhões", Math.abs(popNaTela - popConsolidado / 1e6) <= 0.05);
  teste("nenhum contador ficou em travessão nem vazio",
    ["topoCemaden", "topoInmet", "topoDecretaram", "topoPopulacao", "topoReconhecidos", "topoPendencia"].every(i => txt(i) && txt(i) !== "—"));
  teste("nenhum valor em reais na página (o dinheiro está em Financiamento)", !/R\$/.test(d.getElementById("conteudo").textContent));
  teste("a página não lê o arquivo de recursos", !/recursos_liberados/.test(require("fs").readFileSync(path.join(raiz, "assets/js/defesa-civil.js"), "utf-8")));
  const ponto = d.querySelector("#mapEmergencias circle");
  if (!ponto) { teste("ponto do mapa tem tooltip", false); }
  else {
    ponto.dispatchEvent(new dom.window.MouseEvent("mouseenter", { clientX: 100, clientY: 100, bubbles: true }));
    teste("ponto do mapa tem tooltip, sem valor em reais",
      q("mapTooltip").style.display === "block" && q("mapTooltip").innerHTML.length > 10 && !/R\$/.test(q("mapTooltip").textContent));
  }
  /* A consulta do município usa o módulo comum e responde com os três cartões. */
  const uf = d.getElementById("consultaUF"), mun = d.getElementById("consultaMun");
  const umDecretado = decretados[0];
  if (uf && mun && umDecretado) {
    uf.value = umDecretado.uf; uf.dispatchEvent(new dom.window.Event("change"));
    mun.value = umDecretado.nome; mun.dispatchEvent(new dom.window.Event("input"));
    const card = d.getElementById("consultaCard");
    teste("consulta do município: três cartões e a linha do estado",
      !card.hidden && card.querySelectorAll(".cartao").length === 3 && /municípios decretaram emergência/.test(card.textContent));
  } else teste("consulta do município existe", false);

  // ── busca por município em todo cartão (pedido da editoria, 01/10/2026) ────────────────────
  const campos = [...d.querySelectorAll(".busca-mun input")];
  // Cartão de alerta com a coleta vencida declara a parada e não tem lista para buscar (F28).
  const cartoes = [...d.querySelectorAll("#conteudo .cartao-mapa")]
    .filter(c => !(vencido && SEM_ATUALIZACAO.test(c.textContent)));
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
  const cartaoDec = d.querySelector("#boxEmergencias details.cartao-mapa-dados");
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
    mapasCobrados.every(id => mapasSvg.some(s => s.id === id)) && mapasSvg.every(s => s.querySelectorAll("g.siglas text").length === 27));
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
  /* "Cadastro Nacional" é o do art. 3º-A da Lei 12.340: a INSCRIÇÃO, voluntária, é que gera o dever
     de plano. 16/10/2026 (METODOLOGIA §107): a lista são os 2.095 INDICADOS pela União ao Cadastro
     Nacional (página do MIDR, 28/07/2026); quem se inscreveu não tem fonte pública. A página pode
     nomear o cadastro só como indicação da União; afirmar inscrição ou dever é afirmar o que nenhuma
     fonte pública diz. 17/10/2026 (HANDOVER_DEFESA_CIVIL §6): as três listas federais foram para o
     Monitor de riscos, e a regra vale nas duas páginas. */
  const regraDoCadastro = (pagina, visivel) => {
    const semIndicacao = [...visivel.matchAll(/Cadastro Nacional/gi)]
      .filter(m => !/indicad[oa]s?\b[^.]{0,60}$/i.test(visivel.slice(Math.max(0, m.index - 70), m.index)));
    teste(`${pagina}: "Cadastro Nacional" só aparece como indicação da União`, semIndicacao.length === 0);
    teste(`${pagina}: não afirma inscrição no Cadastro Nacional nem dever de plano`,
      !/(inscrit[oa]s?|cadastrad[oa]s?)\b[^.]{0,40}Cadastro Nacional|t[êe]m o dever\b/i.test(visivel));
  };
  regraDoCadastro("Defesa civil", d.getElementById("conteudo").textContent);

  const mr = renderizar("monitor-de-riscos.html", raiz);
  setTimeout(() => {
    const qm = id => mr.dom.window.document.getElementById(id);
    teste("Monitor de riscos: zero erros de runtime", mr.erros.length === 0);
    const LISTAS = ["mapListaIndicados", "mapListaSemiarido", "mapListaFogo"];
    teste("Monitor de riscos: as três listas federais têm os 27 territórios, sem ponto por município",
      LISTAS.every(id => qm(id) && qm(id).querySelectorAll("path.uf-path").length === 27 && !qm(id).querySelector("circle")));
    const visivel = qm("conteudo").textContent;
    regraDoCadastro("Monitor de riscos", visivel);
    teste("Monitor de riscos: a lista de indicados é nomeada pelas fontes certas (MIDR e Casa Civil)",
      /indicados pela União/i.test(visivel) && /MIDR e Casa Civil/.test(visivel));
    if (falhas.length) { console.error(`\n✗ ${falhas.length} verificação(ões) falharam.`); process.exit(1); }
    console.log("\n✓ RUNTIME (Defesa civil e listas federais do Monitor de riscos) OK — todas as verificações passaram.");
    process.exit(0);
  }, 900);
}, 900);
