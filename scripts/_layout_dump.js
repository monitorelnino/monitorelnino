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
  // Item 3.2 do handover (02/10/2026): TEXTO EXISTENTE E INVISÍVEL. Um texto pode estar no DOM e
  // não ser lido — cor igual ao fundo, opacidade zero, `visibility: hidden`, altura útil menor que
  // doze pixels. O despejo mede e o portão reprova, porque texto que não se lê é pior do que texto
  // ausente: ele passa no portão que conta palavras e não chega ao leitor.
  const corLegivel = (frente, fundo) => {
    const n = c => (String(c).match(/[\d.]+/g) || [0, 0, 0]).slice(0, 3).map(Number);
    const [r1, g1, b1] = n(frente), [r2, g2, b2] = n(fundo);
    return Math.abs(r1 - r2) + Math.abs(g1 - g2) + Math.abs(b1 - b2) > 24;
  };
  const fundoDe = el => {
    let e = el;
    while (e) {
      const c = getComputedStyle(e).backgroundColor;
      if (c && !/rgba\(0, 0, 0, 0\)|transparent/.test(c)) return c;
      e = e.parentElement;
    }
    return "rgb(255, 255, 255)";
  };
  const invisiveis = [...document.querySelectorAll("main p, main li, main dt, main dd, main h2, main h3, main span")]
    .filter(el => (el.textContent || "").trim().length > 2)
    .filter(el => {
      if (el.closest("details:not([open])") || el.closest("[hidden]") || el.closest(".sr-only")) return false;
      const cs = getComputedStyle(el);
      const r = el.getBoundingClientRect();
      if (cs.display === "none" || cs.visibility === "hidden") return true;
      if (parseFloat(cs.opacity || "1") < 0.15) return true;
      if (r.height > 0 && r.height < 12) return true;
      return !corLegivel(cs.color, fundoDe(el));
    })
    .map(el => ({ tag: el.tagName.toLowerCase(), id: el.id || "",
                  texto: (el.textContent || "").trim().replace(/\s+/g, " ").slice(0, 60),
                  motivo: (() => {
                    const cs = getComputedStyle(el), r = el.getBoundingClientRect();
                    if (cs.display === "none" || cs.visibility === "hidden") return "escondido";
                    if (parseFloat(cs.opacity || "1") < 0.15) return "opacidade " + cs.opacity;
                    if (r.height > 0 && r.height < 12) return "altura útil " + Math.round(r.height) + "px";
                    return "cor igual ao fundo";
                  })() }))
    .slice(0, 8);
  const figuras = [...document.querySelectorAll("figure")].map(f => ({
    id: f.id,
    classes: [...f.classList],
    cartao_mapa: f.classList.contains("cartao-mapa"),
    tem_midia: !!f.querySelector("svg, canvas"),
    tem_lista: !!f.querySelector("details, dl, table, .busca-mun"),
    largura: Math.round(f.getBoundingClientRect().width),
    visivel: vis(f),
    pai_grade: (f.parentElement && [...f.parentElement.classList].join(" ")) || "",
    // A chave de dado declarada no próprio elemento: duas figuras com a mesma chave na mesma seção
    // dizem a mesma coisa duas vezes, e é o que o item 3.2 manda reprovar.
    chave_de_dado: f.dataset.chave || "",
    secao: (() => { let e = f.parentElement; while (e && !e.id) e = e.parentElement; return e ? e.id : ""; })(),
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
  /* 03/10/2026 (conformidade permanente): a medição deixa de ser só de FORMA e passa a incluir o
     que as regras de tipografia, de componente e de acessibilidade precisam para serem conferidas
     por máquina. Continua valendo a divisão: aqui só se mede; quem julga é
     scripts/verificar_conformidade.py, contra layout/regras.json. */
  const estiloDe = el => {
    const cs = getComputedStyle(el);
    return { familia: (cs.fontFamily || "").split(",")[0].replace(/['"]/g, "").trim(),
             peso: cs.fontWeight, tamanho: Math.round(parseFloat(cs.fontSize || "0")),
             espacamento: cs.letterSpacing, caixa: cs.textTransform, cor: cs.color };
  };
  const amostra = (seletor, limite) => [...document.querySelectorAll(seletor)]
    .filter(el => (el.textContent || "").trim().length > 0 && vis(el))
    .slice(0, limite || 6)
    .map(el => Object.assign({ seletor: seletor, id: el.id || "",
                               texto: (el.textContent || "").trim().slice(0, 40) }, estiloDe(el)));
  const tipografia = [].concat(
    amostra("main h1", 2), amostra("main h2"), amostra("main h3:not(.ficha-rotulo)"),
    amostra("main .figura-titulo"), amostra("main .cartao-numero-valor"),
    amostra("main .cartao-numero-rotulo"), amostra("main .figura-sub"),
    amostra("main .fonte-figura"), amostra("main p.hint", 3), amostra("main .map-legend span", 4));
  /* Alvo de toque: no celular, botão e link de 20 px não se acerta com o dedo. A régua é a do
     documento de direção de arte (44 px), e a medição só vale a 390 px — no desktop o ponteiro
     resolve, e cobrar lá produziria vermelho que ninguém deve apagar. */
  const alvos = [...document.querySelectorAll("main a, main button, main summary, main input, main select, main [role=button]")]
    .filter(el => vis(el))
    .map(el => { const r = el.getBoundingClientRect();
                 return { tag: el.tagName.toLowerCase(), id: el.id || "",
                          texto: (el.textContent || "").trim().slice(0, 30),
                          largura: Math.round(r.width), altura: Math.round(r.height),
                          /* Link dentro de texto corrido tem a altura da LINHA, e esticá-lo para 44 px quebraria a
                             prosa. Conta como texto corrido: parágrafo, item de lista, nota, legenda, CRÉDITO
                             DE FIGURA e célula de tabela — os dois últimos entraram em 03/10/2026, quando o
                             portão novo apontou o link da portaria no crédito e o da fonte na tabela. */
                          dentro_de_texto: !!el.closest("p, li, dd, .note, .hint, figcaption, .fonte-figura, td, th, .map-legend") }; })
    .filter(a => a.altura < 44 && !a.dentro_de_texto)
    .slice(0, 12);
  const figurasCompletas = [...document.querySelectorAll("figure")].map(f => ({
    id: f.id,
    titulo: ((f.querySelector(".figura-titulo") || {}).textContent || "").trim(),
    legenda: ((f.querySelector(".figura-sub") || {}).textContent || "").trim(),
    fonte: ((f.querySelector(".fonte-figura") || {}).textContent || "").trim(),
    tem_midia: !!f.querySelector("svg, canvas"),
    rotulada: [...f.querySelectorAll("svg, canvas, img")]
      .every(m => (m.getAttribute("aria-label") || m.getAttribute("alt") || "").trim().length > 3),
    visivel: vis(f),
  }));
  return {
    titulo: document.title,
    tipografia, alvos_de_toque: alvos, figuras_completas: figurasCompletas,
    fundo_do_corpo: getComputedStyle(document.body).backgroundColor,
    largura_main: Math.round((document.querySelector("main") || document.body).getBoundingClientRect().width),
    h2: [...document.querySelectorAll("main h2")].map(h => (h.textContent || "").trim()).filter(Boolean),
    secoes, grades, figuras, numeros, invisiveis,
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
