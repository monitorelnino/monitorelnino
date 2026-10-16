#!/usr/bin/env node
/* Texto público — UM verificador, UMA renderização por página (consolidação item 3; 13 e 16/10/2026).
 * Fundiu, nesta ordem: verificar_vocabulario_publico.js + verificar_voz_editorial.js (13/10) e, em 16/10,
 * verificar_legendas.js (portão 19), verificar_semana_epidemiologica.js, verificar_palavras.js,
 * verificar_figuras.js, verificar_fichas_semanticas.js, verificar_imprensa_do_dado.js,
 * verificar_textos_enquadramento.py, verificar_vocabulario_dos_scripts.py e o `--so-texto-proibido` de
 * verificar_conformidade.py. Nove scripts renderizavam as mesmas páginas, com o mesmo jsdom, para olhar
 * o mesmo texto — e dois deles com a URL errada, de modo que o leitor do catálogo servia o texto da
 * página inicial em todas. As REGRAS moram em `layout/regras.json` (texto_publico, vocabulario_proibido);
 * aqui só se julga. Dentro de bloco `data-proveniencia="1"` nome de arquivo e caminho são o assunto (v3.1 §9).
 * Uso: node scripts/verificar_texto_publico.js [--forma] [--listar] [--autoteste]
 *   sem --forma: o que barra a publicação (jargão, refrão, vocabulário, semana, legendas, prosa, figura,
 *   fichas, palavras, enquadramento, imprensa); --forma acrescenta as regras de FORMA (A7-03: só no PR). */
const fs = require("fs"), path = require("path");
const { JSDOM, VirtualConsole } = require("jsdom"); const { inlinePageJs } = require("./_inline_js");
const S = require("../assets/semana.js");
const RAIZ = path.join(__dirname, "..");
const listar = process.argv.includes("--listar"), comForma = process.argv.includes("--forma");
const ler = (rel) => JSON.parse(fs.readFileSync(path.join(RAIZ, rel), "utf-8"));
const R = ler("layout/regras.json"), T = R.texto_publico, L = T.legendas, F = T.figura_componente, V = R.vocabulario_proibido;
const re = (r) => [new RegExp(r.padrao, r.flags), r.motivo];
const rx = (lista, flags = "i") => (lista || []).map((p) => new RegExp(p, flags));
const JARGAO = T.jargao_interno.map(re), FORMA = T.forma.map(re), REFRAOS = T.refraos.map(re);
const SEMANA = T.semana.map((r) => [new RegExp(r.padrao, r.flags), r.nome]);
const EXCECOES = L.excecoes.map((r) => new RegExp(r.padrao, r.flags));
const LEXICO = [["avaliativo", rx(L.avaliativo)], ["interpretação", rx(L.interpretativo)], ["causalidade", rx(L.causal)], ["teto probatório", rx(L.teto)]];
const P = Object.fromEntries(Object.entries(L.prosa).map(([k, v]) => [k, Array.isArray(v) ? rx(v) : new RegExp(v, "i")]));
const PAGINAS = R.paginas_publicas.concat(T.paginas_extras.flatMap((p) => p.endsWith("*.html")
  ? (fs.existsSync(path.join(RAIZ, p.slice(0, -6))) ? fs.readdirSync(path.join(RAIZ, p.slice(0, -6))).filter((b) => b.endsWith(".html")).sort().map((b) => p.slice(0, -6) + b) : [])
  : [p])).filter((p) => fs.existsSync(path.join(RAIZ, p)));
const norm = (s) => String(s || "").replace(/\s+/g, " ").trim();
const t = (e) => norm(e ? e.textContent : "");

/* ── funções puras: cada uma é o que o autoteste prova sem página ───────────────────────────────── */
function achados(texto, textoDeProva, textoDeNota, forma) {
  const regras = forma ? JARGAO.concat(FORMA) : JARGAO;
  const fora = [];
  for (const [r, motivo] of regras) { const m = texto.match(r); if (m) fora.push(`${motivo}: ${[...new Set(m)].slice(0, 6).join(" | ")}`); }
  for (const [r, motivo] of regras.filter(([, mo]) => !/nome de arquivo|caminho de dados/.test(mo))) {
    const m = textoDeProva.match(r); if (m) fora.push(`${motivo} (bloco de prova): ${[...new Set(m)].slice(0, 6).join(" | ")}`); }
  for (const [r] of REFRAOS) { const m = textoDeNota.match(r);
    if (m && m.length >= T.refrao_a_partir_de) fora.push(`"${r.source}" aparece ${m.length}x em legendas/notas — consolide numa ficha ou nota única`); }
  return fora;
}
/* Vocabulário proibido: global + por página + `texto_proibido` do contrato (sensível à caixa, de propósito:
 * barra "FIGURA", não "figura"), advérbio colado a número, locução de dever. Mesma régua do antigo
 * verificar_conformidade.problemas_de_vocabulario. */
