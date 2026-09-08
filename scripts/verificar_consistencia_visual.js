#!/usr/bin/env node
/* Portão de consistência visual (07/09/2026, auditoria da editoria): elementos equivalentes têm o MESMO estilo
 * computado em todo o site, em três larguras (1366 · 900 · 390). Mede num Chromium real (Playwright), com os
 * dados servidos localmente, e falha quando:
 *   (1) uma família de elementos equivalentes (h1, h2, h3, corpo, legenda, crédito, subtítulo de figura…) tem mais
 *       de UMA combinação de font-size · font-weight · line-height · letter-spacing · font-family · margens;
 *   (2) algum font-size computado está fora da escala de tokens.css (12 · 14 · 16 · 18 · 22 · 28 · 36 · 48);
 *   (3) figuras lado a lado (mesma linha da grade) têm altura ou largura diferentes, ou título/legenda/crédito
 *       em posição vertical diferente relativa ao topo do cartão;
 *   (4) algum crédito de figura foge do formato "Fonte: … · Atualização: dd/mm/aaaa" (ou "sem coleta até o corte");
 *   (5) numeração visível de figura não começa em 1 ou não é sequencial;
 *   (6) há rolagem horizontal.
 * Uso: node scripts/verificar_consistencia_visual.js [--relatorio]  (imprime o inventário completo). */
const { chromium } = require("playwright"); const http = require("http"), fs = require("fs"), path = require("path");
const RAIZ = path.join(__dirname, "..");
const PAGINAS = fs.readdirSync(RAIZ).filter(f => f.endsWith(".html")).sort();
const LARGURAS = [1366, 900, 390];
const ESCALA = new Set([12, 14, 16, 18, 22, 28, 36, 48]);
const RELATORIO = process.argv.includes("--relatorio");
// famílias de elementos equivalentes (seletor → nome). Cada família deve ter UM só estilo computado por largura.
const FAMILIAS = {
  "h1 (página)": "main h1",
  "h2 (seção)": "main h2:not(.ficha h2)",
  "h3 (título de figura/cartão)": ".figura-titulo",
  "subtítulo de figura": ".figura-sub",
  "legenda de figura": ".map-legend",
  "item de legenda": ".map-legend > span:not(.escala)",
  "crédito de figura": ".fonte-figura",
  "número de figura": ".figura-num",
  "corpo (parágrafo de painel)": ".panel > p:not(.hint):not(.note):not(.selo):not(.kicker):not(.legenda-regioes)",
  "apoio (.hint)": "p.hint",
  "nota (.note)": "p.note, .note",
  "versalete (.selo/.kicker)": ".selo, .kicker",
  "cabeçalho de tabela": ".mun-table thead th",
  "célula de tabela": ".mun-table td",
  "painel": ".panel",
  "figura": ".figura",
  "cartão de texto": ".cartao",
  "navegação": ".mainnav a, .mainnav span.ativa",
  "rodapé": "footer.site-footer",
};
const PROPS = ["fontSize", "fontWeight", "lineHeight", "letterSpacing", "fontFamily", "marginTop", "marginBottom", "paddingTop", "paddingBottom", "paddingLeft", "paddingRight", "textTransform"];
// prosa: o espaçamento é do contêiner (último parágrafo sem margem, utilitários de ritmo), por isso compara só a tipografia
const SO_TIPOGRAFIA = new Set(["corpo (parágrafo de painel)", "apoio (.hint)", "nota (.note)", "versalete (.selo/.kicker)", "célula de tabela"]);
const PROPS_TIPO = ["fontSize", "fontWeight", "lineHeight", "letterSpacing", "fontFamily", "textTransform"];
const MIME = { ".html": "text/html; charset=utf-8", ".js": "text/javascript", ".css": "text/css", ".json": "application/json", ".svg": "image/svg+xml", ".xml": "application/xml", ".png": "image/png", ".pdf": "application/pdf", ".md": "text/markdown" };
const srv = http.createServer((req, res) => { const u = decodeURIComponent(req.url.split("?")[0]); const f = path.join(RAIZ, u === "/" ? "index.html" : u);
  if (!f.startsWith(RAIZ) || !fs.existsSync(f) || fs.statSync(f).isDirectory()) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { "Content-Type": MIME[path.extname(f)] || "application/octet-stream" }); fs.createReadStream(f).pipe(res); });

