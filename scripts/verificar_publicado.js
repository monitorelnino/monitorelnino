#!/usr/bin/env node
/* verificar_publicado.js — o site que está NO AR é o que foi mesclado? (14/09/2026, exercício de publicação)
 * Roda contra um endereço real (padrão: https://monitorelnino.com.br), depois de um deploy:
 *  1. todas as páginas do sitemap.xml respondem 200 em HTTPS, com CSP e (no ensaio) X-Robots-Tag: noindex;
 *  2. cada arquivo do docs/MANIFEST_SHA256.txt servido tem o MESMO sha256 do manifesto (prova de integridade
 *     do deploy: nada a mais, nada trocado); PDFs incluídos;
 *  3. canário de conteúdo: data/meta.json tem atualizado_em e a média de data/indice.json bate com o data-alvo
 *     do medidor em index.html.
 * Uso: node scripts/verificar_publicado.js [--base URL] [--ensaio|--lancamento]
 *   --ensaio     exige noindex (cabeçalho ou robots.txt bloqueando)  · --lancamento exige que NÃO haja noindex
 * Só lê; imprime ✓/✗ e sai com 1 se algo falhar. Sem dependências além do Node 20.
 */
const fs = require("fs"), path = require("path"), crypto = require("crypto");
const raiz = path.resolve(__dirname, "..");
const args = process.argv.slice(2);
const base = (args.includes("--base") ? args[args.indexOf("--base") + 1] : "https://monitorelnino.com.br").replace(/\/$/, "");
const modo = args.includes("--lancamento") ? "lancamento" : "ensaio";
const falhas = []; const teste = (n, ok, extra = "") => { console.log((ok ? "  ✓ " : "  ✗ ") + n + (extra ? " · " + extra : "")); if (!ok) falhas.push(n); };
const sha = b => crypto.createHash("sha256").update(b).digest("hex");
async function pegar(rel) {
  const r = await fetch(base + "/" + rel.replace(/^\//, ""), { redirect: "manual", headers: { "User-Agent": "Monitor El Nino Brasil (verificar_publicado)" } });
  return { status: r.status, headers: r.headers, corpo: Buffer.from(await r.arrayBuffer()) };
}
(async () => {
  console.log(`verificar_publicado · base=${base} · modo=${modo}`);
  // 1. páginas do sitemap
  const sm = fs.readFileSync(path.join(raiz, "sitemap.xml"), "utf8");
  const paginas = [...sm.matchAll(/<loc>([^<]+)<\/loc>/g)].map(m => m[1].replace(/^https?:\/\/[^/]+\/?/, "") || "index.html");
  let csp = 0, noindex = 0;
  for (const p of paginas) {
    const r = await pegar(p);
    teste(`página ${p || "/"}: 200`, r.status === 200, String(r.status));
    if (r.headers.get("content-security-policy")) csp++;
    if (/noindex/i.test(r.headers.get("x-robots-tag") || "")) noindex++;
  }
  teste("CSP presente em todas as páginas", csp === paginas.length, `${csp}/${paginas.length}`);
  const robots = await pegar("robots.txt");
  const robotsBloqueia = /Disallow:\s*\/\s*$/m.test(robots.corpo.toString("utf8"));
  if (modo === "ensaio") teste("ensaio: noindex em todas as páginas e robots.txt bloqueando", noindex === paginas.length && robotsBloqueia, `noindex ${noindex}/${paginas.length} · robots ${robotsBloqueia}`);
  else teste("lançamento: sem noindex e robots.txt liberando", noindex === 0 && !robotsBloqueia, `noindex ${noindex} · robots bloqueia ${robotsBloqueia}`);
  // 2. integridade: cada arquivo do manifesto, servido == mesclado
  const linhas = fs.readFileSync(path.join(raiz, "docs", "MANIFEST_SHA256.txt"), "utf8").split("\n").filter(l => l && !l.startsWith("#"));
  let ok = 0, dif = [], falt = [];
  for (const l of linhas) {
    const m = l.match(/^([0-9a-f]{64})\s+\*?(.+)$/); if (!m) continue;
    const [, h, arq] = m;
    // só o que o navegador de fato pede: páginas, dados, PDFs, feeds, código e assets do site — não código de robô nem documentação-fonte
    if (arq.startsWith(".") || arq.startsWith(".github/") || arq.startsWith("scripts/") || arq.startsWith("docs/") || !/\.(html|pdf|json|csv|xml|txt|js|css|svg|png|jpg|webp|woff2?|ico|webmanifest)$/i.test(arq) || /^(package(-lock)?\.json|requirements\.txt|LEIA-ME\.md)$/.test(arq)) continue;
    const r = await pegar(arq);
    if (r.status !== 200) { falt.push(`${arq} (${r.status})`); continue; }
    if (arq === "robots.txt" && modo === "ensaio") { ok++; continue; }   // substituído de propósito no ensaio
    if (sha(r.corpo) === h) ok++; else dif.push(arq);
  }
  teste(`integridade: ${ok} arquivo(s) servidos iguais ao manifesto`, dif.length === 0 && falt.length === 0, (dif.length ? "diferentes: " + dif.slice(0, 8).join(", ") : "") + (falt.length ? " · ausentes: " + falt.slice(0, 8).join(", ") : ""));
  // 3. canário de conteúdo
  try {
    const meta = JSON.parse((await pegar("data/meta.json")).corpo.toString("utf8"));
    teste("meta.json com atualizado_em", /^\d{2}\/\d{2}\/\d{4}$/.test(meta.atualizado_em || ""), meta.atualizado_em);
    const idx = JSON.parse((await pegar("data/indice.json")).corpo.toString("utf8"));
    const ufs = Object.keys(idx).filter(k => k.length === 2); const media = Math.round(ufs.reduce((a, u) => a + idx[u].total, 0) / ufs.length * 10) / 10;
    const home = (await pegar("index.html")).corpo.toString("utf8"); const alvo = parseFloat((home.match(/data-alvo="([\d.]+)"/) || [])[1]);
    teste("canário: média do índice servida = medidor da home", Math.abs(media - alvo) < 0.06, `${media} × ${alvo}`);
  } catch (e) { teste("canário de conteúdo", false, e.message); }
  console.log(falhas.length ? `\n✗ PUBLICADO: ${falhas.length} verificação(ões) falharam.` : "\n✓ PUBLICADO OK — páginas no ar, cabeçalhos certos, arquivos idênticos ao manifesto, canário confere.");
  process.exit(falhas.length ? 1 : 0);
})().catch(e => { console.error("✗ erro:", e.message); process.exit(1); });
