#!/usr/bin/env node
/* Portão de SEO (07/09/2026): título único (≤ 110 caracteres), descrição única (70–170), canônica no domínio,
 * Open Graph e Twitter completos, JSON-LD válido, um único <h1>, sitemap com todas as páginas, robots com sitemap. */
const fs = require("fs"), path = require("path"); const RAIZ = path.join(__dirname, ".."); const falhas = []; const BASE = "https://monitorelnino.com.br/";
const paginas = fs.readdirSync(RAIZ).filter(f => f.endsWith(".html")); const titulos = new Map(), descs = new Map();
for (const p of paginas) {
  const h = fs.readFileSync(path.join(RAIZ, p), "utf-8");
  const t = (h.match(/<title>([^<]*)<\/title>/) || [])[1] || ""; const d = (h.match(/<meta name="description" content="([^"]*)"/) || [])[1] || "";
  if (!t || t.length > 110) falhas.push(`${p}: título ausente ou > 110 caracteres (${t.length})`);
  if (d.length < 70 || d.length > 170) falhas.push(`${p}: descrição fora de 70–170 caracteres (${d.length})`);
  if (titulos.has(t)) falhas.push(`${p}: título repetido de ${titulos.get(t)}`); titulos.set(t, p);
  if (descs.has(d)) falhas.push(`${p}: descrição repetida de ${descs.get(d)}`); descs.set(d, p);
  const can = (h.match(/<link rel="canonical" href="([^"]*)"/) || [])[1] || "";
  if (!can.startsWith(BASE) || !can.endsWith(p === "index.html" ? "/" : p)) falhas.push(`${p}: canônica ausente ou errada (${can})`);
  for (const k of ["og:title", "og:description", "og:url", "og:image", "og:type", "og:locale", "twitter:card", "twitter:title", "twitter:image"]) if (!h.includes(`"${k}"`)) falhas.push(`${p}: falta ${k}`);
  const ld = [...h.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g)];
  if (!ld.length) falhas.push(`${p}: sem JSON-LD`);
  for (const m of ld) { try { const j = JSON.parse(m[1]); const arr = Array.isArray(j) ? j : [j]; if (!arr.every(x => x["@context"] && x["@type"] && x.url)) falhas.push(`${p}: JSON-LD sem @context/@type/url`); } catch (e) { falhas.push(`${p}: JSON-LD inválido — ${e.message.slice(0, 60)}`); } }
  const h1 = (h.match(/<h1[\s>]/g) || []).length; if (h1 !== 1) falhas.push(`${p}: ${h1} <h1> (deve ser 1)`);
  if (!/<html lang="pt-BR">/.test(h)) falhas.push(`${p}: sem lang="pt-BR"`);
}
const sm = fs.existsSync(path.join(RAIZ, "sitemap.xml")) ? fs.readFileSync(path.join(RAIZ, "sitemap.xml"), "utf-8") : "";
for (const p of paginas) if (p !== "obrigado.html" && !sm.includes(BASE + (p === "index.html" ? "" : p) + "<")) falhas.push(`sitemap.xml sem ${p}`);
const rb = fs.existsSync(path.join(RAIZ, "robots.txt")) ? fs.readFileSync(path.join(RAIZ, "robots.txt"), "utf-8") : "";
if (!/Sitemap: https:\/\/monitorelnino\.com\.br\/sitemap\.xml/.test(rb)) falhas.push("robots.txt sem a linha Sitemap");
if (!fs.existsSync(path.join(RAIZ, "assets", "social", "card-monitor-el-nino.png"))) falhas.push("cartão social ausente");
if (falhas.length) { console.log("✗ SEO:"); falhas.forEach(f => console.log("   -", f)); process.exit(1); }
console.log(`✓ SEO OK — ${paginas.length} páginas com título e descrição únicos, canônica, Open Graph, Twitter, JSON-LD, um h1; sitemap e robots.`);
