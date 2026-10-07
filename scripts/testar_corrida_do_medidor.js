// scripts/testar_corrida_do_medidor.js — o medidor espera a condição, não o relógio
// =================================================================================
//
// Item 2 do `HANDOVER_publicacao_definitiva_e_rodadas_agora_06-10-2026.md`.
//
// O QUE ACONTECEU
// ----------------
// Três publicações de 06/10 morreram com "texto exigido ausente: 'desembolsado é o que já saiu do
// caixa'" — com a página certa e o dado certo (`compromissos_federais.json`: 5 itens,
// R$ 1.383.300.000, igual desde 02/09). A frase é escrita por `assets/js/financiamento.js` depois
// de um `fetch` encadeado, e `_layout_dump.js` esperava `networkidle` mais 1.500 ms FIXOS. Em
// runner lento, media antes de a frase existir.
//
// Era corrida no MEDIDOR, não defeito da página nem do dado. Aumentar o tempo fixo seria a mesma
// corrida, mais lenta.
//
// O QUE ESTE TESTE FAZ
// ---------------------
// Atrasa em 3 s o JSON que a frase precisa, e mede duas vezes:
//
//   · com espera FIXA de 1.500 ms  → tem de FALHAR (é o defeito, reproduzido);
//   · com a espera por CONDIÇÃO    → tem de PASSAR (é o conserto, provado).
//
// Um teste que só provasse o conserto não provaria que ele conserta alguma coisa.
//
// USO
//   node scripts/testar_corrida_do_medidor.js
const http = require("http"), fs = require("fs"), path = require("path");
const { chromium } = require("playwright");

const RAIZ = path.join(__dirname, "..");
const PAGINA = "financiamento.html";
const ATRASO_MS = 3000;
const ALVO = "desembolsado é o que já saiu do caixa";

const TIPOS = { ".html": "text/html", ".js": "text/javascript", ".css": "text/css",
                ".json": "application/json", ".svg": "image/svg+xml" };

function servidor() {
  return http.createServer((req, res) => {
    const rel = decodeURIComponent((req.url || "/").split("?")[0]).replace(/^\//, "") || "index.html";
    const f = path.join(RAIZ, rel);
    if (!f.startsWith(RAIZ) || !fs.existsSync(f) || fs.statSync(f).isDirectory()) {
      res.writeHead(404); return res.end("nao encontrado");
    }
    res.writeHead(200, { "content-type": TIPOS[path.extname(f)] || "application/octet-stream" });
    fs.createReadStream(f).pipe(res);
  });
}

async function medir(porta, esperarPorCondicao) {
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: 1280, height: 900 } });
  const page = await ctx.newPage();
  await page.route(/vlibras\.gov\.br|fonts\.g|netlify/, r => r.abort());
  // O atraso que reproduz o runner lento: exatamente o arquivo de que a frase depende.
  await page.route(/compromissos_federais\.json/, async (rota) => {
    await new Promise(r => setTimeout(r, ATRASO_MS));
    await rota.continue();
  });
  // A JANELA EM QUE A CORRIDA ACONTECE, reproduzida de forma deterministica.
  //
  // `networkidle` espera 500 ms sem conexao -- e um `fetch` ENCADEADO, que so comeca depois de o
  // anterior resolver e de uma conta rodar, pode comecar DEPOIS dessa janela. Em producao foi isso:
  // a espera era `networkidle` mais 1.500 ms e mesmo assim media cedo. Atrasar o JSON por `route`
  // nao reproduz, porque o `networkidle` passa a esperar o proprio atraso.
  //
  // Entao o lado do RELOGIO mede a partir de `domcontentloaded`, que e exatamente a janela em que
  // o defeito mora: a pagina ja existe, o encadeamento ainda nao terminou. O lado da CONDICAO parte
  // do mesmo ponto -- a diferenca entre os dois e so o que cada um espera.
  await page.goto(`http://127.0.0.1:${porta}/${PAGINA}`,
                  { waitUntil: "domcontentloaded", timeout: 45000 });
  if (esperarPorCondicao) {
    try {
      await page.waitForFunction(
        (alvo) => ((document.querySelector("main") || document.body).innerText || "").includes(alvo),
        ALVO, { timeout: 20000 });
    } catch (e) { /* o julgamento é do texto medido, abaixo */ }
  }
  await page.waitForTimeout(1500);
  const texto = await page.evaluate(() => (document.querySelector("main") || document.body).innerText || "");
  await ctx.close(); await b.close();
  return texto.includes(ALVO);
}

(async () => {
  const srv = servidor();
  await new Promise(r => srv.listen(0, "127.0.0.1", r));
  const porta = srv.address().port;
  const falhas = [];
  const ok = (nome, cond) => {
    console.log((cond ? "  ✓ " : "  ✗ ") + nome);
    if (!cond) falhas.push(nome);
  };

  const comRelogio = await medir(porta, false);
  ok(`com espera FIXA e o JSON atrasado em ${ATRASO_MS} ms, o medidor NAO ve a frase (o defeito)`,
     comRelogio === false);

  const comCondicao = await medir(porta, true);
  ok("com espera por CONDICAO, o medidor ve a frase (o conserto)", comCondicao === true);

  srv.close();
  if (falhas.length) {
    console.log(`✗ CORRIDA DO MEDIDOR: ${falhas.length} falha(s)`);
    process.exit(1);
  }
  console.log("✓ CORRIDA DO MEDIDOR OK — o defeito se reproduz com relogio e some com condicao.");
})();
