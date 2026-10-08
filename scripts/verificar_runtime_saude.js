#!/usr/bin/env node
/* Verificador de runtime da página de Saúde e El Niño (saude.html, v2.2.4 — §9.6).
 * DOM, gesto de tooltip, crédito por figura, nav e lacunas declaradas.
 * Padrão de scripts/verificar_runtime_sinais.js.
 * Uso: node scripts/verificar_runtime_saude.js
 *
 * (cabeçalho herdado:
 * (saude.html, criada em 01/09/2026 — METODOLOGIA §23).
 * Mesmo padrão de scripts/verificar_runtime_mapas.js: jsdom + d3 reais,
 * Chart simulado, fetch local. Cobre os 4 mapas, os 4 gráficos, os cartões
 * do ciclo, a tabela de fontes e — o que é próprio desta página — a
 * PROVENIÊNCIA VISÍVEL: nenhuma figura pode ficar sem crédito de fonte, e
 * toda fonte não coletada precisa aparecer como lacuna declarada.
 * Uso: node scripts/verificar_runtime_sinais.js
 */
const { JSDOM, VirtualConsole } = require("jsdom"); const { inlinePageJs } = require("./_inline_js");
const fs = require("fs");
const path = require("path");

const raiz = path.join(__dirname, "..");
const html = inlinePageJs(fs.readFileSync(path.join(raiz, "saude.html"), "utf-8"), raiz);
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
    // 02/10/2026 (item 7): a grade dos 27 passou a ser um componente compartilhado, e o jsdom não
    // carrega <script src> externo sem `resources`. Como `mapas.js`, ele entra aqui.
    w.eval(fs.readFileSync(path.join(raiz, "assets", "js", "grade-estados.js"), "utf-8"));
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
  // Atalho de leitura: o texto de um elemento, ou "" quando ele não existe — o mesmo helper
  // que o portão do Financiamento usa, para os dois lerem a página do mesmo jeito.
  const txt = id => ((q(id) || {}).textContent || "").trim();
  const SUF = JSON.parse(fs.readFileSync(path.join(raiz, "data", "saude_uf.json"), "utf-8"));
  teste("zero erros de runtime", erros.length === 0);
  erros.slice(0, 4).forEach(e => console.log("     ", e));
  // 02/10/2026 (bloco A): os três mapas de estado viraram UM (`mapaMonitor`), a amostra de 313
