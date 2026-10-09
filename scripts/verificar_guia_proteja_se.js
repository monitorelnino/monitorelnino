#!/usr/bin/env node
/* Portão do "Leve com você" do Proteja-se (09/10/2026, ajuste 7).
 *
 * Gera o PDF e a imagem num Chromium real, pelos próprios geradores da página, e reprova:
 *   PDF — glifo que a fonte do PDF não tem ("→"), marca d'água, título de seção nas três últimas
 *         linhas da página, mais de 2 páginas; e, havendo `pdftotext`, glifo substituto no texto
 *         extraído ("!’", "�");
 *   imagem — texto desenhado com família que não estava carregada (document.fonts.check), e título
 *         de risco a menos de 40 px do primeiro item. Sem as fontes (sem rede), o gerador tem de
 *         RECUSAR com aviso, nunca desenhar com a fonte errada.
 *
 *   node scripts/verificar_guia_proteja_se.js --autoteste
 *   node scripts/verificar_guia_proteja_se.js
 */
const path = require("path"), fs = require("fs"), http = require("http"), os = require("os");
const { execFileSync } = require("child_process");
const RAIZ = path.join(__dirname, "..");
const ALTURA_A4 = 841.89, PE = 60, LINHA = 14.5;

function problemasPdf(log, paginas) {
  const p = [];
  log.forEach(e => {
    if (/[←-⇿]/.test(e.txt)) p.push(`glifo de seta sem suporte na fonte do PDF: "${e.txt.slice(0, 60)}"`);
    if (e.size >= 60) p.push(`marca d'água: "${e.txt}" em ${e.size} pt`);
    if (e.titulo && e.y > ALTURA_A4 - PE - 3 * LINHA) p.push(`título "${e.txt}" sem três linhas abaixo na página ${e.page}`);
  });
  if (paginas > 2) p.push(`${paginas} páginas`);
  return p;
}
function problemasImagem(log) {
  const p = [];
  log.forEach((e, i) => {
    if (!e.carregada) p.push(`texto desenhado sem a fonte carregada (${e.font}): "${e.txt.slice(0, 40)}"`);
    if (e.titulo && log[i + 1] && log[i + 1].y - e.y < 40) p.push(`título "${e.txt}" colado no primeiro item (${(log[i + 1].y - e.y).toFixed(0)} px)`);
  });
  return p;
}
function autoteste() {
  const casos = [
    ["seta no PDF reprova", problemasPdf([{ txt: "ver na fonte →", y: 100, size: 10 }], 2).length === 1],
    ["marca d'água reprova", problemasPdf([{ txt: "MARÉ", y: 400, size: 120 }], 2).length === 1],
    ["título no pé da página reprova", problemasPdf([{ txt: "Incêndios e fumaça", y: 770, size: 13.5, titulo: true, page: 1 }], 2).length === 1],
    ["PDF limpo passa", problemasPdf([{ txt: "ver na fonte", y: 300, size: 9 }], 2).length === 0],
    ["fonte não carregada reprova", problemasImagem([{ txt: "Proteja-se", font: "300 42px Fraunces", carregada: false, y: 10 }]).length === 1],
    ["título colado reprova", problemasImagem([{ txt: "Chuvas", titulo: true, carregada: true, y: 100 }, { txt: "item", carregada: true, y: 124 }]).length === 1],
    ["imagem limpa passa", problemasImagem([{ txt: "Chuvas", titulo: true, carregada: true, y: 100 }, { txt: "item", carregada: true, y: 168 }]).length === 0],
  ];
  casos.forEach(([n, ok]) => console.log(`  ${ok ? "OK  " : "FALHA"} ${n}`));
  const f = casos.filter(c => !c[1]).length;
  console.log(`${f ? "X" : "OK"} AUTOTESTE — ${casos.length} casos, sem navegador e sem escrita.`);
  return f ? 1 : 0;
}
async function principal() {
  const { chromium } = require("playwright");
  const MIME = { ".html": "text/html; charset=utf-8", ".js": "text/javascript", ".css": "text/css", ".json": "application/json", ".svg": "image/svg+xml", ".png": "image/png" };
  const srv = http.createServer((q, r) => { const u = decodeURIComponent(q.url.split("?")[0]); const f = path.join(RAIZ, u === "/" ? "index.html" : u);
    if (!f.startsWith(RAIZ) || !fs.existsSync(f) || fs.statSync(f).isDirectory()) { r.writeHead(404); return r.end(); }
    r.writeHead(200, { "Content-Type": MIME[path.extname(f)] || "application/octet-stream" }); fs.createReadStream(f).pipe(r); });
  await new Promise(r => srv.listen(0, "127.0.0.1", r));
  const b = await chromium.launch(); const page = await b.newPage({ viewport: { width: 1280, height: 900 } });
  page.on("dialog", d => d.dismiss());
  const falhas = [];
  try {
    await page.addInitScript(() => { window.__GUIA_TESTE = {}; });
    await page.goto(`http://127.0.0.1:${srv.address().port}/proteja-se.html`, { waitUntil: "networkidle" });
    const pdf = await page.evaluate(() => {
      const Orig = window.jspdf.jsPDF;
      window.jspdf.jsPDF = function (...a) { const d = new Orig(...a); const t = d.text.bind(d); d.__log = [];
        d.text = function (txt, x, y, o) { const tam = d.getFontSize();
          d.__log.push({ txt: [].concat(txt).join("\n"), y, page: d.internal.getNumberOfPages(), size: tam, titulo: tam === 13.5 });
          return t(txt, x, y, o); }; return d; };
      gerarPDFGuia();
      const doc = window.__GUIA_TESTE.pdf;
      return { log: doc.__log, paginas: doc.internal.getNumberOfPages(), b64: btoa(doc.output()) };
    });
    problemasPdf(pdf.log, pdf.paginas).forEach(x => falhas.push("PDF: " + x));
    try {
      const arq = process.env.GUIA_PDF_SAIDA || path.join(os.tmpdir(), "guia-teste.pdf"); fs.writeFileSync(arq, Buffer.from(pdf.b64, "base64"));
      const txt = execFileSync("pdftotext", ["-layout", arq, "-"], { encoding: "utf8" });
      if (/!’|�/.test(txt)) falhas.push("PDF: glifo substituto no texto extraído");
    } catch (e) { if (e.code !== "ENOENT") falhas.push("PDF: pdftotext falhou — " + e.message); }
    const img = await page.evaluate(async () => {
      const log = []; const P = CanvasRenderingContext2D.prototype, orig = P.fillText;
      P.fillText = function (t, x, y, w) { log.push({ txt: String(t), y, font: this.font, carregada: document.fonts.check(this.font), titulo: /^700 27px/.test(this.font) }); return orig.call(this, t, x, y, w); };
      gerarImagemGuia();
      for (let i = 0; i < 100 && !window.__GUIA_TESTE.imagem && !window.__GUIA_TESTE.recusa; i++) await new Promise(r => setTimeout(r, 100));
      return { log, recusa: window.__GUIA_TESTE.recusa || null, gerada: !!window.__GUIA_TESTE.imagem };
    });
    if (img.recusa === "fontes" && !img.log.length) console.log("  nota: sem as fontes do site (sem rede), a imagem foi RECUSADA com aviso — comportamento exigido.");
    else if (!img.gerada) falhas.push("imagem: não foi gerada (" + img.recusa + ")");
    else problemasImagem(img.log).forEach(x => falhas.push("imagem: " + x));
    console.log(`  PDF: ${pdf.paginas} página(s), ${pdf.log.length} trechos de texto; imagem: ${img.gerada ? img.log.length + " textos" : "recusada sem fonte"}`);
  } finally { await b.close(); srv.close(); }
  falhas.forEach(f => console.log("  ✗ " + f));
  console.log(falhas.length ? `✗ GUIA PROTEJA-SE: ${falhas.length} problema(s).` : "✓ GUIA PROTEJA-SE OK — PDF e imagem sem glifo quebrado, sem marca d'água, sem título órfão, com a fonte do site.");
  return falhas.length ? 1 : 0;
}
if (process.argv.includes("--autoteste")) process.exit(autoteste());
principal().then(c => process.exit(c)).catch(e => { console.error(e); process.exit(1); });
