#!/usr/bin/env node
/* Cartão social (Open Graph/Twitter, 1200×630) — 15/09/2026: nome MARÉ · Medida de Antecipação e Resposta ao El Niño.
 * Renderiza um HTML mínimo com os tokens do site e captura com Playwright. Números lidos dos dados (nunca digitados).
 * Uso: node scripts/gerar_cartao_social.js  →  assets/social/card-monitor-el-nino.png */
const { chromium } = require("playwright"); const fs = require("fs"); const path = require("path");
const RAIZ = path.join(__dirname, ".."); const idx = JSON.parse(fs.readFileSync(path.join(RAIZ, "data", "indice.json"), "utf-8"));
const meta = JSON.parse(fs.readFileSync(path.join(RAIZ, "data", "meta.json"), "utf-8"));
const media = (Object.values(idx).reduce((s, v) => s + v.total, 0) / 27).toFixed(1).replace(".", ",");
const faixa = +media.replace(",", ".") < 25 ? "estágio inicial" : +media.replace(",", ".") < 50 ? "em construção" : +media.replace(",", ".") < 70 ? "consolidado" : "avançado";
const logo = "data:image/svg+xml;base64," + fs.readFileSync(path.join(RAIZ, "assets", "futura-positivo.svg")).toString("base64");
const html = `<!DOCTYPE html><html lang="pt-BR"><head><meta charset="utf-8"><style>
:root{--ink:#0E0F0D;--muted:#55645B;--musgo:#2E3D30;--argila:#7C4A34;--ambar:#C9814B;--mineral:#8FA5A8;--sintetico:#5E7C93;--trilho:#E7DECD;--borda:#CDBB9F;}
body{margin:0;width:1200px;height:630px;background:#FFFFFF;font-family:Georgia,'Times New Roman',serif;color:var(--ink);position:relative;overflow:hidden}
.topo{position:absolute;left:0;right:0;top:0;height:8px;background:var(--musgo)}
.logo{position:absolute;left:72px;top:56px;width:190px;height:40px}
.mare{position:absolute;left:72px;top:126px;font-size:150px;line-height:1;font-weight:400;letter-spacing:-.012em}
.sub{position:absolute;left:72px;top:290px;font-size:40px;line-height:1.2}
.sub em{font-style:italic}
.linha{position:absolute;left:72px;top:352px;font-family:'Arial Narrow',Arial,sans-serif;font-size:19px;letter-spacing:.06em;text-transform:uppercase;color:var(--sintetico)}
.nums{position:absolute;left:72px;top:410px;display:flex;gap:70px}
.n b{display:block;font-size:64px;line-height:1;font-weight:400}
.n span{display:block;font-family:Arial,sans-serif;font-size:19px;color:var(--muted);margin-top:8px;max-width:280px;line-height:1.3}
.rodape{position:absolute;left:72px;bottom:44px;font-family:Arial,sans-serif;font-size:19px;color:var(--muted)}
.barra{position:absolute;right:72px;bottom:52px;width:360px;height:16px;background:var(--trilho);border:1px solid var(--borda);border-radius:8px;overflow:hidden}
.barra i{display:block;height:100%;width:${media.replace(",", ".")}%;background:linear-gradient(90deg,var(--argila) 0%,var(--ambar) 20%,var(--mineral) 48%,var(--musgo) 88%);background-size:calc(10000%/${media.replace(",", ".")}) 100%;border-radius:8px 0 0 8px}
</style></head><body><div class="topo"></div><img class="logo" src="${logo}" alt="">
<div class="mare">MARÉ</div><div class="sub">Medida de Antecipação e Resposta ao <em>El Niño</em></div>
<div class="linha">Como o país se prepara para o ciclo 2026/2027 · dados verificados em fontes oficiais</div>
<div class="nums"><div class="n"><b>27</b><span>estados verificados um a um</span></div><div class="n"><b>5.571</b><span>municípios por nível de verificação</span></div><div class="n"><b>${media}</b><span>média nacional do índice · ${faixa} · dados até ${meta.corte}</span></div></div>
<div class="rodape">monitorelnino.com.br · Futura Evidence Lab · metodologia aberta, dados abertos</div><div class="barra"><i></i></div></body></html>`;
(async () => { const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1200, height: 630 }, deviceScaleFactor: 1 }); await p.setContent(html); await p.waitForTimeout(300);
  await p.screenshot({ path: path.join(RAIZ, "assets", "social", "card-monitor-el-nino.png") }); await b.close(); console.log("✓ cartão social gerado (1200×630), média", media); })();
