#!/usr/bin/env node
/**
 * verificar_publicado.js — o site PUBLICADO, contra o domínio real (14/09/2026).
 * Os 18 portões provam o conteúdo antes do merge; este prova o deploy depois:
 *   1. toda página do sitemap.xml responde 200 em HTTPS;
 *   2. cabeçalhos: CSP, HSTS, nosniff presentes; X-Robots-Tag noindex presente no ENSAIO
 *      (--esperar-noindex) e AUSENTE no lançamento (--esperar-index);
 *   3. integridade: o SHA-256 de cada arquivo servido = docs/MANIFEST_SHA256.txt do repositório
 *      (amostra: todas as páginas, todos os data/*.json referenciados no manifesto, PDFs, sitemap);
 *   4. canário de conteúdo: data/meta.json com data de edição; data/indice.json com 27 UFs.
 * Uso: node scripts/verificar_publicado.js --base https://monitorelnino.com.br [--esperar-noindex|--esperar-index] [--amostra N]
 * Sai com 1 se algo falhar. Sem dependências além do Node 20 (fetch nativo).
 */
const fs = require("fs"), path = require("path"), crypto = require("crypto");
const raiz = path.resolve(__dirname, "..");
const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? (args[i + 1] || true) : d; };
const BASE = String(opt("--base", "https://monitorelnino.com.br")).replace(/\/$/, "");
const ESPERAR_NOINDEX = args.includes("--esperar-noindex");
const ESPERAR_INDEX = args.includes("--esperar-index");
const AMOSTRA = parseInt(opt("--amostra", "400"), 10);
const falhas = []; const ok = (nome, cond, extra = "") => { console.log((cond ? "  ✓ " : "  ✗ ") + nome + (extra ? " · " + extra : "")); if (!cond) falhas.push(nome); };

async function get(url, tentativas = 3) {
  for (let i = 0; i < tentativas; i++) {
    try {
      const r = await fetch(url, { redirect: "manual", headers: { "User-Agent": "Monitor El Nino Brasil (verificar_publicado)" } });
      const buf = Buffer.from(await r.arrayBuffer());
      return { status: r.status, headers: r.headers, buf };
    } catch (e) { if (i === tentativas - 1) return { status: 0, headers: new Map(), buf: Buffer.alloc(0), erro: e.message }; await new Promise(r => setTimeout(r, 1500 * (i + 1))); }
  }
}

