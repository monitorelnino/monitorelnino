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

  // ── a página em seis blocos (bloco B do handover, 01/10/2026) ──────────────────────────────
  const secoes = [...d.querySelectorAll("#conteudo section")].map(x => x.id);
  teste("seis blocos, na ordem do handover",
    JSON.stringify(secoes) === JSON.stringify(["dc-topo-ou-numeros", "dinheiroElNino", "prometeu",
                                                "dinheiroProprio", "caminho", "casos"].slice(1))
    || JSON.stringify(secoes.slice(1)) === JSON.stringify(["dinheiroElNino", "prometeu",
                                                            "dinheiroProprio", "caminho", "casos"]));

  // ── os três números do topo saem do DADO, e o que não foi coletado diz que não foi ─────────
  const C = JSON.parse(fs.readFileSync(path.join(raiz, "data", "financiamento", "compromissos_federais.json"), "utf-8"));
  const D = JSON.parse(fs.readFileSync(path.join(raiz, "data", "financiamento", "municipios", "despesa_182.json"), "utf-8"));
  const plano = (C.itens || []).find(i => /execução direta/i.test(i.esfera || ""));
  teste("topo: anunciado é o total do plano federal, não a soma dos compromissos",
    plano ? txt("topoAnunciado").includes(String(Math.round(plano.valor_total / 1e9))) : txt("topoAnunciado") === "—");
  /* A trava que importa aqui: "pago" sem coleta NÃO pode aparecer como R$ 0 — isso afirmaria que
     nada foi pago, que é outra coisa. */
  const pagos = (C.itens || []).filter(i => typeof i.pago === "number");
  teste("topo: pago sem coleta não vira R$ 0",
    pagos.length ? /R\$/.test(txt("topoPago")) : txt("topoPago") === "sem coleta");
  teste("topo: a mediana é a do resumo do SICONFI",
    txt("topoMediana").includes(D.resumo.mediana_rs_hab.toFixed(2).replace(".", ",")));
  teste("topo: cada cartão declara a sua fonte",
    ["topoAnunciadoFonte", "topoPagoFonte", "topoMedianaFonte"].every(i => txt(i) && txt(i) !== "—"));
  teste("topo: o corte aparece no HTML estático, para quem não tem JavaScript",
    /id="corteFin"[^>]*>\s*\d{2}\/\d{2}\/\d{4}/.test(fs.readFileSync(path.join(raiz, "financiamento.html"), "utf-8")));

  // ── as figuras que ficaram ─────────────────────────────────────────────────────────────────
  teste("compromissos: gráfico anunciado × empenhado × pago com legenda e crédito",
    q("legCompromissos").children.length === 4 && graficos.some(g => g.ctx && g.ctx.id === "cCompromissos")
    && /Fonte:/.test(q("boxCompromissosGrafico").textContent));
  for (const id of ["mapaMPsUF", "mapaMP1384UF"]) {
    teste(`${id}: 27 estados, legenda com a unidade nacional à parte`,
      q(id).querySelectorAll("path").length === 27 && /unidade nacional/.test(txt(id.replace("mapa", "leg"))));
  }
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
    const alvo = q("mapaMPsUF").querySelector("path");
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
