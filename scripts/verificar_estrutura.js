#!/usr/bin/env node
// Verificação estrutural das páginas do Monitor El Niño Brasil.
// Roda como etapa BLOQUEANTE do pipeline (atualizar.py) e manualmente:
//   node scripts/verificar_estrutura.js            → páginas do pacote
//   node scripts/verificar_estrutura.js a.html b…  → arquivos indicados
// Checa: (1) balanceamento de tags estruturais fora dos <script>;
// (2) nenhum elemento órfão como filho direto do <body> além de .wrap e scripts;
// (3) todo h1/h2 dentro de .wrap (e dentro de <main>, quando a página tem um);
// (4) masthead e rodapé unificados presentes e dentro do contêiner.
const fs = require("fs");
const path = require("path");
const { JSDOM } = require("jsdom");

const RAIZ = path.join(__dirname, "..");
const PADRAO = ["index.html", "proteja-se.html", "envie-dados.html", "obrigado.html", "mapas-e-graficos.html", "para-gestores.html", "sinais-de-risco.html"]
  .map(a => path.join(RAIZ, a));
const arquivos = process.argv.length > 2 ? process.argv.slice(2) : PADRAO;

const TAGS = ["div", "main", "section", "header", "footer", "form", "details", "ul", "ol", "table"];
let falhas = 0;
const falha = (msg) => { console.log("  ✗ " + msg); falhas++; };

