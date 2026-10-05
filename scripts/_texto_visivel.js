// Despeja o TEXTO VISÍVEL de uma página, em ordem, para comparar antes e depois de uma mudança.
//
// Item 1.4 do handover do catálogo de conteúdo (05/10/2026): "migração sem mudar uma vírgula —
// para cada página, antes e depois, renderizar em 1280 e 390 px e comparar texto visível e
// capturas; diferença = o PR não fecha". Este arquivo é a metade do texto; as capturas saem do
// renderizador de figura.
//
// Ele NÃO julga: despeja. Quem compara é `scripts/verificar_migracao_de_conteudo.py`, que lê dois
// despejos e diz onde diferem. A divisão é a mesma do `_layout_dump.js`: o navegador mede, o
// Python decide.
//
// Por que texto VISÍVEL e não o HTML: o catálogo muda de onde o texto vem, não o que ele é. O HTML
// muda de propósito (ganha `data-conteudo`), então comparar HTML daria diferença em toda linha
// migrada e não provaria nada. O que tem de ficar idêntico é o que o leitor lê.
//
// Uso: node scripts/_texto_visivel.js <pagina.html> [saida.json]
const { chromium } = require("playwright");
const http = require("http"), fs = require("fs"), path = require("path");

const RAIZ = path.join(__dirname, "..");
const MIME = { ".html": "text/html; charset=utf-8", ".js": "text/javascript", ".css": "text/css",
  ".json": "application/json", ".svg": "image/svg+xml", ".png": "image/png", ".woff2": "font/woff2",
  ".csv": "text/csv", ".xml": "application/xml", ".pdf": "application/pdf", ".jsonl": "text/plain" };

const srv = http.createServer((req, res) => {
  const u = decodeURIComponent(req.url.split("?")[0]);
  const f = path.join(RAIZ, u === "/" ? "index.html" : u);
  if (!f.startsWith(RAIZ) || !fs.existsSync(f) || fs.statSync(f).isDirectory()) {
    res.writeHead(404); return res.end();
  }
  res.writeHead(200, { "Content-Type": MIME[path.extname(f)] || "application/octet-stream" });
  fs.createReadStream(f).pipe(res);
});

const PAGINA = process.argv[2];
const SAIDA = process.argv[3] || null;
if (!PAGINA) { console.error("uso: node scripts/_texto_visivel.js <pagina.html> [saida.json]"); process.exit(2); }

(async () => {
  await new Promise(r => srv.listen(0, "127.0.0.1", r));
  const base = `http://127.0.0.1:${srv.address().port}`;
  const b = await chromium.launch();
  const fora = { pagina: PAGINA, larguras: {} };

  for (const largura of [1280, 390]) {
    const ctx = await b.newContext({
      viewport: { width: largura, height: largura === 1280 ? 900 : 844 },
      deviceScaleFactor: 1,
    });
    const pg = await ctx.newPage();
    await pg.goto(`${base}/${PAGINA}`, { waitUntil: "networkidle" });
    // O dado chega por fetch e preenche os cartões; sem esta espera o despejo pegaria o
    // travessão de espera no lugar do número, e a comparação "antes x depois" ficaria instável
    // por motivo que não é a migração.
    await pg.waitForTimeout(2500);
    // Abre todo `details`: o texto dentro de "Ver em lista" é texto público e tem de ser comparado.
    await pg.evaluate(() => document.querySelectorAll("details").forEach(d => (d.open = true)));
    await pg.waitForTimeout(300);

    fora.larguras[largura] = await pg.evaluate(() => {
      const visivel = (el) => {
        const s = getComputedStyle(el);
        if (s.display === "none" || s.visibility === "hidden" || Number(s.opacity) === 0) return false;
        if (el.closest("[hidden]")) return false;
        return true;
      };
      const saida = [];
      const anda = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
      for (let n = anda.nextNode(); n; n = anda.nextNode()) {
        const t = (n.textContent || "").replace(/\s+/g, " ").trim();
        if (!t) continue;
        const pai = n.parentElement;
        if (!pai || ["SCRIPT", "STYLE", "TEMPLATE"].includes(pai.tagName)) continue;
        if (!visivel(pai)) continue;
        saida.push(t);
      }
      return saida;
    });
    await ctx.close();
  }

  await b.close(); srv.close();
  const txt = JSON.stringify(fora, null, 1) + "\n";
  if (SAIDA) { fs.writeFileSync(SAIDA, txt, { encoding: "utf8" }); console.error(`despejo em ${SAIDA}`); }
  else process.stdout.write(txt);
})().catch(e => { console.error(e); process.exit(1); });
