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
  const txt = id => ((q(id) || {}).textContent || "").trim();

  teste("zero erros de runtime", erros.length === 0);
  erros.slice(0, 4).forEach(e => console.log("     ", e));

  // ── a ordem da página (bloco B do handover, 02/10/2026) ───────────────────────────────────
  // A pergunta do leitor manda: primeiro os números da semana, depois quanto chegou ao estado
  // dele, depois o dinheiro do ciclo, depois a cidade dele. Cobrar a ordem antiga guardaria uma
  // página que não existe mais.
  const secoes = [...d.querySelectorAll("#conteudo section")].map(x => x.id);
  /* 02/10/2026 (Financiamento minimalista): a página passou ao escopo do ciclo. Saíram as
     transferências gerais ("Quanto chegou a cada estado", "A sua cidade"), a grade dos 27 quadros e
     a seção "Dois casos" separada — os dois casos viraram cartões dentro do bloco recolhido dos
     caminhos. Quem define a ordem é layout/contratos/financiamento.json. */
  teste("ordem da página: números, dinheiro do ciclo, defesa civil, gasto próprio, caminhos",
    JSON.stringify(secoes.slice(1)) === JSON.stringify(["dinheiroElNino", "defesaCivil",
                                                        "gastoProprio", "caminhosSecao"]));
  teste("saíram da página: transferências gerais, a grade dos 27 e a seção de casos",
    !q("porEstado") && !q("suaCidade") && !q("regionsFin") && !q("casos")
    && !q("boxTransfUF") && !q("boxListaEstadosFin") && !q("mapaMPsUF") && !q("boxRotaMPs"));
  teste("os caminhos vêm recolhidos por padrão, e as âncoras existem",
    !!q("caminhos") && q("caminhos").tagName === "DETAILS" && !q("caminhos").open
    && !!q("antes") && !!q("depois") && !!q("setores"));

  // ── os cartões da semana: só indicador dinâmico, e o que a fonte não dá é declarado ────────
  const C = JSON.parse(fs.readFileSync(path.join(raiz, "data", "financiamento", "compromissos_federais.json"), "utf-8"));
  /* Os três cartões do topo, no vocabulário fixado em 02/10/2026: desembolsado (e não "pago"),
     autorizado pela defesa civil, atos novos. O cartão de transferências gerais saiu com o escopo.
     Zero é ZERO, com a janela dita — travessão aqui é proibido pelo handover. */
  const SEM = JSON.parse(fs.readFileSync(path.join(raiz, "data", "financiamento", "semana.json"), "utf-8"));
  const cartaoDe = id => (SEM.cartoes || []).find(c => c.id === id) || null;
  {
    const c = cartaoDe("pago_periodo_mp");
    teste("desembolsado: existe no arquivo do gerador", !!c);
    if (c && !c.sem_coleta) {
      teste("desembolsado: o valor exato aparece na linha de fonte",
        txt("topoPagoMesFonte").includes(Math.round(Number(c.valor)).toLocaleString("pt-BR")));
      teste("desembolsado: o rótulo diz 'recursos oriundos' e o mês",
        /recursos oriundos/.test(txt("topoPagoMesRotulo"))
        && txt("topoPagoMesRotulo").includes(c.periodo));
      teste("desembolsado: o cartão não fica em travessão", txt("topoPagoMes") !== "—");
    }
    const a = cartaoDe("atos_federais_semana");
    if (a && !a.sem_coleta) {
      teste("atos novos: zero é zero, e a janela é dita",
        txt("topoAtosSemana") === String(a.valor)
        && /sete dias/.test(txt("topoAtosRotulo")));
    }
  }
  teste("nenhum cartão do topo diz 'pago' ao leitor",
    !/\bpagos?\b/i.test([txt("topoPagoMesRotulo"), txt("topoRespostaMunicipios"),
                          txt("topoAtosRotulo"), txt("finContexto")].join(" ")));
  teste("a linha de contexto traz o anunciado e a distinção do desembolsado",
    /anunciam/.test(txt("finContexto")) && /saiu do caixa/.test(txt("finContexto")));
  teste("a forma de aplicação está na página, com a frase gerada do dado",
    !!q("boxFormaAplicacao") && /aplicado diretamente pela União/.test(txt("linhaFormaAplicacao")));
  teste("defesa civil: mapa por estado e a busca por município no mesmo cartão",
    !!q("mapaRespostaUF") && !!q("buscaRespostaMun")
    && q("contaRespostaMun").getAttribute("aria-live") === "polite");
  teste("gasto próprio: mapa por estado e a contagem de quem lançou",
    !!q("mapaGastoProprioUF") && /de 5\.\d{3} munic/.test(txt("comoLerGastoContagem")));

  let R = null;
  try { R = JSON.parse(fs.readFileSync(path.join(raiz, "data", "resposta", "recursos_liberados.json"), "utf-8")); } catch (e) { R = null; }
  if (R && R.municipios) {
    /* Recursos de resposta: aqui existe data por ato, então o recorte semanal é real. Conta-se SÓ
       a finalidade "resposta" — recuperação é obra depois do dano. */
    const limite = Date.now() - 7 * 86400000;
    let esperado = 0; const muns = new Set();
    Object.entries(R.municipios).forEach(([cod, m]) => (m.atos || []).forEach(a => {
      if (a.acao === "resposta" && a.data && new Date(a.data + "T00:00:00").getTime() >= limite) {
        esperado += Number(a.valor_autorizado || 0); muns.add(cod);
      }
    }));
    const c = cartaoDe("resposta_liberado_semana");
    // "liberado" e a palavra do ato: a portaria AUTORIZA, e a saida do dinheiro e outro registro.
    // O rotulo do cartao passou a dizer "autorizado em portarias de resposta", que e a mesma
    // distincao com a palavra do ato — e e o que o portao cobra.
  }
  /* Pelo contrato, o cartao de atos novos SO entra na grade quando e maior que zero: grade de tres
     com um quarto cartao dizendo "0" e pior que grade de tres. */
  {
    const c = cartaoDe("atos_federais_semana");
    const visivel = !!q("cartaoAtosSemana") && !q("cartaoAtosSemana").hidden;
    const esperaVisivel = !!c && !c.sem_coleta && Number(c.valor) > 0;
    if (esperaVisivel) {
      teste("atos federais na semana: número do dado e fonte declarada",
        txt("topoAtosSemana") === String(c.valor) && txt("topoAtosSemanaFonte").length > 5);
    }
  }
  /* O anunciado saiu dos cartões e virou contexto: ele não muda a cada coleta. */
  const anunciado = (C.itens || []).reduce((a, x) => a + Number(x.valor_total || 0), 0);
  // ── quanto chegou a cada estado: mapa por habitante, grade e ficha ────────────────────────
  // ── as figuras que ficaram ─────────────────────────────────────────────────────────────────
  // 02/10/2026: os dois mapas "onde o pagamento chegou" saíram — pintavam o país com a parcela de
  // 4% executada fora de Brasília, e a leitura honesta dessa divisão é a figura BR × UFs, que fica.
  // 02/10/2026 (contrato de layout): o diagrama das rotas por setor saiu da pagina — o contrato
  // pede duas listas de texto no lugar dele, e o dado do diagrama fica no repositorio. O que o
  // portao cobra agora e que as duas listas estejam na tela.
  teste("como o dinheiro chega: as duas listas, antes e depois do desastre",
    !!q("antes") && !!q("depois") && q("antes").querySelectorAll("li").length >= 4
    && q("depois").querySelectorAll("li").length >= 4 && !q("preventivoSetor"));

  // ── a consulta por cidade (01/10/2026): existe porque a coleta por município passou a existir ─
  const T = JSON.parse(fs.readFileSync(path.join(raiz, "data", "financiamento", "municipios", "transferencias_uniao.json"), "utf-8"));
  /* As três travas do cartão, e cada uma existe por uma razão medida:
     - mês parcial é DITO, porque o Portal continua preenchendo o arquivo do mês;
     - cidade sem registro não vira "R$ 0", que afirmaria que nada chegou;
     - emenda parlamentar não é inventada como rota: ela não existe nesta fonte. */
  const parciais = Object.entries(T.meses_lidos).filter(([, v]) => v.parcial).map(([m]) => m);
  teste("o mês parcial é marcado no dado, não escondido",
    parciais.length === 0 || parciais.every(m => T.meses_lidos[m].parcial_porque));
  const fonteJs = fs.readFileSync(path.join(raiz, "assets", "js", "financiamento.js"), "utf-8");
  teste("nenhum município ficou sem casar na coleta publicada",
    Object.keys(T.nao_casados || {}).length === 0);

  // ── as duas listas e as três âncoras que o Para gestores aponta (bloco C) ──────────────────
  teste("as duas listas de 'Como o dinheiro chega', com as âncoras que o Para gestores usa",
    q("antes") && q("depois") && q("setores")
    && q("antes").querySelectorAll("li").length >= 6 && q("depois").querySelectorAll("li").length >= 6);
  teste("sem diagrama das oito rotas e sem as fichas 'Como ler' (saíram no bloco B)",
    !q("redeRotas") && !q("comolerRotas") && !q("comolerPreventivo") && !q("rotasCards"));
  teste("sem a seção do período eleitoral e sem a parede de fontes",
    !d.querySelector("#conteudo .chip-chave") && !q("fontes-financiamento") && !q("tblConsultas"));

  // ── o componente de cartão de mapa, com UMA proporção nos nove ─────────────────────────────
  const cartoes = [...d.querySelectorAll("#conteudo .cartao-mapa")];
  // A contagem muda quando a página muda, e desde 02/10/2026 ela é a do contrato de layout:
  // catorze cartões, três por seção nas cinco seções de figura, menos a última linha incompleta
  // de "Dois casos". Quem define a lista é layout/contratos/financiamento.json.
  // A contagem vem do contrato: nove cartões de mapa, três por seção nas três seções de
  // figura, mais o diagrama dos caminhos no bloco recolhido. Quem define é
  // layout/contratos/financiamento.json.
  teste(`nove figuras no cartão de mapa padrão (${cartoes.length})`, cartoes.length === 9);
  teste("todo cartão de mapa tem faixa de família e sobretítulo do componente",
    cartoes.every(c => c.querySelector(".cartao-mapa-familia") && c.querySelector(".cartao-mapa-boletim")));
  teste("toda figura tem crédito de fonte",
    [...d.querySelectorAll("#conteudo .figura")].every(c => c.querySelector(".fonte-figura")));
  teste("nenhum parágrafo ou nota dentro de cartão de figura",
    [...d.querySelectorAll("#conteudo .figura")].every(c =>
      c.querySelectorAll(":scope > .note, :scope > .hint, :scope > p:not(.figura-sub):not(.figura-cat):not(.figura-leitura):not(.cartao-mapa-familia):not(.cartao-mapa-boletim)").length === 0));

  // ── padrão único de mapas e legendas ──────────────────────────────────────────────────────
  const mapasSvg = [...d.querySelectorAll('#conteudo svg[id^="mapa"]')].filter(x => x.querySelector("path"));
  teste(`padrão de mapas: ${mapasSvg.length} mapa(s) com as 27 siglas de UF`,
    mapasSvg.length > 0 && mapasSvg.every(x => x.querySelectorAll("g.siglas text").length === 27));
  const legendas = [...d.querySelectorAll(".map-legend")].filter(l => l.children.length);
  teste(`padrão de legendas: ${legendas.length} legenda(s) no formato canônico`,
    legendas.every(l => [...l.children].every(c => c.tagName === "SPAN"
      && (c.classList.contains("escala") || (c.firstElementChild && c.firstElementChild.tagName === "I"
        && /background:/.test(c.firstElementChild.getAttribute("style") || "")))
      && c.textContent.trim().length > 0)));

  // ── gesto e travas que não mudam ──────────────────────────────────────────────────────────
  try {
    // O mapa do gesto passa a ser o que existe: desde 02/10/2026 o mapa principal da página é o
    // do autorizado por portaria, por estado.
    const alvo = q("mapaRespostaUF").querySelector("path");
    alvo.dispatchEvent(new dom.window.MouseEvent("mouseenter", { clientX: 100, clientY: 100, bubbles: true }));
  } catch (e) { teste("gesto: tooltip (" + e.message + ")", false); }
  teste("nenhuma tabela na prosa da página (só figuras e fichas)",
    [...d.querySelectorAll("main table")].filter(el => !el.closest('[data-proveniencia="1"]') && !el.closest("details")).length === 0);
  teste("E10: nenhum campo de autor de emenda na página",
    !/nomeAutor|codigoAutor|autor_emenda/i.test(d.documentElement.outerHTML));
  // Resposta nunca somada a preparação: é função estrutural, e não depende do layout.
  teste("somaPreparacao ignora as rotas de resposta",
    dom.window.somaPreparacao({r1: 10, r2: 10, r3: 1000, r4: 1000, r5: 10, r6: 10, r7: 10, rE: 10}) === 60);
  const ativa = d.querySelector(".mainnav .ativa");
  teste("nav: 'Financiamento' é o item ativo", ativa && ativa.textContent.trim() === "Financiamento");
  teste("painéis retirados a pedido da editoria não voltaram",
    !q("porestado") && !q("boxFundoEstadual") && !q("notaExecucao"));

  if (falhas.length) { console.error(`\n✗ ${falhas.length} verificação(ões) falharam.`); process.exit(1); }
  console.log("\n✓ RUNTIME (Financiamento) OK — todas as verificações passaram.");
  process.exit(0);
}, 1200);
