#!/usr/bin/env node
/* Portão — voz editorial (16/09/2026, a pedido da editoria; ver docs/VOZ_EDITORIAL.md).
 * Uma legenda descreve o que a figura é; a ressalva metodológica mora uma vez por página
 * (a ficha "Como ler", uma nota "O que a figura não diz") — nunca repetida como refrão em
 * cada legenda. Este portão faz a parte mecânica: se a mesma frase-marcador aparecer 3+
 * vezes no texto visível (.hint, .note, .card-body) de uma página, é sinal de refrão, não
 * de coincidência — consolide num só lugar. Não pega tom (isso é leitura humana ou do
 * Claude, contra VOZ_EDITORIAL.md); pega repetição, que é mecânico e objetivo.
 * Uso: node scripts/verificar_voz_editorial.js [--listar] */
const fs = require("fs"), path = require("path");
const { JSDOM, VirtualConsole } = require("jsdom");
const { inlinePageJs } = require("./_inline_js");
const RAIZ = path.join(__dirname, "..");
const listar = process.argv.includes("--listar");
const PAGINAS = ["index.html", "pesquisadores.html", "calendario-eleitoral.html", "defesa-civil.html",
  "monitor-de-riscos.html", "saude.html", "financiamento.html", "proteja-se.html", "prefeituras.html",
  "obrigado.html", "imprensa.html"].filter(p => fs.existsSync(path.join(RAIZ, p)));

// Frases-marcador de ressalva metodológica que só devem aparecer uma vez por página (na
// ficha ou numa nota dedicada) — não em cada legenda de figura. Lista curta e literal de
// propósito: o objetivo é pegar o refrão óbvio, não policiar toda frase com "não".
const MARCADORES = [/peso zero/gi, /não atribui(mos)? (casos |eventos )?ao El Niño/gi,
  /nunca se somam?/gi, /nunca (se )?combinam?/gi, /não é tarefa/gi];

(async () => {
  let total = 0;
  for (const p of PAGINAS) {
    const html = inlinePageJs(fs.readFileSync(path.join(RAIZ, p), "utf-8"), RAIZ);
    const vc = new VirtualConsole();
    const dom = new JSDOM(html, { url: "https://localhost/", runScripts: "dangerously", virtualConsole: vc, beforeParse(w) {
      global.window = w; global.document = w.document; w.d3 = require("d3"); w.eval(fs.readFileSync(path.join(RAIZ, "assets", "mapas.js"), "utf-8"));
      class Chart { constructor() {} } Chart.defaults = { font: {}, color: "" }; w.Chart = Chart;
      w.fetch = (rel) => { try { return Promise.resolve({ ok: true, json: () => Promise.resolve(JSON.parse(fs.readFileSync(path.join(RAIZ, rel), "utf-8"))) }); } catch (e) { return Promise.resolve({ ok: false }); } };
    } });
    await new Promise(r => setTimeout(r, 1200));
    const d = dom.window.document;
    const texto = [...d.querySelectorAll(".hint, .note, .card-body")].map(e => e.textContent).join(" \n ");
    const achados = [];
    for (const re of MARCADORES) { const m = texto.match(re); if (m && m.length >= 3) achados.push([re.source, m.length]); }
    if (achados.length) { total += achados.length; console.log(`  ✗ ${p}:`); achados.forEach(([re, n]) => console.log(`      "${re}" aparece ${n}x em legendas/notas — consolide numa ficha ou nota única`)); }
    else if (listar) console.log(`  ✓ ${p}`);
  }
  console.log(total ? `✗ VOZ EDITORIAL: ${total} refrão(ões) repetido(s). Consolide na ficha da página (docs/VOZ_EDITORIAL.md). Publicação bloqueada.`
    : "✓ VOZ EDITORIAL OK — nenhuma ressalva repetida como refrão em legendas/notas.");
  process.exit(total ? 1 : 0);
})();
