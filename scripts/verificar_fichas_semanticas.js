#!/usr/bin/env node
/* Portão das fichas semânticas (§191, 23/09/2026).
 *
 * POR QUE EXISTE. O §35 da AI_EDITORIAL_NARRATIVE_GOVERNANCE.md pede, para cada visualização, uma
 * ficha interna com universo, unidade de análise, território, período, variável, fonte, conclusões
 * permitidas e não permitidas e função narrativa — "memória semântica para impedir que futuras
 * alterações percam o significado da figura". Uma ficha sem portão envelhece em silêncio: alguém
 * acrescenta uma figura, ninguém escreve a ficha, e a memória some exatamente onde ela serviria.
 *
 * O QUE ELE GARANTE, e só isso: que toda figura renderizada tenha ficha, que nenhuma ficha aponte
 * para figura que não existe mais, e que os campos obrigatórios estejam preenchidos. Ele NÃO julga
 * o conteúdo da ficha — isso é leitura humana, e o §29 reserva à editoria o que muda significado.
 *
 * As fichas não aparecem na interface (§35), e este portão também confere isso: nenhum texto da
 * ficha pode vazar para o HTML renderizado.
 *
 * Uso: node scripts/verificar_fichas_semanticas.js
 */
const { JSDOM, VirtualConsole } = require("jsdom"); const { inlinePageJs } = require("./_inline_js");
const fs = require("fs"), path = require("path");
const raiz = path.join(__dirname, "..");
const PAGINAS = ["index.html", "pesquisadores.html", "calendario-eleitoral.html", "defesa-civil.html",
                 "monitor-de-riscos.html", "saude.html", "financiamento.html", "proteja-se.html",
                 "imprensa.html", "blog.html", "prefeituras.html"];
const falhas = [];

const doc = JSON.parse(fs.readFileSync(path.join(raiz, "docs", "fichas_semanticas.json"), "utf-8"));
const FICHAS = doc.fichas || {};
const OBRIGATORIOS = doc.campos_obrigatorios || [];

// Mesma montagem do portão de figuras: as páginas buscam dados em data/, e sem fetch local o
// documento nem chega a ter figura.
function renderizar(pagina) {
  const html = inlinePageJs(fs.readFileSync(path.join(raiz, pagina), "utf-8"), raiz);
  const vc = new VirtualConsole();
  return new JSDOM(html, {
    url: "https://localhost/", runScripts: "dangerously", virtualConsole: vc,
    beforeParse(w) {
      global.window = w; global.document = w.document; global.navigator = w.navigator;
      w.d3 = require("d3");
      try { w.eval(fs.readFileSync(path.join(raiz, "assets", "mapas.js"), "utf-8")); } catch (e) {}
      class Chart { constructor() {} } Chart.defaults = { font: {}, color: "", plugins: { legend: { labels: {} }, tooltip: {} }, elements: {} };
      w.Chart = Chart;
      w.fetch = (rel) => {
        try { const txt = fs.readFileSync(path.join(raiz, String(rel).replace(/^\.\//, "")), "utf-8");
              return Promise.resolve({ ok: true, json: () => Promise.resolve(JSON.parse(txt)), text: () => Promise.resolve(txt) }); }
        catch (e) { return Promise.resolve({ ok: false }); }
      };
    }
  });
}

const vistas = new Set();
(async () => {
for (const pagina of PAGINAS) {
  let d;
  try { const dom = renderizar(pagina); await new Promise(r => setTimeout(r, 1500)); d = dom.window.document; }
  catch (e) { falhas.push(`${pagina}: não renderizou (${e.message})`); continue; }
  for (const fig of d.querySelectorAll(".figura")) {
    const id = fig.id;
    if (!id) { falhas.push(`${pagina}: figura sem id — não há como fichá-la (§35)`); continue; }
    const chave = `${pagina}#${id}`;
    vistas.add(chave);
    const ficha = FICHAS[chave];
    if (!ficha) { falhas.push(`${chave}: figura sem ficha semântica (§35)`); continue; }
    for (const campo of OBRIGATORIOS) {
      const v = ficha[campo];
      const vazio = v == null || (typeof v === "string" && !v.trim()) || (Array.isArray(v) && !v.length);
      if (vazio) falhas.push(`${chave}: campo obrigatório vazio na ficha — '${campo}' (§35)`);
    }
  }
}

for (const chave of Object.keys(FICHAS)) {
  if (!vistas.has(chave)) falhas.push(`${chave}: ficha órfã — a figura não existe mais (§35)`);
}

// §35: a ficha é memória interna, nunca interface. Uma frase da ficha no HTML significa que alguém
// renderizou raciocínio de bastidor, que é o que o §27 proíbe nominalmente.
const marcas = Object.values(FICHAS).map(f => f.pergunta_que_responde).filter(Boolean);
for (const pagina of PAGINAS) {
  const html = fs.readFileSync(path.join(raiz, pagina), "utf-8");
  for (const m of marcas) if (html.includes(m)) falhas.push(`${pagina}: texto de ficha semântica renderizado na interface (§27, §35): "${m.slice(0, 60)}"`);
}

if (falhas.length) {
  console.log("✗ FICHAS SEMÂNTICAS: problemas encontrados:");
  falhas.forEach(f => console.log("  ✗ " + f));
  process.exit(1);
}
console.log(`✓ FICHAS SEMÂNTICAS OK — ${vistas.size} figura(s) com ficha completa, nenhuma órfã, nada vazado para a interface (§35).`);
})();
