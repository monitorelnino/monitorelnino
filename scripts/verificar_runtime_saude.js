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
teste("mapa dos planos saiu (handover VIGIAR §A): não há mapaMonitor, a lista dos tipos fica", !q("mapaMonitor") && !!q("listaTiposPlano"));
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

  // Os quatro cartões do topo leem `topo_saude.json` (semana consolidada, valor do país e quantos
  // estados estão acima da faixa habitual). A prova é independente: o valor e a semana do cartão
  // têm de ser os do `consolidado` do arquivo comum do desfecho, que é de onde o topo nasce.
  const SEM = require("../assets/semana.js");
  const datasDe = (chave) => SEM.porExtenso(Number(String(chave).split("-")[0]),
                                            Number(String(chave).split("-")[1]), true);
  const TS = JSON.parse(fs.readFileSync(path.join(raiz, "data", "saude_desfechos", "topo_saude.json"), "utf8"));
  const comum = d => JSON.parse(fs.readFileSync(path.join(raiz, "data", "saude_desfechos", d + ".json"), "utf8")).ultimo.BR;
  for (const [d, nid, eid, sid, fid] of [["dengue", "nDengueSE", "estadosDengueSE", "semanaDengueSE", "fonteDengueSE"],
      ["srag", "nSragSE", "estadosSragSE", "semanaSragSE", "fonteSragSE"], ["chikungunya", "nChikSE", "estadosChikSE", "semanaChikSE", "fonteChikSE"]]) {
    const x = TS.desfechos[d], c = comum(d).consolidado;
    teste(`cartão de ${d}: valor e datas da semana consolidada, ou a lacuna dita`, x.valor_br == null
      ? !/^\d/.test(txt(nid)) && /sem semana em comum/.test(txt(sid))
      : txt(nid).replace(/\./g, "") === String(c.valor) && txt(sid) === "semana " + datasDe(c.periodo));
    teste(`cartão de ${d}: quantos estados acima da faixa, pelo número do arquivo`,
      x.ufs_acima_faixa === 0 ? /nenhum estado acima da faixa habitual para a época/.test(txt(eid))
      : new RegExp(`${x.ufs_acima_faixa}.*estados? acima da faixa habitual para a época|um estado acima`).test(txt(eid)));
    teste(`cartão de ${d}: fonte e data de consulta`, /^Fonte: .+ · consultado em \d{2}\/\d{2}\/\d{4}$/.test(txt(fid)));
    teste(`cartão de ${d}: a semana não vem como número`, !/semana epidemiológica|\bSE ?\d/.test(txt(sid)));
  }
  teste("cartões de casos: a unidade é notificação (dengue, chikungunya) e caso hospitalizado notificado (SRAG)",
    /notificaç/i.test(q("cartaoDengue").textContent) && /hospitalizad/i.test(q("cartaoSrag").textContent));
  teste("a linha única sob a fileira não fala em El Niño nem em relação",
    !/El Niño|relação/.test(q("numerosSaude").textContent));
  teste("cartão de estados em alerta: a agregação por estado é declarada",
    /nível 3 ou 4/.test(q("cartaoAlerta").textContent) && /de 27$/.test(txt("nUFsAlerta")));
  teste("calor é linha de contexto com os municípios lidos, não cartão",
    !q("nCalorMun") && /^Calor: .+ dos .+ municípios em classe severa ou extrema de excesso de calor \(.+, \d{2}\/\d{2}\/\d{4}\)\.$/.test(txt("linhaCalorSaude")));
  // Lê do DISCO: o `MSAUDE` do portão é declarado mais abaixo, e usá-lo aqui quebraria por ordem
  // de declaração — o mesmo tropeço do portão do Financiamento, e a mesma correção.
  const MSd2 = JSON.parse(fs.readFileSync(path.join(raiz, "data", "monitor_saude.json"), "utf8"));
  // A7-14 (12/10/2026): zero medido aparece por extenso no cartão ("zero"), pela régua de números.
  const _emerg = MSd2.resposta.emergencias;
  teste("cartão de emergências, se a página o tiver: do agregado de resposta",
    !q("nEmergSaude") || txt("nEmergSaude") === (_emerg == null ? "sem dado" : _emerg === 0 ? "zero" : Number(_emerg).toLocaleString("pt-BR")));

  // A situação por estado: lista dos tipos com as siglas em círculos (botões); tipo sem estado não aparece, sem "zero".
  const botoes = () => [...d.querySelectorAll("#listaTiposPlano button[data-uf]")];
  teste("lista dos tipos de plano: 27 siglas como botões, só os tipos que têm estado, sem contagem nem 'zero'", (() => {
    const tipos = ["NOVO", "READ", "VIG", "ELAB", "LAC", "NAO_VERIFICADO"].filter(t => Object.values(MSd2.ufs).some(u => u.instrumento.status === t));
    const dds = [...d.querySelectorAll("#listaTiposPlano dd")];
    return botoes().length === 27 && dds.length === tipos.length && !/zero|\d+ estados?/.test(q("listaTiposPlano").textContent)
      && botoes().every(b => b.classList.contains("chip-risco") && /^Abrir a ficha de /.test(b.getAttribute("aria-label")));
  })());
  teste("círculo de SE: o cartão traz tipo, documento, órgão e a fonte oficial (instrumento.url)", (() => {
    const i = MSd2.ufs.SE.instrumento, b = botoes().find(x => x.dataset.uf === "SE");
    b.dispatchEvent(new dom.window.MouseEvent("mouseover", { bubbles: true }));
    const t = q("mapTooltip"), a = t.querySelector("a");
    return t.style.display === "block" && t.classList.contains("map-tooltip--clicavel") && t.textContent.includes(i.doc) && (!i.orgao || t.textContent.includes(i.orgao))
      && (i.url ? !!a && a.getAttribute("href") === i.url : !a);
  })());
  teste("a linha da escada vem dos pontos do dado (metodo.escada), não do texto", (() => {
    const e = MSd2.metodo.escada;
    return txt("escadaPlano") === `O índice de cada estado no MARÉ Saúde é o do tipo de plano: feito para este El Niño, ${e.NOVO}; atualizado, ${e.READ}; recorrente, ${e.VIG}; em elaboração, ${e.ELAB}; não localizado, ${e.LAC}.`;
  })());
  // Ficha aberta pelo círculo.
  const NOME_DO_TIPO = { NOVO: "Plano feito para este El Niño", READ: "Plano anual atualizado para o ciclo", VIG: "Plano recorrente, sem atualização para o ciclo",
    ELAB: "Plano em elaboração", LAC: "Plano não localizado até o corte", NAO_VERIFICADO: "Ainda não verificado" };
  teste("ficha de SE abre pelo círculo, com o tipo de plano do dado", (() => {
    const b = botoes().find(x => x.dataset.uf === "SE");
    b.click();
    return q("detailSaudeConteudo").textContent.includes(NOME_DO_TIPO[MSd2.ufs.SE.instrumento.status]);
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
  /* O detalhe do desfecho escolhido (dengue, o primeiro) lê os MESMOS campos do mesmo arquivo que o topo.
     Três casos garantem que cada estado se atualiza certo: se o arquivo mudar e algum divergir, o PR não passa. */
  {
    const DD = JSON.parse(fs.readFileSync(path.join(raiz, "data", "saude_desfechos", "dengue.json"), "utf8"));
    const PAL = dom.window.MonitorMapas.PALETA.posicao;
    const norm = s => String(s).replace(/\s+/g, " ");
    // (a) a ficha de uma UF mostra o valor, a taxa e o intervalo da faixa do arquivo, e a semana do próprio valor
    const c = DD.ultimo.SE.consolidado, f = DD.faixa_habitual.SE[c.periodo.split("-")[1]];
    const caminhoSE = [...q("mapaDesfecho").querySelectorAll("path")].find(x => /^Sergipe:/.test(x.getAttribute("aria-label")));
    const ficha = norm(caminhoSE.getAttribute("aria-label"));
    const dec = v => dom.window.MonitorMapas.numBR(v, Number.isInteger(Number(v)) ? 0 : 1);
    teste("detalhe do desfecho (a): a ficha traz valor, taxa, faixa e a semana do próprio valor",
      ficha.includes(dec(c.valor) + " notificações · " + dec(c.por_100mil) + " por 100 mil habitantes")
      && ficha.includes("(de " + dec(f.mediana) + " a " + dec(f.p90) + ")")
      && ficha.includes(dom.window.MonitorSemana.porExtenso(Number(c.periodo.split("-")[0]), Number(c.periodo.split("-")[1]), true)));
    // (b) as UFs pintadas em cada cor somam os três números da frase de leitura
    const pintadas = cor => [...q("mapaDesfecho").querySelectorAll("path")].filter(x => x.getAttribute("fill") === cor).length;
    const fr = /(\d+) acima, (\d+) dentro e (\d+) abaixo/.exec(txt("leituraDesfecho")) || [];
    teste("detalhe do desfecho (b): as cores do mapa somam os números da frase de leitura",
      fr.length === 4 && +fr[1] === pintadas(PAL.acima) && +fr[2] === pintadas(PAL.dentro) && +fr[3] === pintadas(PAL.abaixo));
    // (c) o "acima" do mapa da dengue é o ufs_acima_faixa do topo
    teste("detalhe do desfecho (c): o acima do mapa é o ufs_acima_faixa do topo",
      pintadas(PAL.acima) === TS.desfechos.dengue.ufs_acima_faixa);
    teste("detalhe do desfecho: sem rótulo de família, subtítulo com território e semana, ano mostrado no eixo",
      !/Desfecho escolhido/.test(txt("boxDesfecho")) && /^Brasil · semana de /.test(txt("legendaDesfecho"))
      && /por 100 mil habitantes$/.test(txt("tituloDesfecho")));
  }
  teste("dlDesfechoUF: lista por estado com a taxa por 100 mil",
    q("dlDesfechoUF").querySelectorAll("dt").length >= 26 && /por 100 mil habitantes/.test(txt("dlDesfechoUF")));
  teste("os quadros por agravo saíram, e o desfecho escolhido tem um gráfico só",
    !q("cDesfAcum") && !q("cDengueSemana") && !q("cSRAG") && !q("mapaCalor") && !!q("cDesfecho"));

  try {
    teste("saúde: a figura de estados tem o título do catálogo", q("boxMonitor").querySelector(".figura-titulo").textContent === "Plano estadual de saúde para o El Niño, por estado");
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
    teste("consulta: sete cartões, no formato dos outros cartões municipais", cartao.querySelectorAll(".cartao").length === 7 && !cartao.querySelector("table"));
    teste("consulta: dengue com nível e semana em datas, fonte InfoDengue", /Nível 2 \(atenção\)/.test(t) && /Semana de \d+ a \d+ de \w+ de 2026 · InfoDengue \(Fiocruz e FGV\)/.test(t));
    teste("consulta: o estado é dito como do estado, sem acumulado do ano nem nota", /SRAG \(síndrome respiratória aguda grave\), casos hospitalizados notificados \(estado\)/.test(t)
      && /casos? hospitalizados? notificados? no estado na semana de/.test(t) && !/no estado em 2026/.test(t) && !/MARÉ Saúde \(estado\)[\s\S]*de 100/.test(t));
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
