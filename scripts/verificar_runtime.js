#!/usr/bin/env node
/* Verificador de runtime do Monitor El Niño Brasil.
 * Executa index.html num navegador simulado (jsdom + d3 reais, Chart simulado),
 * com fetch local para data/*.json, e valida a renderização e o fluxo do cidadão.
 * Requer: npm i jsdom d3   ·   Uso: node scripts/verificar_runtime.js
 */
const N_PONTOS = require("../data/pontos_mapa.json").length;
const INDICE = require("../data/indice.json");
const INDICE_META = require("../data/meta.json");
const { JSDOM, VirtualConsole } = require("jsdom"); const { inlinePageJs } = require("./_inline_js");
const fs = require("fs");
const path = require("path");

const raiz = path.join(__dirname, "..");
const html = inlinePageJs(fs.readFileSync(path.join(raiz, "index.html"), "utf-8"), raiz);
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
    class Chart { constructor(ctx, cfg) { w.__charts = (w.__charts || []).concat([{ ctx, cfg }]); } } Chart.defaults = { font: {}, color: "", plugins: { legend: { labels: {} }, tooltip: {} }, elements: {} };
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
  // v3.1 §4: a tabela de auditoria vive em pesquisadores.html (verificada lá pelo runtime de resposta/pesquisadores)
  teste("seletor de UF populado", q("ufSelect") && q("ufSelect").children.length === 28);
  // 14/09/2026: "Como ler o MARÉ" é ficha popup no mesmo <dialog> do estado, aberta pelo link abaixo da barra do índice
  try {
    teste("home sem atalhos .hero-links; link 'como ler o MARÉ' abaixo da barra", d.querySelectorAll(".hero-links").length === 0 && !!d.querySelector(".gauge-zone #linkComoLer") && q("linkComoLer").textContent === "como ler o MARÉ");
    q("linkComoLer").dispatchEvent(new dom.window.MouseEvent("click", { bubbles: true, cancelable: true }));
    teste("clique abre a ficha 'Como ler o MARÉ' no dialog", q("detail").open && /Como ler o MARÉ/.test(q("detailConteudo").textContent) && /O que o índice não conta/.test(q("detailConteudo").textContent));
    q("detailFechar").dispatchEvent(new dom.window.Event("click", { bubbles: true }));
    teste("fechar pelo × devolve o estado inicial", !q("detail").open);
    // 14/09 (auditoria §1.6): o calendário volta à home só como "porta" explicativa, nunca como o antigo atalho "o que a lei deixa aberto"
    teste("'o que a lei deixa aberto' saiu da página principal (só as portas 'por que há páginas fora do ar')", ![...d.querySelectorAll("a")].some(a => /o que a lei deixa aberto/i.test(a.textContent)));
  } catch (e) { teste("ficha 'Como ler o MARÉ' (" + e.message + ")", false); }

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
  // 16/09/2026 (handover §2.1): recalcular_mare.py reescreve gaugeNum e data-alvo desde 03/09 — este
  // teste garante que o aria-label (paridade de acessibilidade) nunca fica para trás dos dois.
  teste("medidor do herói: aria-label com o mesmo número de data-alvo (paridade de acessibilidade)", (() => {
    const alvo = q("gaugeFill").dataset.alvo; const alvoFmt = parseFloat(alvo).toFixed(1).replace(".", ",");
    const trilho = q("gaugeFill").closest(".gauge-track");
    const rotulo = trilho && trilho.getAttribute("aria-label");
    return !!rotulo && rotulo.includes(`em ${alvoFmt} de 100`);
  })());
  teste("linguagem: município não verificado diz 'Ainda não verificamos'", cardNV.includes("Ainda não verificamos"));
    teste("linguagem: município não verificado NÃO diz 'Não localizamos'", !/[Nn]ão localizamos/.test(cardNV));
  } catch (e) { teste("portão de linguagem v2.2.4", false); }

  try {
    const tile = d.querySelector('#regions .tile[data-uf="SC"]');
    tile.click();
    teste("detalhe do estado abre ao clique", q("detail").open && q("detail").innerHTML.includes("Santa Catarina"));
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
  const fonte = inlinePageJs(fs.readFileSync(path.join(raiz, "index.html"), "utf-8"), raiz);
  const ger = fonte.slice(fonte.indexOf("function gerarRelatorioCidadao("), fonte.indexOf("function gerarPDF(){"));
  const secoes = ["Em emergência, ligue", "Risco projetado para ", "O que já existe", "O que ainda falta", "Como se proteger", "Links úteis"];   // 'Pedido de informação pronto' retirada em 13/09/2026 (pedido de Patricia)
  const posicoes = secoes.map(s => ger.indexOf("secao('" + s));
  teste("PDF do cidadão: as 6 seções existem, na ordem", posicoes.every((p, k) => p > 0 && (k === 0 || p > posicoes[k-1])));
  // 15/09/2026 (§1.9): Proteja-se num JSDOM próprio — seletor de estado vindo do dado; guias em acordeões; a UF escolhida abre o guia do seu risco
  try {
    const htmlP = inlinePageJs(fs.readFileSync(path.join(raiz, "proteja-se.html"), "utf-8"), raiz);
    const domP = new JSDOM(htmlP, { url: "https://localhost/", runScripts: "dangerously", virtualConsole: vc, beforeParse(w) {
      w.d3 = require("d3"); w.eval(fs.readFileSync(path.join(raiz, "assets", "mapas.js"), "utf-8")); class Chart { constructor() {} } Chart.defaults = { font: {}, color: "" }; w.Chart = Chart;
      w.fetch = (rel) => { try { const txt = fs.readFileSync(path.join(raiz, rel), "utf-8"); return Promise.resolve({ ok: true, json: () => Promise.resolve(JSON.parse(txt)) }); } catch (e) { return Promise.resolve({ ok: false }); } }; } });
    setTimeout(() => {
      const dP = domP.window.document, qP = id => dP.getElementById(id);
      const selP = qP("selUFProteja"); teste("proteja-se: seletor com 27 estados (do dado)", !!selP && selP.options.length === 28);
      teste("proteja-se: guias em acordeões fechados por padrão", ["acc-guia-chuvas","acc-guia-fogo","acc-guia-seca"].every(id => qP(id) && !qP(id).open));
      const S = JSON.parse(fs.readFileSync(path.join(raiz, "data", "sinais_risco.json"), "utf8"));
      const ufChuva = Object.keys(S.uf).find(u => (S.uf[u].risco_projetado || {}).tipo === "chuvas");
      if (ufChuva && selP) { selP.value = ufChuva; selP.dispatchEvent(new domP.window.Event("change", { bubbles: true }));
        teste("proteja-se: escolher um estado de chuvas abre o guia de chuvas e mostra a classificação", qP("acc-guia-chuvas").open && !qP("acc-guia-fogo").open && !qP("riscoDoEstado").hidden && /Chuva/i.test(qP("riscoDoEstado").textContent)); }
      // 15/09/2026: "Defesa Civil do seu estado" — 27 cartões do dado (contatos_uf.json), cada um com telefone tocável; a UF escolhida no seletor de risco preenche o cartão em destaque
      const C = JSON.parse(fs.readFileSync(path.join(raiz, "data", "contatos_uf.json"), "utf8"));
      teste("proteja-se: 27 cartões de contato, todos com telefone (tel:) e órgão", qP("contatoGrade").querySelectorAll(".contato").length === 27 && [...qP("contatoGrade").querySelectorAll(".contato")].every(c => c.querySelector('a[href^="tel:"]') && c.querySelector(".contato-orgao").textContent.length > 10));
      teste("proteja-se: telefone do cartão bate com o dado (primeiro telefone de cada UF)", Object.keys(C.uf).every(uf => { const c = dP.getElementById("contato-" + uf); return c && c.textContent.includes(C.uf[uf].telefones[0]); }));
      if (ufChuva) teste("proteja-se: o estado escolhido aparece em destaque em 'Defesa Civil do seu estado'", !qP("contatoDestaque").hidden && qP("contatoDestaque").textContent.includes(C.uf[ufChuva].nome));
      teste("proteja-se: barra de emergência com 190 · 192 · 193 · 199 e 40199, tocáveis", ["190","192","193","199","40199"].every(n => [...dP.querySelectorAll("#emergNums a")].some(a => a.textContent.includes(n))));
      fim();
    }, 400);
  } catch (e) { teste("proteja-se: seletor/acordeões (" + e.message + ")", false); fim(); }
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
  const esperados = prazos.filter(m => m.vencimento && m.data_base && m.titulo_curto && Math.round((_d(m.vencimento) - _hoje) / 86400000) >= -60).length;   // 05/09/2026: barra exige data_base
  // 15/09/2026: os relógios saíram; os prazos em curso entram no Calendário em colunas, junto dos marcos do ciclo
  const marcosCiclo = JSON.parse(fs.readFileSync(path.join(raiz, "data", "marcos_ciclo.json"), "utf-8")).marcos.filter(m => _d(m.ate || m.data) >= _hoje).length;
  const linhasCal = [...q("marcosCiclo").querySelectorAll(".cal-linha:not(.cal-cabecalho)")];
  teste(`calendário: ${esperados} prazo(s) + ${marcosCiclo} marco(s) do ciclo em linhas data · marco · fonte`, linhasCal.length === esperados + marcosCiclo && linhasCal.every(l => l.querySelectorAll(".cal-data, .cal-marco, .cal-fonte").length === 3));
  teste("calendário: prazos em curso marcados e com contagem de dias ou 'transcorrido'", linhasCal.filter(l => l.classList.contains("prazo")).length === esperados && linhasCal.filter(l => l.classList.contains("prazo")).every(l => /em \d+ dias?|vence hoje|transcorrido/.test(l.textContent)));
  teste("calendário: linhas em ordem de data", (() => { const ds = linhasCal.map(l => { const m = l.querySelector(".cal-data").textContent.match(/(\d{2})\/(\d{2})\/(\d{4})/); return m ? +m[3] * 10000 + +m[2] * 100 + +m[1] : 0; }); return ds.every((v, i) => i === 0 || v >= ds[i - 1]); })());
  // 13/09/2026 (pedido de Patricia): gerador de pedido de LAI pronto (31/08/2026–13/09/2026)
  // retirado da parte visível do site — pedidos de LAI passam a ser feitos por e-mail, de forma
  // privada. Testes correspondentes (cartão da cidade e detalhe do estado) removidos junto.
  teste("PDF do cidadão: estado e município usam o mesmo gerador",
    /function gerarPDFEstado\(uf\)\{ ?gerarRelatorioCidadao\(uf, null\)/.test(fonte) && /gerarRelatorioCidadao\(uf, cid \|\| null\)/.test(fonte));

  // 15/09/2026: a linha do tempo do herói saiu da inicial (pedido da editoria); o tooltip compartilhado é testado nas páginas de mapas.

  // KPIs do topo: sempre calculados a partir dos dados carregados (nunca texto fixo) —
  // guarda-corpo contra o card ficar desatualizado silenciosamente (achado de 31/08/2026).
  const nLAC = Object.values(INDICE).filter(v => v.status_estadual === "LAC").length;
  // 14/09/2026 (auditoria §2.1–§2.4, §2.7): título-fato, interpretações com números do dado, três números, "O que vem"
  // 15/09/2026 (pedido da editoria): sem h2 no herói, sem botão "Consultar seu município"; o subtítulo do cabeçalho traz o escopo e o corte
  // 16/09/2026 (handover da voz editorial, §2.1/D2): o subtítulo foi reescrito — a identidade
  // ("verificação independente, em fontes oficiais") aparece uma única vez, aqui, e a frase segue
  // trazendo os 27 estados, o total de municípios e o corte.
  // 16/09/2026 (handover de identidade, §4.2): a abertura virou dois parágrafos .site-sub (o texto
  // "27 estados e os municípios" ficou no segundo); "Dados até" saiu do site-sub e foi para o .meta,
  // ao lado de "Última verificação". O teste passa a olhar o masthead inteiro, não só o primeiro nó.
  teste("home: herói sem h2 e sem botão de consulta; abertura com municípios e corte", (() => {
    const mast = d.querySelector(".mast-body"); const txt = mast ? mast.textContent : "";
    return !d.querySelector(".hero h2") && !d.querySelector('.hero a[href="#minhacidade"]')
      && /27 estados e (os|dos) [\d.]+ municípios/.test(txt) && /Dados até \d{2}\/\d{2}\/\d{4}\./.test(txt);
  })());
  // 15/09/2026: a linha de interpretação do medidor (contagens por categoria) saiu da inicial (pedido da editoria).
  // 16/09/2026 (handover de identidade, §4.4): "Primeiro decreto do ciclo: X. N aceitos... M ainda não"
  // virou "desde X. N reconhecidos pelo governo federal." — mesma informação, frase mais curta.
  teste("contador: interpretação com municípios, milhões, data e reconhecidos", /municípios, [\d,]+ milhões de pessoas, desde \d{2}\/\d{2}\/\d{4}.*reconhecidos pelo governo federal/.test(q("interpResposta").textContent));
  teste("home sem os três cartões, sem a nota do período eleitoral e sem o bloco 'escondeu' (15/09/2026)", !q("tres") && !q("notaDefeso") && !q("blocoPosDefeso") && !q("n1Anunciado"));
  teste("ordem da home: medidores → sua cidade → estados → calendário → cruzamento risco × estágio → indique um documento", (() => { const ids = [...d.querySelectorAll("main > .panel, main > .mare-duas, main > .hero")].map(e => e.id); const pos = k => ids.indexOf(k); return pos("hero") < pos("cidade") && pos("cidade") < pos("prazos") && pos("prazos") < pos("cruzamento") && pos("cruzamento") < pos("formulario") && pos("formulario") === ids.length - 1; })());
  teste("calendário nunca vazio (marcos do ciclo)", q("marcosCiclo").querySelectorAll(".cal-linha:not(.cal-cabecalho)").length >= 1 && !/Nenhum prazo em curso até o corte/.test(d.body.textContent));
  teste("porta para o calendário eleitoral segue na inicial (ficha Como ler o MARÉ)", d.querySelectorAll('a[href="calendario-eleitoral.html"]').length >= 1);
  teste("cruzamento risco × estágio: figura no fim da inicial, gráfico com as 27 UFs", (() => { const g = (dom.window.__charts || []).find(c => c.ctx && c.ctx.id === "cCruz"); const soma = g ? g.cfg.data.datasets.reduce((s, ds) => s + ds.data.reduce((a, b) => a + b, 0), 0) : -1; return !!q("boxCruz") && q("boxCruz").classList.contains("figura") && soma === Object.keys(INDICE).length; })());
  teste("todas as barras usam a arte única do medidor (nenhum .resp-fill / .tile-fill2 / .barra-resp)", !d.querySelector(".resp-fill, .tile-fill2, .barra-resp") && d.querySelectorAll("#hero .gauge-fill").length === 2 && !!d.querySelector("#hero .gauge-fill--resposta"));
  teste("cartões de estado: cinco campos na face (barras + nível + instrumento + capital)", d.querySelectorAll(".tile .tile-face").length === 27 && [...d.querySelectorAll(".tile .tile-face")].every(f => f.querySelectorAll("span").length === 3));

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

  // 16/09/2026 (handover urgente): os testes acima conferem o DOM depois que assets/js/index.js já
  // rodou — não provam nada sobre o fallback estático (o que um leitor sem JavaScript recebe), porque
  // o JS já teria sobrescrito um "—" essa altura. Este bloco lê o ARQUIVO cru, sem jsdom nem JS, para
  // as três páginas com medidor/corte no cabeçalho.
  {
    const IDS_DADO = {
      "index.html": ["heroVerifFederal", "metaUltimaVerif", "respNum", "respCorte", "respLinha", "interpResposta", "heroCorte", "metaAtualizado", "corteDados", "ctSemana", "ctNovo"],
      "saude.html": ["corteSaude", "gaugeSaudeNum", "gaugeSaudeN", "gaugeSaudeNV", "gaugeSaudeCorte", "rsNum", "rsCorte", "ctSemanaSaude", "ctNovoSaude"],
      "financiamento.html": ["corteFin", "notaFogoCorte"],
    };
    const CORTES_IGUAIS = { "index.html": [["heroCorte", "respCorte", "corteDados"], ["metaUltimaVerif", "metaAtualizado"]] };
    for (const [pagina, ids] of Object.entries(IDS_DADO)) {
      const bruto = fs.readFileSync(path.join(raiz, pagina), "utf-8");
      const valorDe = (id) => {
        // captura da tag com o id até o PRIMEIRO fechamento de p/span/strong/div depois dela — cobre
        // conteúdo com HTML aninhado (ex.: interpResposta começa com <strong>280</strong> ...), não só texto puro
        const m = bruto.match(new RegExp('<[a-z]+[^>]*id="' + id + '"[^>]*>([\\s\\S]*?)</(?:p|span|strong|div)>'));
        return m ? m[1].replace(/<[^>]+>/g, "").replace(/&nbsp;/g, " ").trim() : null;
      };
      for (const id of ids) {
        const valor = valorDe(id);
        if (id === "respLinha") continue;   // JS também deixa vazio de propósito (15/09) — não é lacuna
        teste(`${pagina}: #${id} sem "—"/vazio no HTML estático (sem JS)`, valor !== null && valor !== "" && valor !== "—" && valor.toLowerCase() !== "null");
      }
      for (const grupo of (CORTES_IGUAIS[pagina] || [])) {
        const valores = grupo.map(valorDe);
        teste(`${pagina}: ${grupo.join(" = ")} (mesmo corte, mesmo valor no estático)`, valores.every(v => v === valores[0]));
      }
      // 16/09/2026: a versão ampla ("nenhuma data solta fora de um id") pegava falso positivo demais —
      // comentário HTML, placeholder de formulário, conteúdo já dinâmico sem id no <strong> interno,
      // e datas de calendário fixas e legítimas (29/06, 04/07, 25/10 do período eleitoral). O que o
      // handover queria evitar de verdade é o bug específico já visto: um corte antigo hardcoded no
      // lugar de um campo dinâmico. Trava só esse caso, que é testável sem ambiguidade.
      teste(`${pagina}: não repete o corte hardcoded antigo (26/08/2026) fora de um campo dinâmico`,
        !/Corte dos dados: 26\/08\/2026|corte 26\/08\/2026|em 26\/08\/2026/i.test(bruto));
    }
    const respostaNacional = require("../data/resposta/por_uf.json").nacional;
    const brutoIndex = fs.readFileSync(path.join(raiz, "index.html"), "utf-8");
    const mAlvo = brutoIndex.match(/id="respFill" data-alvo="([\d.]+)"/);
    teste("index.html: #respFill data-alvo ≠ \"0\" a menos que o índice de resposta seja mesmo zero",
      !!mAlvo && (parseFloat(mAlvo[1]) > 0 || (respostaNacional && (respostaNacional.indice || 0) === 0)));
  }

  // 15/09/2026: o fim é chamado pelo bloco assíncrono de Proteja-se (acima), depois que ele terminar
  fim.falhas = falhas;
}, 600);
function fim() {
  const falhas = fim.falhas || [];
  if (falhas.length) { console.error(`\n✗ ${falhas.length} verificação(ões) falharam.`); process.exit(1); }
  console.log("\n✓ RUNTIME OK — todas as verificações passaram.");
  process.exit(0);
}
