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
const { renderizar } = require("./_inline_js");
const fs = require("fs");
const path = require("path");

const raiz = path.join(__dirname, "..");


const { dom, erros, graficos } = renderizar("saude.html", raiz);

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
  // 19/10/2026 (remoção aprovada pela editoria): os quadros por agravo saíram e com eles os três
// mapas de doença. Sobra o mapa de prontidão; o mapa do detalhe do desfecho é cobrado abaixo,
// junto do cartão e da lista, porque ele e eles são a mesma seção única.
for (const id of ["mapaMonitor"]) {
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
    !/semana epidemiológica|\bSE ?\d/.test(txt("rotuloDengueSE")));
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
  // A7-14 (12/10/2026): zero medido aparece por extenso no cartão ("zero"), pela régua de números.
  const _emerg = MSd2.resposta.emergencias;
  teste("cartão de emergências, se a página o tiver: do agregado de resposta",
    !q("nEmergSaude") || txt("nEmergSaude") === (_emerg == null ? "sem dado" : _emerg === 0 ? "zero" : Number(_emerg).toLocaleString("pt-BR")));

  // Um mapa só por estado, e a grade com ficha. Quantos cartoes a secao tem e em que ordem
  // e materia do contrato (verificar_conformidade); aqui se cobra o que so o DOM mostra:
  // a prontidao esta no mapa e o risco previsto tem figura propria.
  teste("prontidão no mapa e risco previsto na seção do estado",
    !!q("mapaMonitor") && !!q("boxRiscoSan"));
  teste("grade dos 27 com ficha ao clicar", (() => {
    const tiles = [...d.querySelectorAll("#regionsSaude .tile")];
    if (tiles.length !== 27) return false;
    tiles.find(t => t.dataset.uf === "GO").click();
    return q("detailSaudeConteudo").textContent.length > 40;
  })());
  // A7-02 (12/10/2026): a grade mostrava 0,0 em 21 cartões (o número ficava só no
  // `data-contar`) e nenhum portão comparava o cartão com o dado. Agora: todo estado verificado
  // ESCREVE a prontidão de `monitor_saude.json`, e o não verificado diz isso, sem número.
  teste("grade: cada cartão escreve a prontidão do dado, não 0,0", (() => {
    const U = MSd2.ufs || {};
    const tiles = [...d.querySelectorAll("#regionsSaude .tile")];
    if (tiles.length !== 27) return false;
    return tiles.every(t => {
      const m = U[t.dataset.uf] || {};
      const s = t.querySelector(".tile-score");
      if (!s) return false;
      if (!m.verificado) return /não verificado/.test(s.textContent);
      const escrito = parseFloat((s.textContent || "").replace(",", "."));
      return isFinite(escrito) && Math.abs(escrito - Number(m.prontidao)) < 0.06;
    });
  })());
  // A4-33 (12/10/2026): o portão abria só a ficha de GO, e MS, MT e PB lançavam ReferenceError
  // ao abrir (A4-02) com o portão verde. Agora abre as 27 e cobra conteúdo e nenhum erro novo.
  teste("as 27 fichas de estado abrem, sem erro de script", (() => {
    const antes = erros.length;
    const tiles = [...d.querySelectorAll("#regionsSaude .tile")];
    const vazias = [];
    for (const t of tiles) {
      try { t.click(); } catch (e) { erros.push(String(e)); }
      if ((q("detailSaudeConteudo").textContent || "").length <= 40) vazias.push(t.dataset.uf);
    }
    return tiles.length === 27 && vazias.length === 0 && erros.length === antes;
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

  // A seção única de desfechos, no cartão escolhido: a posição na faixa habitual é a frase do
  // dado (ela está no cartão, não numa nota à parte), e o detalhe traz o mapa por 100 mil e a
  // lista por estado. Um detalhe por vez: o portão confere o que está aberto na carga.
  teste("gradeDesfechos: um cartão por desfecho com arquivo, com a posição na faixa habitual",
    q("gradeDesfechos").querySelectorAll("[data-desfecho]").length >= 1
    && /(da faixa habitual \(|sem faixa habitual para a época)/.test(txt("gradeDesfechos"))
    && !/semana epidemiológica|\bSE ?\d/.test(txt("gradeDesfechos")));
  teste("mapaDesfecho: 27 estados e legenda com a ausência declarada",
    q("mapaDesfecho").querySelectorAll("path").length === 27
    && /sem período fechado/.test(txt("legMapaDesfecho")));
  teste("dlDesfechoUF: lista por estado com a taxa por 100 mil",
    q("dlDesfechoUF").querySelectorAll("dt").length >= 26 && /por 100 mil habitantes/.test(txt("dlDesfechoUF")));
  teste("os quadros por agravo saíram, e o desfecho escolhido tem um gráfico só",
    !q("cDesfAcum") && !q("cDengueSemana") && !q("cSRAG") && !q("mapaCalor") && !!q("cDesfecho"));

  // 15/09/2026 (§2.10): títulos-fato de Saúde vêm do dado
  try {
    const SUFd = JSON.parse(fs.readFileSync(path.join(raiz, "data", "saude_uf.json"), "utf8")); const UFS = Object.keys(SUFd.uf); const st = u => (SUFd.uf[u] || {}).status || "NAO_VERIFICADO";
    const c = k => UFS.filter(u => k.includes(st(u))).length;
    // 23/09/2026 (governança editorial §12, §32.8): boxMonitor pinta PRONTIDÃO SANITÁRIA; o título-fato
    // anterior contava estados por status de instrumento, que é o objeto da figura seguinte, e saía
    // quase igual ao dela. O princípio que este portão guarda continua o mesmo — o título vem do dado,
    // nunca digitado —, e a contagem agora sai do agregado autoritativo em monitor_saude.json.
    // 16/10/2026 (lote 6, bloco 3): o título identifica o objeto — "MARÉ Saúde por estado, de 0
    // a 100" —, e quem não foi verificado é dito no subtítulo; "prontidão" sai da página.
    teste("saúde: o mapa do índice tem o título do catálogo, sem \"prontidão\"", q("boxMonitor").querySelector(".figura-titulo").textContent === "MARÉ Saúde por estado, de 0 a 100" && !/prontid/i.test(d.querySelector("main").textContent));
    // Lote 6, §2: a tabela do mapa tem as seis colunas de leitor, uma linha por UF, sem travessão.
    const linhasMon = [...d.querySelectorAll("#tblMonitor tbody tr")];
    teste("saúde: tabela do índice com 27 linhas de 6 colunas, sem travessão nem componente interno",
      linhasMon.length === 27 && linhasMon.every((tr) => tr.children.length === 6 && ![...tr.children].some((td) => td.textContent.trim() === "—") && !/lido\(s\)|cobertura sanit/.test(tr.textContent)));
    // 19/10/2026: a nota do InfoDengue saiu com os quadros por agravo (decisão da editoria) — ela
    // explicava um nível que a página não mostra mais. O que o portão continua guardando é a fonte
    // da série respiratória, que é primária e vive no cartão do topo, não no InfoGripe.
    teste("respiratórias: a fonte declarada é o SIVEP-Gripe, não o InfoGripe",
      /SIVEP-Gripe/.test(txt("fonteSragSE")) && !/InfoGripe/.test(d.querySelector("main").textContent));
  } catch (e) { teste("saúde: títulos-fato (" + e.message + ")", false); }
  console.log(falhas.length ? `\n✗ ${falhas.length} verificação(ões) falharam.` : "\n✓ RUNTIME (saúde) OK — mapas, cartões, tooltip, créditos e lacunas declaradas.");
  process.exit(falhas.length ? 1 : 0);
}, 900);