function vocabulario(texto, pagina, contrato) {
  const tx = texto || "", baixo = tx.toLowerCase(), p = [];
  const proibidas = [...new Set([].concat(V.global || [], (V.por_pagina || {})[pagina] || [], (contrato || {}).texto_proibido || []))].sort();
  for (const w of proibidas) { const i = tx.indexOf(w); if (w && i >= 0) p.push(`vocabulário proibido: '${w}' — …${tx.slice(Math.max(0, i - 40), i + 40)}`); }
  for (const adv of V.com_numero || []) { const m = new RegExp("\\b" + adv + "\\s+\\d").exec(baixo); if (m) p.push(`juízo colado a número: '${adv}' — …${tx.slice(Math.max(0, m.index - 30), m.index + 40)}`); }
  for (const loc of V.dever || []) { const i = baixo.indexOf(loc.toLowerCase()); if (i >= 0) p.push(`locução de dever fora de citação de lei: '${loc}' — …${tx.slice(Math.max(0, i - 40), i + 40)}`); }
  return p;
}
/* O texto de marcação que os scripts de página escrevem (entre `>` e `<` em literais), sem interpolação:
 * é como o cartão de estado dizia "(Atom)" dentro de um <dialog> que só abre no clique (09/10/2026). */
function textosDeMarcacao(fonte) {
  return [...String(fonte).replace(/\$\{[^{}]*\}/g, " ").matchAll(/>([^<>`'"]{2,400})</g)].map((m) => m[1].trim()).filter((x) => /[A-Za-zÀ-ÿ]{3}/.test(x));
}
const semana = (texto) => SEMANA.filter(([r]) => r.test(texto)).map(([r, nome]) => { const m = r.exec(texto); return `${nome} — …${JSON.stringify(texto.slice(Math.max(0, m.index - 50), m.index + 60))}`; });
const semExcecoes = (s) => EXCECOES.reduce((x, r) => x.replace(r, " "), s);
function classificar(texto) {
  const x = semExcecoes(texto), a = [];
  for (const [rot, lista] of LEXICO) for (const r of lista) { const m = x.match(r); if (m) a.push(`${rot}: "${m[0]}"`); }
  const caps = x.match(/\b[A-ZÁÉÍÓÚÂÊÔÃÕÇ]{2,}\b(?:\s+[A-ZÁÉÍÓÚÂÊÔÃÕÇ]{2,}\b)+/g);
  if (caps && caps.some((c) => c.split(/\s+/).some((w) => w.length > L.caixa_alta_palavra_maior_que))) a.push(`ênfase em caixa alta: "${caps[0]}"`);
  return a;
}
const frases = (s) => s.split(/[.!?](?:\s|$)/).filter((x) => x.trim().length > 0).length;
/* Prosa (voz editorial §10): `contexto` = {citacao, fichaOuLei} lidos dos atributos declarados no HTML. */
function prosa(s, contexto) {
  const a = [];
  if (!contexto.citacao && P.travessao_pontuacao.test(s)) a.push("travessão como pontuação de frase (reescreva com vírgula, ponto, ou duas frases)");
  if (contexto.fichaOuLei) return a;
  a.push(...classificar(s));
  if (P.enfase.test(semExcecoes(s))) a.push('ênfase "só/única/nunca/sempre"');
  if (/\?/.test(s)) a.push("interrogação");
  if (P.lei.test(s)) a.push("artigo de lei fora da ficha/bloco legal");
  if (P.denuncia.test(s)) a.push('"denuncia/expõe"');
  if (P.autorreferencia.test(s)) a.push("o site falando de si (vai para a ficha)");
  if (P.processo.test(s)) a.push('processo narrado ("carregando")');
  if (P.traco_vazio.test(s)) a.push('"—" em frase corrida (use "sem coleta até {corte}")');
  for (const r of P.glossario) { const m = s.match(r); if (m) a.push(`glossário: "${m[0]}"`); }
  return a;
}
function palavras(html) {
  const x = html.replace(/<script[\s\S]*?<\/script>/g, "").replace(/<style[\s\S]*?<\/style>/g, "").replace(/<nav class="mainnav"[\s\S]*?<\/nav>/g, "")
    .replace(/<footer[\s\S]*?<\/footer>/g, "").replace(/<p class="figura-sub"[^>]*>[\s\S]*?<\/p>/g, "")
    .replace(/<div class="panel[^"]*" id="[a-z0-9-]+" data-proveniencia="1"[\s\S]*?<\/div>\s*(?=<div class="panel|<\/main|<!--)/g, "");
  return x.replace(/<[^>]+>/g, " ").split(/\s+/).filter(Boolean).length;
}
function enquadramento(fonte) {
  const E = T.enquadramento, tx = fonte || "", i = tx.indexOf(E.inicio);
  if (i < 0) return [`bloco do enquadramento não encontrado em ${E.arquivo} — sem bloco não há o que conferir`];
  const j = tx.indexOf("\nfunction ", tx.indexOf(E.funcao, i) + 1), bloco = tx.slice(i, j > i ? j : undefined), ruins = [];
  for (const [fam, frase] of Object.entries(E.aprovados)) if (!bloco.includes(frase)) ruins.push(`texto de ${fam} ausente ou alterado — ele é literal e aprovado: ${frase.slice(0, 60)}…`);
  for (const c of E.complementos) if (!bloco.includes(`'${c}'`)) ruins.push(`complemento de risco '${c}' ausente do vocabulário fechado`);
  for (const m of bloco.matchAll(new RegExp(E.dever, "gi"))) ruins.push(`palavra de dever/obrigação/recomendação no bloco, linha ${bloco.slice(0, m.index).split("\n").length} do trecho: '${m[0]}' — nenhuma destas listas cria dever de plano para o município`);
  return ruins;
}
const CREDITO = new RegExp(F.credito), CREDITO_EXPLICA = new RegExp(F.credito_explicacao, "i");
const credito = (s) => (!CREDITO.test(s) ? [`crédito fora do formato "Fonte: … · Atualização: dd/mm/aaaa" — "${s.slice(0, 80)}"`] : [])
  .concat(s.length > F.credito_maximo ? [`crédito longo demais (${s.length} caracteres)`] : [], CREDITO_EXPLICA.test(s) ? [`crédito com explicação — "${s.slice(0, 80)}"`] : []);
const ESTADOS = rx(F.subtitulo_estados, "");
const subtitulo = (s) => (s.length > F.subtitulo_maximo || (!s.includes("·") && !ESTADOS.some((r) => r.test(s)))) ? [`subtítulo fora do padrão (≤ ${F.subtitulo_maximo} caracteres, separado por "·") — "${s.slice(0, 60)}"`] : [];
const fichaIncompleta = (ficha, obrigatorios) => (obrigatorios || []).filter((c) => { const v = (ficha || {})[c]; return v == null || (typeof v === "string" && !v.trim()) || (Array.isArray(v) && !v.length); });

/* ── a renderização, uma por página ─────────────────────────────────────────────────────────────── */
function renderizar(pagina) {
  const html = inlinePageJs(fs.readFileSync(path.join(RAIZ, pagina), "utf-8"), RAIZ);
  // A URL leva o NOME da página: `assets/catalogo.js` escolhe o catálogo pelo caminho, e com "/" ele servia
  // o texto da inicial (ou o de reserva) em todas — portão que lê outra página não confere nada.
  return new JSDOM(html, { url: "https://localhost/" + pagina, runScripts: "dangerously", virtualConsole: new VirtualConsole(), beforeParse(w) {
    global.window = w; global.document = w.document; global.navigator = w.navigator; w.d3 = require("d3");
    try { w.eval(fs.readFileSync(path.join(RAIZ, "assets", "mapas.js"), "utf-8")); } catch (e) {}
    // Chart simulado: SÓ o que vira texto na tela entra na varredura da semana (rótulos do eixo, nomes das
    // séries, títulos de eixo). Os valores não — '201447' é um número de casos, não ano+semana.
    w.__rotulos = [];
    class Chart { constructor(ctx, cfg) { const d = (cfg && cfg.data) || {}; try {
      w.__rotulos.push((d.labels || []).join(" "), (d.datasets || []).map((s) => s && s.label).filter(Boolean).join(" "));
      Object.values(((cfg && cfg.options) || {}).scales || {}).forEach((e) => { if (e && e.title && e.title.text) w.__rotulos.push(String(e.title.text)); }); } catch (e) {} } }
    Chart.defaults = { font: {}, color: "", plugins: { legend: { labels: {} }, tooltip: {} }, elements: {} }; w.Chart = Chart;
    w.fetch = (rel) => { try { const txt = fs.readFileSync(path.join(RAIZ, String(rel).replace(/^\.?\//, "").split("?")[0]), "utf-8");
      return Promise.resolve({ ok: true, json: () => Promise.resolve(JSON.parse(txt)), text: () => Promise.resolve(txt) }); } catch (e) { return Promise.resolve({ ok: false, status: 404 }); } };
  } });
}

function julgarPagina(pagina, dom, fichas, vistas) {
  const d = dom.window.document, falhas = [], contrato = ler0("layout/contratos/" + (pagina.startsWith("blog/") ? "blog-post" : pagina.replace(".html", "")) + ".json");
  const f = (x) => falhas.push(`${pagina} › ${x}`);
  // (1) figuras: componente, portão 19 e fichas semânticas
  let figuras = 0, elementos = 0;
  const registrar = (onde, papel, texto, extras = []) => { if (!texto) return; elementos++; const a = classificar(texto).concat(extras); if (a.length) f(`${onde} › ${papel}: ${a.join(" · ")} — "${texto.slice(0, 90)}"`); };
  d.querySelectorAll(".figura").forEach((c) => {
    figuras++; const id = c.id || t(c.querySelector(".figura-titulo")).slice(0, 40) || "(sem id)";
    const exc = (L.tamanhos_por_figura || {})[`${pagina}#${c.id}`], TAM = Object.assign({}, L.tamanhos, exc && exc.motivo && exc.registrado_em && exc.decidido_por ? exc : {});
    const ruins = [...c.querySelectorAll(F.proibidos)].filter((e) => { const det = e.tagName === "DETAILS" ? e : e.closest("details");
      if (det && (det.querySelector("table") || det.dataset.alternativa === "dados")) return false;
      if (F.partes.some((k) => e.classList.contains(k)) || e.closest(".cartao-mapa-leitura") || e.closest(".cartao-mapa-rodape")) return false; return true; });
    if (ruins.length) f(`${id}: ${ruins.length} elemento(s) proibido(s) na figura — ${ruins.slice(0, 2).map((e) => e.tagName.toLowerCase() + ": " + t(e).slice(0, 70)).join(" | ")}`);
    const ti = t(c.querySelector(".figura-titulo")); if (!ti) f(`${id}: figura sem título`);
    registrar(id, "título", ti, ti.length > TAM.titulo ? [`título com ${ti.length} caracteres (máx. ${TAM.titulo})`] : []);
    const subs = c.querySelectorAll(".figura-sub"); if (!subs.length) f(`${id}: figura sem subtítulo (período · variável · unidade)`); if (subs.length > 1) f(`${id}: ${subs.length} subtítulos (máximo 1)`);
    subs.forEach((e) => registrar(id, "subtítulo", t(e), subtitulo(t(e))));
    c.querySelectorAll(".figura-leitura").forEach((e) => { const s = t(e); registrar(id, "leitura", s, [].concat(
      !L.leituras_aprovadas.includes(s) && frases(s) > TAM.leitura_frases ? [`${frases(s)} frases (máx. ${TAM.leitura_frases})`] : [], s.length > TAM.leitura ? [`${s.length} caracteres (máx. ${TAM.leitura})`] : [])); });
    c.querySelectorAll(".map-legend span, .map-legend li, .map-legend b").forEach((e) => { const s = t(e); if (!e.querySelector("span, li")) registrar(id, "item de legenda", s, s.length > TAM.item_de_legenda ? [`item de legenda com ${s.length} caracteres (máx. ${TAM.item_de_legenda})`] : []); });
    const cred = c.querySelectorAll(".fonte-figura"); if (!cred.length) f(`${id}: figura sem crédito de fonte`); if (cred.length > 1) f(`${id}: ${cred.length} créditos (máximo 1)`);
    cred.forEach((e) => registrar(id, "crédito", t(e), credito(t(e))));
    c.querySelectorAll("summary").forEach((e) => registrar(id, "resumo", t(e)));
    c.querySelectorAll(".figura-midia text, .figura-midia .vazio, .figura-midia .lacuna").forEach((e) => registrar(id, "rótulo na mídia", t(e)));
    if (fichas) { if (!c.id) f("figura sem id — não há como fichá-la (§35)"); else { const chave = `${pagina}#${c.id}`; vistas.add(chave);
      if (!fichas.fichas[chave]) f(`${chave}: figura sem ficha semântica (§35)`); else fichaIncompleta(fichas.fichas[chave], fichas.campos_obrigatorios).forEach((campo) => f(`${chave}: campo obrigatório vazio na ficha — '${campo}' (§35)`)); } }
  });
  d.querySelectorAll(F.creditos_de_cartao).forEach((e) => { if (!CREDITO.test(t(e))) f(`crédito de cartão fora do formato único — "${t(e).slice(0, 80)}"`); });
  d.querySelectorAll(L.indicadores).forEach((e) => registrar(e.id || e.className.split(" ")[0], "indicador", t(e)));
  // (2) prosa (voz editorial §10), só nas páginas de dados declaradas
  if (L.prosa_em.includes(pagina)) d.querySelectorAll("main p, main li, main dd, main summary, main figcaption, dialog p, dialog li, dialog dd").forEach((e) => {
    if (e.closest(".figura") || e.querySelector("p, li")) return; const s = t(e); if (!s || s.length < 12) return; elementos++;
    const a = prosa(s, { citacao: !!e.closest('[data-voz="citacao"]'), fichaOuLei: !!(e.closest('[data-voz="ficha"]') || e.closest('[data-voz="lei"]') || e.closest('[data-proveniencia="1"]') || e.closest('[data-voz="citacao"]')) });
    if (a.length) { const alvo = e.closest("[id]"); f(`prosa (${alvo ? alvo.id : "?"}): ${a.join(" · ")} — "${s.slice(0, 90)}"`); } });
  // (3) semana no texto que o leitor vê e nos rótulos do Chart
  semana([(d.querySelector("main") || d.body).textContent, (dom.window.__rotulos || []).join(" ")].join("\n")).forEach((x) => f(`semana: ${x}`));
  // (4) identidade (16/09/2026): "MARÉ Legal" na navegação; "MARÉ Saúde" no h1 da Saúde
  if (pagina === "index.html" && !new RegExp(L.identidade.nav_de_index_traz).test(t(d.querySelector(".mainnav")))) f(`nav não traz "${L.identidade.nav_de_index_traz}" (identidade do índice principal)`);
  if (pagina === "saude.html" && !new RegExp(L.identidade.h1_de_saude_traz).test(t(d.querySelector("h1")))) f('h1 não traz "MARÉ Saúde"');
  // (5) imprensa: regra 0 — nada à mão que dependa do dado
  if (pagina === T.imprensa.pagina) imprensa(d).forEach(f);
  // (6) jargão, forma, refrão e vocabulário sobre o texto renderizado (fora de script/style/code/pre)
  const textoDeNota = [...d.querySelectorAll(".hint, .note, .card-body")].map((e) => e.textContent).join(" \n ");
  d.querySelectorAll("script, style, noscript, code, pre").forEach((e) => e.remove());
  const provas = [...d.querySelectorAll('[data-proveniencia="1"]')], textoDeProva = norm(provas.map((e) => e.textContent).join(" ")); provas.forEach((e) => e.remove());
  const corpo = norm(d.body.textContent);
  achados(corpo, textoDeProva, textoDeNota, comForma).forEach(f);
  vocabulario(corpo, pagina, contrato).forEach(f);
  return { falhas, figuras, elementos };
}
const ler0 = (rel) => { try { return ler(rel); } catch (e) { return {}; } };
function imprensa(d) {
  const I = T.imprensa, falhas = [], txt = (id) => t(d.getElementById(id));
  for (const id of I.obrigatorios) { if (!d.getElementById(id)) { falhas.push(`id '${id}' não existe mais — o portão cobra um campo que a página não tem`); continue; }
    const v = txt(id); if (!v || v === "—") falhas.push(`'${id}' ficou em "${v || "vazio"}" — é número ou data que vem do banco`); }
  const idx = ler("data/indice.json"), uf = Object.keys(idx).find((k) => k.length === 2), vm = String((idx[uf] || {}).metodo || "").match(/^v(\d+(?:\.\d+)*)/);
  const saude = ler("data/monitor_saude.json"), corpo = t(d.querySelector("main") || d.body);
  for (const [rot, v] of [["MARÉ Legal", vm && vm[1]], ["MARÉ Saúde", saude.versao != null ? String(saude.versao) : null]])
    if (v && new RegExp("vers[aã]o[^.]{0,20}" + v.replace(/\./g, "\\.")).test(corpo)) falhas.push(`a versão do ${rot} ("${v}") aparece no texto, e a editoria a tirou da página em 05/10/2026`);
  const verificadas = (saude.resumo || {}).verificadas;
  if (verificadas != null) { const m = /m[ée]dia dos (\d+) verificados/.exec(corpo);
    if (verificadas >= I.todas_as_ufs && m) falhas.push(`os ${I.todas_as_ufs} estados estão verificados e a página ainda diz "média dos ${m[1]} verificados"`);
    if (verificadas < I.todas_as_ufs && (!m || Number(m[1]) !== Number(verificadas))) falhas.push(`a página diz "${m ? m[1] : "—"}" estados verificados e data/monitor_saude.json diz "${verificadas}"`); }
  const vezes = ler("data/cadencia_publicacao.json").publicacoes_por_dia;
  if (vezes) { const m = /recalculados a cada publica[çc][ãa]o,\s*([^,.]+?)\s*vezes? por dia/.exec(corpo);
    if (!m || String(m[1]).trim() !== String(vezes)) falhas.push(`a página diz "${m ? m[1].trim() : "—"}" publicações por dia e data/cadencia_publicacao.json diz "${vezes}"`); }
  return falhas;
}

function autoteste() {
  const ok = [], E = T.enquadramento, bom = "const ENQ_TEXTO = {\n" + Object.values(E.aprovados).map((f) => `  x: '${f}',\n`).join("") + "};\nconst ENQ_TIPO = {d: 'deslizamento', e: 'enxurrada', i: 'inundação'};\nfunction enquadramentoBox(uf, nome){ return ''; }\nfunction outra(){ /* aqui o texto deve poder dizer deve */ }\n";
  const c = (n, cond) => ok.push([n, cond]);
  // jargão, forma, refrão
  c("nome de arquivo reprova", achados("veja data/estados.json", "", "", false).length === 2);
  c("'portão' reprova", achados("o portão reprovou", "", "", false).length === 1);
  c("nome de arquivo no bloco de prova passa", achados("", "arquivo indice.json", "", false).length === 0);
  c("'robô' no bloco de prova reprova", achados("", "o robô coletou", "", false).length === 1);
  c("texto limpo passa", achados("Decretos de emergência desde 29/06/2026.", "", "", true).length === 0);
  c("forma só com --forma", achados("em 2026-10-13", "", "", false).length === 0 && achados("em 2026-10-13", "", "", true).length === 1);
  c("slug em endereço não é data ISO", achados("blog/2026-10-06-seca", "", "", true).filter((a) => /data ISO/.test(a)).length === 0);
  c("molde não preenchido reprova (forma)", achados("Procurado em {canais}", "", "", true).length === 1);
  c("ressalva 3x é refrão", achados("", "", "peso zero. peso zero. peso zero.", false).length === 1);
  c("ressalva 2x não é refrão", achados("", "", "peso zero. peso zero.", false).length === 0);
  // vocabulário (régua do antigo verificar_conformidade.problemas_de_vocabulario)
  c("vocabulário: texto limpo passa", vocabulario("Os municípios com decreto no ciclo.", "x.html", {}).length === 0);
  c("vocabulário: palavra global proibida reprova", vocabulario("houve um desastre", "x.html", {}).some((x) => x.includes("desastre")));
  c("vocabulário: 'figura' em frase legítima NÃO é a numeração 'FIGURA'", vocabulario("a fonte primária de cada figura", "imprensa.html", {}).length === 0);
  c("vocabulário: juízo colado a número reprova", vocabulario("apenas 3 estados publicaram", "x.html", {}).some((x) => x.includes("juízo")));
  c("vocabulário: a mesma palavra longe de número NÃO reprova", !vocabulario("apenas o estado publicou", "x.html", {}).some((x) => x.includes("juízo")));
  c("vocabulário: locução de dever reprova", vocabulario("o município deve publicar o plano", "x.html", {}).some((x) => x.includes("dever")));
  c("vocabulário: proibido do contrato entra junto", vocabulario("Backlog da fila", "x.html", { texto_proibido: ["Backlog"] }).some((x) => x.includes("Backlog")));
  c("vocabulário: proibido por página entra", vocabulario("sem antecipação", "saude.html", {}).length === 1 && vocabulario("sem antecipação", "index.html", {}).length === 0);
  // texto que nasce em script (09/10/2026, ajuste 1)
  const vocabJs = (src) => textosDeMarcacao(src).flatMap((x) => vocabulario(x, "x.js", {}));
  c("scripts: o texto antigo do cartão reprova", vocabJs('<p class="note">Acompanhe: <a href="f.xml" type="application/atom+xml">feed de atualizações (Atom)</a> — x</p>').length > 0);
  // 16/10/2026 (editoria): nenhum texto sobre feed no site — o link do cartão do estado saiu.
  c("scripts: link com texto de feed reprova", vocabJs('<p class="note"><a href="feeds/${d.uf}.xml">Feed de atualizações de ${esc(d.nome)}</a></p>').length > 0);
  c("scripts: atributo type não é texto", vocabJs('<a type="application/atom+xml">Documento</a>').length === 0);
  c("scripts: palavra dentro de outra não casa", vocabJs("<p>anatomia do dado</p>").length === 0);
  // semana: a conversão de assets/semana.js contra o calendário do MS (quatro viradas de ano) e os padrões
  [[2023, 1, "1 a 7 de janeiro de 2023"], [2024, 1, "31 de dezembro de 2023 a 6 de janeiro de 2024"], [2025, 1, "29 de dezembro de 2024 a 4 de janeiro de 2025"], [2026, 1, "4 a 10 de janeiro de 2026"]]
    .forEach(([ano, n, esp]) => c(`semana 1 de ${ano}: ${esp}`, S.porExtenso(ano, n, false) === esp));
  let quatroDias = true; for (let ano = 2015; ano <= 2035; ano++) { const r = S.semanaParaDatas(ano, 1); let dias = 0;
    for (let i = 0; i < 7; i++) { const d = new Date(r.inicio.getTime() + i * 86400000); if (d.getUTCMonth() === 0 && d.getUTCFullYear() === ano) dias++; } if (dias < 4) quatroDias = false; }
  c("semana 1 tem ao menos 4 dias de janeiro, de 2015 a 2035", quatroDias);
  const r33 = S.semanaParaDatas(2026, 33); c("a semana vai de domingo a sábado", r33.inicio.getUTCDay() === 0 && r33.fim.getUTCDay() === 6);
  c("semana 33 de 2026: 16 a 22 de agosto", S.porExtenso(2026, 33, false) === "16 a 22 de agosto de 2026");
  c("travessia de mês: 30 de agosto a 5 de setembro de 2026", S.porExtenso(2026, 35, false) === "30 de agosto a 5 de setembro de 2026");
  c("travessia de ano traz os dois anos", /2023.*2024/.test(S.porExtenso(2024, 1, false)));
  c("semana 0, 54 e texto devolvem null", S.semanaParaDatas(2026, 0) === null && S.semanaParaDatas(2026, 54) === null && S.semanaParaDatas(2026, "x") === null);
  c("semana 53 só existe no ano que a tem (2026 não, 2020 sim)", S.semanaParaDatas(2026, 53) === null && S.semanaParaDatas(2020, 53) !== null);
  ["semana epidemiológica 33", "Semanas Epidemiológicas", "33 semana(s) fechada(s)", "SE 33", "SE33", "202637", "acumulado de 2026 até a semana 33"].forEach((x) => c(`semana: pega ${JSON.stringify(x)}`, semana(x).length > 0));
  ["na semana de 16 a 22 de agosto de 2026", "202.637 notificações", "de 1º de janeiro a 22 de agosto de 2026", "o ano de 2026", "SE Sergipe", "08/06/202652.4"].forEach((x) => c(`semana: não pega ${JSON.stringify(x)}`, semana(x).length === 0));
  // legendas (portão 19) e prosa — mutações que cada regra tem de pegar, e exceções que tem de respeitar
  c("legenda neutra passa", classificar("Municípios com decreto de emergência, por estado, até 10/10/2026").length === 0);
  c("avaliativo reprova", classificar("situação grave nos estados").some((x) => x.startsWith("avaliativo")));
  c("item oficial da ANA 'Grave' sozinho passa; 'situação grave' não", classificar("Grave").length === 0 && classificar("situação grave").length === 1);
  c("interpretação reprova", classificar("o mapa revela a desigualdade").some((x) => x.startsWith("interpretação")));
  c("causalidade reprova", classificar("casos subiram devido a chuva").some((x) => x.startsWith("causalidade")));
  c("teto probatório: 'não existe' reprova; 'sem plano localizado' passa", classificar("não existe plano").length === 1 && classificar("sem plano localizado").length === 0);
  c("caixa alta reprova; sigla curta passa", classificar("ATENÇÃO MÁXIMA").length === 1 && classificar("Fonte: ANA e INMET").length === 0);
  c("nome de doença não é juízo", classificar("síndrome respiratória aguda grave").length === 0);
  c("frase de privacidade aprovada passa", prosa("Não pedimos seu nome nem contato, só as informações sobre o documento. A conferência é feita pela nossa equipe.", {}).length === 0);
  c("prosa: travessão como pontuação reprova, mesmo em ficha; não em citação", prosa("Avisou — e choveu", { fichaOuLei: true }).length === 1 && prosa("Avisou — e choveu", { citacao: true, fichaOuLei: true }).length === 0);
  c("prosa: ênfase 'só' reprova fora da ficha", prosa("Só dois estados publicaram o plano.", {}).some((x) => x.includes("ênfase")));
  c("prosa: interrogação e artigo de lei reprovam fora da ficha", prosa("Quem decide? Art. 3 da Lei 12.608.", {}).length === 2 && prosa("Quem decide? Art. 3 da Lei 12.608.", { fichaOuLei: true }).length === 0);
  c("prosa: traço vazio reprova; travessão entre palavras não é traço vazio", prosa("Corte dos dados: —", {}).some((x) => x.includes("frase corrida")) && !prosa("Avisou, El Niño forte, com seca", {}).length);
  c("prosa: glossário e autorreferência reprovam", prosa("O arcabouço público, e o site não compara estados.", {}).length === 2);
  // componente de figura, palavras, enquadramento, fichas
  c("crédito no formato único passa", credito("Fonte: Cemaden · Atualização: 02/10/2026").length === 0 && credito("Fonte: INMET · Atualização: sem coleta até o corte").length === 0);
  c("crédito fora do formato ou com explicação reprova", credito("Cemaden, 2026").length === 1 && credito("Fonte: aguardamos o órgão · Atualização: 02/10/2026").length === 1);
  c("subtítulo sem '·' ou longo reprova", subtitulo("Período 2026").length === 1 && subtitulo("x".repeat(141) + " · y").length === 1 && subtitulo("2026 · municípios · contagem").length === 0);
  c("subtítulo de estado 'Sem atualização desde …' passa (portão 17 o exercita)", subtitulo("Sem atualização desde 01/09/2026 00:00").length === 0 && subtitulo("Sem dado").length === 1);
  c("palavras: conta a prosa, não script, nav, rodapé, legenda ou prova", palavras('<nav class="mainnav">a b</nav><p>um dois três</p><p class="figura-sub">x y</p><script>z z</script><footer>f</footer>') === 3);
  c("enquadramento: bloco correto passa", enquadramento(bom).length === 0);
  c("enquadramento: arquivo sem o bloco reprova", enquadramento("var x = 1;").some((p) => p.includes("não encontrado")));
  c("enquadramento: texto alterado ou ausente reprova", enquadramento(bom.replace("delimitação", "lista")).some((p) => p.includes("texto de seca")) && enquadramento(bom.replace(E.aprovados.fogo, "")).some((p) => p.includes("texto de fogo")));
  c("enquadramento: complemento removido reprova", enquadramento(bom.replace("e: 'enxurrada'", "e: 'x'")).some((p) => p.includes("'enxurrada' ausente")));
  c("enquadramento: 'deve', 'recomenda-se' e 'obrigatório' no bloco reprovam, com a linha", ["deve elaborar plano", "recomenda-se o plano", "plano obrigatório"].every((x) => enquadramento(bom.replace("return '';", "// " + x)).some((p) => p.includes("palavra de dever") && p.includes("linha"))));
  c("enquadramento: 'deve' FORA do bloco e 'desenvolve' não reprovam", enquadramento(bom.replace("return '';", "// desenvolve a lista")).length === 0);
  c("enquadramento: fonte vazia ou nula reprova sem quebrar", enquadramento("").length === 1 && enquadramento(null).length === 1);
  c("ficha completa passa; campo vazio ou lista vazia reprova", fichaIncompleta({ tipo: "mapa", universo: ["x"] }, ["tipo", "universo"]).length === 0 && fichaIncompleta({ tipo: " ", universo: [] }, ["tipo", "universo"]).length === 2);
  ok.forEach(([n, b]) => console.log(`  ${b ? "✓" : "✗"} ${n}`));
  const ruins = ok.filter(([, b]) => !b).length;
  console.log(ruins ? `✗ AUTOTESTE: ${ruins} falha(s)` : `✓ AUTOTESTE OK — ${ok.length} casos, sem página, sem rede e sem escrita.`);
  return ruins ? 1 : 0;
}

if (process.argv.includes("--autoteste")) process.exit(autoteste());
(async () => {
  if (autoteste() !== 0) process.exit(1);
  const falhas = [], fichas = ler0(F.fichas), vistas = new Set(); let figuras = 0, elementos = 0;
  for (const p of PAGINAS) {
    const dom = renderizar(p); await new Promise((r) => setTimeout(r, 2500));
    const r = julgarPagina(p, dom, fichas.fichas ? fichas : null, vistas); dom.window.close();
    figuras += r.figuras; elementos += r.elementos; falhas.push(...r.falhas);
    const html = fs.readFileSync(path.join(RAIZ, p), "utf-8"), lim = T.palavras_por_pagina[p];
    if (lim) { const n = palavras(html); if (n > lim[1]) falhas.push(`${p} › ${n} palavras estáticas (teto ${lim[1]})`); else if (n > lim[0]) console.log(`  ⚠ ${p}: ${n} palavras (meta §7: ${lim[0]}; teto ${lim[1]})`); }
    if (listar) console.log(`  ${r.falhas.length ? "✗" : "✓"} ${p}: ${r.figuras} figura(s), ${r.elementos} texto(s)`);
  }
  for (const chave of Object.keys((fichas.fichas) || {})) if (!vistas.has(chave)) falhas.push(`${chave}: ficha órfã — a figura não existe mais (§35)`);
  const marcas = Object.values(fichas.fichas || {}).map((x) => x.pergunta_que_responde).filter(Boolean);
  for (const p of PAGINAS) { const html = fs.readFileSync(path.join(RAIZ, p), "utf-8"); for (const m of marcas) if (html.includes(m)) falhas.push(`${p} › texto de ficha semântica renderizado na interface (§27, §35): "${m.slice(0, 60)}"`); }
  // tooltips (showTip) e texto de marcação dos scripts de página: o DOM só os cria no hover ou no clique
  for (const a of fs.readdirSync(path.join(RAIZ, "assets", "js")).filter((x) => x.endsWith(".js")).map((x) => "assets/js/" + x).concat("assets/mapas.js")) {
    const src = fs.readFileSync(path.join(RAIZ, a), "utf-8"), semComentario = src.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, ""), rt = /showTip\(([\s\S]*?),\s*(?:evt|\{clientX)/g; let m;
    while ((m = rt.exec(semComentario))) { const lit = (m[1].match(/(['"`])((?:\\.|(?!\1)[\s\S])*?)\1/g) || []).map((s) => s.slice(1, -1).replace(/\$\{[^}]*\}/g, " ").replace(/<[^>]+>/g, " ")).join(" ");
      elementos++; const x = classificar(lit); if (x.length) falhas.push(`${a} › tooltip: ${x.join(" · ")} — "${norm(lit).slice(0, 90)}"`); }
    for (const x of textosDeMarcacao(src)) vocabulario(x, a, {}).forEach((v) => falhas.push(`${a} › ${v} — ${JSON.stringify(x.slice(0, 80))}`));
  }
  enquadramento(fs.readFileSync(path.join(RAIZ, T.enquadramento.arquivo), "utf-8")).forEach((x) => falhas.push(`${T.enquadramento.arquivo} › ${x}`));
  if (falhas.length) { console.log(`✗ TEXTO PÚBLICO: ${falhas.length} problema(s). Publicação bloqueada.`); falhas.forEach((x) => console.log("   - " + x)); process.exit(1); }
  console.log(`✓ TEXTO PÚBLICO OK — ${PAGINAS.length} páginas, ${figuras} figuras e ${elementos} textos: sem jargão, refrão, termo proibido, semana ou juízo; componente de figura, fichas, palavras, enquadramento e Imprensa em dia${comForma ? "; forma em dia" : ""}.`);
})();
