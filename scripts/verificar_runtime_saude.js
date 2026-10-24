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
  teste("cartões de casos trazem a ressalva de parcialidade e a linha que diz o que cada cartão mostra", (() => {
    const t = q("numerosSaude").textContent;
    return /são parciais e sobem com as notificações atrasadas/.test(t)
      && /Cada cartão mostra a semana mais recente/.test(t);
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

  // Um mapa só por estado (24/10/2026, aprovado pela editoria): categórico por TIPO de plano, com a
  // lista dos seis tipos e as siglas como botões, que abrem a mesma ficha que o mapa. Saíram o
  // cartão de risco previsto e a grade dos 27 ladrilhos.
  const U = MSd2.ufs || {};
  const ficha = uf => { const b = [...d.querySelectorAll("#listaTiposPlano button")].find(x => x.dataset.uf === uf); if (b) b.click(); return q("detailSaudeConteudo").textContent; };
  teste("mapa por tipo de plano: legenda com os seis tipos e lista dos seis tipos", q("legMonitor").children.length === 6
    && q("listaTiposPlano").querySelectorAll("dt").length === 6 && !q("boxRiscoSan") && !q("regionsSaude"));
  teste("a lista tem as 27 siglas como botões, e a soma dos tipos é 27", q("listaTiposPlano").querySelectorAll("button[data-uf]").length === 27
    && [...q("listaTiposPlano").querySelectorAll("dt")].reduce((t, e) => t + Number(e.textContent.split("·").pop()), 0) === 27);
  teste("a nota escreve a escada do dado, não números digitados", Object.values(MSd2.metodo.escada).every(v => txt("notaEscadaSaude").includes(String(v))));
  // A7-33 (12/10/2026): a ficha de MS, MT e PB lançava ReferenceError ao abrir com o portão verde.
  // Abre as 27 pela lista, sem o mapa (SE, DF, AL e RN são pequenos demais no toque), e cobra
  // conteúdo e nenhum erro novo.
  teste("as 27 fichas de estado abrem pela lista, sem erro de script", (() => {
    const antes = erros.length, vazias = [];
    for (const uf of Object.keys(U)) { try { if (ficha(uf).length <= 20) vazias.push(uf); } catch (e) { erros.push(String(e)); } }
    return vazias.length === 0 && erros.length === antes;
  })());
  teste("ficha: a nota do dado, o tipo de plano e o órgão", (() => {
    const uf = Object.keys(U).find(u => U[u].verificado && U[u].instrumento.orgao), m = U[uf], t = ficha(uf);
    return t.includes(String(m.prontidao).replace(".", ",")) && t.includes(m.instrumento.orgao) && /Tipo de plano/.test(t);
  })());
  /* "Se preenche sozinha": a linha Coordenação lê `ufs.<UF>.coordenacao` do motor. Injeta o ato num estado
     sem registro e exige que a ficha o mostre; sem registro, a ficha diz "ainda não verificada". */
  teste("ficha: a coordenação aparece quando o motor a traz e diz 'ainda não verificada' quando não", (() => {
    const livre = Object.keys(U).find(u => !U[u].coordenacao.f1.doc && !U[u].coordenacao.f2.doc);
    const sem = ficha(livre);
    dom.window.eval("MSAUDE.ufs." + livre + ".coordenacao.f1 = {status: 'CRIADO_CICLO', doc: 'Portaria SES de teste do portão', data: '01/10/2026', url: 'https://exemplo.gov.br/ato'}");
    const com = ficha(livre);
    return /ainda não verificada/.test(sem) && !/Portaria SES de teste do portão/.test(sem)
      && /Portaria SES de teste do portão/.test(com) && /criada para o ciclo/.test(com) && !/antecipação/i.test(com);
  })());

  // A seção única de desfechos, no cartão escolhido: a posição na faixa habitual é a frase do
  // dado (ela está no cartão, não numa nota à parte), e o detalhe traz o mapa por 100 mil e a
  // lista por estado. Um detalhe por vez: o portão confere o que está aberto na carga.
  teste("gradeDesfechos: um cartão por desfecho com arquivo, com a posição na faixa habitual",
    q("gradeDesfechos").querySelectorAll("[data-desfecho]").length >= 1
    && /((acima|dentro|abaixo) da faixa habitual para a época|sem faixa habitual para a época)/.test(txt("gradeDesfechos"))
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
    teste("saúde: o mapa tem o título do catálogo, sem \"prontidão\"", q("boxMonitor").querySelector(".figura-titulo").textContent === "Plano estadual de saúde para o El Niño, por estado" && !/prontid/i.test(d.querySelector("main").textContent));
    // Lote 6, §2: a tabela do mapa tem as seis colunas de leitor, uma linha por UF, sem travessão.
    const linhasMon = [...d.querySelectorAll("#tblMonitor tbody tr")];
    teste("saúde: tabela do mapa com 27 linhas de 4 colunas, sem travessão nem componente interno",
      linhasMon.length === 27 && linhasMon.every((tr) => tr.children.length === 4 && ![...tr.children].some((td) => td.textContent.trim() === "—") && !/lido\(s\)|cobertura sanit/.test(tr.textContent)));
    // 19/10/2026: a nota do InfoDengue saiu com os quadros por agravo (decisão da editoria) — ela
    // explicava um nível que a página não mostra mais. O que o portão continua guardando é a fonte
    // da série respiratória, que é primária e vive no cartão do topo, não no InfoGripe.
    teste("respiratórias: a fonte declarada é o SIVEP-Gripe, não o InfoGripe",
      /SIVEP-Gripe/.test(txt("fonteSragSE")) && !/InfoGripe/.test(d.querySelector("main").textContent));
  } catch (e) { teste("saúde: títulos-fato (" + e.message + ")", false); }
  console.log(falhas.length ? `\n✗ ${falhas.length} verificação(ões) falharam.` : "\n✓ RUNTIME (saúde) OK — mapas, cartões, tooltip, créditos e lacunas declaradas.");
  process.exit(falhas.length ? 1 : 0);
}, 900);
