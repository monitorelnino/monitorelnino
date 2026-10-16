/* Helper dos portões (06/09/2026, CSP sem unsafe-inline): o jsdom dos portões não carrega recurso
 * externo, então o helper devolve o HTML com o script da página embutido no lugar da tag
 * <script src="assets/…">, preservando a posição.
 *
 * 05/10/2026 — ELE PEGAVA MENOS DO QUE PRECISAVA, e isso escondia o que os portões deveriam ver.
 * O padrão antigo exigia `assets/js/` e o atributo `defer`. `assets/catalogo.js` não tem nenhum dos
 * dois: mora um nível acima e entra sem `defer`, porque o texto da página tem de estar posto antes
 * de o leitor ver a página. Resultado: todo portão de navegador renderizava as páginas migradas
 * SEM o leitor do catálogo, e conferia o texto de RESERVA do HTML no lugar do texto publicado —
 * incluindo os moldes, que ficavam com as chaves por resolver. Um portão que lê outra página que
 * não a que vai ao ar não está conferindo nada.
 *
 * Agora pega tambem `assets/catalogo.js`, com ou sem `defer`, mantendo a ordem do documento --
 * que e o que o faz carregar antes do script da pagina.
 *
 * E so ele. A primeira tentativa abriu para qualquer `assets/**.js` e levou junto o
 * `assets/mapas.js`, que tem permissao declarada para codigo de cor em hexadecimal: embutido na
 * pagina, ele virou "script de pagina com hexadecimal" e reprovou o portao de estrutura em 10
 * paginas de uma vez. O inlinador existe para que o jsdom RODE a pagina, nao para redesenhar o que
 * cada portao considera codigo da pagina -- e alargar o que ele embute muda isso sem avisar.
 * `assets/vendor/` continua de fora pela mesma logica, com um motivo a mais: nao e codigo deste
 * repositorio. */
const fs = require("fs"), path = require("path");

/* 08/10/2026: entra `assets/semana.js` junto, pelo mesmo motivo do `catalogo` e com o mesmo
 * sintoma. Ele converte a semana epidemiologica em intervalo de datas, e sem ele as frases da
 * Saude renderizavam SEM a data -- "notificacoes de dengue na semana", e so. Pior: o portao da
 * semana passava verde, porque nao havia nem a palavra proibida nem a data. Portao que le uma
 * pagina diferente da que vai ao ar nao esta conferindo nada, e esta e a segunda vez que este
 * arquivo aprende isso. */
const TAG = /<script src="(assets\/(?:js\/[^"]+?|catalogo|semana)\.js)(?:\?v=[0-9a-f]+)?"((?:\s+\w+)*)><\/script>/g;

function inlinePageJs(html, raiz) {
  return String(html).replace(TAG, (m, rel) => {
    const p = path.join(raiz, rel);
    return fs.existsSync(p) ? "<script>\n" + fs.readFileSync(p, "utf-8") + "\n</script>" : m;
  });
}

/* 16/10/2026 (consolidação item 6): UMA renderização de página para todos os portões de jsdom. Até aqui
 * sete scripts montavam o mesmo JSDOM, cada um com o seu Chart simulado, o seu `fetch` de disco e o seu
 * captador de erro — e quatro deles com a URL `/`, de modo que `assets/catalogo.js` servia o catálogo da
 * inicial (ou o texto de reserva) em toda página. A URL aqui é SEMPRE a da página.
 * Devolve { dom, window, document, erros, graficos, rotulos }:
 *   erros    — jsdomError, window.onerror e unhandledrejection (o fluxo async de __load/__init incluído);
 *   graficos — toda instância de Chart criada pela página, como {ctx, cfg};
 *   rotulos  — só o que o Chart escreveria na tela: rótulos do eixo, nomes das séries, títulos de eixo.
 * `opcoes.url` troca a URL de propósito (declarado); `opcoes.aoCriar(w)` roda depois da montagem. */
function renderizar(pagina, raiz, opcoes = {}) {
  const { JSDOM, VirtualConsole } = require("jsdom");
  const erros = [], graficos = [], rotulos = [], vc = new VirtualConsole();
  vc.on("jsdomError", (e) => erros.push(e.detail && e.detail.stack ? e.detail.stack.split("\n")[0] : e.message));
  const html = inlinePageJs(fs.readFileSync(path.join(raiz, pagina), "utf-8"), raiz);
  const dom = new JSDOM(html, { url: opcoes.url || "https://localhost/" + pagina, runScripts: "dangerously", virtualConsole: vc, beforeParse(w) {
    global.window = w; global.document = w.document; global.navigator = w.navigator; w.d3 = require("d3");
    // módulo único de mapas (o <script src> externo não é carregado pelo jsdom sem resources)
    try { w.eval(fs.readFileSync(path.join(raiz, "assets", "mapas.js"), "utf-8")); } catch (e) { erros.push("mapas.js: " + e.message); }
    class Chart { constructor(ctx, cfg) { graficos.push({ ctx, cfg }); const d = (cfg && cfg.data) || {}; try {
      rotulos.push((d.labels || []).join(" "), (d.datasets || []).map((s) => s && s.label).filter(Boolean).join(" "));
      Object.values(((cfg && cfg.options) || {}).scales || {}).forEach((e) => { if (e && e.title && e.title.text) rotulos.push(String(e.title.text)); }); } catch (e) {} } }
    Chart.defaults = { font: {}, color: "", plugins: { legend: { labels: {} }, tooltip: {} }, elements: {} }; w.Chart = Chart;
    w.fetch = (rel) => { try { const txt = fs.readFileSync(path.join(raiz, String(rel).replace(/^\.?\//, "").split("?")[0]), "utf-8");
      return Promise.resolve({ ok: true, json: () => Promise.resolve(JSON.parse(txt)), text: () => Promise.resolve(txt) }); } catch (e) { return Promise.resolve({ ok: false, status: 404 }); } };
    w.addEventListener("error", (e) => erros.push("onerror: " + e.message));
    w.addEventListener("unhandledrejection", (e) => erros.push("unhandledrejection: " + ((e.reason && e.reason.message) || e.reason)));
    if (opcoes.aoCriar) opcoes.aoCriar(w);
  } });
  return { dom, window: dom.window, document: dom.window.document, erros, graficos, rotulos };
}
module.exports = { inlinePageJs, TAG, renderizar };
