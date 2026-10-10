#!/usr/bin/env node
/* scripts/verificar_semana_epidemiologica.js — a semana não chega ao leitor como semana
 * =====================================================================================
 *
 * Item 0 do handover "MARÉ Saúde: correção completa da página" (07/10/2026), e é regra da
 * editoria para o SITE INTEIRO, não só para a Saúde: o leitor não sabe o que é semana
 * epidemiológica, e por isso ela não aparece. O dado continua guardado por semana — isso é da
 * fonte; o que muda é o que se escreve na tela, que passa a ser o intervalo de datas.
 *
 * O PORTÃO FAZ DUAS COISAS, e elas são diferentes de propósito:
 *
 *   (a) PROVA A CONVERSÃO. `assets/semana.js` traduz (ano, semana) em datas pela regra do
 *       Ministério da Saúde — domingo a sábado, e a semana 1 é a primeira com pelo menos quatro
 *       dias de janeiro. Os casos abaixo foram conferidos contra o calendário epidemiológico
 *       publicado pelo MS, em quatro anos de virada diferente: 2023 (1º de janeiro no domingo),
 *       2024 (na segunda), 2025 (na quarta) e 2026 (na quinta). São justamente as viradas que
 *       quebram implementações ingênuas, e é por isso que são elas que estão aqui.
 *
 *   (b) PROCURA A SEMANA NO TEXTO RENDERIZADO. Não no fonte: no que o navegador mostra, que é
 *       onde o leitor a encontraria. Texto montado em tempo de execução, a partir do dado, não
 *       aparece numa busca pelo fonte — e é exatamente de lá que vinham "semana epidemiológica
 *       33" e "33 semana(s) fechada(s)".
 *
 * USO
 *   node scripts/verificar_semana_epidemiologica.js --autoteste   (só a conversão, sem navegador)
 *   node scripts/verificar_semana_epidemiologica.js
 */
const fs = require("fs");
const path = require("path");
const { JSDOM, VirtualConsole } = require("jsdom");
const { inlinePageJs } = require("./_inline_js");
const S = require("../assets/semana.js");

const raiz = path.join(__dirname, "..");

// As páginas com texto gerado a partir de dado semanal. A regra vale no site inteiro; estas são
// as que têm como produzir a semana na tela.
const PAGINAS = ["saude.html", "imprensa.html", "index.html", "blog.html"];

/* O que não pode aparecer, e o nome de cada coisa para o relatório dizer o que achou. */
const PROIBIDOS = [
  { nome: "semana epidemiológica", re: /semanas?\s+epidemiol[óo]gicas?/i },
  { nome: "semana fechada", re: /semanas?\s*\(?s?\)?\s+fechadas?/i },
  { nome: "sigla SE com número", re: /\bSE\s?\d{1,2}\b/ },
  // "202637" é ano+semana colados, como a fonte grava. Seis dígitos começando em 20 e terminando
  // num número de semana plausível. O ano sozinho (2026) não casa, e um valor com separador de
  // milhar ("202.637") também não, porque o ponto quebra a sequência.
  // A guarda `(?<![\d/])` … `(?![\d/])` nasceu de um falso positivo MEDIDO: a tabela de estados
  // emitia "08/06/202652.4" — a data colada ao número seguinte, sem separador —, e os seis
  // dígitos "202652" casavam como ano+semana. Aquilo era outro defeito, e dos reais (a tabela,
  // item 2), mas um padrão que nomeia errado o que encontra manda consertar a coisa errada.
  { nome: "ano+semana colados (202637)", re: /(?<![\d/])20\d{2}(?:0[1-9]|[1-4]\d|5[0-3])(?![\d/])/ },
  { nome: "“até a semana N”", re: /at[ée]\s+a\s+semana\s+\d{1,2}\b/i },
];

