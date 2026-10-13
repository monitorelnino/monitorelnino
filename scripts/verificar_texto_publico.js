#!/usr/bin/env node
/* Texto público — um verificador, uma renderização por página (consolidação item 3, 13/10/2026).
 * Fundiu `verificar_vocabulario_publico.js` (portão 16, 03/09/2026) e `verificar_voz_editorial.js`
 * (16/09/2026): os dois renderizavam as mesmas páginas, com o mesmo jsdom, para olhar o mesmo texto.
 * As regras saíram do código e moram em `layout/regras.json → texto_publico`:
 *   jargao_interno — nome de arquivo, caminho de dados, código de decisão, "portão", "robô"… (barra);
 *   refraos        — a mesma ressalva 3+ vezes em .hint/.note/.card-body é refrão (barra);
 *   forma          — data ISO, undefined/NaN, {chave}, texto interno, ponto decimal (`--forma`, só no PR).
 * Dentro de bloco `data-proveniencia="1"` nome de arquivo e caminho de dados são o assunto (v3.1 §9).
 * Uso: node scripts/verificar_texto_publico.js [--forma] [--listar] [--autoteste] */
const fs = require("fs"), path = require("path");
const { JSDOM, VirtualConsole } = require("jsdom"); const { inlinePageJs } = require("./_inline_js");
const RAIZ = path.join(__dirname, "..");
const listar = process.argv.includes("--listar"), comForma = process.argv.includes("--forma");
const T = JSON.parse(fs.readFileSync(path.join(RAIZ, "layout", "regras.json"), "utf-8")).texto_publico;
const re = (r) => [new RegExp(r.padrao, r.flags), r.motivo];
const JARGAO = T.jargao_interno.map(re), FORMA = T.forma.map(re), REFRAOS = T.refraos.map(re);
// Ficam fora DE PROPÓSITO: `mudancas.html` e `indice-de-conteudo.html` (páginas internas).
const PAGINAS = ["index.html", "defesa-civil.html", "monitor-de-riscos.html", "saude.html", "financiamento.html",
  "proteja-se.html", "prefeituras.html", "obrigado.html", "imprensa.html", "blog.html"]
  .concat(fs.existsSync(path.join(RAIZ, "blog")) ? fs.readdirSync(path.join(RAIZ, "blog"))
    .filter((b) => b.endsWith(".html")).sort().map((b) => "blog/" + b) : [])
  .filter((p) => fs.existsSync(path.join(RAIZ, p)));

/* O que reprova num texto já renderizado. Função pura: o autoteste a prova sem página. */
function achados(texto, textoDeProva, textoDeNota, forma) {
  const regras = forma ? JARGAO.concat(FORMA) : JARGAO;
  const fora = [];
  for (const [r, motivo] of regras) { const m = texto.match(r); if (m) fora.push(`${motivo}: ${[...new Set(m)].slice(0, 6).join(" | ")}`); }
  for (const [r, motivo] of regras.filter(([, mo]) => !/nome de arquivo|caminho de dados/.test(mo))) {
    const m = textoDeProva.match(r); if (m) fora.push(`${motivo} (bloco de prova): ${[...new Set(m)].slice(0, 6).join(" | ")}`); }
  for (const [r] of REFRAOS) { const m = textoDeNota.match(r);
    if (m && m.length >= T.refrao_a_partir_de) fora.push(`"${r.source}" aparece ${m.length}x em legendas/notas — consolide numa ficha ou nota única`); }
  return fora;
}

function autoteste() {
  const casos = [
    ["nome de arquivo reprova", achados("veja data/estados.json", "", "", false).length === 2],
    ["'portão' reprova", achados("o portão reprovou", "", "", false).length === 1],
    ["nome de arquivo no bloco de prova passa", achados("", "arquivo indice.json", "", false).length === 0],
    ["'robô' no bloco de prova reprova", achados("", "o robô coletou", "", false).length === 1],
    ["texto limpo passa", achados("Decretos de emergência desde 29/06/2026.", "", "", true).length === 0],
    ["forma só com --forma", achados("em 2026-10-13", "", "", false).length === 0 && achados("em 2026-10-13", "", "", true).length === 1],
    ["slug em endereço não é data ISO", achados("blog/2026-10-06-seca", "", "", true).filter((a) => /data ISO/.test(a)).length === 0],
    ["molde não preenchido reprova (forma)", achados("Procurado em {canais}", "", "", true).length === 1],
    ["ressalva 3x é refrão", achados("", "", "peso zero. peso zero. peso zero.", false).length === 1],
    ["ressalva 2x não é refrão", achados("", "", "peso zero. peso zero.", false).length === 0],
  ];
  casos.forEach(([n, ok]) => console.log(`  ${ok ? "✓" : "✗"} ${n}`));
  const ruins = casos.filter(([, ok]) => !ok).length;
  console.log(ruins ? `✗ AUTOTESTE: ${ruins} falha(s)` : `✓ AUTOTESTE OK — ${casos.length} casos, sem página.`);
  process.exit(ruins ? 1 : 0);
}

if (process.argv.includes("--autoteste")) autoteste();
else (async () => {
  let total = 0;
  for (const p of PAGINAS) {
    const html = inlinePageJs(fs.readFileSync(path.join(RAIZ, p), "utf-8"), RAIZ); const vc = new VirtualConsole();
    const dom = new JSDOM(html, { url: "https://localhost/", runScripts: "dangerously", virtualConsole: vc, beforeParse(w) {
      global.window = w; global.document = w.document; w.d3 = require("d3"); w.eval(fs.readFileSync(path.join(RAIZ, "assets", "mapas.js"), "utf-8"));
      class Chart { constructor() {} } Chart.defaults = { font: {}, color: "" }; w.Chart = Chart;
      w.fetch = (rel) => { try { return Promise.resolve({ ok: true, json: () => Promise.resolve(JSON.parse(fs.readFileSync(path.join(RAIZ, rel), "utf-8"))) }); } catch (e) { return Promise.resolve({ ok: false }); } };
    } });
    await new Promise((r) => setTimeout(r, 1500));
    const d = dom.window.document;
    const textoDeNota = [...d.querySelectorAll(".hint, .note, .card-body")].map((e) => e.textContent).join(" \n ");
    d.querySelectorAll("script, style, noscript, code, pre").forEach((e) => e.remove());
    const provas = [...d.querySelectorAll('[data-proveniencia="1"]')];
    const textoDeProva = provas.map((e) => e.textContent).join(" ").replace(/\s+/g, " ");
    provas.forEach((e) => e.remove());
    const fora = achados(d.body.textContent.replace(/\s+/g, " "), textoDeProva, textoDeNota, comForma);
    if (fora.length) { total += fora.length; console.log(`  ✗ ${p}:`); fora.forEach((a) => console.log(`      ${a}`)); }
    else if (listar) console.log(`  ✓ ${p}`);
  }
  console.log(total ? `✗ TEXTO PÚBLICO: ${total} problema(s). Publicação bloqueada.`
    : "✓ TEXTO PÚBLICO OK — sem jargão interno, sem refrão de ressalva" + (comForma ? ", forma em dia." : "."));
  process.exit(total ? 1 : 0);
})();
