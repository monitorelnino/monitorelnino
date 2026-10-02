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
  teste("ordem da página: semana, estado, ciclo, cidade, dinheiro próprio, caminho, casos",
    JSON.stringify(secoes.slice(1)) === JSON.stringify(["porEstado", "dinheiroElNino", "suaCidade",
                                                        "dinheiroProprio", "caminho", "casos"]));
  teste("saíram da página: os dois mapas da parcela de 4%, o diagrama das rotas e a mediana",
    !q("mapaMPsUF") && !q("mapaMP1384UF") && !q("boxRotaMPs") && !q("topoMediana"));

  // ── os cartões da semana: só indicador dinâmico, e o que a fonte não dá é declarado ────────
  const C = JSON.parse(fs.readFileSync(path.join(raiz, "data", "financiamento", "compromissos_federais.json"), "utf-8"));
  /* A trava central deste bloco: "pago na semana" e "transferido na semana" NÃO existem na fonte —
     as medidas federais publicam agregado sem data de pagamento e o Portal entrega o mês. Eles têm
     de dizer isso, com o motivo, e nunca mostrar R$ 0 nem um número inventado. A página Imprensa
     declara a mesma falta: um número aqui e a falta lá seriam duas contas para a mesma coisa. */
  for (const [valor, fonte] of [["topoPagoSemana", "topoPagoSemanaFonte"],
                                ["topoTransfSemana", "topoTransfSemanaFonte"]]) {
    teste(`${valor}: sem dado nesta edição, com o motivo medido`,
      txt(valor) === "sem dado nesta edição" && /sem data de pagamento|por mês/.test(txt(fonte)));
  }
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
    const mostrado = Number(txt("topoRespostaSemana").replace(/[^\d]/g, "")) || 0;
    teste("recursos de resposta na semana: o valor é o do dado, só da finalidade resposta",
      Math.abs(mostrado - Math.round(esperado)) <= 1);
    teste("recursos de resposta: o cartão diz quantos municípios receberam",
      new RegExp(`\\b${muns.size}\\b`).test(txt("topoRespostaMunicipios")) || muns.size === 0);
    teste("recursos de resposta: o cartão diz 'liberado', e nunca 'pago'",
      /liberado/.test(txt("topoRespostaFonte")) && !/\bpago\b/.test(txt("topoRespostaFonte")));
  }
  teste("atos federais na semana: número do dado e fonte declarada",
    /^\d+$/.test(txt("topoAtosSemana")) && txt("topoAtosSemanaFonte").length > 5);
  /* O anunciado saiu dos cartões e virou contexto: ele não muda a cada coleta. */
  const anunciado = (C.itens || []).reduce((a, x) => a + Number(x.valor_total || 0), 0);
  teste("o valor anunciado virou linha de contexto, fora dos cartões",
    !q("topoAnunciado") && (anunciado === 0 || /anunciados para o ciclo/.test(txt("finContexto"))));

  // ── quanto chegou a cada estado: mapa por habitante, grade e ficha ────────────────────────
  teste("mapa por estado: 27 unidades desenhadas",
    q("mapaTransfUF").querySelectorAll("path").length === 27);
  teste("mapa por estado: a legenda declara quem não teve mês lido",
    /sem mês lido/.test(txt("legTransfUF")));
  teste("mapa por estado: a linha do cartão diz quantos meses foram lidos",
    new RegExp(`${Object.keys(JSON.parse(fs.readFileSync(path.join(raiz, "data", "financiamento", "municipios", "transferencias_uniao.json"), "utf-8")).meses_lidos || {}).length} mês`).test(txt("linhaTransfUF")));
  teste("grade por estado: um cartão por UF com número, e ficha ao clicar", (() => {
    const tiles = [...d.querySelectorAll("#regionsFin .tile")];
    if (!tiles.length) return false;
    tiles[0].click();
    return tiles.length >= 26 && /por habitante/.test(txt("detailFinConteudo"));
  })());
  teste("a ficha do estado distingue transferido de gasto",
    /Transferido não é gasto/.test(txt("detailFinConteudo")));

  // ── as figuras que ficaram ─────────────────────────────────────────────────────────────────
  teste("compromissos: gráfico anunciado × empenhado × pago com legenda e crédito",
    q("legCompromissos").children.length === 4 && graficos.some(g => g.ctx && g.ctx.id === "cCompromissos")
    && /Fonte:/.test(q("boxCompromissosGrafico").textContent));
  // 02/10/2026: os dois mapas "onde o pagamento chegou" saíram — pintavam o país com a parcela de
  // 4% executada fora de Brasília, e a leitura honesta dessa divisão é a figura BR × UFs, que fica.
  teste("a divisão entre unidades nacionais e estados está na página, com número do dado",
    /%/.test(txt("mpsBrPct")) && q("boxMpsBrUf") !== null);
  teste("RS: gráfico com os números do dado na legenda",
    graficos.some(g => g.ctx && g.ctx.id === "cRS") && /138 municípios/.test(txt("legRS")));
  const PS = JSON.parse(fs.readFileSync(path.join(raiz, "data", "financiamento", "preventivo_setores.json"), "utf8"));
  const nRotas = PS.setores.reduce((a, s) => a + s.rotas.length, 0);
  teste("preventivo por setor: um nó por rota mais o nó de ausência",
    q("preventivoSetor").querySelectorAll("g.nos g[role=img]").length === nRotas + 1);
  teste("preventivo por setor: nó de ausência da seca sem aresta",
    q("preventivoSetor").querySelectorAll(".aresta.d0").length === 0);

  // ── a consulta por cidade (01/10/2026): existe porque a coleta por município passou a existir ─
  const T = JSON.parse(fs.readFileSync(path.join(raiz, "data", "financiamento", "municipios", "transferencias_uniao.json"), "utf-8"));
  teste("a consulta por cidade está na página, com rótulo e resultado anunciado",
    q("cidadeUF") && q("cidadeNome") && q("cidadeResultado")
    && d.querySelector('label[for="cidadeUF"]') && d.querySelector('label[for="cidadeNome"]')
    && q("cidadeConta").getAttribute("aria-live") === "polite");
  teste("a contagem traz os municípios com registro e os meses lidos, do dado",
    txt("cidadeConta").includes(Object.keys(T.municipios).length.toLocaleString("pt-BR"))
    && txt("cidadeConta").includes(String(Object.keys(T.meses_lidos).length)));
  /* As três travas do cartão, e cada uma existe por uma razão medida:
     - mês parcial é DITO, porque o Portal continua preenchendo o arquivo do mês;
     - cidade sem registro não vira "R$ 0", que afirmaria que nada chegou;
     - emenda parlamentar não é inventada como rota: ela não existe nesta fonte. */
  const parciais = Object.entries(T.meses_lidos).filter(([, v]) => v.parcial).map(([m]) => m);
  teste("o mês parcial é marcado no dado, não escondido",
    parciais.length === 0 || parciais.every(m => T.meses_lidos[m].parcial_porque));
  const fonteJs = fs.readFileSync(path.join(raiz, "assets", "js", "financiamento.js"), "utf-8");
  teste("cidade sem registro não vira R$ 0",
    /nenhuma transferência da União registrada/.test(fonteJs));
  teste("emenda parlamentar não é inventada como caminho",
    !/emenda/i.test(JSON.stringify(T.rotas)) && /não é identificável nesta fonte/.test(fonteJs));
  teste("as rotas do arquivo são as cinco declaradas",
    JSON.stringify(T.rotas) === JSON.stringify(["constitucional", "saude", "assistencia_social", "defesa_civil", "outras"]));
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
  // A contagem muda quando a página muda: três cartões de mapa saíram (os dois da parcela de
  // 4% e o diagrama das rotas) e um entrou (transferido por habitante).
  teste(`sete figuras no cartão de mapa padrão (${cartoes.length})`, cartoes.length === 7);
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
    // O mapa do gesto passa a ser o que existe: transferido por habitante, que é o mapa
    // principal da página desde 02/10/2026.
    const alvo = q("mapaTransfUF").querySelector("path");
    alvo.dispatchEvent(new dom.window.MouseEvent("mouseenter", { clientX: 100, clientY: 100, bubbles: true }));
    teste("gesto: tooltip", q("mapTooltip").style.display === "block" && q("mapTooltip").innerHTML.length > 5);
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