function autoteste() {
  let falhas = 0;
  const ok = (nome, cond) => { console.log((cond ? "  ✓ " : "  ✗ ") + nome); if (!cond) falhas++; };

  // (a) as quatro viradas de ano, contra o calendário do Ministério da Saúde
  const CALENDARIO = [
    [2023, 1, "1 a 7 de janeiro de 2023"],
    [2024, 1, "31 de dezembro de 2023 a 6 de janeiro de 2024"],
    [2025, 1, "29 de dezembro de 2024 a 4 de janeiro de 2025"],
    [2026, 1, "4 a 10 de janeiro de 2026"],
  ];
  CALENDARIO.forEach(([ano, n, esperado]) => {
    const obtido = S.porExtenso(ano, n, false);
    ok(`semana 1 de ${ano}: ${esperado}`, obtido === esperado);
    if (obtido !== esperado) console.log(`      obtido: ${obtido}`);
  });

  // A regra em si, dita de outro jeito: toda semana 1 tem pelo menos quatro dias de janeiro.
  for (let ano = 2015; ano <= 2035; ano++) {
    const r = S.semanaParaDatas(ano, 1);
    let dias = 0;
    for (let i = 0; i < 7; i++) {
      const d = new Date(r.inicio.getTime() + i * 86400000);
      if (d.getUTCMonth() === 0 && d.getUTCFullYear() === ano) dias++;
    }
    if (dias < 4) { ok(`semana 1 de ${ano} tem ao menos 4 dias de janeiro (tem ${dias})`, false); break; }
    if (ano === 2035) ok("semana 1 tem ao menos 4 dias de janeiro, de 2015 a 2035", true);
  }
  // E a semana começa sempre num domingo e termina num sábado.
  const r33 = S.semanaParaDatas(2026, 33);
  ok("a semana vai de domingo a sábado", r33.inicio.getUTCDay() === 0 && r33.fim.getUTCDay() === 6);
  ok("semana 33 de 2026: 16 a 22 de agosto", S.porExtenso(2026, 33, false) === "16 a 22 de agosto de 2026");
  // A travessia de mês e a de ano têm redação própria, e é fácil errar as duas.
  ok("travessia de mês: 30 de agosto a 5 de setembro de 2026",
     S.porExtenso(2026, 35, false) === "30 de agosto a 5 de setembro de 2026");
  ok("travessia de ano traz os dois anos", /2023.*2024/.test(S.porExtenso(2024, 1, false)));
  // Pedido inválido devolve null, e não uma data inventada.
  ok("semana 0, 54 e texto devolvem null",
     S.semanaParaDatas(2026, 0) === null && S.semanaParaDatas(2026, 54) === null
     && S.semanaParaDatas(2026, "x") === null);
  // 2026 não tem semana 53 (a 53ª já cairia na semana 1 de 2027); 2020 tem.
  ok("semana 53 só existe no ano que a tem (2026 não, 2020 sim)",
     S.semanaParaDatas(2026, 53) === null && S.semanaParaDatas(2020, 53) !== null);

  // (b) a própria lista de proibidos, provada contra exemplos — padrão que não pega o que
  // deveria é pior do que padrão nenhum, porque dá a impressão de estar guardando.
  const DEVE_PEGAR = ["semana epidemiológica 33", "Semanas Epidemiológicas", "33 semana(s) fechada(s)",
                      "SE 33", "SE33", "202637", "acumulado de 2026 até a semana 33"];
  const NAO_PEGAR = ["na semana de 16 a 22 de agosto de 2026", "202.637 notificações",
                     "de 1º de janeiro a 22 de agosto de 2026", "o ano de 2026", "SE Sergipe"];
  DEVE_PEGAR.forEach(t => ok(`pega ${JSON.stringify(t)}`, PROIBIDOS.some(p => p.re.test(t))));
  NAO_PEGAR.forEach(t => ok(`não pega ${JSON.stringify(t)}`, !PROIBIDOS.some(p => p.re.test(t))));

  if (falhas) { console.log(`\n✗ SEMANA: ${falhas} falha(s) no autoteste.`); return 1; }
  console.log("\n✓ AUTOTESTE OK — conversão conferida contra o calendário do MS e padrões provados.");
  return 0;
}

