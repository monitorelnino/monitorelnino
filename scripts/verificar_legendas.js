#!/usr/bin/env node
/* Portão 19 — legendas neutras (15/09/2026, regra editorial permanente da editoria).
 * Legenda, título auxiliar, subtítulo, item de legenda, crédito e rótulo de tooltip de uma figura
 * DESCREVEM o que está representado; nunca avaliam, dramatizam, interpretam nem atribuem causa.
 * Verifica, nas 11 páginas renderizadas com dados (jsdom + d3 + fetch local):
 *   (a) léxico avaliativo e alarmista ("preocupante", "alarmante", "grave", "crítico"…);
 *   (b) aberturas interpretativas ("revela", "demonstra", "fica evidente", "chama atenção"…);
 *   (c) causalidade não demonstrada ("provocou", "por causa de", "devido a", "explica"…);
 *   (d) teto probatório: "sem plano / sem instrumento / sem ato" só com "localizado/identificado";
 *       nunca "não existe" nem "não tem plano";
 *   (e) tamanho: título ≤ 100 caracteres; leitura (.figura-leitura) ≤ 2 frases e ≤ 240 caracteres;
 *       item de legenda ≤ 140 caracteres; ênfase em CAIXA ALTA proibida.
 * Também varre as strings de tooltip (showTip) dos scripts das páginas, que o DOM não renderiza.
 * Termos técnicos legítimos ficam na lista de exceções (ex.: "síndrome respiratória aguda grave",
 * "janela crítica" declarada pelo Ministério da Saúde).
 * Uso: node scripts/verificar_legendas.js [--listar] */
const fs = require("fs"), path = require("path");
const { JSDOM, VirtualConsole } = require("jsdom"); const { inlinePageJs } = require("./_inline_js");
const RAIZ = path.join(__dirname, ".."); const listar = process.argv.includes("--listar");
const PAGINAS = ["index.html", "defesa-civil.html", "saude.html", "financiamento.html", "sinais-de-risco.html", "calendario-eleitoral.html",
  "pesquisadores.html", "imprensa.html", "prefeituras.html", "proteja-se.html", "obrigado.html"].filter(p => fs.existsSync(path.join(RAIZ, p)));

// Exceções: colocações técnicas ou oficiais que contêm uma palavra da lista, mas não são juízo.
const EXCECOES = [/síndrome respiratória aguda grave/gi, /aguda grave/gi, /janela crítica/gi, /sinais de alarme/gi, /nível \d \((?:baixa atividade|atenção|alerta|emergência)\)/gi,
  /alerta[s]? (?:hidrológic|geológic|meteorológic|vigente|de risco|nacional|laranja|vermelh)/gi, /nível de alerta/gi, /em alerta/gi, /avisos? meteorológic/gi, /alertas? (?:do|de) CEMADEN/gi,
  /restrição importante de transporte/gi, /grau de urgência/gi, /situação de emergência|estado de emergência|emergência sanitária|emergências sanitárias|decreto de emergência|decretos de emergência/gi,
  /grave e urgente necessidade pública/gi, /matéria urgente, relevante/gi, /risco de fogo/gi, /pior desfecho/gi, /melhor(?:es)? (?:esforços|estimativa)/gi];
const AVALIATIVO = [/preocupant/i, /alarmant/i, /alarmism/i, /impressionant/i, /\bsignificativ[oa]s?\b/i, /\bgrave(s|mente)?\b/i, /\bcrític[oa]s?\b/i, /\bexpressiv[oa]s?\b/i,
  /chocant/i, /surpreendent/i, /lamentav/i, /\bfelizmente\b/i, /\binfelizmente\b/i, /\bdramátic/i, /\bassustador/i, /\benorme/i, /\bgigantesc/i, /\bdrástic/i,
  /\bfrágil\b|\bfragilidade/i, /\bdespreparad/i, /\bfracass/i, /\binsuficient/i, /\bprecári/i, /\binaceitáv/i, /\bescandal/i, /\burgent(e|íssim)/i, /\bpior(es)?\b/i, /\bmelhor(es)?\b/i,
  /\bpositiv[oa]s?\b/i, /\bnegativ[oa]s?\b/i, /forte tendência/i, /problema crescente/i, /cenário preocupante/i, /situação alarmante/i, /avanço importante/i, /\bexemplar(es)?\b/i, /\bnotáve(l|is)\b/i];
