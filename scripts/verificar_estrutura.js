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
const { JSDOM } = require("jsdom"); const { inlinePageJs } = require("./_inline_js");

const RAIZ = path.join(__dirname, "..");
let __baseCss = null;
function baseCssParaBreakpoints() { if (__baseCss === null) __baseCss = fs.readFileSync(path.join(RAIZ, "assets", "base.css"), "utf-8"); return __baseCss; }
// 03/09/2026: YAML dos workflows sem chave duplicada (o GitHub recusa o arquivo inteiro)
try { require("child_process").execSync("python3 scripts/validar_workflows.py", { cwd: RAIZ, stdio: "pipe" }); } catch (e) { console.log("  ✗ workflows inválidos: " + String(e.stdout || "")); process.exit(1); }
const PADRAO = ["index.html", "proteja-se.html", "envie-dados.html", "obrigado.html", "pesquisadores.html", "calendario-eleitoral.html", "defesa-civil.html", "sinais-de-risco.html", "saude.html", "financiamento.html", "imprensa.html"]
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

  // (1-bis) harmonização v2.2.4: fonte única de tokens e navegação canônica
  if (!/<link[^>]+href="assets\/tokens\.css(\?v=[0-9a-f]+)?"/.test(html)) falha(`${nome}: sem <link> para assets/tokens.css`);
  if (/:root\s*\{/.test(semScripts)) falha(`${nome}: bloco :root inline (tokens só em assets/tokens.css)`);
  const NAV_ORDEM = ["O monitor", "Risco climático", "Proteja-se", "Defesa civil", "Saúde", "Financiamento", "Pesquisadores", "Imprensa", "Envie um plano ou decreto"];   // 07/09/2026: seções na ordem da editoria; o CTA (botão) fecha a barra
  const navM = html.match(/<nav class="mainnav"[^>]*>([\s\S]*?)<\/nav>/);
  if (!navM) { falha(`${nome}: sem <nav class="mainnav">`); }
  else {
    const rotulos = [...navM[1].matchAll(/>([^<>]+)<\/(?:a|span)>/g)].map(m => m[1].trim());
    if (JSON.stringify(rotulos) !== JSON.stringify(NAV_ORDEM))
      falha(`${nome}: nav fora da ordem canônica (${rotulos.join(" · ")})`);
    const ativa = navM[1].match(/<span class="ativa(?: [^"]*)?"[^>]*>([^<]+)<\/span>/) || (nome === "calendario-eleitoral.html" ? ["", "Calendário"] : null);
    if (nome !== "obrigado.html" && !ativa) falha(`${nome}: nav sem item ativo`);
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
  d.querySelectorAll(".figura, .cartao").forEach(cartao => {
    const paragrafosVisiveis = [...cartao.querySelectorAll(".note")]
      .filter(p => !p.closest("details"));
    const total = paragrafosVisiveis.reduce((s, p) => s + p.textContent.trim().length, 0);
    if (total > 320) {
      const titulo = cartao.querySelector(".figura-titulo")?.textContent.slice(0, 40) || "?";
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
  // v3.1 §14 (06/09/2026): escala tipográfica, hex proibido fora dos tokens, dois breakpoints
  // Auditoria de consistência (07/09/2026): escala de 8 degraus (tokens.css); nenhuma página tem <style> nem
  // font-size/font-weight/line-height/font-family em atributo style; componentes só em base.css.
  const ESCALA = new Set([12, 14, 16, 18, 22, 28, 36, 48]);
  const foraEscala = [...(css + ";" + inline).matchAll(/font-size:\s*([\d.]+)px/g)].map(m => +m[1]).filter(v => !ESCALA.has(v));
  if (foraEscala.length) falha(`${nome}: font-size fora da escala (12·14·16·18·22·28·36·48): ${[...new Set(foraEscala)].join(", ")}px`);
  if (d.querySelector("style")) falha(`${nome}: bloco <style> na página (todo estilo vive em assets/base.css e assets/tokens.css)`);
  const inlineTipo = [...d.querySelectorAll("[style]")].map(el => el.getAttribute("style")).filter(v => /font-size|font-weight|line-height|font-family|letter-spacing|margin|padding/.test(v));
  if (inlineTipo.length) falha(`${nome}: ${inlineTipo.length} atributo(s) style com tipografia ou espaçamento (usar classes de base.css): ${inlineTipo.slice(0, 3).join(" | ")}`);
  const bruto0 = inlinePageJs(fs.readFileSync(path.join(RAIZ, nome), "utf-8"), RAIZ);
  const jsTipo = [...bruto0.replace(/^[\s\S]*?<body/, "").matchAll(/style=\\?["'][^"']*(font-size|font-weight|line-height|font-family)/g)];
  if (jsTipo.length) falha(`${nome}: script da página gera HTML com tipografia inline (${jsTipo.length})`);
  // componente único de figura: toda .figura tem título, subtítulo e mídia; nenhum título de figura ou de seção começa com número à mão
  d.querySelectorAll(".figura").forEach(f => {
    const id = f.id || "(sem id)";
    if (!f.querySelector(":scope > .figura-titulo")) falha(`${nome}: figura #${id} sem .figura-titulo`);
    if (!f.querySelector(":scope > .figura-sub")) falha(`${nome}: figura #${id} sem .figura-sub`);
    if (!f.querySelector(":scope > .figura-midia")) falha(`${nome}: figura #${id} sem .figura-midia`);
    if (!/figura--(mapa|grafico|tabela|diagrama|barras|indicador)/.test(f.className)) falha(`${nome}: figura #${id} sem variante de mídia (figura--mapa|grafico|tabela|diagrama|barras|indicador)`);
    if (f.tagName !== "FIGURE") falha(`${nome}: figura #${id} deve ser <figure>`);
  });
  [...d.querySelectorAll(".figura-titulo, main h2")].forEach(h => { if (/^\s*\d+[a-z]?\s*[·.)]/.test(h.textContent)) falha(`${nome}: numeração à mão em "${h.textContent.trim().slice(0, 40)}" (a numeração é automática: contadores CSS figura/secao, a partir de 1)`); });
  for (const cls of ["map-box", "chart-box", "map-card-h", "map-card-sub", "maps-grid", "charts-grid", "card", "kpi", "tr-card", "wide", "h-alta"]) if (d.querySelector("." + cls)) falha(`${nome}: classe legada .${cls} (usar .figura / .cartao / .grade-figuras / .grade-cartoes)`);
  const bruto = inlinePageJs(fs.readFileSync(path.join(RAIZ, nome), "utf-8"), RAIZ);
  const hex = [...bruto.matchAll(/#[0-9A-Fa-f]{6}\b/g)].map(m => m[0]);
  if (hex.length) falha(`${nome}: cor em hex fora de tokens.css/mapas.js (${hex.length}): ${[...new Set(hex)].slice(0, 5).join(", ")}`);
  const bps = [...(css + baseCssParaBreakpoints()).matchAll(/@media[^{]*\((?:max|min)-width:\s*(\d+)px\)/g)].map(m => +m[1]).filter(v => ![640, 1020, 1021].includes(v));
  if (bps.length) falha(`${nome}: breakpoint fora de 640/1020: ${[...new Set(bps)].join(", ")}px`);
  // 07/09/2026: ids órfãos — o JS da página escreve num elemento que o HTML não tem (raiz de 3 quebras de página desde 04/09)
  const jsPag = path.join(RAIZ, "assets", "js", nome.replace(".html", ".js"));
  if (fs.existsSync(jsPag)) {
    const js = fs.readFileSync(jsPag, "utf-8"); const orfaos = new Set();
    for (const m of js.matchAll(/document\.getElementById\('([A-Za-z0-9_-]+)'\)\.(?:innerHTML|textContent|style|value|hidden|classList|setAttribute|addEventListener)/g)) if (!new RegExp(`id="${m[1]}"`).test(bruto)) orfaos.add(m[1]);
    for (const m of js.matchAll(/document\.querySelector\('#([A-Za-z0-9_-]+)[^']*'\)\.(?:innerHTML|textContent|style|value)/g)) if (!new RegExp(`id="${m[1]}"`).test(bruto)) orfaos.add(m[1]);
    if (orfaos.size) falha(`${nome}: JS escreve em id(s) inexistente(s) sem guarda: ${[...orfaos].join(", ")}`);
  }
  // v2.3: as regras compartilhadas vivem em assets/base.css; a página só precisa importá-la
  const baseCss = fs.readFileSync(path.join(RAIZ, "assets", "base.css"), "utf-8");
  if (nome === "index.html") {   // uma vez por execução: a folha base só usa tokens para fonte e espaçamento
    const fsPx = [...baseCss.matchAll(/font-size:\s*([\d.]+)px/g)].map(m => +m[1]);
    if (fsPx.length) falha(`base.css: font-size em px fora dos tokens (${[...new Set(fsPx)].join(", ")}px)`);
    const espacos = [...baseCss.matchAll(/(?:^|[;{\s])(?:margin|padding|gap)(?:-top|-bottom|-left|-right|-block|-inline)?:\s*([^;}]+)/g)].map(m => m[1]).filter(v => /\d+px/.test(v) && !/var\(--sp-|var\(--esp-|var\(--grade-/.test(v) && !/^0(px)?$/.test(v.trim()));
    const arbitrarios = espacos.map(v => v.match(/\d+(?:\.\d+)?px/g) || []).flat().map(v => parseFloat(v)).filter(v => ![0, 1, 2, 3].includes(v));
    if (arbitrarios.length) falha(`base.css: espaçamento em px fora da escala de tokens (${[...new Set(arbitrarios)].join(", ")}px)`);
    const tokensCss = fs.readFileSync(path.join(RAIZ, "assets", "tokens.css"), "utf-8");
    for (const t of ["--fs-display: 48px", "--fs-h1: 36px", "--fs-h2: 28px", "--fs-h3: 22px", "--fs-h4: 18px", "--fs-body: 16px", "--fs-small: 14px", "--fs-caption: 12px", "--sp-1: 4px", "--sp-9: 96px", "--grade-max: 1180px"]) if (!tokensCss.includes(t)) falha(`tokens.css: token ausente ou alterado: ${t}`);
  }
  const temBase = /<link[^>]+href="assets\/base\.css(\?v=[0-9a-f]+)?"/.test(html);   // ?v= = carimbo de cache (05/09/2026)
  if (!temBase) falha(`${nome}: sem <link> para assets/base.css`);
  if (!/prefers-reduced-motion/.test(css + (temBase ? baseCss : ""))) falha(`${nome}: sem @media (prefers-reduced-motion)`);
  if (!/\.masthead--mini \.site-title\{[^}]*var\(--fs-h2\)/.test(baseCss)) falha(`${nome}: base.css sem a escala canônica do masthead compacto (var(--fs-h2))`);
  // v2.3 (03/09/2026): motor único de mapas — assets/mapas.js
  const temMapa = /<svg id="map/.test(html) || /d3\.geoMercator/.test(html);
  if (temMapa && !/<script src="assets\/mapas\.js(\?v=[0-9a-f]+)?"><\/script>/.test(html)) falha(`${nome}: página com mapa sem assets/mapas.js`);
  for (const fn of ["showTip", "hideTip", "desenharSiglas"]) if (new RegExp("function " + fn + "\\(").test(html)) falha(`${nome}: define ${fn} localmente (deve vir de MonitorMapas)`);
  if (/geoMercator\(\)\.fitSize/.test(html) && nome !== "defesa-civil.html") falha(`${nome}: cria projeção própria (usar MonitorMapas.contexto)`);
  const legendasManuais = (html.match(/innerHTML = [^\n]*<span><i style=\\?"background/g) || []).length;
  if (legendasManuais) falha(`${nome}: ${legendasManuais} legenda(s) montada(s) à mão (usar MonitorMapas.legenda)`);
  if (/new Chart\(/.test(html)) {
    if (!/MonitorMapas\.padraoGraficos\(/.test(html)) falha(`${nome}: usa Chart.js sem MonitorMapas.padraoGraficos`);
    if (/Chart\.defaults\./.test(html)) falha(`${nome}: define Chart.defaults localmente (padrão único em assets/mapas.js)`);
  }
  // nenhuma página pode redefinir os componentes da folha base
  const NUCLEO = [".mainnav a, .mainnav span", ".mainnav .ativa, .mainnav .ativa:hover", "header.masthead", ".site-title", ".masthead--mini .site-title", ".kicker", ".map-box", ".chart-box", ".map-legend", ".map-tooltip", "footer.site-footer", ".skip", ".panel"];
  { // 03/09/2026: o index também não pode redefinir o núcleo (a nav duplicada dele vencia a base)
    for (const sel of NUCLEO) {
      const re = new RegExp("(^|[\\s}])" + sel.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "\\s*\\{");
      if (re.test(css)) falha(`${nome}: redefine '${sel}' localmente (deve viver só em assets/base.css)`);
    }
  }
  if (/aria-label=/.test(html.replace(/<script[\s\S]*?<\/script>/g, "")) && [...d.querySelectorAll("[aria-label]")].some(el => ["SPAN","DIV","PATH"].includes(el.tagName) && !el.getAttribute("role")))
    falha(`${nome}: aria-label em span/div/path sem role (aria-prohibited-attr)`);
}

// 09/09/2026: paleta semântica única. Toda cor DE DADO (faixa do MARÉ, status, categoria de ato, família de risco,
// ordinal de intensidade, ano da série, rota do dinheiro, ENOS, antecipação × resposta) vem de MonitorMapas.PALETA.
// Nos scripts de página, MonitorMapas.cor('nome') só pode nomear cores estruturais (traço, fundo, tinta, ausência de dado);
// hex cru é proibido fora de assets/mapas.js e assets/tokens.css. Assim, o mesmo conceito tem a mesma cor em todas as páginas.
{
  const ESTRUTURAIS = new Set(["branco", "linha", "abissal", "vazio", "osso-claro", "sem-dado", "zebra", "preto", "muted", "areia", "cinza-quente"]);
  const mapas0 = fs.readFileSync(path.join(RAIZ, "assets", "mapas.js"), "utf-8");
  const dirJs = path.join(RAIZ, "assets", "js");
  const scripts = fs.readdirSync(dirJs).filter(f => f.endsWith(".js")).map(f => path.join("assets", "js", f)).concat(["assets/colunas.js"]);
  for (const rel of scripts) {
    const src = fs.readFileSync(path.join(RAIZ, rel), "utf-8");
    const hex = src.match(/#[0-9a-fA-F]{6}\b/g) || [];
    if (hex.length) falha(`${rel}: ${hex.length} cor(es) em hex cru (${[...new Set(hex)].slice(0, 5).join(", ")}) — usar MonitorMapas.PALETA`);
    const conhecidas = new Set([...mapas0.matchAll(/(?:^|[\s{,])'?([a-z][a-z-]*)'?\s*:\s*'#[0-9A-Fa-f]{6}'/g)].map(m => m[1]));
    const desconhecidas = [...src.matchAll(/MonitorMapas\.cor\('([a-z-]+)'\)/g)].map(m => m[1]).filter(n => !conhecidas.has(n));
    if (desconhecidas.length) falha(`${rel}: MonitorMapas.cor() com nome inexistente na paleta (${[...new Set(desconhecidas)].join(", ")})`);
    const semanticas = [...src.matchAll(/MonitorMapas\.cor\('([a-z-]+)'\)/g)].map(m => m[1]).filter(n => !ESTRUTURAIS.has(n));
    if (semanticas.length) falha(`${rel}: ${semanticas.length} cor(es) semântica(s) fora da paleta única (${[...new Set(semanticas)].join(", ")}) — usar MonitorMapas.PALETA.*`);
  }
  const mapas = fs.readFileSync(path.join(RAIZ, "assets", "mapas.js"), "utf-8");
  for (const chave of ["faixas:", "status:", "categorias:", "verificacao:", "risco:", "consistencia:", "enso:", "rampaPerigo:", "rampaPreparo:", "ordinal4:", "anos:", "rotas:", "chaves:", "temas:"])
    if (!mapas.includes(chave)) falha(`assets/mapas.js: PALETA sem o bloco '${chave.replace(":", "")}'`);
  // a tríade de risco da folha (tokens.css) e a do motor (mapas.js) precisam ser a mesma cor
  const tk = fs.readFileSync(path.join(RAIZ, "assets", "tokens.css"), "utf-8");
  const tok = n => (tk.match(new RegExp("--" + n + ":\\s*(#[0-9A-Fa-f]{6})")) || [])[1];
  const corMotor = n => (mapas.match(new RegExp("\\b" + n + ":'(#[0-9A-Fa-f]{6})'")) || [])[1];
  const risco = (mapas.match(/risco:\s*\{([^}]*)\}/) || [])[1] || "";
  const nomeRisco = fam => (risco.match(new RegExp(fam + ":\\s*COR(?:\\.(\\w+)|\\['([\\w-]+)'\\])")) || []).slice(1).find(Boolean);
  for (const [tkn, fam] of [["chuva", "chuvas"], ["seca", "seca"], ["fogo", "fogo"]]) {
    const nome = nomeRisco(fam); const cm = nome && corMotor(nome);
    if (!tok(tkn) || !cm || tok(tkn).toUpperCase() !== cm.toUpperCase()) falha(`tríade de risco divergente: --${tkn} (${tok(tkn)}) × PALETA.risco.${fam} (${nome} = ${cm})`);
  }
}

if (falhas) {
  console.log(`\n✗ ESTRUTURA: ${falhas} problema(s) em ${arquivos.length} página(s). Publicação bloqueada.`);
  process.exit(1);
}
console.log(`✓ ESTRUTURA OK — árvore íntegra, contêineres, masthead e rodapé consistentes em ${arquivos.length} página(s).`);