for (const arq of arquivos) {
  const nome = path.basename(arq);
  const html = fs.readFileSync(arq, "utf-8");

  // (1) balanceamento fora dos scripts
  const semScripts = html.replace(/<script\b[\s\S]*?<\/script>/g, "");
  const abre = {}, fecha = {};
  for (const m of semScripts.matchAll(new RegExp("<(\\/?)(" + TAGS.join("|") + ")\\b", "g"))) {
    (m[1] ? fecha : abre)[m[2]] = ((m[1] ? fecha : abre)[m[2]] || 0) + 1;
  }
  for (const t of new Set([...Object.keys(abre), ...Object.keys(fecha)])) {
    if ((abre[t] || 0) !== (fecha[t] || 0)) {
      falha(`${nome}: <${t}> desbalanceado (${abre[t] || 0} aberturas × ${fecha[t] || 0} fechos)`);
    }
  }

  // (2)–(4) auditoria da árvore como o navegador a enxerga
  const d = new JSDOM(html).window.document;
  // Órfãos permitidos por design: o skip-link de acessibilidade (deve ser o 1º
  // filho do body) e tooltips flutuantes com position:fixed.
  const PERMITIDOS = (el) => el.classList.contains("wrap") || el.tagName === "SCRIPT"
    || (el.tagName === "A" && el.classList.contains("skip"))
    || el.classList.contains("map-tooltip")
    || el.hasAttribute("vw");  // widget VLibras (plugin oficial gov.br), inserido antes de </body> por instrução do fabricante
  const orfaos = [...d.body.children].filter(el => !PERMITIDOS(el));
  if (orfaos.length) {
    falha(`${nome}: ${orfaos.length} elemento(s) órfão(s) fora de .wrap: ` +
      orfaos.slice(0, 4).map(o => o.tagName + (o.className ? "." + String(o.className).split(" ")[0] : "")).join(", "));
  }
  const temMain = !!d.querySelector("main");
  const fora = [...d.querySelectorAll("h1, h2")].filter(h => {
    if (!h.closest(".wrap")) return true;
    if (temMain && !h.closest("main") && !h.closest("header") && !h.closest("footer")) return true;
    return false;
  });
  if (fora.length) {
    falha(`${nome}: ${fora.length} título(s) fora do contêiner: ` +
      fora.map(h => h.textContent.trim().slice(0, 34)).join(" | "));
  }
  if (!d.querySelector("header.masthead")) falha(`${nome}: masthead ausente`);
  const rodape = d.querySelector("footer.site-footer");
  if (!rodape || !rodape.closest(".wrap")) falha(`${nome}: rodapé ausente ou fora do contêiner`);

  // (5) âncoras internas: todo href="#algo" precisa ter um id="algo" na MESMA página
  // (achado de 31/08/2026 — a divisão de mapas/gráficos em página própria deixou
  // 3 links quebrados em index.html, sem nenhum portão que os pegasse antes).
  const idsDaPagina = new Set([...d.querySelectorAll("[id]")].map(el => el.id));
  const ancorasQuebradas = [...d.querySelectorAll('a[href^="#"]')]
    .map(a => a.getAttribute("href").slice(1))
    .filter(alvo => alvo && !idsDaPagina.has(alvo));
  if (ancorasQuebradas.length) {
    falha(`${nome}: ${ancorasQuebradas.length} âncora(s) interna(s) quebrada(s): #` +
      [...new Set(ancorasQuebradas)].slice(0, 5).join(", #"));
  }

  // (6) cartões de mapa/gráfico com texto de introdução desproporcional (achado de
  // Patricia, 31/08/2026: mapas herdados de painéis largos tinham parágrafos de
  // até 700 caracteres, o que inflava a altura do cartão e empurrava mapa e legenda
  // para baixo, quebrando a harmonia visual do grid). Só conta o texto VISÍVEL por
  // padrão — parágrafos dentro de <details> (fechado) não contam, são para quem
  // quiser aprofundar.
  const cartoesLongos = [];
  d.querySelectorAll(".map-box, .chart-box").forEach(cartao => {
    const paragrafosVisiveis = [...cartao.querySelectorAll(".note")]
      .filter(p => !p.closest("details"));
    const total = paragrafosVisiveis.reduce((s, p) => s + p.textContent.trim().length, 0);
    if (total > 320) {
      const titulo = cartao.querySelector(".map-card-h")?.textContent.slice(0, 40) || "?";
      cartoesLongos.push(`${titulo} (${total} caracteres)`);
    }
  });
  if (cartoesLongos.length) {
    falha(`${nome}: ${cartoesLongos.length} cartão(ões) com texto de introdução desproporcional: ` +
      cartoesLongos.join("; "));
  }

  // (7) acessibilidade e consistência de design, verificáveis sem navegador
  // (auditoria de 31/08/2026 com axe-core em 3 viewports; a versão completa é
  // scripts/auditar_ux.js — aqui ficam as regras baratas que evitam regressão):
  const h1s = d.querySelectorAll("h1").length;
  if (h1s !== 1) falha(`${nome}: ${h1s} <h1> (deve ser exatamente 1)`);
  if (!d.querySelector("main")) falha(`${nome}: sem landmark <main>`);
  if (!d.querySelector('meta[name="description"]')) falha(`${nome}: sem <meta name="description">`);
  if (!d.querySelector('a.skip[href="#conteudo"]')) falha(`${nome}: sem skip link para #conteudo`);
  const css = [...d.querySelectorAll("style")].map(s => s.textContent).join("\n");
  if (/'Archivo Narrow'\s*,\s*(monospace|sans-serif)\b/.test(css) || /'Fraunces'\s*,\s*sans-serif/.test(css))
    falha(`${nome}: pilha de fallback de fonte fora do padrão (Fraunces→Georgia,serif; Archivo Narrow→Arial Narrow,Arial)`);
  const inline = [...d.querySelectorAll("[style]")].map(el => el.getAttribute("style")).join(";");
  const tamanhos = [...(css + ";" + inline).matchAll(/font-size:\s*([\d.]+)px/g)].map(m => +m[1]).filter(v => v < 12);
  if (tamanhos.length) falha(`${nome}: font-size abaixo de 12px no CSS: ${[...new Set(tamanhos)].join(", ")}px`);
  const clampTitulo = css.match(/\.site-title\{[^}]*font-size:(clamp\([^)]*\))/);
  if (clampTitulo && clampTitulo[1] !== "clamp(33px, 5.4vw, 46px)") falha(`${nome}: .site-title com escala diferente das outras páginas: ${clampTitulo[1]}`);
  if (!/prefers-reduced-motion/.test(css)) falha(`${nome}: sem @media (prefers-reduced-motion)`);
  if (/aria-label=/.test(html.replace(/<script[\s\S]*?<\/script>/g, "")) && [...d.querySelectorAll("[aria-label]")].some(el => ["SPAN","DIV","PATH"].includes(el.tagName) && !el.getAttribute("role")))
    falha(`${nome}: aria-label em span/div/path sem role (aria-prohibited-attr)`);
}

if (falhas) {
  console.log(`\n✗ ESTRUTURA: ${falhas} problema(s) em ${arquivos.length} página(s). Publicação bloqueada.`);
  process.exit(1);
}
console.log(`✓ ESTRUTURA OK — árvore íntegra, contêineres, masthead e rodapé consistentes em ${arquivos.length} página(s).`);