(async () => {
  await new Promise(r => srv.listen(0, "127.0.0.1", r)); const porta = srv.address().port; const falhas = []; const inventario = {};
  const b = await chromium.launch();
  for (const largura of LARGURAS) {
    const ctx = await b.newContext({ viewport: { width: largura, height: 900 }, deviceScaleFactor: 1 });
    const porFamilia = {};   // família → { assinatura → [página…] }
    const tamanhos = {};     // font-size computado → páginas
    for (const p of PAGINAS) {
      const page = await ctx.newPage();
      await page.route(/vlibras\.gov\.br|fonts\.g|netlify/, r => r.abort());
      try { await page.goto(`http://127.0.0.1:${porta}/${p}`, { waitUntil: "networkidle", timeout: 30000 }); } catch (e) { falhas.push(`${p}@${largura}: não carregou`); await page.close(); continue; }
      await page.waitForTimeout(900);
      const r = await page.evaluate(({ FAMILIAS, PROPS, SO_TIPOGRAFIA, PROPS_TIPO }) => {
        const vis = el => { const cs = getComputedStyle(el); if (cs.display === "none" || cs.visibility === "hidden") return false; const det = el.closest("details"); if (det && !det.open && !el.closest("summary")) return false; if (el.closest("[hidden]")) return false; return el.getClientRects().length > 0; };
        const out = { familias: {}, tamanhos: {}, figuras: [], creditos: [], numeros: [], scroll: document.documentElement.scrollWidth > innerWidth + 1 };
        for (const [nome, sel] of Object.entries(FAMILIAS)) {
          const els = [...document.querySelectorAll(sel)].filter(vis);
          const props = SO_TIPOGRAFIA.includes(nome) ? PROPS_TIPO : PROPS;
          out.familias[nome] = els.map(el => { const cs = getComputedStyle(el); const o = {}; for (const k of props) o[k] = cs[k]; o.fontFamily = o.fontFamily.split(",")[0].replace(/"/g, ""); return { assinatura: JSON.stringify(o), texto: (el.textContent || "").trim().replace(/\s+/g, " ").slice(0, 40) }; });
        }
        document.querySelectorAll("body *").forEach(el => { if (!vis(el)) return; if (el.closest("svg, canvas, script, style")) return; const fs = parseFloat(getComputedStyle(el).fontSize); if (!isNaN(fs)) { const k = String(fs); out.tamanhos[k] = out.tamanhos[k] || (el.tagName.toLowerCase() + (el.className && typeof el.className === "string" ? "." + el.className.split(" ")[0] : "")); } });
        document.querySelectorAll(".figura").forEach(f => { if (!vis(f)) return; const r = f.getBoundingClientRect(); const top = r.top + scrollY; const rel = s => { const e = f.querySelector(s); if (!e || !vis(e)) return null; return Math.round(e.getBoundingClientRect().top + scrollY - top); };
          out.figuras.push({ id: f.id || (f.querySelector(".figura-titulo") || {}).textContent, top: Math.round(top), left: Math.round(r.left), w: Math.round(r.width), h: Math.round(r.height), titulo: rel(".figura-titulo"), sub: rel(".figura-sub"), midia: rel(".figura-midia"), largo: f.classList.contains("figura--largo") }); });
        document.querySelectorAll(".fonte-figura").forEach(c => { if (vis(c)) out.creditos.push((c.textContent || "").trim().replace(/\s+/g, " ")); });
        document.querySelectorAll(".figura").forEach(f => { if (!vis(f)) return; const n = f.querySelector(".figura-num"); out.numeros.push(n ? n.textContent.trim() : "(sem número)"); });
        out.secoes = document.body.classList.contains("pagina-dados") ? [...document.querySelectorAll("main > .panel > h2:first-child")].map(h => h.textContent.trim()) : [];
        return out;
      }, { FAMILIAS, PROPS, SO_TIPOGRAFIA: [...SO_TIPOGRAFIA], PROPS_TIPO });
      if (r.scroll) falhas.push(`${p}@${largura}: rolagem horizontal`);
      for (const [nome, itens] of Object.entries(r.familias)) { porFamilia[nome] = porFamilia[nome] || {}; for (const it of itens) { (porFamilia[nome][it.assinatura] = porFamilia[nome][it.assinatura] || []).push(p + " › " + it.texto); } }
      for (const [t, ex] of Object.entries(r.tamanhos)) (tamanhos[t] = tamanhos[t] || new Set()).add(p + " › " + ex);
      // (3) lado a lado: figuras com o mesmo top (±4px) devem ter mesma largura/altura e mesma posição interna
      const linhas = {}; for (const f of r.figuras) { const k = Math.round(f.top / 8); (linhas[k] = linhas[k] || []).push(f); }
      for (const grupo of Object.values(linhas)) { if (grupo.length < 2) continue;
        const ws = new Set(grupo.map(g => g.w)), hs = new Set(grupo.map(g => g.h));
        if (ws.size > 1) falhas.push(`${p}@${largura}: figuras lado a lado com larguras diferentes: ${grupo.map(g => g.id + "=" + g.w).join(", ")}`);
        if (hs.size > 1) falhas.push(`${p}@${largura}: figuras lado a lado com alturas diferentes: ${grupo.map(g => g.id + "=" + g.h).join(", ")}`);
        for (const k of ["titulo", "sub", "midia"]) { const vs = new Set(grupo.map(g => g[k]).filter(v => v != null)); if (vs.size > 1) falhas.push(`${p}@${largura}: ${k} em posição vertical diferente entre figuras lado a lado: ${grupo.map(g => g.id + "=" + g[k]).join(", ")}`); }
      }
      // (4) crédito no formato único
      for (const c of r.creditos) if (!/^Fonte: .+ · Atualização: (\d{2}\/\d{2}\/\d{4}|sem coleta até o corte)$/.test(c)) falhas.push(`${p}@${largura}: crédito fora do formato "Fonte: … · Atualização: dd/mm/aaaa": "${c.slice(0, 90)}"`);
      // (5) numeração: Figura 1, 2, 3… na ordem do documento
      if (largura === LARGURAS[0]) { r.numeros.forEach((n, i) => { const m = n.match(/^Figura (\d+)$/); if (!m || +m[1] !== i + 1) falhas.push(`${p}: numeração de figura fora de sequência (esperado "Figura ${i + 1}", há "${n}")`); });
        r.secoes.forEach((t, i) => { if (!t.startsWith((i + 1) + " · ")) falhas.push(`${p}: numeração de seção fora de sequência (esperado "${i + 1} · …", há "${t.slice(0, 40)}")`); }); }
      if (RELATORIO && largura === LARGURAS[0]) inventario[p] = { figuras: r.figuras.length, creditos: r.creditos.length };
      await page.close();
    }
    for (const [nome, ass] of Object.entries(porFamilia)) { const chaves = Object.keys(ass); if (chaves.length > 1) {
      falhas.push(`@${largura} · família "${nome}" com ${chaves.length} estilos diferentes:`); chaves.forEach(k => { const o = JSON.parse(k); falhas.push(`      ${o.fontFamily} ${o.fontSize}/${o.lineHeight} ${o.fontWeight} ls=${o.letterSpacing}${o.marginTop != null ? ` m=${o.marginTop}/${o.marginBottom} p=${o.paddingTop}/${o.paddingRight}/${o.paddingBottom}/${o.paddingLeft}` : ""} ← ${ass[k].length}× (ex.: ${ass[k].slice(0, 2).join(" | ")})`); }); } }
    const fora = Object.entries(tamanhos).filter(([t]) => !ESCALA.has(+t));
    if (fora.length) falhas.push(`@${largura} · font-size computado fora da escala: ` + fora.map(([t, ex]) => `${t}px (${[...ex][0]})`).join("; "));
    if (RELATORIO) console.log(`@${largura}: tamanhos computados em uso: ${Object.keys(tamanhos).map(Number).sort((a, b) => a - b).join(", ")}`);
    await ctx.close();
  }
  await b.close(); srv.close();
  if (RELATORIO) console.log(JSON.stringify(inventario));
  if (falhas.length) { console.log("✗ CONSISTÊNCIA VISUAL: " + falhas.length + " problema(s):"); falhas.forEach(f => console.log("   - " + f)); process.exit(1); }
  console.log(`✓ CONSISTÊNCIA VISUAL OK — ${PAGINAS.length} páginas × ${LARGURAS.length} larguras: famílias equivalentes com um só estilo, tamanhos na escala, figuras alinhadas, créditos e numeração no padrão.`);
})();