function renderizar(pagina) {
  const html = inlinePageJs(fs.readFileSync(path.join(raiz, pagina), "utf-8"), raiz);
  const vc = new VirtualConsole();
  return new JSDOM(html, {
    url: "https://localhost/" + pagina, runScripts: "dangerously", virtualConsole: vc,
    beforeParse(w) {
      global.window = w; global.document = w.document; w.d3 = require("d3");
      w.eval(fs.readFileSync(path.join(raiz, "assets", "mapas.js"), "utf-8"));
      // O Chart é simulado, e os rótulos que ele receberia entram na varredura: eixo e tooltip
      // são texto que o leitor vê, mesmo não estando no DOM.
      // SÓ O QUE VIRA TEXTO NA TELA: os rótulos do eixo, os nomes das séries e os títulos dos
      // eixos. Os VALORES não entram, e isso não é economia — é correção: varrendo `data.data`
      // inteiro, o padrão de ano+semana casou com "201447", que é um número de casos. Padrão que
      // acusa um valor de série manda consertar o dado onde não há nada errado.
      w.__rotulos = [];
      class Chart {
        constructor(ctx, cfg) {
          const d = (cfg && cfg.data) || {};
          try { w.__rotulos.push((d.labels || []).join(" ")); } catch (e) {}
          try { w.__rotulos.push((d.datasets || []).map(s => s && s.label).filter(Boolean).join(" ")); } catch (e) {}
          try {
            const esc = ((cfg && cfg.options) || {}).scales || {};
            Object.keys(esc).forEach(k => {
              const t = esc[k] && esc[k].title && esc[k].title.text;
              if (t) w.__rotulos.push(String(t));
            });
          } catch (e) {}
        }
      }
      Chart.defaults = { font: {}, color: "" };
      w.Chart = Chart;
      w.fetch = (rel) => {
        const p = path.join(raiz, String(rel).replace(/^\//, "").split("?")[0]);
        try { return Promise.resolve({ ok: true, json: () => Promise.resolve(JSON.parse(fs.readFileSync(p, "utf-8"))) }); }
        catch (e) { return Promise.resolve({ ok: false, status: 404 }); }
      };
    },
  });
}

async function main() {
  if (process.argv.includes("--autoteste")) process.exit(autoteste());
  if (autoteste() !== 0) process.exit(1);

  const falhas = [];
  for (const pagina of PAGINAS) {
    if (!fs.existsSync(path.join(raiz, pagina))) continue;
    const dom = renderizar(pagina);
    await new Promise(r => setTimeout(r, 2500));
    const d = dom.window.document;
    const alvo = [(d.querySelector("main") || d.body).textContent,
                  (dom.window.__rotulos || []).join(" ")].join("\n");
    PROIBIDOS.forEach(p => {
      const m = p.re.exec(alvo);
      if (m) {
        const i = m.index;
        falhas.push(`${pagina}: ${p.nome} — …${JSON.stringify(alvo.slice(Math.max(0, i - 50), i + 60))}`);
      }
    });
    console.log(`  ${falhas.length ? "·" : "✓"} ${pagina}: ${falhas.length ? "ver abaixo" : "sem semana no texto exibido"}`);
    dom.window.close();
  }
  if (falhas.length) {
    console.log(`\n✗ SEMANA EPIDEMIOLÓGICA: ${falhas.length} ocorrência(s) no texto que o leitor vê:`);
    falhas.slice(0, 12).forEach(f => console.log("   - " + f));
    process.exit(1);
  }
  console.log("\n✓ SEMANA EPIDEMIOLÓGICA OK — nenhuma página mostra semana, sigla ou ano+semana ao leitor.");
}

main().catch(e => { console.error(e); process.exit(1); });
