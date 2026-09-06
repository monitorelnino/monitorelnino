#!/usr/bin/env node
/* Portão de palavras estáticas por página (v3.1 §7). Conta o texto fora de <script>, <style>, nav e rodapé.
 * "teto" bloqueia a publicação; "meta" (§7) é o alvo da edição — acima da meta o portão avisa, não bloqueia. */
const fs = require("fs"), path = require("path"); const RAIZ = path.join(__dirname, "..");
const LIMITES = { // [meta §7, teto]
  "index.html": [500, 800], "sinais-de-risco.html": [350, 420], "calendario-eleitoral.html": [600, 900], "defesa-civil.html": [400, 450],
  "saude.html": [554, 600], "financiamento.html": [550, 720], "proteja-se.html": [800, 1150], "para-gestores.html": [600, 860],
  "imprensa.html": [700, 1060], "pesquisadores.html": [1500, 2200], "envie-dados.html": [150, 520], "obrigado.html": [100, 160] };
function palavras(f) {
  let t = fs.readFileSync(path.join(RAIZ, f), "utf-8");
  t = t.replace(/<script[\s\S]*?<\/script>/g, "").replace(/<style[\s\S]*?<\/style>/g, "").replace(/<nav class="mainnav"[\s\S]*?<\/nav>/g, "").replace(/<footer[\s\S]*?<\/footer>/g, "");
  return t.replace(/<[^>]+>/g, " ").split(/\s+/).filter(Boolean).length;
}
let falhas = 0, avisos = 0;
for (const [f, [meta, teto]] of Object.entries(LIMITES)) {
  if (!fs.existsSync(path.join(RAIZ, f))) continue;
  const n = palavras(f);
  if (n > teto) { console.log(`  ✗ ${f}: ${n} palavras estáticas (teto ${teto})`); falhas++; }
  else if (n > meta) { console.log(`  ⚠ ${f}: ${n} palavras (meta §7: ${meta}; teto ${teto})`); avisos++; }
}
if (falhas) { console.log(`✗ PALAVRAS: ${falhas} página(s) acima do teto. Publicação bloqueada.`); process.exit(1); }
console.log(`✓ PALAVRAS OK — nenhuma página acima do teto${avisos ? ` (${avisos} acima da meta do §7, a apertar)` : ""}.`);