const INTERPRETATIVO = [/fica evidente/i, /é importante destacar/i, /merece atenção/i, /não podemos ignorar/i, /chama (a )?atenção/i, /os números são claros/i, /\brevela(m|ndo)?\b/i,
  /\bdemonstra(m|ndo)?\b/i, /\bevidencia(m|ndo)?\b/i, /\bcomprova(m|ndo)?\b/i, /\bmostra(m)? que\b/i, /isso (mostra|revela|significa|indica)/i, /o país enfrenta/i, /se agrava/i, /deteriora/i];
const CAUSAL = [/\bprovoc(ou|a|am|aram|ando)\b/i, /\bcausou\b|\bcausaram\b|\bcausa(m|ndo)? (o|a|um|uma)\b/i, /\bpor causa d/i, /\bdevido a/i, /\bgraças a/i, /\blev(ou|aram) a\b/i,
  /\bresult(ou|aram) em\b/i, /\bexplica(m)?\b/i, /\bem consequência\b/i, /\bpor isso\b/i];
const TETO = [/\bnão existe(m)?\b/i, /\bnão (tem|têm) plano\b/i, /\bsem (plano|instrumento|ato)s?\b(?! (?:localizad|identificad|próprio|municipal próprio)|(?: (?:estadual|municipal|preventivo|do ciclo|para o ciclo))* (?:localizad|identificad))/i];

function classificar(texto) {
  let t = texto; EXCECOES.forEach(re => { t = t.replace(re, " "); });
  const achados = [];
  for (const [rot, lista] of [["avaliativo", AVALIATIVO], ["interpretação", INTERPRETATIVO], ["causalidade", CAUSAL], ["teto probatório", TETO]])
    for (const re of lista) { const m = t.match(re); if (m) achados.push(`${rot}: "${m[0]}"`); }
  // ênfase tipográfica: duas ou mais palavras seguidas em caixa alta (siglas de até 5 letras são permitidas)
  const caps = t.match(/\b[A-ZÁÉÍÓÚÂÊÔÃÕÇ]{2,}\b(?:\s+[A-ZÁÉÍÓÚÂÊÔÃÕÇ]{2,}\b)+/g);
  if (caps && caps.some(c => c.split(/\s+/).some(w => w.length > 5))) achados.push(`ênfase em caixa alta: "${caps[0]}"`);
  return achados;
}
const frases = s => s.split(/[.!?](?:\s|$)/).filter(x => x.trim().length > 0).length;
const t = e => (e ? e.textContent : "").replace(/\s+/g, " ").trim();

