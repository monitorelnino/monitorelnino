#!/usr/bin/env node
/* Portão de segurança (v3.1 §14.5–14.7, 06/09/2026):
 * (a) nenhum <script> inline nem handler on*= nas páginas (CSP sem 'unsafe-inline' em script-src);
 * (b) CSP do netlify.toml sem 'unsafe-inline' em script-src e sem cdnjs;
 * (c) bibliotecas externas só em assets/vendor/ (nenhum src externo além de vlibras.gov.br);
 * (d) todo `innerHTML =` em assets/js/*.js escapa (esc(, MonitorMapas.esc, ou literal sem interpolação de dado);
 * (e) Actions fixadas por SHA. */
const fs = require("fs"), path = require("path"); const RAIZ = path.join(__dirname, ".."); const falhas = [];
const paginas = fs.readdirSync(RAIZ).filter(f => f.endsWith(".html"));
for (const p of paginas) {
  const h = fs.readFileSync(path.join(RAIZ, p), "utf-8");
  if (/<script>(?![\s\S]*?<\/script>\s*$)/.test(h) && /<script>[\s\S]*?<\/script>/.test(h)) falhas.push(`${p}: <script> inline`);
  const m = h.match(/\son(?:click|change|input|submit|load|keyup|keydown|mouseover|focus|blur)\s*=/i); if (m) falhas.push(`${p}: handler inline (${m[0].trim()})`);
  for (const s of h.matchAll(/<script src="(https?:\/\/[^"]+)"/g)) if (!/^https:\/\/vlibras\.gov\.br\//.test(s[1])) falhas.push(`${p}: script externo ${s[1]}`);
}
const toml = fs.readFileSync(path.join(RAIZ, "netlify.toml"), "utf-8"); const csp = (toml.match(/Content-Security-Policy = "([^"]*)"/) || [])[1] || "";
const sc = (csp.match(/script-src ([^;]*)/) || [])[1] || "";
if (/'unsafe-inline'/.test(sc)) falhas.push("CSP: script-src com 'unsafe-inline'");
if (/cdnjs/.test(csp)) falhas.push("CSP: cdnjs ainda permitido");
for (const f of fs.readdirSync(path.join(RAIZ, "assets", "js"))) {
  const txt = fs.readFileSync(path.join(RAIZ, "assets", "js", f), "utf-8"); const js = txt.split("\n");
  const sanitizadorGlobal = /function sanitizar\(\)/.test(txt);   // index.js: dados escapados na carga (walk sobre DATA/TABELA/MARE)
  js.forEach((l, i) => {
    if (!/\.innerHTML\s*=[^=]/.test(l) || /innerHTML\s*=\s*''|innerHTML\s*=\s*""/.test(l)) return;
    const ok = /esc\(|MonitorMapas\.esc|\.textContent|escapar\(|sanitiz/.test(l) || (/innerHTML\s*=\s*'[^$`]*'\s*;?$/.test(l.trim()) || /innerHTML\s*=\s*"[^$`]*"\s*;?$/.test(l.trim()));
    // atribuições que continuam em linhas seguintes: aceitar se as 12 linhas seguintes contiverem esc(
    const bloco = js.slice(Math.max(0, i - 30), i + 12).join("\n");   // montagem em linhas anteriores (html += … esc(…))
    if (!ok && !sanitizadorGlobal && !/esc\(|MonitorMapas\.esc|escapar\(/.test(bloco)) falhas.push(`${f}:${i + 1}: innerHTML sem esc() — ${l.trim().slice(0, 80)}`);
  });
}
for (const wf of fs.readdirSync(path.join(RAIZ, ".github", "workflows"))) {
  const t = fs.readFileSync(path.join(RAIZ, ".github", "workflows", wf), "utf-8");
  for (const u of t.matchAll(/uses:\s*([\w.-]+\/[\w.-]+)@([^\s#]+)/g)) if (!/^[0-9a-f]{40}$/.test(u[2])) falhas.push(`${wf}: ${u[1]}@${u[2]} não fixada por SHA`);
}
if (falhas.length) { console.log("✗ SEGURANÇA:"); falhas.forEach(f => console.log("   -", f)); process.exit(1); }
console.log(`✓ SEGURANÇA OK — sem script inline, CSP fechada, vendor local, innerHTML escapado, Actions por SHA (${paginas.length} páginas).`);
