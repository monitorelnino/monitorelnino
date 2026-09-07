#!/usr/bin/env node
/* Portão anticontrafactual do Calendário eleitoral (v3.1 §8): a página e o JSON não podem afirmar o que
 * "teria" acontecido sem a lei; cada dispositivo publicado tem trecho conferido, fonte e data; a tabela renderiza. */
const { JSDOM } = require("jsdom"); const { inlinePageJs } = require("./_inline_js"); const fs = require("fs"), path = require("path"); const raiz = path.join(__dirname, "..");
const falhas = [];
const PROIB = [/\bteria(m)?\b/i, /\bpoderia(m)? ter\b/i, /\bse n[ãa]o fosse\b/i, /\bsem a lei\b/i, /\bcustou\b/i, /\bteriam sido\b/i, /\bhouvesse\b/i, /\bcontrafactual\b/i];
const html = inlinePageJs(fs.readFileSync(path.join(raiz, "calendario-eleitoral.html"), "utf-8"), raiz).replace(/<script[\s\S]*?<\/script>/g, "");
const D = JSON.parse(fs.readFileSync(path.join(raiz, "data", "calendario", "dispositivos.json"), "utf-8"));
for (const rx of PROIB) { const m = html.match(rx); if (m) falhas.push(`página: expressão contrafactual "${m[0]}"`); }
for (const x of D.dispositivos) {
  for (const campo of ["bloqueia", "excecao", "significa"]) for (const rx of PROIB) { const m = String(x[campo]).match(rx); if (m) falhas.push(`${x.id}.${campo}: expressão contrafactual "${m[0]}"`); }
  if (!x.trecho || x.trecho.length < 40) falhas.push(`${x.id}: sem trecho conferido`);
  if (!/^https?:\/\//.test(x.fonte || "")) falhas.push(`${x.id}: sem fonte lida`);
}
if (!/^\d{2}\/\d{2}\/\d{4}$/.test(D.conferido_em || "")) falhas.push("JSON sem data de conferência");
const pagina = inlinePageJs(fs.readFileSync(path.join(raiz, "calendario-eleitoral.html"), "utf-8"), raiz);
const dom = new JSDOM(pagina, { url: "https://localhost/", runScripts: "dangerously", beforeParse(w) { w.fetch = rel => { try { const t = fs.readFileSync(path.join(raiz, String(rel)), "utf-8"); return Promise.resolve({ ok: true, json: () => Promise.resolve(JSON.parse(t)) }); } catch (e) { return Promise.resolve({ ok: false }); } }; } });
setTimeout(() => {
  const d = dom.window.document;
  if (d.querySelectorAll("#tblDispositivos tbody tr").length !== D.dispositivos.length) falhas.push("tabela de dispositivos não renderizou todas as linhas");
  if (d.querySelectorAll("#listaNaoSuspenso li").length !== D.nao_suspenso.length) falhas.push("lista do não suspenso incompleta");
  if (!/art\. 73, VI, a/.test(d.body.textContent) && !/73, VI, a/.test(d.body.textContent)) falhas.push("dispositivo 73, VI, a ausente do texto visível");
  if (falhas.length) { console.log("✗ CALENDÁRIO:"); falhas.forEach(f => console.log("   -", f)); process.exit(1); }
  console.log("✓ CALENDÁRIO OK — sem contrafactual, dispositivos com trecho conferido e fonte, tabela e lista renderizadas.");
}, 1500);
