// Recorta UM cartão de figura em PNG. Quem decide o que recortar é
// `scripts/renderizar_figura.py`; aqui só se abre o navegador e se tira o pedaço.
//
// A divisão é a mesma de `_layout_dump.js` e `_texto_visivel.js`: o navegador mede e recorta, o
// Python decide. Ele recebe um JSON com `{largura, pedidos: [{id, pagina, seletor, saida}]}`,
// reusa a mesma instância para todos os pedidos (abrir o Chromium é o que custa) e devolve 0 só se
// todos saíram.
//
// Uso: node scripts/_recortar_figura.js '{"largura":1280,"pedidos":[…]}'
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

let PEDIDO;
try { PEDIDO = JSON.parse(process.argv[2] || "{}"); }
catch (e) { console.error("JSON inválido no argumento"); process.exit(2); }
const LARGURA = PEDIDO.largura || 1280;
const PEDIDOS = PEDIDO.pedidos || [];
if (!PEDIDOS.length) { console.error("nenhum pedido"); process.exit(2); }

(async () => {
  await new Promise(r => srv.listen(0, "127.0.0.1", r));
  const base = `http://127.0.0.1:${srv.address().port}`;
  const b = await chromium.launch();
  const ctx = await b.newContext({
    viewport: { width: LARGURA, height: LARGURA === 1280 ? 900 : 844 },
    deviceScaleFactor: 2,   // a editoria lê legenda nesta imagem; 1× deixa o versalete ilegível
  });
  let falhas = 0;
  let paginaAberta = null;
  const pg = await ctx.newPage();

  for (const p of PEDIDOS) {
    if (paginaAberta !== p.pagina) {
      await pg.goto(`${base}/${p.pagina}`, { waitUntil: "networkidle" });
      // O dado chega por fetch e preenche os cartões. Sem a espera, a imagem sai com o travessão
      // de espera no lugar do número — e a editoria revisaria uma figura que não existe.
      await pg.waitForTimeout(2500);
      // `details` abertos: "Ver em lista" é parte do cartão, e o que fica escondido na revisão
      // volta como surpresa depois de publicado.
      await pg.evaluate(() => document.querySelectorAll("details").forEach(d => (d.open = true)));
      await pg.waitForTimeout(400);
      paginaAberta = p.pagina;
    }
    const alvo = await pg.$(p.seletor);
    if (!alvo) {
      console.error(`  ✗ ${p.id}: não achei o cartão (${p.seletor})`);
      falhas += 1; continue;
    }
    await alvo.scrollIntoViewIfNeeded();
    await pg.waitForTimeout(250);
    fs.mkdirSync(path.dirname(p.saida), { recursive: true });
    await alvo.screenshot({ path: p.saida });
    const kb = Math.round(fs.statSync(p.saida).size / 1024);
    console.log(`  ✓ ${p.id} → ${path.relative(RAIZ, p.saida).replace(/\\/g, "/")} (${kb} kB)`);
  }

  await ctx.close(); await b.close(); srv.close();
  if (falhas) { console.error(`✗ ${falhas} figura(s) não saíram`); process.exit(1); }
  console.log(`✓ ${PEDIDOS.length} figura(s) a ${LARGURA} px`);
})().catch(e => { console.error(e); process.exit(1); });
