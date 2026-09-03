#!/usr/bin/env node
/* Portão 11 — acessibilidade e responsividade (v2.3, 02/09/2026)
 * Verificações estáticas (jsdom) nas 8 páginas: idioma, viewport, skip-link,
 * um único h1, ordem de títulos, alt em imagens, rótulos em campos de formulário,
 * mapas SVG com role/aria-label, nav com aria-current, sem tabindex positivo,
 * tabelas com cabeçalho, contraste AA dos pares de tokens usados em texto,
 * e presença dos pontos de quebra canônicos e do foco visível na folha base.
 * Uso: node scripts/verificar_acessibilidade.js
 */
const fs = require("fs"), path = require("path"); const { JSDOM } = require("jsdom");
const RAIZ = path.join(__dirname, ".."); let falhas = 0;
const falha = m => { console.log("  ✗ " + m); falhas++; };
const PAGINAS = ["index.html","mapas-e-graficos.html","sinais-de-risco.html","saude.html","financiamento.html","proteja-se.html","envie-dados.html","para-gestores.html","obrigado.html","imprensa.html"];
const base = fs.readFileSync(path.join(RAIZ,"assets","base.css"),"utf-8"), tokens = fs.readFileSync(path.join(RAIZ,"assets","tokens.css"),"utf-8");
// contraste WCAG dos pares texto/fundo usados no site
const hex = n => { const m = tokens.match(new RegExp("--" + n + ":\\s*(#[0-9A-Fa-f]{6})")); return m && m[1]; };
const lum = h => { const c = [1,3,5].map(i => parseInt(h.slice(i,i+2),16)/255).map(x => x <= .03928 ? x/12.92 : Math.pow((x+.055)/1.055, 2.4)); return .2126*c[0]+.7152*c[1]+.0722*c[2]; };
const ratio = (a,b) => { const [x,y] = [lum(a),lum(b)].sort((p,q)=>q-p); return (x+.05)/(y+.05); };
for (const [texto, fundo, min, uso] of [["ink","bg",4.5,"texto sobre fundo"],["ink","surface",4.5,"texto sobre painel"],["muted","bg",4.5,"texto secundário sobre fundo"],["muted","surface",4.5,"texto secundário sobre painel"],["link","bg",4.5,"links sobre fundo"],["link","surface",4.5,"links sobre painel"],["neutro","bg",4.5,"'não verificado' sobre fundo"],["rust","surface",3,"cor de dado sobre painel (≥3:1)"]]) {
  const r = ratio(hex(texto), hex(fundo)); if (r < min) falha(`contraste ${uso}: --${texto}/--${fundo} = ${r.toFixed(2)}:1 (mínimo ${min}:1)`);
}
for (const bp of ["max-width:1020px","max-width:880px","max-width:640px","max-width:420px"]) if (!base.includes(bp)) falha(`base.css sem ponto de quebra ${bp}`);
if (!/:focus-visible\{/.test(base)) falha("base.css sem foco visível (:focus-visible)");
if (!/\.mainnav a, \.mainnav span\{[^}]*min-height:36px/.test(base)) falha("base.css sem alvo de toque mínimo na navegação");
for (const p of PAGINAS) {
  const html = fs.readFileSync(path.join(RAIZ, p), "utf-8"); const d = new JSDOM(html).window.document;
  if ((d.documentElement.getAttribute("lang") || "").toLowerCase() !== "pt-br") falha(`${p}: <html lang> ausente ou diferente de pt-BR`);
  if (!d.querySelector('meta[name="viewport"][content*="width=device-width"]')) falha(`${p}: sem meta viewport responsiva`);
  if (!d.querySelector("a.skip[href^='#']")) falha(`${p}: sem link 'pular para o conteúdo' (a.skip)`);
  const h1 = d.querySelectorAll("h1"); if (h1.length !== 1) falha(`${p}: ${h1.length} <h1> (esperado 1)`);
  let nivel = 0; d.querySelectorAll("h1,h2,h3,h4").forEach(h => { const n = Number(h.tagName[1]); if (nivel && n > nivel + 1) falha(`${p}: salto de nível de título (h${nivel} → h${n}: "${h.textContent.trim().slice(0,40)}")`); nivel = n; });
  d.querySelectorAll("img").forEach(i => { if (!i.hasAttribute("alt")) falha(`${p}: <img> sem alt (${(i.getAttribute("src")||"").slice(0,40)})`); });
  d.querySelectorAll("svg").forEach(s => { if (s.closest("footer")) return; if (!(s.getAttribute("role") && (s.getAttribute("aria-label") || s.getAttribute("aria-labelledby"))) && !s.getAttribute("aria-hidden")) falha(`${p}: <svg id="${s.id||"?"}"> sem role+aria-label`); });
  d.querySelectorAll("input:not([type=hidden]):not([type=submit]), select, textarea").forEach(c => { const id = c.id; const ok = (id && d.querySelector(`label[for="${id}"]`)) || c.closest("label") || c.getAttribute("aria-label") || c.getAttribute("aria-labelledby"); if (!ok) falha(`${p}: campo de formulário sem rótulo (${c.name||c.id||c.tagName})`); });
  if (d.querySelector("[tabindex]:not([tabindex='0']):not([tabindex='-1'])")) falha(`${p}: tabindex positivo (quebra a ordem de tabulação)`);
  d.querySelectorAll("table").forEach(t => { if (!t.querySelector("th")) falha(`${p}: tabela sem cabeçalho <th>`); });
  if (p !== "obrigado.html" && !d.querySelector('.mainnav [aria-current="page"]')) falha(`${p}: nav sem aria-current="page"`);
  d.querySelectorAll("a[target=_blank]").forEach(a => { if (!/noopener/.test(a.getAttribute("rel")||"")) falha(`${p}: link externo sem rel=noopener`); });
  if (!/<link[^>]+assets\/base\.css/.test(html)) falha(`${p}: sem assets/base.css`);
}
console.log(falhas ? `✗ ACESSIBILIDADE: ${falhas} problema(s). Publicação bloqueada.` : "✓ ACESSIBILIDADE OK — idioma, viewport, skip-link, títulos, alt, rótulos, SVG rotulados, foco visível, contraste AA e pontos de quebra nas 8 páginas.");
process.exit(falhas ? 1 : 0);