(async () => {
  console.log(`verificar_publicado · base=${BASE} · modo=${ESPERAR_NOINDEX ? "ensaio (noindex)" : ESPERAR_INDEX ? "lançamento (index)" : "sem exigência de robots"}`);
  // 1. sitemap
  const sm = await get(`${BASE}/sitemap.xml`);
  ok("sitemap.xml responde 200", sm.status === 200, `status=${sm.status}`);
  const locs = [...sm.buf.toString("utf8").matchAll(/<loc>([^<]+)<\/loc>/g)].map(m => m[1].trim());
  ok("sitemap lista as páginas (≥ 11)", locs.length >= 11, `${locs.length} entradas`);
  const paginas = locs.filter(u => /\/$|\.html$/.test(u));
  for (const u of paginas) {
    const alvo = u.replace(/^https?:\/\/[^/]+/, BASE);
    const r = await get(alvo);
    const h = r.headers;
    ok(`200 · ${alvo.replace(BASE, "") || "/"}`, r.status === 200, `status=${r.status}${r.erro ? " " + r.erro : ""}`);
    if (r.status !== 200) continue;
    const csp = h.get("content-security-policy") || "", hsts = h.get("strict-transport-security") || "", nosniff = h.get("x-content-type-options") || "";
    ok(`cabeçalhos · ${alvo.replace(BASE, "") || "/"}`, csp.includes("default-src 'self'") && hsts.includes("max-age") && nosniff === "nosniff");
    const robots = (h.get("x-robots-tag") || "").toLowerCase();
    if (ESPERAR_NOINDEX) ok(`noindex presente · ${alvo.replace(BASE, "") || "/"}`, robots.includes("noindex"), `x-robots-tag=${robots || "(vazio)"}`);
    if (ESPERAR_INDEX) ok(`noindex AUSENTE · ${alvo.replace(BASE, "") || "/"}`, !robots.includes("noindex"), `x-robots-tag=${robots || "(vazio)"}`);
    const html = r.buf.toString("utf8");
    ok(`sem mixed content · ${alvo.replace(BASE, "") || "/"}`, !/(src|href)=["']http:\/\//.test(html));
  }
  // 2. robots.txt coerente com o modo
  const rb = await get(`${BASE}/robots.txt`);
  if (ESPERAR_NOINDEX) ok("robots.txt bloqueia tudo (ensaio)", rb.status === 200 && /Disallow:\s*\/\s*$/m.test(rb.buf.toString()));
  if (ESPERAR_INDEX) ok("robots.txt do site (lançamento), com sitemap", rb.status === 200 && /Sitemap:/i.test(rb.buf.toString()) && !/^Disallow:\s*\/\s*$/m.test(rb.buf.toString()));
  // 3. integridade contra o manifesto do repositório
  const manifesto = path.join(raiz, "docs", "MANIFEST_SHA256.txt");
  if (fs.existsSync(manifesto)) {
    const linhas = fs.readFileSync(manifesto, "utf8").split("\n").map(l => l.trim()).filter(Boolean);
    const entradas = linhas.map(l => { const m = l.match(/^([0-9a-f]{64})\s+\*?(.+)$/); return m ? { hash: m[1], arq: m[2].replace(/^\.\//, "") } : null; }).filter(Boolean);
    // robots.txt fica de fora no ensaio (é trocado de propósito); .github, scripts, docs e node não são servidos ao público
    // fora da amostra: o que o Netlify não serve (dotfiles, netlify.toml) e o que não é do site público
    const servidos = entradas.filter(e => !/^(\.github|scripts|docs|node_modules|tests?|leituras_qd)\//.test(e.arq) && !/^\./.test(e.arq) && !/^(robots\.txt|netlify\.toml|package.*\.json|requirements\.txt|.*\.py|README\.md|CHANGELOG\.md|METODOLOGIA\.md|LICENSE.*)$/.test(e.arq));
    const prioridade = servidos.filter(e => /\.(html|pdf|xml)$|^data\/(meta|indice|sinais_risco|saude_sinais|monitor_saude)\.json$|^data\/saude_desfechos\/(serie_painel|dda_serie|chik_serie_painel|srag_serie)\.json$|^assets\/js\/|^assets\/.*\.css$/.test(e.arq));
    const resto = servidos.filter(e => !prioridade.includes(e));
    const amostra = prioridade.concat(resto.slice(0, Math.max(0, AMOSTRA - prioridade.length)));
    let iguais = 0, prettyUrls = 0, diferentes = [], ausentes = [];
    for (const e of amostra) {
      const r = await get(`${BASE}/${e.arq.split("/").map(encodeURIComponent).join("/")}`);
      if (r.status !== 200) { ausentes.push(`${e.arq} (${r.status})`); continue; }
      let h = crypto.createHash("sha256").update(r.buf).digest("hex");
      if (h !== e.hash && /\.html$/.test(e.arq)) {
        // 14/09/2026 (provado no 1º ensaio): o "Pretty URLs" do Netlify reescreve href="x.html" → href='/x' e
        // href="index.html" → href='/'. Desfazemos SÓ essa reescrita conhecida e comparamos de novo — qualquer
        // outra diferença continua sendo divergência real.
        const norm = r.buf.toString("utf8").replace(/href='\/'/g, 'href="index.html"').replace(/href='\/([a-z0-9-]+)'/g, 'href="$1.html"');
        h = crypto.createHash("sha256").update(Buffer.from(norm, "utf8")).digest("hex");
        if (h === e.hash) prettyUrls++;
      }
      if (h === e.hash) { iguais++; continue; }
      diferentes.push(e.arq);
      // prova da divergência: tamanho e primeiro trecho diferente (para distinguir pós-processamento do Netlify de conteúdo trocado)
      const local = fs.existsSync(path.join(raiz, e.arq)) ? fs.readFileSync(path.join(raiz, e.arq)) : null;
      if (local) {
        let i = 0; while (i < local.length && i < r.buf.length && local[i] === r.buf[i]) i++;
        console.log(`    · ${e.arq}: repositório=${local.length} B · servido=${r.buf.length} B · diverge no byte ${i}`);
        console.log(`      repo:    ${JSON.stringify(local.toString("utf8", Math.max(0, i - 60), i + 160))}`);
        console.log(`      servido: ${JSON.stringify(r.buf.toString("utf8", Math.max(0, i - 60), i + 160))}`);
      }
    }
    ok(`integridade: ${iguais}/${amostra.length} arquivo(s) servidos batem com o manifesto` + (prettyUrls ? ` (${prettyUrls} HTML só com a reescrita "Pretty URLs" do Netlify)` : ""), diferentes.length === 0 && ausentes.length === 0,
       (diferentes.length ? "diferentes: " + diferentes.slice(0, 8).join(", ") : "") + (ausentes.length ? " · ausentes: " + ausentes.slice(0, 8).join(", ") : ""));
  } else ok("manifesto presente no repositório", false);
  // 4. canários de conteúdo
  const meta = await get(`${BASE}/data/meta.json`);
  let m = null; try { m = JSON.parse(meta.buf.toString()); } catch (e) {}
  ok("data/meta.json com data de edição (dd/mm/aaaa)", !!m && /^\d{2}\/\d{2}\/\d{4}$/.test(m.atualizado_em || ""), m ? `atualizado_em=${m.atualizado_em} corte=${m.corte}` : `status=${meta.status}`);
  const idx = await get(`${BASE}/data/indice.json`);
  let I = null; try { I = JSON.parse(idx.buf.toString()); } catch (e) {}
  ok("data/indice.json com 27 UFs", !!I && Object.keys(I).filter(k => k.length === 2).length === 27);
  console.log(falhas.length ? `\n✗ PUBLICADO: ${falhas.length} verificação(ões) falharam.` : "\n✓ PUBLICADO OK — páginas, cabeçalhos, robots no modo esperado, integridade contra o manifesto e canários.");
  process.exit(falhas.length ? 1 : 0);
})();
