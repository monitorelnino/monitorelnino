/* Helper dos portões (06/09/2026, CSP sem unsafe-inline): os scripts das páginas vivem em assets/js/<página>.js;
 * o jsdom dos portões não carrega recursos externos, então o helper devolve o HTML com o script da página
 * embutido no lugar da tag <script src="assets/js/…" defer>, preservando a posição. */
const fs = require("fs"), path = require("path");
function inlinePageJs(html, raiz) {
  return html.replace(/<script src="(assets\/js\/[^"]+?)(?:\?v=[0-9a-f]+)?" defer><\/script>/g, (m, rel) => {
    const p = path.join(raiz, rel);
    return fs.existsSync(p) ? "<script>\n" + fs.readFileSync(p, "utf-8") + "\n</script>" : m;
  });
}
module.exports = { inlinePageJs };
