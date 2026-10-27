#!/usr/bin/env node
/* Verificador de runtime do Financiamento (financiamento.html).
 *
 * Reescrito em 17/10/2026 com a página (HANDOVER_FINANCIAMENTO_16-10-2026): renderiza com jsdom, d3
 * real, Chart simulado e `fetch` servindo `data/` do disco, e confere o RESULTADO. O que ele barra:
 *   (a) número do topo diferente do que o gerador escreveu (`financiamento/semana.json` → `topo`),
 *       a mesma conta que a Imprensa lê;
 *   (b) barra zero no lugar de etapa não coletada (a página escreve "não localizado até o corte");
 *   (c) mapa da figura principal sem os 27 territórios ou com círculo a mais ou a menos;
 *   (d) a volta do que saiu (cartões "Como ler", diagrama das rotas, "ciclo" sozinho);
 *   (e) consulta do município sem os quatro cartões.
 * Uso: node scripts/verificar_runtime_financiamento.js
 */
const { renderizar } = require("./_inline_js");
const fs = require("fs");
const path = require("path");

const raiz = path.join(__dirname, "..");
const ler = p => JSON.parse(fs.readFileSync(path.join(raiz, p), "utf-8"));
const MPS = ler("data/financiamento/mps_2026.json");
const SEM = ler("data/financiamento/semana.json");

const reaisNaTela = s => { const m = String(s).replace(/\./g, "").match(/([\d,]+)\s*(bi|mi|mil)?/); if (!m) return NaN;
  return Number(m[1].replace(",", ".")) * ({bi: 1e9, mi: 1e6, mil: 1e3}[m[2]] || 1); };
const perto = (tela, valor) => Math.abs(reaisNaTela(tela) - valor) <= Math.max(0.006 * valor, 1);

const { dom, erros } = renderizar("financiamento.html", raiz);

setTimeout(() => {
  const d = dom.window.document, q = id => d.getElementById(id);
  const falhas = [];
  const teste = (nome, cond) => { console.log((cond ? "  ✓ " : "  ✗ ") + nome); if (!cond) falhas.push(nome); };
  const txt = id => ((q(id) || {}).textContent || "").trim();

  teste("zero erros de runtime", erros.length === 0);
  erros.slice(0, 4).forEach(e => console.log("     ", e));
  teste("ordem da página: números, por risco, onde chega, mês a mês, município",
    [...d.querySelectorAll("#conteudo section")].map(x => x.id).join(",") === "dc-topo,caminhos,chega,mesames,municipio");
  teste("âncoras que o Para gestores e a Defesa civil usam existem", ["antes", "caminhos", "depois"].every(q));

  // (a) números do topo: os do gerador (`financiamento/semana.json` → `topo`), a mesma conta que a Imprensa lê
  const TOPO = (SEM.topo || []);
  const doTopo = id => (TOPO.find(c => c.id === id) || {});
  [["topoAnunciado", "anunciado_atos"], ["topoPago", "pago_ate_agora"], ["topoDefesaCivil", "defesa_civil_ciclo"], ["topoSus", "sus_emergencia"]]
    .forEach(([el, id]) => { const c = doTopo(id);
      teste(`${el} = ${id} do gerador`, c.valor == null || c.sem_coleta ? /sem coleta|não calculado/.test(txt(el)) : perto(txt(el), c.valor)); });
  teste("nenhum cartão do topo em travessão ou vazio",
    ["topoAnunciado", "topoPago", "topoDireto", "topoDefesaCivil", "topoSus"].every(i => txt(i) && txt(i) !== "—"));

  // (b) etapa não coletada é dita, não desenhada como zero
  const linhasBarra = [...d.querySelectorAll("#caminhos .barra-linha")];
  teste("etapa sem execução coletada: texto, nunca barra", linhasBarra.every(l => l.querySelector(".barra") || /não localizado até o corte/.test(l.textContent)));
  teste("tabela das origens com todas as origens", d.querySelectorAll("#tblOrigens tbody tr").length >= MPS.mps.length);

  // (c) figura principal
  const svg = q("mapChega");
  teste("mapa onde chega: 27 territórios", svg && svg.querySelectorAll("path.uf-path").length === 27);
  const esperado = (SEM.mapa || []).filter(x => x.valor > 0 && x.lat != null && /^(defesa_civil|saude)$/.test(x.origem)).length;
  teste(`mapa onde chega: ${esperado} círculos (defesa civil + FNS de emergência)`, svg && svg.querySelectorAll("circle").length === esperado);
  const c0 = svg && svg.querySelector("circle");
  if (c0) {
    c0.dispatchEvent(new dom.window.MouseEvent("mouseenter", { clientX: 100, clientY: 100, bubbles: true }));
    teste("tooltip do círculo exibe município e valor", q("mapTooltip").style.display === "block" && /R\$/.test(q("mapTooltip").textContent));
  } else teste("tooltip do círculo exibe município e valor", esperado === 0);

  // (d) o que saiu não volta
  teste("saíram os 'Como ler', o diagrama das rotas e o mapa do FNS por estado",
    !q("boxCaminhos") && !q("boxComoLerGasto") && !q("boxComoLerFns") && !q("boxFnsEmergenciaUF") && !q("boxFormaAplicacao"));
  teste("nenhum 'ciclo' sozinho no texto", !/\bciclo\b/i.test(q("conteudo").textContent.replace(/El Niño 2026\/2027/g, "")));
  teste("toda figura tem crédito de fonte", [...d.querySelectorAll("#conteudo .figura")].every(c => c.querySelector(".fonte-figura")));
  teste("E10: nenhum campo de autor de emenda na página", !/nomeAutor|codigoAutor|autor_emenda/i.test(d.documentElement.outerHTML));
  const ativa = d.querySelector(".mainnav .ativa");
  teste("nav: 'Financiamento' é o item ativo", ativa && ativa.textContent.trim() === "Financiamento");

  // (e) consulta do município
  const uf = q("consultaUF"), mun = q("consultaMun");
  uf.value = "RS"; uf.dispatchEvent(new dom.window.Event("change"));
  setTimeout(() => {
    mun.value = "Porto Alegre"; mun.dispatchEvent(new dom.window.Event("input"));
    const card = q("consultaCard");
    teste("consulta do município: quatro cartões e a linha do estado",
      !card.hidden && card.querySelectorAll(".cartao").length === 4 && /autorizados pela defesa civil federal/.test(card.textContent));
    if (falhas.length) { console.error(`\n✗ ${falhas.length} verificação(ões) falharam.`); process.exit(1); }
    console.log("\n✓ RUNTIME (Financiamento) OK — todas as verificações passaram.");
    process.exit(0);
  }, 2500);
}, 1500);