function renderizar(pagina) {
  const html = inlinePageJs(fs.readFileSync(path.join(RAIZ, pagina), "utf-8"), RAIZ);
  return new JSDOM(html, { url: "https://localhost/", runScripts: "dangerously", virtualConsole: new VirtualConsole(), beforeParse(w) {
    global.window = w; global.document = w.document; global.navigator = w.navigator;
    w.d3 = require("d3"); try { w.eval(fs.readFileSync(path.join(RAIZ, "assets", "mapas.js"), "utf-8")); } catch (e) {}
    class Chart { constructor() {} } Chart.defaults = { font: {}, color: "", plugins: { legend: { labels: {} }, tooltip: {} }, elements: {} }; w.Chart = Chart;
    w.fetch = (rel) => { try { const txt = fs.readFileSync(path.join(RAIZ, String(rel).replace(/^\.\//, "")), "utf-8");
      return Promise.resolve({ ok: true, json: () => Promise.resolve(JSON.parse(txt)), text: () => Promise.resolve(txt) }); } catch (e) { return Promise.resolve({ ok: false }); } };
  } });
}

(async () => {
  const falhas = []; let figuras = 0, elementos = 0;
  for (const pagina of PAGINAS) {
    const dom = renderizar(pagina); await new Promise(r => setTimeout(r, 1800));
    const d = dom.window.document;
    const registrar = (onde, papel, texto, extras = []) => {
      if (!texto) return; elementos++;
      const a = classificar(texto).concat(extras);
      if (a.length) falhas.push(`${pagina} › ${onde} › ${papel}: ${a.join(" · ")} — "${texto.slice(0, 90)}"`);
    };
    d.querySelectorAll(".figura").forEach(c => {
      figuras++; const id = c.id || t(c.querySelector(".figura-titulo")).slice(0, 40) || "(sem id)";
      const ti = t(c.querySelector(".figura-titulo")); registrar(id, "título", ti, ti.length > 100 ? [`título com ${ti.length} caracteres (máx. 100)`] : []);
      registrar(id, "subtítulo", t(c.querySelector(".figura-sub")));
      c.querySelectorAll(".figura-leitura").forEach(e => { const s = t(e); registrar(id, "leitura", s, [].concat(frases(s) > 2 ? [`${frases(s)} frases (máx. 2)`] : [], s.length > 240 ? [`${s.length} caracteres (máx. 240)`] : [])); });
      c.querySelectorAll(".map-legend span, .map-legend li, .map-legend b").forEach(e => { const s = t(e); if (!e.querySelector("span, li")) registrar(id, "item de legenda", s, s.length > 140 ? [`item de legenda com ${s.length} caracteres (máx. 140)`] : []); });
      registrar(id, "crédito", t(c.querySelector(".fonte-figura")));
      c.querySelectorAll("summary").forEach(e => registrar(id, "resumo", t(e)));
      c.querySelectorAll(".figura-midia text, .figura-midia .vazio, .figura-midia .lacuna").forEach(e => registrar(id, "rótulo na mídia", t(e)));
    });
    // cartões de indicador e legendas fora de figura (medidores da home, três números, contador)
    d.querySelectorAll(".cartao--kpi, .contador-zone .note, .contador-zone .gauge-ends, .gauge-head .glabel, .gfaixa-badge, .map-legend:not(.figura .map-legend)").forEach(e => registrar(e.id || e.className.split(" ")[0], "indicador", t(e)));
  }
  // tooltips: strings literais dos scripts das páginas (o DOM só as cria no hover)
  const js = fs.readdirSync(path.join(RAIZ, "assets", "js")).filter(f => f.endsWith(".js"));
  for (const f of js) {
    const src = fs.readFileSync(path.join(RAIZ, "assets", "js", f), "utf-8").replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");
    const re = /showTip\(([\s\S]*?),\s*(?:evt|\{clientX)/g; let m;
    while ((m = re.exec(src))) {
      const literais = (m[1].match(/(['"`])((?:\\.|(?!\1)[\s\S])*?)\1/g) || []).map(s => s.slice(1, -1).replace(/\$\{[^}]*\}/g, " ").replace(/<[^>]+>/g, " ")).join(" ");
      elementos++; const a = classificar(literais);
      if (a.length) falhas.push(`assets/js/${f} › tooltip: ${a.join(" · ")} — "${literais.replace(/\s+/g, " ").trim().slice(0, 90)}"`);
    }
  }
  if (listar) console.log(`  ${figuras} figuras · ${elementos} textos verificados`);
  if (falhas.length) {
    console.log("✗ LEGENDAS: texto de figura com juízo, interpretação, causa não demonstrada, afirmação acima do teto ou fora do tamanho:");
    falhas.forEach(f => console.log("   - " + f)); process.exit(1);
  }
  console.log(`✓ LEGENDAS OK — ${figuras} figuras e ${elementos} textos de figura descrevem sem avaliar, interpretar ou atribuir causa (regra editorial de 15/09/2026).`);
})();