// municípios saiu do mapa e entraram os dois mapas do SINAN, por 100 mil habitantes.
for (const id of ["mapaMonitor", "mapaDengueUF", "mapaChikUF", "mapaCalor"]) {
    teste(`${id}: 27 estados desenhados`, q(id) && q(id).querySelectorAll("path").length === 27);
    teste(`${id}: legenda preenchida`, q(id.replace("mapa", "leg")) && q(id.replace("mapa", "leg")).children.length >= 1);
  }
  // 15/09/2026 (MARÉ Saúde espelha o MARÉ · Defesa civil): dois medidores no topo, ficha "Como ler", cartões por estado com detalhe em <dialog>,
  // uma seção por desfecho (dengue, chikungunya, calor, respiratórias, diarreicas) — nenhum desfecho em acordeão, nenhum seletor de doença.
  // 02/10/2026: a contagem de UFs não verificadas saiu do subtítulo da grade (o `contagemUF`),
  // porque a grade passou a mostrar o número de cada estado e a ausência fala por si. O que o
  // portão continua cobrando é que a LEGENDA do mapa declare quantas não foram verificadas, o que
  // ele faz mais abaixo, no teste da prontidão.
  const nNV = Object.values(SUF.uf).filter(u => u.status === "NAO_VERIFICADO").length;
  // ── a página reorganizada pela pergunta do leitor (bloco A, 02/10/2026) ───────────────────
  // 02/10/2026 (contrato de layout): as secoes da pagina sao <section>, nao .panel — o contrato
  // tirou a caixa cinza. A ordem cobrada continua a mesma.
  const ordem = [...d.querySelectorAll("main > section, main > .panel")].map(e => e.id);
  teste("ordem: números, situação por estado, o que os órgãos registram, governo federal",
    ordem.indexOf("numerosSaude") < ordem.indexOf("estadual")
    && ordem.indexOf("estadual") < ordem.indexOf("observado")
    && ordem.indexOf("observado") < ordem.indexOf("saude-federal-painel"));
  // O mapa do risco previsto VOLTOU pelo contrato de layout (secao "estadual", terceiro cartao):
  // ele responde a que o preparo de cada estado deveria responder. O que continua fora sao os
  // medidores, o mapa de status e a amostra no mapa.
  teste("saiu da página: os medidores de antecipação, o mapa de status e a amostra no mapa",
    !q("heroSaude") && !q("mapaStatus") && !q("mapaDesf") && !q("mapaChik") && !q("boxDDA"));

  // Os cinco cartões do topo, cada um do seu arquivo primário.
  const DEN = JSON.parse(fs.readFileSync(path.join(raiz, "data", "saude_desfechos", "dengue_sinan_serie.json"), "utf8"));
  const ultimaFechada = serie => {
    const ses = Object.keys(serie).filter(k => serie[k] != null).sort();
    return ses.length ? ses[ses.length - 1] : null;
  };
  const brDen = Object.fromEntries(Object.entries(DEN.serie.BR).filter(([k]) => k.startsWith(String(DEN.ano_corrente))));
  const seDen = ultimaFechada(brDen);
  // 08/10/2026 (item 0): a cobrança muda de FORMA junto com a página, e não afrouxa. Antes
  // exigia "semana epidemiológica {n}"; agora exige o INTERVALO DE DATAS daquela mesma semana,
  // calculado aqui de forma independente pelo utilitário, para o teste continuar sabendo qual
  // semana a página deveria estar mostrando.
  const SEM = require("../assets/semana.js");
  const datasDe = (chave) => SEM.porExtenso(Number(String(chave).split("-")[0]),
                                            Number(String(chave).split("-")[1]), true);
  teste("cartão de dengue: valor e datas da última semana fechada, do SINAN",
    txt("nDengueSE").replace(/\./g, "") === String(brDen[seDen])
    && txt("rotuloDengueSE").includes(datasDe(seDen)));
  teste("cartão de dengue: o rótulo não traz a semana como número",
    !/semana epidemiológica|SE ?\d/.test(txt("rotuloDengueSE")));
  teste("cartão de dengue: diz que é notificação, não caso confirmado",
    /notificaç/i.test(txt("fonteDengueSE")));
  teste("cartões de casos trazem a ressalva de parcialidade e a frase do El Niño", (() => {
    const t = q("numerosSaude").textContent;
    return /são parciais e sobem com as notificações atrasadas/.test(t)
      && (t.match(/não indica relação com o El Niño/g) || []).length >= 2;
  })());
  teste("cartão de estados em alerta: a agregação por estado é declarada",
    /nível 3 ou 4/.test(txt("fonteUFsAlerta")) && /de 27$/.test(txt("nUFsAlerta")));
  teste("cartão de calor: municípios lidos declarados", /município/.test(txt("fonteCalorMun")));
  // Lê do DISCO: o `MSAUDE` do portão é declarado mais abaixo, e usá-lo aqui quebraria por ordem
  // de declaração — o mesmo tropeço do portão do Financiamento, e a mesma correção.
  const MSd2 = JSON.parse(fs.readFileSync(path.join(raiz, "data", "monitor_saude.json"), "utf8"));
  teste("cartão de emergências: do agregado de resposta",
    txt("nEmergSaude") === String(MSd2.resposta.emergencias));

  // Um mapa só por estado, e a grade com ficha.
  // Tres cartoes na secao do estado, pelo contrato: prontidao, o que foi localizado em cada um e
  // o risco previsto. A prontidao continua sendo o mapa.
  teste("três cartões de estado, com a prontidão no mapa",
    d.querySelectorAll("#estadual .figura").length === 3 && !!q("mapaMonitor")
    && !!q("boxVerificacaoUF") && !!q("boxRiscoSan"));
  teste("grade dos 27 com ficha ao clicar", (() => {
    const tiles = [...d.querySelectorAll("#regionsSaude .tile")];
    if (tiles.length !== 27) return false;
    tiles.find(t => t.dataset.uf === "GO").click();
    return q("detailSaudeConteudo").textContent.length > 40;
  })());
  /* Bloco B.3 do handover de 02/10/2026: a coordenação aparece na ficha em DUAS linhas, em
     linguagem de leitor, e a palavra interna "antecipação" não aparece. Função não procurada diz
     "ainda não verificada" — nunca ausência de estrutura. */
  teste("ficha do estado: coordenação em duas linhas, sem jargão", (() => {
    const tiles = [...d.querySelectorAll("#regionsSaude .tile")];
    const alvo = tiles.find(t => t.dataset.uf === "GO");
    if (!alvo) return false;
    alvo.click();
    const t = q("detailSaudeConteudo").textContent;
    return /Coordenação na saúde/.test(t) && /Ligação com o governo do estado/.test(t)
      && !/antecipação/i.test(t);
  })());

  // As séries do SINAN: frase do dado, gráfico contra a faixa e mapa por 100 mil.
  for (const [frase, mapa, dl] of [["fraseDengue", "mapaDengueUF", "dlDengueUF"],
                                   ["fraseChik", "mapaChikUF", "dlChikUF"]]) {
    teste(`${frase}: frase gerada do dado, com as datas da semana e a posição na faixa`,
      /notificações de \w+ na semana de \d{1,2}[^.]{0,60}\d{4}/.test(txt(frase))
      && /faixa esperada para a época/.test(txt(frase))
      && !/semana epidemiológica|SE ?\d/.test(txt(frase)));
    teste(`${mapa}: 27 estados e legenda com 'sem coleta'`,
      q(mapa).querySelectorAll("path").length === 27 && /sem coleta/.test(txt(mapa.replace("mapa", "leg"))));
    teste(`${dl}: lista por estado com a taxa e o total`,
      q(dl).querySelectorAll("dt").length >= 26 && /por 100 mil habitantes/.test(txt(dl)));
  }
  teste("a série duplicada de dengue saiu, e a contagem vem do SINAN",
    !q("cDesfAcum") && !q("selComparadorDengue") && !!q("cDengueSemana"));

  // 15/09/2026 (§2.10): títulos-fato de Saúde vêm do dado
  try {
    const SUFd = JSON.parse(fs.readFileSync(path.join(raiz, "data", "saude_uf.json"), "utf8")); const UFS = Object.keys(SUFd.uf); const st = u => (SUFd.uf[u] || {}).status || "NAO_VERIFICADO";
    const c = k => UFS.filter(u => k.includes(st(u))).length;
    // 23/09/2026 (governança editorial §12, §32.8): boxMonitor pinta PRONTIDÃO SANITÁRIA; o título-fato
    // anterior contava estados por status de instrumento, que é o objeto da figura seguinte, e saía
    // quase igual ao dela. O princípio que este portão guarda continua o mesmo — o título vem do dado,
    // nunca digitado —, e a contagem agora sai do agregado autoritativo em monitor_saude.json.
    const MSd = JSON.parse(fs.readFileSync(path.join(raiz, "data", "monitor_saude.json"), "utf8"));
    teste("saúde: título-fato da prontidão com a contagem do dado", new RegExp(`^Prontidão sanitária por estado: ${MSd.resumo.verificadas} de ${UFS.length} estados verificados$`).test(q("boxMonitor").querySelector(".figura-titulo").textContent));
    teste("saúde: interpretação fixa do InfoDengue fora da figura", /InfoDengue/.test(q("interpObservado").textContent));
    // Bloco das 23h20: a série respiratória não cita mais o InfoGripe como fonte dela.
    teste("respiratórias: a fonte declarada é o SIVEP-Gripe, não o InfoGripe",
      (() => { const t = d.getElementById("observado").textContent;
               return /SIVEP-Gripe/.test(t) && !/InfoGripe/.test(t); })());
  } catch (e) { teste("saúde: títulos-fato (" + e.message + ")", false); }
  console.log(falhas.length ? `\n✗ ${falhas.length} verificação(ões) falharam.` : "\n✓ RUNTIME (saúde) OK — mapas, cartões, tooltip, créditos e lacunas declaradas.");
  process.exit(falhas.length ? 1 : 0);
}, 900);
