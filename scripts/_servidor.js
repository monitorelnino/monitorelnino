/* Servidor estático dos portões de navegador: serve a raiz do repositório numa porta livre (srv.listen(0, "127.0.0.1")). */
const http = require("http"), fs = require("fs"), path = require("path");
const MIME = { ".html": "text/html; charset=utf-8", ".js": "text/javascript", ".css": "text/css", ".json": "application/json", ".svg": "image/svg+xml", ".xml": "application/xml", ".png": "image/png", ".pdf": "application/pdf", ".md": "text/markdown", ".woff2": "font/woff2" };
module.exports = (raiz) => http.createServer((q, r) => {
  const u = decodeURIComponent(q.url.split("?")[0]), f = path.join(raiz, u === "/" ? "index.html" : u);
  if (!f.startsWith(raiz) || !fs.existsSync(f) || fs.statSync(f).isDirectory()) { r.writeHead(404); return r.end(); }
  r.writeHead(200, { "Content-Type": MIME[path.extname(f)] || "application/octet-stream" }); fs.createReadStream(f).pipe(r);
});
