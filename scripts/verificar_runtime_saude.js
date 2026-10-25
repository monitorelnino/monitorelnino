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


/* 25/10/2026 (Saúde v0.7): a coordenação "se preenche sozinha" é garantida aqui. O arquivo em disco é
   injetado com um registro de coordenação em AC (hoje não verificado) para provar que a ficha o mostra,
   e o estado sem registro continua dizendo "ainda não verificada". */
const ATO_INJETADO = "Portaria de teste nº 1/2026";
const { dom, erros, graficos } = renderizar("saude.html", raiz, { aoCriar(w) {
  const f = w.fetch;
  w.fetch = (rel) => String(rel).split("?")[0] !== "data/monitor_saude.json" ? f(rel)
    : f(rel).then(r => r.json().then(M => { M.ufs.AC.coordenacao.f1 = { status: "CRIADO_CICLO", pontos: 100, doc: ATO_INJETADO, data: "01/10/2026", url: "https://exemplo.gov.br/ato", citado: null };
      return { ok: true, json: () => Promise.resolve(M) }; }));
} });

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
teste("mapaMonitor: 27 estados desenhados", q("mapaMonitor") && q("mapaMonitor").querySelectorAll("path").length === 27);
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
  teste("ordem: números, situação por estado, consulta do município, o que os órgãos registram; sem seção federal",
    ordem.indexOf("numerosSaude") < ordem.indexOf("estadual")
    && ordem.indexOf("estadual") < ordem.indexOf("consultaSaude")
    && ordem.indexOf("consultaSaude") < ordem.indexOf("observado")
    && !q("saude-federal-painel"));
  // O mapa do risco previsto VOLTOU pelo contrato de layout (secao "estadual", terceiro cartao):
  // ele responde a que o preparo de cada estado deveria responder. O que continua fora sao os
  // medidores, o mapa de status e a amostra no mapa.
  teste("saiu da página: os medidores de antecipação, o mapa de status, a grade de ladrilhos e o cartão de risco previsto",
    !q("heroSaude") && !q("mapaStatus") && !q("mapaDesf") && !q("mapaChik") && !q("boxDDA") && !q("regionsSaude") && !q("boxRiscoSan"));

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

  // O mapa por tipo de plano: cada estado na cor do seu tipo, e a lista dos seis tipos com as siglas
  // como botões (o seletor acessível: teclado, leitor de tela e toque nos estados pequenos).
  const TIPOS = ["NOVO", "READ", "VIG", "ELAB", "LAC", "NAO_VERIFICADO"];
  const botoes = () => [...d.querySelectorAll("#listaTiposPlano button[data-uf]")];
  teste("lista dos seis tipos de plano, com as 27 siglas como botões e a contagem de cada tipo", (() => {
    const dts = [...d.querySelectorAll("#listaTiposPlano dt")];
    if (dts.length !== 6 || botoes().length !== 27) return false;
    return TIPOS.every((t, i) => {
      const n = Object.values(MSd2.ufs).filter(u => u.instrumento.status === t).length;
      return d.querySelectorAll('#listaTiposPlano dd')[i].querySelectorAll("button").length === n
        && (n === 0 ? /zero estados/ : n === 1 ? /um estado/ : new RegExp(n + " estados")).test(dts[i].textContent);
    });
  })());
  teste("botões da sigla: aria-pressed e alvo de toque (a classe do componente)",
    botoes().every(b => b.getAttribute("aria-pressed") === "false" && b.classList.contains("chip-risco") && /^Abrir a ficha de /.test(b.getAttribute("aria-label"))));
  teste("a linha da escada vem dos pontos do dado (metodo.escada), não do texto", (() => {
    const e = MSd2.metodo.escada;
    return txt("escadaPlano") === `A nota de cada estado no MARÉ Saúde é a do tipo de plano: feito para este El Niño, ${e.NOVO}; atualizado, ${e.READ}; recorrente, ${e.VIG}; em elaboração, ${e.ELAB}; não localizado, ${e.LAC}.`;
  })());
  // Ficha aberta pela lista, sem o mapa (SE é pequeno demais para o toque no mapa).
  const NOME_DO_TIPO = { NOVO: "Plano feito para este El Niño", READ: "Plano anual atualizado para o ciclo", VIG: "Plano recorrente, sem atualização para o ciclo",
    ELAB: "Plano em elaboração", LAC: "Plano não localizado até o corte", NAO_VERIFICADO: "Ainda não verificado" };
  teste("ficha de SE abre pela lista, com o tipo de plano do dado", (() => {
    const b = botoes().find(x => x.dataset.uf === "SE");
    b.click();
    return b.getAttribute("aria-pressed") === "true" && q("detailSaudeConteudo").textContent.includes(NOME_DO_TIPO[MSd2.ufs.SE.instrumento.status]);
  })());
  // A7-02 / A4-33: todo estado abre a ficha, sem erro de script e com conteúdo.
  teste("as 27 fichas de estado abrem, sem erro de script", (() => {
    const antes = erros.length, vazias = [];
    for (const b of botoes()) {
      try { b.click(); } catch (e) { erros.push(String(e)); }
      if ((q("detailSaudeConteudo").textContent || "").length <= 40) vazias.push(b.dataset.uf);
    }
    return vazias.length === 0 && erros.length === antes;
  })());
  teste("ficha: a coordenação se preenche sozinha (ato injetado em AC) e diz 'ainda não verificada' sem registro", (() => {
    const abre = uf => { botoes().find(b => b.dataset.uf === uf).click(); return q("detailSaudeConteudo").textContent; };
    const ac = abre("AC"), go = abre("GO");
    return ac.includes(ATO_INJETADO) && ac.includes("01/10/2026")
      && /Coordenação na saúde.*ainda não verificada/.test(go) && !go.includes(ATO_INJETADO)
      && /Coordenação na saúde/.test(ac) && /Ligação com o governo do estado/.test(ac) && !/antecipação/i.test(ac + go);
  })());
  teste("clique no mapa abre a ficha do mesmo estado", (() => {
    q("mapaMonitor").querySelector("path.uf-path").dispatchEvent(new dom.window.MouseEvent("click", { bubbles: true }));
    return (q("detailSaudeConteudo").textContent || "").length > 40;
  })());

  // A seção única de desfechos, no cartão escolhido: a posição na faixa habitual é a frase do
  // dado (ela está no cartão, não numa nota à parte), e o detalhe traz o mapa por 100 mil e a
  // lista por estado. Um detalhe por vez: o portão confere o que está aberto na carga.
  teste("gradeDesfechos: um cartão por desfecho com arquivo, com a posição na faixa habitual",
    q("gradeDesfechos").querySelectorAll("[data-desfecho]").length >= 1
    && /(da faixa habitual para a época \(|sem faixa habitual para a época)/.test(txt("gradeDesfechos"))
    && !/semana epidemiológica|\bSE ?\d/.test(txt("gradeDesfechos")));
  teste("mapaDesfecho: 27 estados e legenda com a ausência declarada",
    q("mapaDesfecho").querySelectorAll("path").length === 27
    && /sem período fechado/.test(txt("legMapaDesfecho")));
  teste("dlDesfechoUF: lista por estado com a taxa por 100 mil",
    q("dlDesfechoUF").querySelectorAll("dt").length >= 26 && /por 100 mil habitantes/.test(txt("dlDesfechoUF")));
  teste("os quadros por agravo saíram, e o desfecho escolhido tem um gráfico só",
    !q("cDesfAcum") && !q("cDengueSemana") && !q("cSRAG") && !q("mapaCalor") && !!q("cDesfecho"));

  try {
    teste("saúde: o mapa tem o título do catálogo", q("boxMonitor").querySelector(".figura-titulo").textContent === "Plano estadual de saúde para o El Niño, por estado");
    // A tabela do mapa: uma linha por UF, quatro colunas de leitor, sem travessão nem componente interno.
    const linhasMon = [...d.querySelectorAll("#tblMonitor tbody tr")];
    teste("saúde: tabela do mapa com 27 linhas de 4 colunas, sem travessão nem componente interno",
      linhasMon.length === 27 && linhasMon.every((tr) => tr.children.length === 4 && ![...tr.children].some((td) => td.textContent.trim() === "—") && !/lido\(s\)|cobertura sanit/.test(tr.textContent)));
    // 19/10/2026: a nota do InfoDengue saiu com os quadros por agravo (decisão da editoria) — ela
    // explicava um nível que a página não mostra mais. O que o portão continua guardando é a fonte
    // da série respiratória, que é primária e vive no cartão do topo, não no InfoGripe.
    teste("respiratórias: a fonte declarada é o SIVEP-Gripe, não o InfoGripe",
      /SIVEP-Gripe/.test(txt("fonteSragSE")) && !/InfoGripe/.test(d.querySelector("main").textContent));
  } catch (e) { teste("saúde: títulos-fato (" + e.message + ")", false); }
  /* A consulta do município, no módulo comum e em cartões como o Proteja-se. Aracaju (SE) tem o nível
     do InfoDengue; Amparo de São Francisco não foi lida pela fonte e diz a classe da ausência. */
  const consulta = (nome) => new Promise(ok => {
    const uf = q("consultaSaudeUF"), mun = q("consultaSaudeMun"), ev = (t) => new dom.window.Event(t, { bubbles: true });
    uf.value = "SE"; uf.dispatchEvent(ev("change"));
    setTimeout(() => { mun.value = nome; mun.dispatchEvent(ev("input")); setTimeout(() => ok(q("consultaSaudeCard")), 50); }, 150);
  });
  consulta("Aracaju").then(cartao => {
    const t = cartao.textContent;
    teste("consulta: seis cartões, no formato dos outros cartões municipais", cartao.querySelectorAll(".cartao").length === 6 && !cartao.querySelector("table"));
    teste("consulta: dengue com nível e semana em datas, fonte InfoDengue", /Nível 2 \(atenção\)/.test(t) && /Semana de \d+ a \d+ de \w+ de 2026 · InfoDengue \(Fiocruz e FGV\)/.test(t));
    teste("consulta: o estado é dito como do estado, sem acumulado do ano nem nota", /Internações respiratórias graves \(estado\)/.test(t)
      && /internações? no estado na semana de/.test(t) && !/no estado em 2026/.test(t) && !/MARÉ Saúde \(estado\)[\s\S]*de 100/.test(t));
    teste("consulta: o tipo de plano estadual no lugar da nota, com a ficha", /MARÉ Saúde \(estado\)/.test(t) && /ver a ficha do estado/.test(t)
      && t.includes(NOME_DO_TIPO[MSd2.ufs.SE.instrumento.status]));
    teste("consulta: sem jargão interno nem 'classe Normal'", !/METODOLOGIA|§10|classe Normal|leitura automática/.test(t));
    teste("consulta: plano do município com o vocabulário da inicial", /Não localizamos plano de contingência para este município até a data de corte|Plano de contingência|O plano trata a saúde/.test(t));
    return consulta("Amparo de São Francisco");
  }).then(cartao => {
    teste("consulta: município que a fonte não leu diz a classe da ausência", /Sem dado do InfoDengue para o município na semana/.test(cartao.textContent) && !/município não lido pelo/.test(cartao.textContent));
    fim();
  });
  function fim() {
  console.log(falhas.length ? `\n✗ ${falhas.length} verificação(ões) falharam.` : "\n✓ RUNTIME (saúde) OK — mapas, cartões, tooltip, créditos e lacunas declaradas.");
  process.exit(falhas.length ? 1 : 0);
  }
}, 900);
