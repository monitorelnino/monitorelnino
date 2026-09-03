#!/usr/bin/env node
/* Portão 16 — vocabulário público (03/09/2026, a pedido da editoria).
 * O texto VISÍVEL das páginas (renderizado, com dados) não pode conter jargão interno:
 * nomes de arquivo/script, referências a decisões/seções internas, "portão", "robô",
 * "PR #", "AUD-", "sessão", "Claude", "documento de redesenho", nem a expressão
 * "pedidos de acesso à informação enviados". A linha narrativa é a do público.
 * Uso: node scripts/verificar_vocabulario_publico.js [--listar] */
const fs = require("fs"), path = require("path"); const { JSDOM, VirtualConsole } = require("jsdom");
const RAIZ = path.join(__dirname, ".."); const listar = process.argv.includes("--listar");
const PAGINAS = ["index.html", "mapas-e-graficos.html", "sinais-de-risco.html", "saude.html", "financiamento.html", "proteja-se.html", "envie-dados.html", "para-gestores.html", "obrigado.html", "imprensa.html"].filter(p => fs.existsSync(path.join(RAIZ, p)));
const PROIBIDOS = [
  [/\b(?!datapackage\b)[\w-]+\.(py|json|js|yml|sh)\b/g, "nome de arquivo/script (os .csv dos dados abertos são permitidos)"],
  [/\bdata\/[\w./-]+/g, "caminho de dados"],
  [/\bdecis(ão|ões) ?(editorial)? ?[CE]\d{1,2}\b/gi, "referência a decisão interna"],
  [/\((?:E|C)\d{1,2}(?:[,–\-/ ]+(?:E|C)?\d{1,2})*\)/g, "código de decisão entre parênteses"],
  [/\bregra E\d{1,2}\b/gi, "código de decisão"],
  [/\bport(ão|ões)\b/gi, "'portão' (jargão interno)"],
  [/\brob[ôo]\b/gi, "'robô' (dizer 'rotina automática')"],
  [/\bPR #\d+\b/g, "número de PR"],
  [/\bAUD-\d+\b/g, "código de auditoria"],
  [/\bClaude\b/g, "nome do assistente"],
  [/documento de redesenho/gi, "documento interno"],
  [/pedidos? de acesso à informação enviados?/gi, "registro de pedidos de LAI (nunca no site)"],
  [/\bsess[ãa]o (metodológica|paralela|de construção)\b/gi, "'sessão' interna"],
  [/\bTODO\b|\bFIXME\b|\bXXX\b/g, "marcador de pendência"],
];
let total = 0;
(async () => {
  for (const p of PAGINAS) {
    const html = fs.readFileSync(path.join(RAIZ, p), "utf-8"); const vc = new VirtualConsole();
    const dom = new JSDOM(html, { url: "https://localhost/", runScripts: "dangerously", virtualConsole: vc, beforeParse(w) {
      global.window = w; global.document = w.document; w.d3 = require("d3"); w.eval(fs.readFileSync(path.join(RAIZ, "assets", "mapas.js"), "utf-8"));
      class Chart { constructor() {} } Chart.defaults = { font: {}, color: "" }; w.Chart = Chart;
      w.fetch = (rel) => { try { return Promise.resolve({ ok: true, json: () => Promise.resolve(JSON.parse(fs.readFileSync(path.join(RAIZ, rel), "utf-8"))) }); } catch (e) { return Promise.resolve({ ok: false }); } };
    } });
    await new Promise(r => setTimeout(r, 1500));
    const d = dom.window.document; d.querySelectorAll("script, style, noscript, code, pre").forEach(e => e.remove());
    const texto = d.body.textContent.replace(/\s+/g, " ");
    const achados = [];
    for (const [re, motivo] of PROIBIDOS) { const m = texto.match(re); if (m) achados.push([motivo, [...new Set(m)].slice(0, 6)]); }
    if (achados.length) { total += achados.length; console.log(`  ✗ ${p}:`); achados.forEach(([mo, ex]) => console.log(`      ${mo}: ${ex.join(" | ")}`)); }
    else if (listar) console.log(`  ✓ ${p}`);
  }
  console.log(total ? `✗ VOCABULÁRIO PÚBLICO: ${total} problema(s). Publicação bloqueada.` : "✓ VOCABULÁRIO PÚBLICO OK — nenhum jargão interno no texto visível das páginas.");
  process.exit(total ? 1 : 0);
})();
