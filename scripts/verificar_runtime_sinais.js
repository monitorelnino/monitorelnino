#!/usr/bin/env node
/* Verificador de runtime da página de sinais oficiais de risco
 * (sinais-de-risco.html, criada em 01/09/2026 — METODOLOGIA §23).
 * Mesmo padrão de scripts/verificar_runtime_mapas.js: jsdom + d3 reais,
 * Chart simulado, fetch local. Cobre os 4 mapas, os 4 gráficos, os cartões
 * do ciclo, a tabela de fontes e — o que é próprio desta página — a
 * PROVENIÊNCIA VISÍVEL: nenhuma figura pode ficar sem crédito de fonte, e
 * toda fonte não coletada precisa aparecer como lacuna declarada.
 * Uso: node scripts/verificar_runtime_sinais.js
 */
const SINAIS = require("../data/sinais_risco.json");
const MARE = require("../data/indice.json");
const { JSDOM, VirtualConsole } = require("jsdom");
const fs = require("fs");
const path = require("path");

const raiz = path.join(__dirname, "..");
const html = fs.readFileSync(path.join(raiz, "sinais-de-risco.html"), "utf-8");
const erros = [];
const vc = new VirtualConsole();
vc.on("jsdomError", e => erros.push(e.detail && e.detail.stack ? e.detail.stack.split("\n")[0] : e.message));

const graficos = [];  // toda instância de Chart criada pela página

const dom = new JSDOM(html, {
  url: "https://localhost/", runScripts: "dangerously", virtualConsole: vc,
  beforeParse(w) {
    global.window = w; global.document = w.document; global.navigator = w.navigator;
    w.d3 = require("d3");
    // módulo único de mapas (o <script src> externo não é carregado pelo jsdom sem resources)
    w.eval(fs.readFileSync(path.join(raiz, "assets", "mapas.js"), "utf-8"));
    class Chart { constructor(ctx, cfg) { graficos.push({ ctx, cfg }); } }
    Chart.defaults = { font: {}, color: "" };
    w.Chart = Chart;
    w.fetch = (rel) => {
      const p = path.join(raiz, rel);
      try {
        const txt = fs.readFileSync(p, "utf-8");
        return Promise.resolve({ ok: true, json: () => Promise.resolve(JSON.parse(txt)) });
      } catch (e) { return Promise.resolve({ ok: false }); }
    };
    w.addEventListener("error", e => erros.push("onerror: " + e.message));
    w.addEventListener("unhandledrejection", e =>
      erros.push("unhandledrejection: " + ((e.reason && e.reason.message) || e.reason)));
  },
});

