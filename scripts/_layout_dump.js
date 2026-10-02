// Renderizador do portão de layout: serve o site, abre a página em 1280 e 390 px e DESPEJA a forma
// do DOM em JSON. Ele não julga nada — quem julga é scripts/verificar_layout.py, que lê este JSON e
// o compara ao contrato. A divisão é de propósito: a regra de layout é texto legível em
// `layout/contratos/*.json`, e o que precisa de navegador é só a medição.
//
// Uso: node scripts/_layout_dump.js <pagina.html> [saida.json]
const { chromium } = require("playwright");
const http = require("http"), fs = require("fs"), path = require("path");

const RAIZ = path.join(__dirname, "..");
const MIME = { ".html": "text/html; charset=utf-8", ".js": "text/javascript", ".css": "text/css",
  ".json": "application/json", ".svg": "image/svg+xml", ".png": "image/png", ".woff2": "font/woff2",
  ".csv": "text/csv", ".xml": "application/xml", ".pdf": "application/pdf", ".jsonl": "text/plain" };

const srv = http.createServer((req, res) => {
  const u = decodeURIComponent(req.url.split("?")[0]);
  const f = path.join(RAIZ, u === "/" ? "index.html" : u);
  if (!f.startsWith(RAIZ) || !fs.existsSync(f) || fs.statSync(f).isDirectory()) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { "Content-Type": MIME[path.extname(f)] || "application/octet-stream" });
  fs.createReadStream(f).pipe(res);
});

const PAGINA = process.argv[2];
const SAIDA = process.argv[3] || null;
if (!PAGINA) { console.error("uso: node scripts/_layout_dump.js <pagina.html> [saida.json]"); process.exit(2); }

const COLETA = () => {
  const vis = el => {
    const r = el.getBoundingClientRect();
    const cs = getComputedStyle(el);
    return r.width > 1 && r.height > 1 && cs.display !== "none" && cs.visibility !== "hidden";
  };
  const figuras = [...document.querySelectorAll("figure")].map(f => ({
    id: f.id,
    classes: [...f.classList],
    cartao_mapa: f.classList.contains("cartao-mapa"),
    tem_midia: !!f.querySelector("svg, canvas"),
    tem_lista: !!f.querySelector("details, dl, table, .busca-mun"),
    largura: Math.round(f.getBoundingClientRect().width),
    visivel: vis(f),
    pai_grade: (f.parentElement && [...f.parentElement.classList].join(" ")) || "",
  }));
  const grades = [...document.querySelectorAll(".grade-figuras, .grade-numeros")].map(g => ({
    classes: [...g.classList],
    filhos: [...g.children].filter(c => vis(c)).length,
    ids: [...g.children].map(c => c.id || ""),
    largura: Math.round(g.getBoundingClientRect().width),
    colunas: getComputedStyle(g).gridTemplateColumns.split(" ").filter(Boolean).length,
    secao: (() => { let e = g.parentElement; while (e && !e.id) e = e.parentElement; return e ? e.id : ""; })(),
  }));
  const numeros = [...document.querySelectorAll(".cartao-numero")].map(c => ({
    id: c.dataset.cartao || c.id || "",
    valor: ((c.querySelector(".cartao-numero-valor") || {}).textContent || "").trim(),
    rotulo: ((c.querySelector(".cartao-numero-rotulo") || {}).textContent || "").trim(),
    fonte: ((c.querySelector(".cartao-numero-fonte") || {}).textContent || "").trim(),
    valor_id: ((c.querySelector(".cartao-numero-valor span[id]") || c.querySelector(".cartao-numero-valor")) || {}).id || "",
    largura: Math.round(c.getBoundingClientRect().width),
    pai_grade: (c.parentElement && [...c.parentElement.classList].join(" ")) || "",
  }));
  const secoes = [...document.querySelectorAll("main > section, main > .panel")].map(s => ({
    id: s.id,
    classes: [...s.classList],
    h2: ((s.querySelector("h2") || {}).textContent || "").trim(),
    h3: [...s.querySelectorAll("h3")].map(h => (h.textContent || "").trim()).filter(t => t && t.length < 60),
    // Cartao de texto (`.cartao` com id, como as duas listas de "Como o dinheiro chega") nao e
    // <figure> e nao aparece no despejo de figuras. O contrato precisa poder cobrar a presenca
    // dele, e por isso cada secao leva os ids que tem dentro.
    ids: [...s.querySelectorAll("[id]")].map(e => e.id).filter(Boolean),
    borda: (() => { const cs = getComputedStyle(s); return cs.borderStyle !== "none" && parseFloat(cs.borderTopWidth || "0") > 0; })(),
    fundo: getComputedStyle(s).backgroundColor,
  }));
  return {
    titulo: document.title,
    largura_main: Math.round((document.querySelector("main") || document.body).getBoundingClientRect().width),
    h2: [...document.querySelectorAll("main h2")].map(h => (h.textContent || "").trim()).filter(Boolean),
    secoes, grades, figuras, numeros,
    estados: [...document.querySelectorAll("#regionsSaude .tile, #regionsFin .tile")].map(t => ({
      uf: t.dataset.uf || "", texto: (t.textContent || "").trim().slice(0, 40),
      largura: Math.round(t.getBoundingClientRect().width),
      // O pai é a GRADE, não o elemento imediato: os cartões podem estar agrupados por
      // região dentro dela, e foi o que fez a primeira medição contar zero com 27 na tela.
      pai: (t.closest("#regionsSaude, #regionsFin") || {}).id || "",
    })),
    texto_visivel: (document.querySelector("main") || document.body).innerText,
  };
};

(async () => {
  await new Promise(r => srv.listen(0, "127.0.0.1", r));
  const porta = srv.address().port;
  const b = await chromium.launch();
  const saida = { pagina: PAGINA, larguras: {} };
  for (const largura of [1280, 390]) {
    const ctx = await b.newContext({ viewport: { width: largura, height: largura === 1280 ? 900 : 844 }, deviceScaleFactor: 1 });
    const page = await ctx.newPage();
    const erros = [];
    page.on("pageerror", e => erros.push(e.message));
    await page.route(/vlibras\.gov\.br|fonts\.g|netlify/, r => r.abort());
    await page.goto(`http://127.0.0.1:${porta}/${PAGINA}`, { waitUntil: "networkidle", timeout: 45000 });
    await page.waitForTimeout(1500);
    const dados = await page.evaluate(COLETA);
    dados.erros_de_runtime = erros;
    dados.rolagem_horizontal = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
    saida.larguras[String(largura)] = dados;
    await ctx.close();
  }
  await b.close();
  srv.close();
  const texto = JSON.stringify(saida, null, 1);
  if (SAIDA) fs.writeFileSync(SAIDA, texto, "utf-8"); else process.stdout.write(texto);
})().catch(e => { console.error("DUMP FALHOU:", e.message); process.exit(1); });