setTimeout(() => {
  const d = dom.window.document, q = id => d.getElementById(id);
  const falhas = [];
  const teste = (nome, cond) => { console.log((cond ? "  ✓ " : "  ✗ ") + nome); if (!cond) falhas.push(nome); };

  teste("zero erros de runtime", erros.length === 0);
  erros.slice(0, 4).forEach(e => console.log("     ", e));

  // --- mapas: os quatro desenham as 27 UFs, coletados ou não ---
  for (const id of ["mapaTipoRisco", "mapaSecas", "mapaAvisos", "mapaFogo", "mapaCemaden"]) {
    teste(`${id}: 27 estados desenhados`, q(id) && q(id).querySelectorAll("path").length === 27);
    teste(`${id}: legenda preenchida`, q(id.replace("mapa", "leg")) && q(id.replace("mapa", "leg")).children.length >= 2);
  }

  // --- o mapa de tipo de risco reflete o registro, não um valor fixo no HTML ---
  const tipos = new Set(Object.values(SINAIS.uf).map(u => u.risco_projetado && u.risco_projetado.tipo).filter(Boolean));
  const cores = new Set([...q("mapaTipoRisco").querySelectorAll("path")].map(p => p.getAttribute("fill")));
  teste(`mapa de tipo de risco: ${tipos.size} tipo(s) distintos no registro viram ${cores.size} cor(es)`,
    cores.size === tipos.size);
  teste("tabela de risco projetado: 27 linhas",
    q("tblTipoRisco") && q("tblTipoRisco").querySelectorAll("tbody tr").length === 27);

  // --- gráficos: os dois derivados do registro sempre existem;
  //     os dois dependentes de coleta existem OU exibem lacuna declarada ---
  teste("gráfico de estados por tipo de risco criado", graficos.some(g => g.ctx && g.ctx.id === "cTipos"));
  teste("gráfico do cruzamento risco × faixa MARÉ criado", graficos.some(g => g.ctx && g.ctx.id === "cCruz"));
  const cruz = graficos.find(g => g.ctx && g.ctx.id === "cCruz");
  const somaCruz = cruz ? cruz.cfg.data.datasets.reduce((s, ds) => s + ds.data.reduce((a, b) => a + b, 0), 0) : 0;
  teste(`cruzamento soma exatamente as 27 UFs (somou ${somaCruz})`, somaCruz === Object.keys(MARE).length);

  for (const [wrap, fonte] of [["wrapOni", "noaa_oni"], ["wrapPlume", "iri_plume"]]) {
    const coletada = SINAIS.fontes[fonte].status === "coletado";
    const temCanvas = q(wrap) && q(wrap).querySelector("canvas");
    const temLacuna = q(wrap) && q(wrap).querySelector(".lacuna");
    teste(`${wrap}: ${coletada ? "gráfico desenhado" : "lacuna declarada"}`, coletada ? !!temCanvas : !!temLacuna);
    teste(`${wrap}: nunca gráfico e lacuna ao mesmo tempo`, !(temCanvas && temLacuna));
  }

  // --- cartões do estado do ciclo ---
  teste("quatro cartões de estado do ciclo", q("cartoesCiclo") && q("cartoesCiclo").children.length === 4);

  // --- PROVENIÊNCIA VISÍVEL: regra própria desta página ---
  const creditos = [...d.querySelectorAll("[data-credito]")];
  const figuras = ["boxTipoRisco", "boxSecas", "boxAvisos", "boxFogo", "boxCemaden", "boxOni", "boxPlume", "boxTipos", "boxCruz",
    "cartaoCiclo0", "cartaoCiclo1", "cartaoCiclo2", "cartaoCiclo3"];
  const semCredito = figuras.filter(id => !q(id) || !q(id).querySelector("[data-credito]"));
  teste(`toda figura tem crédito de fonte (${creditos.length} créditos)`, semCredito.length === 0);
  if (semCredito.length) console.log("      sem crédito:", semCredito.join(", "));

  const orgaosCitados = creditos.map(p => p.dataset.credito);
  const fonteDesconhecida = orgaosCitados.filter(f => !SINAIS.fontes[f]);
  teste("todo crédito aponta para fonte do catálogo", fonteDesconhecida.length === 0);

  const coletadasSemData = creditos.filter(p => SINAIS.fontes[p.dataset.credito].status === "coletado"
    && !/consultado em \d{2}\/\d{2}\/\d{4}/.test(p.textContent));
  teste("crédito de fonte coletada traz a data de consulta", coletadasSemData.length === 0);

  const esperaSemTeto = creditos.filter(p => SINAIS.fontes[p.dataset.credito].status !== "coletado"
    && !/Não localizamos|sem coleta até o corte/.test(p.textContent));   // 04/09/2026: crédito de uma linha
  teste("fonte em espera usa a linguagem-teto do projeto", esperaSemTeto.length === 0);

  // --- tabela de fontes: uma linha por fonte catalogada ---
  const nFontes = Object.keys(SINAIS.fontes).length;
  teste(`tabela de fontes: ${nFontes} linhas`, q("tblFontes") && q("tblFontes").querySelectorAll("tbody tr").length === nFontes);

  // --- tooltip funciona no gesto do usuário (lição de 30/08: teste o gesto) ---
  const alvo = d.querySelector("#mapaTipoRisco path");
  alvo.dispatchEvent(new dom.window.MouseEvent("mouseenter", { clientX: 100, clientY: 100, bubbles: true }));
  teste("tooltip de mapa exibe conteúdo no mouseenter",
    q("mapTooltip").style.display === "block" && q("mapTooltip").innerHTML.length > 10);
  alvo.dispatchEvent(new dom.window.MouseEvent("mouseleave", { bubbles: true }));
  teste("tooltip some no mouseleave", q("mapTooltip").style.display === "none");
  alvo.dispatchEvent(new dom.window.FocusEvent("focus", { bubbles: true }));
  teste("tooltip abre também por teclado (foco)", q("mapTooltip").style.display === "block");

  // --- nenhuma pontuação vazando para esta página ---
  const texto = d.body.textContent;
  teste("página declara que não faz previsão climática", /não faz previsão climática/.test(texto));
  teste("página declara peso zero no índice", /não entra no índice MARÉ/.test(texto));


  // ── padrão único de mapas (03/09/2026): siglas das 27 UFs em todo mapa; legendas canônicas ──
  const mapasSvg = [...d.querySelectorAll('svg[id^="map"], svg[id^="mapa"]')].filter(s => s.querySelector("path.uf-path") || s.querySelector("path"));
  teste(`padrão de mapas: ${mapasSvg.length} mapa(s) com siglas das 27 UFs`, mapasSvg.length > 0 && mapasSvg.every(s => s.querySelectorAll("g.siglas text").length === 27));
  const legendas = [...d.querySelectorAll(".map-legend")].filter(l => l.children.length);
  teste(`padrão de legendas: ${legendas.length} legenda(s) no formato canônico`, legendas.every(l => [...l.children].every(c => c.tagName === "SPAN" && (c.classList.contains("escala") || (c.firstElementChild && c.firstElementChild.tagName === "I" && /background:/.test(c.firstElementChild.getAttribute("style") || ""))) && c.textContent.trim().length > 0)));
  if (falhas.length) {
    console.log(`\n✗ RUNTIME (sinais de risco): ${falhas.length} falha(s). Publicação bloqueada.`);
    process.exit(1);
  }
  console.log("\n✓ RUNTIME (sinais de risco) OK — mapas, gráficos, cartões, proveniência visível e lacunas declaradas.");
}, 900);
