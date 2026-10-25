/* A7-17 (12/10/2026): erro de bloco que não renderiza não é engolido em silêncio — vai ao
   console com o lugar, onde o portão de runtime e quem abre o DevTools o veem. */
function _erroSaude(onde) { return function (e) { try { console.error("[MARÉ] falha em " + onde + ":", e); } catch (_) {} }; }
/* A7-14 (12/10/2026): número de cartão pela régua de `layout/regras.json` (numeros) — zero medido
   se escreve por extenso, e ausência de dado nunca vira zero. */
function _qtdCartao(v) {
  if (v === null || v === undefined || v === '') return 'sem dado';
  const x = Number(v);
  if (!Number.isFinite(x)) return 'sem dado';
  return x === 0 ? 'zero' : decBR(x);
}
// ===== saude.html · bloco 1 (extraído em 06/09/2026, CSP sem unsafe-inline) =====
let BR_GEOJSON, MSAUDE;
// Lote 6, §2: a frase do dado nasce oculta e só aparece com texto — nunca "—" nem linha vazia.
const mostrarFrase = (alvo, texto) => { alvo.textContent = texto; alvo.hidden = !texto; };
/* Número em texto público com vírgula decimal (A4-16); não-número passa como veio ("—", nulo).
   21/10/2026: uma casa decimal, SALVO quando ela zeraria um valor medido — 0,037 internação por
   100 mil saía "0", e dizer zero onde houve 75 internações é afirmar o que não se mediu. Abaixo de
   0,05 vale um dígito significativo ("0,04", "0,009"), que é curto e não mente. */
const decBR = v => (v == null || v === '' || isNaN(Number(v))) ? v
  : MonitorMapas.numBR(v, Number.isInteger(Number(v)) ? 0 : 1);

/* A camada, nas palavras da sua classe, pela régua de número do projeto (`_qtdCartao`): sem plano
 * municipal localizado o percentual é ZERO POR CONSTRUÇÃO, e escrever "0 % da população" diria que
 * se mediu cobertura nula onde não se leu documento nenhum — hoje seriam 15 das 27. Nenhuma classe
 * é zero: percentual medido · localizado e não lido · não localizado até o corte. */
const camadaMunicipalSaude = c => {
  const lidos = Number(c.planos_lidos || 0), sem = Number(c.planos_sem_leitura || 0);
  if (c.cobertura_pct == null) return 'sem leitura até o corte';
  if (!lidos) return sem ? 'nenhum plano municipal lido até o corte · ' + sem + (sem === 1 ? ' localizado' : ' localizados')
                         : 'nenhum plano municipal localizado até o corte';
  /* Percentual abaixo da resolução do campo publicado também não é zero: no RS, 3.022 pessoas
   * moram em município cujo plano trata a saúde e `cobertura_pct` traz 0,0. */
  const pct = Number(c.cobertura_pct) === 0 && Number(c.pop_coberta || 0) > 0
    ? 'menos de 0,1' : _qtdCartao(c.cobertura_pct);
  return pct + ' % da população em município cujo plano trata a saúde ('
    + lidos + (lidos === 1 ? ' plano municipal lido' : ' planos municipais lidos')
    + (sem ? ' · ' + sem + ' sem leitura' : '') + ')';
};

/* A SEMANA VIRA DATA — item 0 do handover de 07/10/2026, regra da editoria para o site inteiro.
 *
 * O dado do SINAN e do InfoDengue é por semana epidemiológica, e continua sendo: isso é da fonte.
 * O que não chega ao leitor é a palavra. Ele lê "na semana de 16 a 22 de agosto de 2026", que é
 * como se pensa uma data; "semana epidemiológica 33" exige saber o que é e contar no calendário.
 *
 * A conversão mora em `assets/semana.js`, com a regra do Ministério da Saúde e um autoteste
 * conferido contra o calendário publicado em quatro anos de virada diferente. Aqui ficam só os
 * três ajudantes que traduzem a chave "2026-33" que os arquivos de série usam.
 *
 * Sem o utilitário carregado, as funções devolvem vazio em vez de a chave crua: a página perde a
 * data, e não ganha um "2026-33" na cara do leitor. */
function semanaEmDatas(ano, chave, curta) {
  if (!window.MonitorSemana || !chave) return '';
  // A chave vem "2026-33" nas séries e "202633" no sinal do InfoDengue: a leitura cobre as duas.
  const parte = String(chave).includes('-') ? String(chave).split('-') : [String(chave).slice(0, 4), String(chave).slice(4)];
  const n = Number(parte[1]);
  const a = Number(ano || parte[0]);
  if (!a || !n) return '';
  // COM a preposição: quem chama escreve "na semana " e a função completa "de 16 a 22 de
  // agosto de 2026". Sem ela saía "na semana 16 a 22", que tropeça na leitura.
  return (curta ? MonitorSemana.curta(a, n) : MonitorSemana.porExtenso(a, n, true)) || '';
}
/* O rótulo do eixo: o nome do mês na PRIMEIRA semana dele, vazio nas outras. */
function rotulosDeMes(ano, chaves) {
  let ultimo = null;
  return (chaves || []).map(k => {
    const mes = window.MonitorSemana
      ? MonitorSemana.mesDaSemana(Number(ano), Number(String(k).split('-')[1])) : null;
    if (!mes || mes === ultimo) return '';
    ultimo = mes;
    return mes;
  });
}
/* O eixo de um gráfico semanal: rótulo de mês na primeira semana de cada mês, e o título do
 * tooltip com o intervalo de datas da semana. Recebe os números de semana ("01", "02", …) que os
 * três gráficos de série já montam, e devolve as duas listas na mesma ordem. */
function eixoDeMeses(ano, semanas) {
  const labels = rotulosDeMes(ano, (semanas || []).map(w => ano + '-' + w));
  const titulos = (semanas || []).map(w => semanaEmDatas(ano, ano + '-' + w, true));
  return {labels: labels, titulos: titulos};
}
/* As opções de eixo e tooltip que acompanham `eixoDeMeses`, para os três não divergirem. */
function opcoesDeEixoSemanal(titulos, extra) {
  const base = {ticks: {autoSkip: false, maxRotation: 0}};
  return {x: Object.assign(base, extra || {}),
          tooltipTitulo: itens => (itens && itens[0] ? (titulos[itens[0].dataIndex] || '') : '')};
}

/* O começo do período coberto, por extenso, da primeira semana que tem valor. */
function primeiraSemanaComValor(ano, comValor) {
  if (!window.MonitorSemana || !comValor || !comValor.length) return null;
  const r = MonitorSemana.semanaParaDatas(Number(ano), Number(comValor[0].split('-')[1]));
  if (!r) return null;
  return r.inicio.getUTCDate() + ' de ' + MonitorSemana.MESES[r.inicio.getUTCMonth()]
         + ' de ' + r.inicio.getUTCFullYear();
}
// 14/09/2026: chikungunya — mesmos quatro arquivos do painel, com prefixo chik_ (coletar_desfechos_saude.py --doenca chikungunya).
// Nulos enquanto o coletor não rodar: o comparador e o mapa declaram lacuna, nunca preenchem.
const UFS = ["AC","AL","AM","AP","BA","CE","DF","ES","GO","MA","MG","MS","MT","PA","PB","PE","PI","PR","RJ","RN","RO","RR","RS","SC","SE","SP","TO"];
const NOME_UF = {AC:'Acre',AL:'Alagoas',AM:'Amazonas',AP:'Amapá',BA:'Bahia',CE:'Ceará',DF:'Distrito Federal',ES:'Espírito Santo',GO:'Goiás',MA:'Maranhão',MG:'Minas Gerais',MS:'Mato Grosso do Sul',MT:'Mato Grosso',PA:'Pará',PB:'Paraíba',PE:'Pernambuco',PI:'Piauí',PR:'Paraná',RJ:'Rio de Janeiro',RN:'Rio Grande do Norte',RO:'Rondônia',RR:'Roraima',RS:'Rio Grande do Sul',SC:'Santa Catarina',SE:'Sergipe',SP:'São Paulo',TO:'Tocantins'};
const NEUTRA = MonitorMapas.cor('sem-dado');
const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const { showTip, hideTip } = MonitorMapas;

async function __load(){
  [BR_GEOJSON, MSAUDE] = await Promise.all(['geo_uf','monitor_saude'].map(f => fetch('data/' + f + '.json').then(r => {
      if(!r.ok) throw new Error('Falha ao carregar data/' + f + '.json'); return r.json(); })));
  if (window.MonitorCatalogo && MonitorCatalogo.pronto) { try { await MonitorCatalogo.pronto; } catch (e) {} }
  mapaDosPlanos();
  montarDesfechos().catch(_erroSaude("saude:desfechos"));
}

const fonteFigura = MonitorMapas.credito;

/* ===== A situação de cada estado (v0.7, editoria 24/10/2026) =====
 * Um mapa categórico pelo TIPO DE PLANO que cada secretaria estadual de saúde publicou, na paleta
 * ordinal do site; ao lado, a lista dos seis tipos com as siglas dos estados, e cada sigla é botão
 * (o seletor acessível: teclado, leitor de tela e toque onde DF, SE, AL e RN são pequenos no mapa).
 * Mapa e lista abrem a mesma ficha. Os pontos de cada tipo vêm de `metodo.escada` do dado. */
const TIPOS_DE_PLANO = ['NOVO', 'READ', 'VIG', 'ELAB', 'LAC', 'NAO_VERIFICADO'];
const ufsDoMonitor = () => (MSAUDE && MSAUDE.ufs) || {};
const tipoDoEstado = uf => ((ufsDoMonitor()[uf] || {}).instrumento || {}).status || 'NAO_VERIFICADO';
const textoSaude = (id, v) => (window.MonitorCatalogo && MonitorCatalogo.texto(id, v)) || '';

function mapaDosPlanos() {
  const nome = t => textoSaude('saude.estadual.tipo.' + t);
  const cor = t => MonitorMapas.PALETA.status[t] || NEUTRA;
  const instr = uf => (ufsDoMonitor()[uf] || {}).instrumento || {};
  const ctx = MonitorMapas.contexto(BR_GEOJSON, 480, 460);
  MonitorMapas.ufs(ctx, 'mapaMonitor', uf => cor(tipoDoEstado(uf)),
    uf => '<em>' + esc(nome(tipoDoEstado(uf))) + '</em>' + (instr(uf).doc ? '<br>' + esc(instr(uf).doc) + (instr(uf).data ? ' · ' + esc(instr(uf).data) : '') : ''));
  /* O clique no mapa abre a ficha; o teclado, o leitor de tela e o toque nos estados pequenos usam os botões da lista. */
  d3.selectAll('#mapaMonitor .uf-path').style('cursor', 'pointer').on('click', (ev, f) => abrirDetalheSaude(f.properties.sigla));
  const alvo = document.getElementById('listaTiposPlano');
  alvo.innerHTML = '<p class="cartao-mapa-familia">' + esc(textoSaude('saude.estadual.lista.titulo')) + '</p><dl class="faixa-previsto">'
    + TIPOS_DE_PLANO.map(t => {
      const ufs = UFS.filter(uf => tipoDoEstado(uf) === t);
      return '<div><dt><span class="chip-chave" data-tipo="' + t + '">' + esc(nome(t)) + '</span> ' + esc(textoSaude('saude.estadual.lista.contagem', {n: ufs.length}))
        + '</dt><dd class="chips">' + ufs.map(uf => '<button type="button" class="chip-risco" data-uf="' + uf + '" aria-pressed="false" aria-label="'
          + esc(textoSaude('saude.estadual.lista.botao', {estado: NOME_UF[uf]})) + '">' + uf + '</button>').join('') + '</dd></div>';
    }).join('') + '</dl>';
  alvo.querySelectorAll('[data-tipo]').forEach(e => { e.style.background = cor(e.dataset.tipo); });
  alvo.addEventListener('click', ev => { const b = ev.target.closest('button[data-uf]'); if (b) abrirDetalheSaude(b.dataset.uf); });
  document.getElementById('detailSaude').addEventListener('close', () => alvo.querySelectorAll('button[aria-pressed=true]').forEach(b => b.setAttribute('aria-pressed', 'false')));
  const escada = ((MSAUDE.metodo || {}).escada) || {};
  mostrarFrase(document.getElementById('escadaPlano'), textoSaude('saude.estadual.escada', escada));
  const coord = o => (o && o.doc) ? esc(ST_COORD[o.status] || o.status || '') + (o.data ? ' · ' + esc(o.data) : '') : esc(textoSaude('saude.estadual.ficha.nao_verificada'));
  document.querySelector('#tblMonitor tbody').innerHTML = UFS.map(uf => { const co = (ufsDoMonitor()[uf] || {}).coordenacao || {};
    return '<tr><td><strong>' + uf + '</strong></td><td>' + esc(nome(tipoDoEstado(uf))) + (instr(uf).data ? ' · ' + esc(instr(uf).data) : '') + '</td><td>' + coord(co.f1) + '</td><td>' + coord(co.f2) + '</td></tr>'; }).join('');
  fonteFigura('boxMonitor', {fontes: ['MARÉ Saúde'], data: MSAUDE.gerado_em});
}

/* Os degraus das duas funções da coordenação, em linguagem de leitor (METODOLOGIA §91.3). */
const ST_COORD = {
  CRIADO_CICLO: 'criada para o ciclo',
  REATIVADO_CICLO: 'reativada para o ciclo',
  PERMANENTE: 'estrutura permanente',
  ANUNCIADO: 'anunciada, sem ato publicado',
  NOMEADA_COM_ATRIBUICAO: 'secretaria de saúde nomeada, com atribuição',
  LISTADA_SEM_ATRIBUICAO: 'secretaria de saúde listada, sem atribuição',
  LAC: 'não localizada até o corte',
};

/* A ficha do estado, no <dialog>. A coordenação lê `ufs.<UF>.coordenacao` do monitor e se preenche
 * sozinha à medida que a rotina verifica cada estado; sem registro, diz que não foi verificada. */
function abrirDetalheSaude(uf) {
  const m = ufsDoMonitor()[uf] || {}, i = m.instrumento || {}, c = m.cobertura || {}, co = m.coordenacao || {};
  const RS = (MSAUDE && MSAUDE.resposta) || {};
  const tx = id => esc(textoSaude('saude.estadual.ficha.' + id));
  const linha = (k, v) => '<div class="field"><div class="k">' + k + '</div><div class="v">' + v + '</div></div>';
  const doc = o => (o && o.doc) ? '<span class="pill-nivel">' + esc(ST_COORD[o.status] || o.status) + '</span> ' + esc(o.doc)
    + (o.data ? ' (' + esc(o.data) + ')' : '') + (o.url ? ' · <a href="' + esc(o.url) + '" target="_blank" rel="noopener">' + tx('fonte_oficial') + ' →</a>' : '') : tx('nao_verificada');
  document.getElementById('detailSaudeConteudo').innerHTML = '<div class="uf-name">' + esc(NOME_UF[uf] || uf) + ' <span class="sub">(' + uf + ')</span></div>'
    + (m.verificado ? '' : '<p class="placeholder">' + tx('sem_plano') + '</p>')
    + linha(tx('plano'), '<span class="pill-nivel">' + esc(textoSaude('saude.estadual.tipo.' + tipoDoEstado(uf))) + '</span>' + (i.doc ? ' ' + esc(i.doc) : '')
      + (i.data ? ' (' + esc(i.data) + ')' : '') + (i.orgao ? ' · ' + esc(i.orgao) : '')
      + (i.url ? ' · <a href="' + esc(i.url) + '" target="_blank" rel="noopener">' + tx('fonte_oficial') + ' →</a>' : ''))
    + linha(tx('coordenacao'), doc(co.f1)) + linha(tx('governo'), doc(co.f2))
    + (m.verificado ? linha(tx('camada'), esc(camadaMunicipalSaude(c)) + '; ' + tx('camada_nota')) : '')
    + linha(tx('resposta'), (RS.ufs || []).includes(uf) ? tx('resposta_sim') : tx('resposta_nao'));
  document.querySelectorAll('#listaTiposPlano button[data-uf]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.uf === uf)));
  const dlg = document.getElementById('detailSaude');
  if (!dlg.open) { if (typeof dlg.showModal === 'function') dlg.showModal(); else dlg.open = true; }
}

__load().catch(err => { const m = document.getElementById('subSaude'); if (m) m.insertAdjacentHTML('afterend', '<p class="note u-rust">Erro ao carregar os dados: '+esc(err.message)+'</p>'); });

window.addEventListener('load', function(){ if (window.VLibras && window.VLibras.Widget) { try { new window.VLibras.Widget('https://vlibras.gov.br/app'); } catch (e) {} } });




// 13/09/2026 (proposta de enxugamento, Manus AI): renderEstrutura() (catálogo de 20 desfechos e
// tabela de gatilhos, §36) migrou por completo para pesquisadores.js.



/* ===== Cartões do topo (bloco A.1 do handover de 02/10/2026) =====
 * Cinco indicadores que mudam a cada coleta. Os dois primeiros vêm da FONTE PRIMÁRIA (SINAN e
 * SIVEP-Gripe) e trazem, no próprio cartão, a ressalva de parcialidade e a frase que a editoria
 * fixou: estes números não indicam relação com o El Niño.
 *
 * "Última semana epidemiológica fechada" é a última com valor na série — não a última do
 * calendário. A diferença importa: as semanas recentes existem no arquivo com valor nulo, e tratar
 * nulo como zero publicaria uma queda que é só atraso de notificação.
 */
(function cartoesDoTopoSaude(){
  const el = id => document.getElementById(id);
  const n = v => Number(v || 0).toLocaleString('pt-BR');
  const ultimaFechada = serie => {
    const ses = Object.keys(serie || {}).filter(k => serie[k] != null).sort();
    return ses.length ? {se: ses[ses.length - 1], valor: serie[ses[ses.length - 1]]} : null;
  };

  /* Dengue e chikungunya: o mesmo cartão, cada um do seu arquivo do SINAN. */
  const cartaoSinan = (arquivo, doenca, idValor, idRotulo, idFonte) =>
    fetch('data/saude_desfechos/' + arquivo).then(r => r.ok ? r.json() : null).then(D => {
      const br = ((D || {}).serie || {}).BR;
      const u = br ? ultimaFechada(Object.fromEntries(Object.entries(br).filter(([k]) => k.startsWith(String(D.ano_corrente))))) : null;
      if (!u) { if (el(idValor)) el(idValor).textContent = 'sem coleta'; return; }
      if (el(idValor)) el(idValor).textContent = n(u.valor);
      if (el(idRotulo)) el(idRotulo).textContent = 'notificações de ' + doenca + ' na semana ' + semanaEmDatas(u.se.split('-')[0], u.se);
      MonitorMapas.credito(idFonte, {fontes: ['SINAN (Ministério da Saúde)', D.conta === 'notificacoes' ? 'notificações, não casos confirmados' : ''].filter(Boolean), data: D.gerado_em});
    }).catch(_erroSaude("saude:777"));
  cartaoSinan('dengue_sinan_serie.json', 'dengue', 'nDengueSE', 'rotuloDengueSE', 'fonteDengueSE');
  cartaoSinan('chik_sinan_serie.json', 'chikungunya', 'nChikSE', 'rotuloChikSE', 'fonteChikSE');

  fetch('data/saude_desfechos/srag_serie.json').then(r => r.ok ? r.json() : null).then(S => {
    const serie = (S || {}).serie;
    if (!serie) { if (el('nSragSE')) el('nSragSE').textContent = 'sem coleta'; return; }
    /* O arquivo é {UF: {SE: n}} — e traz a linha `BR` JUNTO das 27 UFs.
       02/10/2026, defeito medido: somar `serie.values()` somava o país duas vezes, porque a linha
       do país entrava na soma das UFs. O cartão publicava 8.534 internações onde a fonte diz 4.267.
       Quando existe a linha `BR`, ela É o país; só na falta dela o país é a soma das UFs. A mesma
       regra está em `scripts/gerar_topo_das_paginas.py`, que é quem a Imprensa lê. */
    const ano = String(S.ano_corrente || new Date().getFullYear());
    const total = {};
    const somar = porSE => {
      if (!porSE || typeof porSE !== 'object') return;
      Object.entries(porSE).forEach(([se, v]) => {
        if (se.startsWith(ano) && typeof v === 'number') total[se] = (total[se] || 0) + v;
      });
    };
    if (serie.BR && typeof serie.BR === 'object') somar(serie.BR);
    else Object.entries(serie).forEach(([uf, porSE]) => { if (uf !== 'BR') somar(porSE); });
    const u = ultimaFechada(total);
    if (!u) { if (el('nSragSE')) el('nSragSE').textContent = 'sem coleta'; return; }
    if (el('nSragSE')) el('nSragSE').textContent = n(u.valor);
    if (el('rotuloSragSE')) {
      el('rotuloSragSE').textContent = 'internações por síndrome respiratória grave na semana '
        + semanaEmDatas(u.se.split('-')[0], u.se);
    }
    MonitorMapas.credito('fonteSragSE', {fontes: ['SIVEP-Gripe (Ministério da Saúde)'], data: S.gerado_em});
  }).catch(_erroSaude("saude:811"));

  /* Estados com dengue em nível de alerta: a régua é do InfoDengue (níveis 3 e 4) e a agregação por
   * estado é nossa — a nota diz qual é, porque o InfoDengue não publica um nível por estado. */
  fetch('data/saude_desfechos/serie_painel.json').then(r => r.ok ? r.json() : null).then(P => {
    const M = (P || {}).municipios || {};
    if (!Object.keys(M).length) { if (el('nUFsAlerta')) el('nUFsAlerta').textContent = 'sem coleta'; return; }
    const ufs = new Set();
    Object.values(M).forEach(m => { if ((m.nivel_ultima_se || 0) >= 3 && m.uf) ufs.add(m.uf); });
    if (el('nUFsAlerta')) el('nUFsAlerta').textContent = ufs.size + ' de 27';
    MonitorMapas.credito('fonteUFsAlerta', {fontes: ['InfoDengue (Fiocruz/FGV)', 'o estado entra quando ao menos um município acompanhado está em nível 3 ou 4'], data: P.gerado_em});
  }).catch(_erroSaude("saude:825"));

  /* O calor vem de `calor_excesso`, que é onde o coletor o escreve: `resumo` com as quatro classes
   * do vocabulário do Ministério da Saúde e `municipios_lidos`. A primeira versão deste cartão
   * procurou o dado em `uf[*].calor_ms`, caminho que o arquivo nunca teve — e dizia "sem coleta"
   * com o dado em disco, que é o pior jeito de errar numa figura de risco. */
  fetch('data/saude_sinais.json').then(r => r.ok ? r.json() : null).then(SS => {
    const C = (SS || {}).calor_excesso || null;
    const r = (C || {}).resumo || null;
    if (!r) {
      /* 11/10/2026: retrato com mais de 9 dias sai do ar (coletar_saude.vencer_calor); o cartão e a
         fonte dizem desde quando não há leitura, em vez de mostrar o retrato velho como o mais recente. */
      const ult = (((SS || {}).fontes || {}).painel_calor_ms || {}).ultima_coleta_ok;
      if (el('nCalorMun')) el('nCalorMun').textContent = ult
        ? 'sem leitura desde ' + String(MonitorMapas.dataBR(ult) || ult).slice(0, 5) : 'sem coleta';
      MonitorMapas.credito('fonteCalorMun', {fontes: ['Painel Nacional de Excesso de Calor (Ministério da Saúde)', ult ? 'nenhum município lido desde então' : 'nenhum município lido até o corte'], data: ult});
      return;
    }
    const acima = Number(r.severo || 0) + Number(r.extremo || 0);
    if (el('nCalorMun')) el('nCalorMun').textContent = n(acima);
    const lidos = C.municipios_lidos || Object.keys(C.municipios || {}).length;
    MonitorMapas.credito('fonteCalorMun', {fontes: ['Painel Nacional de Excesso de Calor (Ministério da Saúde)', n(lidos) + (Number(lidos) === 1 ? ' município lido' : ' municípios lidos')], data: C.data});
  }).catch(_erroSaude("saude:851"));

})();

/* ===== Cartões e figuras criados pelo contrato de layout (02/10/2026) =====
 * Um só lugar para o que o contrato acrescentou: o número do índice no topo, a lista do que foi
 * localizado em cada estado, o mapa do risco previsto, o mapa de síndrome respiratória grave por
 * estado, a distribuição do calor por classe e as três buscas por município.
 */
(function cartoesDoContrato(){
  const el = id => document.getElementById(id);
  const n = v => Number(v || 0).toLocaleString('pt-BR');
  const umaCasa = v => Number(v || 0).toLocaleString('pt-BR', {minimumFractionDigits: 1, maximumFractionDigits: 1});
  const esc = v => String(v == null ? '' : v).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const UFS = ('AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO').split(' ');

  /* 1 · O topo (HANDOVER_SAUDE_PAGINA §1.2): os dois medidores da inicial. À esquerda, o MARÉ Saúde
   * NACIONAL, sobre as 27 UFs, pela mesma regra do MARÉ Legal (editoria, 21/10/2026, 06:54;
   * METODOLOGIA §115, que revoga o alvo "média das verificadas"); à direita, a parcela da população
   * sob emergência em saúde pública. Índice nulo é lacuna declarada, nunca zero. A barra e o número
   * sobem pelo mesmo `animarGauges` da inicial. */
  fetch('data/monitor_saude.json').then(r => r.ok ? r.json() : null).then(MS => {
    const res = ((MS || {}).resumo) || {}, rp = ((MS || {}).resposta) || {};
    const fixa = (id, v) => { const f = el(id); f.dataset.alvo = String(v); f.style.setProperty('--galvo', String(Math.max(v, 0.1)));
      f.closest('.gauge-track').setAttribute('aria-label', 'Barra de progresso: ' + (id === 'gaugeFillSaude' ? 'MARÉ Saúde' : 'emergências em saúde pública') + ' em ' + umaCasa(v) + ' de 100'); };
    const media = res.indice_nacional;
    /* Ausência se escreve em palavras, inclusive no número grande (layout/regras.json, numeros):
       um travessão no lugar do índice deixaria o leitor sem saber se é zero ou se não houve coleta. */
    if (media == null) { el('nIndiceSaude').textContent = 'sem coleta'; el('linhaPreparoSaude').textContent = 'sem coleta até o corte'; }
    else {
      el('nIndiceSaude').textContent = umaCasa(media); el('nIndiceSaude').dataset.contar = media;
      el('faixaSaude').replaceChildren(MonitorMapas.pilulaDaFaixa(media));
      fixa('gaugeFillSaude', media);
      /* A linha ao lado não lê mais o medidor como média parcial: ela conta o ESTATUTO, nas palavras
         da classe. Estado sem plano localizado e estado ainda não verificado são coisas distintas, e
         integrar o nacional não apaga a lacuna (handover do índice nacional, §2). */
      if (window.MonitorCatalogo) MonitorCatalogo.pronto.then(() =>
        MonitorCatalogo.escrever('linhaPreparoSaude', 'saude.topo.preparacao.linha', {
          com_plano: n(res.ufs_com_plano_localizado), denominador: n(res.denominador || 27),
          sem_numero: res.nao_verificadas, corte: (MS || {}).corte || ''}));
    }
    const quando = (MS || {}).gerado_em || (MS || {}).corte || '';
    if (rp.indice == null) {
      el('respNumSaude').textContent = 'sem coleta';
      el('respBadgeSaude').innerHTML = '<span class="gfaixa-pill">sem coleta até o corte</span>';
    } else {
      el('respNumSaude').textContent = umaCasa(rp.indice); el('respNumSaude').dataset.contar = rp.indice;
      fixa('respFillSaude', rp.indice);
      el('respBadgeSaude').innerHTML = '<span class="gfaixa-pill">' + esc(rp.emergencias
        ? n(rp.emergencias) + (rp.emergencias === 1 ? ' emergência' : ' emergências') + ' · ' + umaCasa(100 * (rp.pop_sob_emergencia || 0) / (rp.pop_total || 1)) + ' % da população'
        : 'nenhuma emergência declarada') + '</span>';
    }
    el('linhaRespostaSaude').textContent = 'Parcela da população em estados ou municípios sob emergência em saúde pública declarada desde '
      + (rp.desde || '29/06/2026') + ' · ' + (rp.indice == null ? 'sem coleta até o corte' : rp.emergencias ? 'até ' + quando : 'nenhuma localizada até ' + quando)
      + ' · DOU e diários oficiais estaduais';
    MonitorMapas.animarGauges(el('topoSaude'));
  }).catch(_erroSaude("saude:1066"));

  /* A figura "O que foi localizado em cada estado" (lista dos 27) saiu da página em
   * 19/10/2026 (HANDOVER_SAUDE_PAGINA §2.6 e §7): o documento, o órgão e a data de cada
   * estado abrem na ficha do estado, pelo mapa e pela grade. */

  /* 4 · Consulta do município (HANDOVER_SAUDE_PAGINA §4): o módulo comum, com a mesma renderização em
   * cartões do Proteja-se. Dengue, chikungunya, calor e plano vêm de `data/saude_municipio/<UF>.json`;
   * respiratória grave e MARÉ Saúde são do estado, e o rótulo diz que são. Município que a fonte não
   * leu diz a sua classe de ausência, nunca zero. Todo texto vive no catálogo. */
  const T = (id, v) => textoSaude('saude.consulta.' + id, v);
  const semana = v => { const m = /(\d{4})-(\d{1,2})/.exec(String(v || '')); return (m && MonitorSemana.porExtenso(+m[1], +m[2], true)) || ''; };
  const json = f => fetch(f).then(r => r.ok ? r.json() : null).catch(() => null);
  const porUF = {}, extra = Promise.all([json('data/saude_desfechos/srag.json'), json('data/meta.json')]), cartas = () => cartas.p = cartas.p || json('data/municipios_card.json');
  const cartao = (acento, rotulo, valor, nota, classe) => '<div class="cartao cartao--acento-' + acento + '"><p class="cartao-numero-rotulo">' + esc(rotulo) + '</p>'
    + '<p' + (classe ? ' class="' + classe + '"' : '') + '>' + valor + '</p><p class="note u-mb-0">' + nota + '</p></div>';
  /* O plano do município, com o vocabulário da inicial: o documento e a data com link, ou a frase de
     "não localizamos até a data de corte"; a leitura da saúde no plano é a segunda linha descritiva. */
  const cartaoPlanoDoMunicipio = (sp, pl, uf, meta) => {
    const achou = sp.estado === 'encontrado' || sp.estado === 'estadual';
    const valor = sp.estado === 'nao_verificado' ? T('plano.nao_verificado')
      : achou ? T(sp.data ? 'plano.com_plano_data' : 'plano.com_plano', {documento: sp.documento || sp.fonte || '', data: sp.data || ''}) : T('plano.sem_plano', {corte: (meta || {}).corte || ''});
    const camada = achou && pl ? T(pl.pagina_citada ? 'plano.saude_no_plano' : 'plano.saude_no_plano_sem_pagina', {pagina: pl.pagina_citada}) : '';
    return cartao('musgo', T('rotulo.plano_municipio'), esc(valor) + (achou && sp.url ? ' · <a href="' + esc(sp.url) + '" target="_blank" rel="noopener">' + esc(T('plano.abrir')) + '</a>' : ''),
      [camada && esc(camada), achou && sp.fonte && esc(sp.fonte), '<a href="index.html#' + esc(uf) + '">' + esc(T('plano.ver_inicial')) + '</a>'].filter(Boolean).join(' · '));
  };
  const cartaoArbo = (rotulo, x, d, semanaSemDado) => x
    ? cartao('neutro', rotulo, esc(T('arbo.nivel_' + x.nivel) || T('arbo.nivel_outro', {n: x.nivel})), esc(T('arbo.nota', {semana: semana(x.semana)})))
    : cartao('neutro', rotulo, esc(T('arbo.nao_lido', {semana: semanaSemDado})), esc(T('arbo.nota_nao_lido', {data: (d || {}).gerado_em || ''})));
  fetch('data/geo_uf.json').then(r => r.json()).then(GEO => ConsultaMunicipio.montar({uf: 'consultaSaudeUF', municipio: 'consultaSaudeMun', lista: 'consultaSaudeLista', cartao: 'consultaSaudeCard',
    estados: Object.fromEntries(GEO.features.map(f => [f.properties.sigla, f.properties.name])), semLista: T('sem_lista'),
    municipios: uf => (porUF[uf] = porUF[uf] || Promise.all([json('data/saude_municipio/' + uf + '.json'), extra, cartas()]))
      .then(([D, [S, meta], CARD]) => { porUF[uf].dados = {D, S, meta, CARD}; return D && Object.values(D.municipios).map(x => x.nome); }),
    mostrar: (uf, nome, card) => {
      const {D, S, meta, CARD} = porUF[uf].dados, o = D.origens || {}, [cod, m] = Object.entries(D.municipios).find(([, x]) => x.nome === nome);
      const sp = ConsultaMunicipio.situacaoDoPlano(((CARD || {}).municipios || {})[cod]);
      const sinal = (m.dengue || m.chikungunya || {}).semana, quando = semana(sinal);
      const e = ufsDoMonitor()[uf] || {}, pl = m.saude_no_plano, calor = m.calor && m.calor !== 'Normal';
      const srag = S && S.ultimo && S.ultimo[uf] && S.ultimo[uf].consolidado, pos = srag && posicaoNaFaixa(S, uf);
      card.innerHTML = '<h4>' + esc(nome) + ' · ' + esc(uf) + '</h4><div class="grade-figuras grade-figuras--3">'
        + cartaoArbo(T('rotulo.dengue'), m.dengue, o.dengue, quando) + cartaoArbo(T('rotulo.chikungunya'), m.chikungunya, o.chikungunya, quando)
        + cartao('argila', T('rotulo.calor'), esc(m.calor == null ? T('calor.sem_coleta') : calor ? T('calor.com_excesso', {classe: String(m.calor).toLowerCase()}) : T('calor.sem_excesso')),
            esc(T('calor.nota', {data: MonitorMapas.dataBR((o.calor || {}).data) || ''})))
        + cartao('neutro', T('rotulo.srag'), srag ? esc(T('srag.valor', {n: srag.valor, semana: semana(srag.periodo)})) + (pos ? ' · <span class="posicao posicao--' + pos.posicao + '">' + esc(textoSaude('saude.posicao.' + pos.posicao)) + '</span>' : '') : esc(T('srag.sem_coleta')),
            esc(T('srag.nota', {data: (S && MonitorMapas.dataBR(S.coletado_em)) || ''})))
        + cartao('musgo', T('rotulo.plano_estado'), esc(textoSaude('saude.estadual.tipo.' + tipoDoEstado(uf))) + ' · <a href="#estadual" data-ficha="' + esc(uf) + '">' + esc(T('plano_estado.ficha')) + '</a>',
            esc(T('plano_estado.nota', {data: MSAUDE.corte || ''})))
        + cartaoPlanoDoMunicipio(sp, pl, uf, meta) + '</div>';
      card.querySelector('[data-ficha]').addEventListener('click', ev => { ev.preventDefault(); abrirDetalheSaude(ev.target.dataset.ficha); });
    }})).catch(_erroSaude("saude:consulta"));
})();

/* ===== Seção única de desfechos ============================================================
 * HANDOVER_SAUDE_DESFECHOS_BLOCO (editoria, 16/10/2026) e prioridade da editoria de 19/10.
 *
 * Um cartão por desfecho, todos lidos da MESMA forma: `data/saude_desfechos/<id>.json`, como
 * `desfechos_sus.py` a escreve (série por UF, por 100 mil, faixa habitual da época, último
 * período e o último já fechado). A página não sabe de onde veio cada número: o arquivo diz o
 * rótulo, a unidade, a cadência, a fonte e a data.
 *
 * Desfecho sem arquivo na forma comum não vira cartão vazio nem zero — ele ainda não tem cartão.
 * Território sem série no arquivo declara a lacuna da sua classe, com as palavras da classe.
 * Peso zero no índice (METODOLOGIA §8): o Monitor não atribui casos ao El Niño em nenhuma
 * superfície de desfecho — nem no cartão, nem no detalhe, nem na lista por estado.
 */
/* Os seis desfechos em evidência: o nome do arquivo na forma comum e o id do mesmo desfecho no
   catálogo, que é de onde sai o NOME quando ainda não há arquivo para dar o rótulo. */
const DESFECHOS_DA_SECAO = ['dengue', 'chikungunya', 'srag', 'obitos', 'diarreias', 'leptospirose'];
/* A segunda camada (HANDOVER_SAUDE_DESFECHOS_BLOCO §2): cartão igual, nas linhas seguintes, SEM mapa
   e sem detalhe, na ordem em que o dado nasceu. Os demais do catálogo (pele e olhos, saúde mental,
   ICSAP, tuberculose, desnutrição, malária) ficam no catálogo até a editoria pedir cartão. */
const SEGUNDA_CAMADA = ['internacoes_respiratorias', 'internacoes_cardio', 'internacoes_renal',
                        'internacoes_desidratacao', 'hepatite_a', 'internacoes_fumaca', 'internacoes_calor'];
const NO_CATALOGO = {dengue: 'dengue', chikungunya: 'chik', srag: 'srag', obitos: 'obitos',
                     diarreias: 'dda', leptospirose: 'lepto', internacoes_respiratorias: 'ira',
                     internacoes_cardio: 'cardio', internacoes_renal: 'renal',
                     internacoes_desidratacao: 'desidratacao', hepatite_a: 'hepatite_a',
                     internacoes_fumaca: 'intox_fumaca', internacoes_calor: 'calor_agravo'};
const EM_EVIDENCIA = d => DESFECHOS_DA_SECAO.indexOf(d.desfecho) >= 0;
const FAIXA_COR = {acima: MonitorMapas.PALETA.serie_habitual.acima, dentro: MonitorMapas.cor('vazio')};
let DESFECHOS_LIDOS = [], DESFECHO_ESCOLHIDO = null, DESF_CATALOGO = null;
const __graficoDesfecho = {};

/* "2026-08" → "agosto de 2026"; "2026-33" → a semana em datas (a palavra não chega ao leitor). */
function periodoEmPalavras(chave, cadencia) {
  const [ano, parte] = String(chave || '').split('-');
  if (cadencia === 'semana') return semanaEmDatas(Number(ano), chave, false) || '';
  const meses = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto',
                 'setembro', 'outubro', 'novembro', 'dezembro'];
  return (meses[Number(parte) - 1] || '') + ' de ' + ano;
}

/* O mesmo período, curto o bastante para caber numa legenda de 140 caracteres. */
function periodoCompacto(chave, cadencia) {
  if (!chave) return 'sem período fechado';
  if (cadencia !== 'semana') return periodoEmPalavras(chave, cadencia);
  const [ano] = String(chave).split('-');
  const curta = semanaEmDatas(Number(ano), chave, true);
  return curta ? curta + ' de ' + ano : chave;
}

/* A linha dos períodos recentes sobre a faixa habitual, em SVG: polígono da faixa em mineral,
   linha em tinta, último ponto em argila. Sem eixo e sem número: quem mede é o cartão. */
function serieEmSvg(valores, faixas, rotulo, estado) {
  const L = 240, A = 48, n = valores.length;
  if (n < 2) return '';
  const tetos = faixas.map(f => (f && f.p90) || 0);
  const alto = Math.max(1, Math.max.apply(null, valores.concat(tetos).filter(v => v != null)));
  const x = i => (i * L) / (n - 1), y = v => A - (Math.max(0, v || 0) / alto) * (A - 2);
  const faixaCima = faixas.map((f, i) => x(i) + ',' + y(f && f.p90)).join(' ');
  const faixaBaixo = faixas.map((f, i) => x(i) + ',' + y(f && f.mediana)).reverse().join(' ');
  const temFaixa = faixas.some(f => f && f.p90 != null);
  const linha = valores.map((v, i) => (v == null ? null : x(i) + ',' + y(v)))
    .filter(Boolean).join(' ');
  const ultimo = valores[n - 1];
  return '<svg class="cartao-numero-serie" viewBox="0 0 ' + L + ' ' + A + '" preserveAspectRatio="none"'
    + ' role="img" aria-label="' + esc(rotulo) + '">'
    + (temFaixa ? '<polygon points="' + faixaCima + ' ' + faixaBaixo + '" fill="' + MonitorMapas.PALETA.serie_habitual.faixa + '" fill-opacity="0.28"></polygon>' : '')
    + '<polyline points="' + linha + '" fill="none" stroke="' + MonitorMapas.cor('vazio') + '" stroke-width="1.5"></polyline>'
    /* O último período fechado é marcado por um traço vertical, não por um ponto: a caixa é
       esticada (`preserveAspectRatio="none"`) e um círculo sairia deformado. */
    + (ultimo == null ? '' : '<line x1="' + (L - 1) + '" x2="' + (L - 1) + '" y1="' + (y(ultimo) - 4)
       + '" y2="' + (y(ultimo) + 4) + '" stroke="' + (estado === 'acima' ? FAIXA_COR.acima : FAIXA_COR.dentro)
       + '" stroke-width="2"></line>')
    + '</svg>';
}

/* Os períodos recentes do território, na ordem do calendário: 52 semanas ou 24 meses, SEM os
   períodos que o arquivo declara parciais. Eles ainda recebem registro, e desenhá-los faria a
   linha do cartão cair no fim — ao lado de um valor que é o do último período fechado. */
function recorteRecente(d, uf) {
  const parciais = new Set(d.parcial || []);
  const serie = (d.por_100mil || {})[uf] || {};
  const chaves = Object.keys(serie).sort().filter(ch => !parciais.has(ch));
  const quantos = d.periodo === 'semana' ? 52 : 24;
  return chaves.slice(-quantos);
}

/* A posição do último valor consolidado do território na faixa habitual da SEMANA DO PRÓPRIO VALOR
   (comparar com a faixa de outra semana é o erro a impedir). Uma função para o cartão, a consulta
   do município e, adiante, o topo e o detalhe. A comparação é nos MESMOS números que o leitor lê:
   a precisão do rótulo varia com o tamanho do valor, e só `decBR` decide por ela. */
function posicaoNaFaixa(d, uf) {
  const c = ((d.ultimo || {})[uf] || {}).consolidado;
  const f = c && ((d.faixa_habitual || {})[uf] || {})[String(c.periodo).split('-')[1]];
  if (!f || f.p90 == null) return null;
  const uma = x => Number(String(decBR(x)).replace(/\./g, '').replace(',', '.'));
  const v = uma(c.por_100mil);
  return {posicao: v > uma(f.p90) ? 'acima' : (v < uma(f.mediana) ? 'abaixo' : 'dentro'), mediana: f.mediana, p90: f.p90};
}

function cartaoDesfecho(d, uf) {
  const u = (d.ultimo || {})[uf];
  const fonte = d.fonte || {};
  const cadencia = d.periodo === 'semana' ? ' · por semana · ' : ' · por mês · ';
  const rodape = 'Fonte: ' + esc((fonte.sistema || '').split(',')[0]) + ' · Atualização: ' + esc(MonitorMapas.dataBR(d.coletado_em) || d.coletado_em);
  if (!u || !u.consolidado) {
    return '<div class="cartao-numero cartao-numero--saude">'
      + '<p class="cartao-numero-familia">' + esc(d.rotulo) + '</p>'
      + '<p class="cartao-numero-valor">sem coleta</p>'
      + '<p class="cartao-numero-rotulo">' + esc(d.unidade) + ' por 100 mil' + cadencia
      + 'sem série para este território até o corte</p>'
      + '<p class="cartao-numero-fonte">' + rodape + '</p></div>';
  }
  const c = u.consolidado, chaves = recorteRecente(d, uf);
  const serie = (d.por_100mil || {})[uf] || {}, faixas = (d.faixa_habitual || {})[uf] || {};
  const doAno = ch => faixas[String(ch).split('-')[1]] || null;
  const p = posicaoNaFaixa(d, uf), dentro = p && p.posicao;
  const texto = !p ? textoSaude('saude.posicao.sem_faixa')
    : textoSaude('saude.posicao.' + p.posicao) + ' (' + decBR(p.mediana) + ' a ' + decBR(p.p90) + ')';
  /* Só o desfecho em evidência abre detalhe (§2): o cartão da segunda camada não é botão, não entra
     na ordem de tabulação e não promete um mapa que a seção não desenha para ele. */
  return '<div class="cartao-numero cartao-numero--saude"'
    + (EM_EVIDENCIA(d) ? ' role="button" tabindex="0" data-desfecho="' + esc(d.desfecho)
        + '" aria-pressed="' + (d.desfecho === DESFECHO_ESCOLHIDO) + '"' : '') + '>'
    + '<p class="cartao-numero-familia">' + esc(d.rotulo) + '</p>'
    + '<p class="cartao-numero-valor">' + esc(_qtdCartao(c.por_100mil)) + '</p>'
    + '<p class="cartao-numero-rotulo">' + esc(d.unidade) + ' por 100 mil' + cadencia
    + esc(periodoEmPalavras(c.periodo, d.periodo)) + '</p>'
    + '<p class="cartao-numero-variacao' + (p ? ' posicao posicao--' + dentro : '') + '">' + esc(texto) + '</p>'
    + serieEmSvg(chaves.map(ch => serie[ch]), chaves.map(doAno),
        d.rotulo + ', ' + (d.periodo === 'semana' ? 'últimas 52 semanas' : 'últimos 24 meses')
        + ', sobre a faixa habitual para a época', dentro)
    + '<p class="cartao-numero-fonte">' + rodape + '</p></div>';
}

/* O mapa do detalhe: o último período FECHADO de cada estado, pintado pelos cortes que o próprio
   arquivo traz — os quintis de 2019 a 2025, congelados na primeira gravação (METODOLOGIA §108).
   Cortes congelados são o que permite comparar o mapa de hoje com o de outro dia; recalculá-los a
   cada rodada mudaria a cor sem mudar o dado. Estado sem período fechado fica em sem-dado e a
   legenda nomeia a classe — nunca zero. */
function pintarMapaDoDesfecho(d) {
  const svgId = 'mapaDesfecho';
  if (!document.getElementById(svgId) || !BR_GEOJSON) return;
  const cortes = ((d.cortes_mapa || {}).cortes || []).slice();
  const rampa = MonitorMapas.PALETA.atmosfera.chuva_claro.rampa;
  const faixaDe = v => cortes.reduce((i, corte) => (v > corte ? i + 1 : i), 0);
  const valor = {};
  Object.keys(d.ultimo || {}).forEach(u => {
    const c = (d.ultimo[u] || {}).consolidado;
    if (u !== 'BR' && c && c.por_100mil != null) valor[u] = c.por_100mil;
  });
  const ctx = MonitorMapas.contexto(BR_GEOJSON, 480, 460);
  MonitorMapas.ufs(ctx, svgId,
    u => valor[u] == null ? MonitorMapas.NEUTRA : rampa[Math.min(rampa.length - 1, faixaDe(valor[u]))],
    u => valor[u] == null ? 'sem período fechado até o corte'
      : decBR(valor[u]) + ' ' + d.unidade + ' por 100 mil habitantes');
  const rotuloDaFaixa = i => (i === 0 ? 'até ' + decBR(cortes[0])
    : i === cortes.length ? decBR(cortes[cortes.length - 1]) + ' ou mais'
    : decBR(cortes[i - 1]) + ' a ' + decBR(cortes[i]));
  MonitorMapas.legenda('legMapaDesfecho', rampa.map((cor, i) => ({cor: cor, rotulo: rotuloDaFaixa(i)}))
    .concat([{cor: MonitorMapas.NEUTRA, rotulo: 'sem período fechado'}]));
  const lista = document.getElementById('dlDesfechoUF');
  if (lista) lista.innerHTML = Object.keys(valor).sort((a, b) => valor[b] - valor[a]).map(u =>
    '<dt>' + esc(NOME_UF[u] || u) + '</dt><dd>' + esc(decBR(valor[u])) + ' ' + esc(d.unidade)
    + ' por 100 mil habitantes</dd>').join('');
}

function pintarDesfechos() {
  const grade = document.getElementById('gradeDesfechos');
  const seletor = document.getElementById('ufDesfechos');
  if (!grade || !DESFECHOS_LIDOS.length) return;
  const uf = (seletor && seletor.value) || 'BR';
  const comDetalhe = DESFECHOS_LIDOS.filter(EM_EVIDENCIA);
  if (!comDetalhe.some(d => d.desfecho === DESFECHO_ESCOLHIDO)) DESFECHO_ESCOLHIDO = (comDetalhe[0] || {}).desfecho || null;
  grade.innerHTML = DESFECHOS_LIDOS.map(d => cartaoDesfecho(d, uf)).join('');
  pintarDetalhe(comDetalhe.find(d => d.desfecho === DESFECHO_ESCOLHIDO), uf);
}

/* Um ouvinte na grade, não um por cartão: a grade se repinta inteira a cada troca de território. */
function escolherDesfecho(ev) {
  const alvo = ev.target.closest('[data-desfecho]');
  if (!alvo || (ev.type === 'keydown' && ev.key !== 'Enter' && ev.key !== ' ')) return;
  if (ev.type === 'keydown') ev.preventDefault();
  DESFECHO_ESCOLHIDO = alvo.getAttribute('data-desfecho');
  pintarDesfechos();
}

/* O detalhe do cartão escolhido: a série inteira do território sobre a faixa habitual da época.
   Um detalhe por vez — escolher outro cartão troca o conteúdo, e a página não cresce. */
function pintarDetalhe(d, uf) {
  const fig = document.getElementById('boxDesfecho'), cv = document.getElementById('cDesfecho');
  if (!fig || !cv || !window.Chart) return;
  /* Sem desfecho escolhido não há o que detalhar: a figura recolhe, e declara a lacuna na própria
     linha de fonte — sem nomear sistema que não foi lido. Moldura vazia e muda é o pior desfecho. */
  if (!d) {
    fig.hidden = true;
    fonteFigura('boxDesfecho', {fontes: ['os sistemas de registro declarados em cada desfecho'], data: null});
    return;
  }
  fig.hidden = false;
  /* Só período FECHADO, na linha e no mapa: período parcial ainda recebe registro e, comparado
     com a faixa habitual, desenha queda onde há notificação a caminho. */
  const parciais = new Set(d.parcial || []);
  const chaves = Object.keys((d.por_100mil || {})[uf] || {}).sort().filter(ch => !parciais.has(ch));
  const serie = (d.por_100mil || {})[uf] || {}, faixas = (d.faixa_habitual || {})[uf] || {};
  const doAno = ch => faixas[String(ch).split('-')[1]] || {};
  /* Eixo em meses, como manda a régua do site; o período inteiro, por extenso, fica no texto do
     mouse — a série pode ter oito anos de semanas, e o rótulo por extenso não cabe no eixo. */
  const MES3 = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez'];
  const noEixo = ch => {
    if (d.periodo !== 'semana') return MES3[Number(ch.split('-')[1]) - 1] + '/' + ch.split('-')[0];
    const por = periodoEmPalavras(ch, 'semana').match(/de (\w+) de (\d{4})$/);
    return por ? por[1].slice(0, 3) + '/' + por[2] : ch;
  };
  const rotulos = chaves.map(noEixo);
  const C = window.MonitorCatalogo;
  const campo = (id, texto) => { const el = document.getElementById(id); if (el) el.textContent = texto; };
  const molde = (chave, vals) => (C && C.texto('saude.observado.registram.detalhe.' + chave, vals)) || '';
  const anos = chaves.length ? (chaves[0].split('-')[0] + ' a ' + chaves[chaves.length - 1].split('-')[0]) : 'sem série';
  campo('tituloDesfecho', molde('titulo', {desfecho: d.rotulo,
    territorio: uf === 'BR' ? 'Brasil' : NOME_UF[uf], periodo: anos}));
  const ultimoBR = ((d.ultimo || {}).BR || {}).consolidado || {};
  campo('legendaDesfecho', molde('legenda', {
    periodo: periodoCompacto(ultimoBR.periodo, d.periodo),
    parciais: (d.parcial || []).length
      ? 'os ' + (d.parcial || []).length + ' períodos ainda em registro ficam fora'
      : 'série fechada até o último período'}));
  MonitorMapas.padraoGraficos(window.Chart);
  if (__graficoDesfecho.g && typeof __graficoDesfecho.g.destroy === 'function') __graficoDesfecho.g.destroy();
  __graficoDesfecho.g = new Chart(cv, {data: {labels: rotulos, datasets: [
      {type: 'line', label: 'valor observado', data: chaves.map(ch => serie[ch] ?? null),
       borderColor: MonitorMapas.cor('vazio'), borderWidth: 1.5, pointRadius: 0, order: 1},
      /* A faixa é uma FAIXA, não duas linhas: o traço de cima preenche até o de baixo, como a
         legenda aprovada diz ("faixa cinza") e como a linha dentro do cartão já desenha. */
      {type: 'line', label: 'faixa habitual para a época', fill: '+1',
       data: chaves.map(ch => doAno(ch).p90 ?? null), borderColor: MonitorMapas.PALETA.serie_habitual.faixa,
       backgroundColor: MonitorMapas.PALETA.serie_habitual.faixa_fundo, borderWidth: 1, pointRadius: 0, order: 2},
      {type: 'line', label: 'faixa habitual para a época',
       data: chaves.map(ch => doAno(ch).mediana ?? null), borderColor: MonitorMapas.PALETA.serie_habitual.faixa,
       borderWidth: 1, pointRadius: 0, order: 2}]},
    options: {animation: false, responsive: true, maintainAspectRatio: false,
      plugins: {legend: {display: false},
        tooltip: {callbacks: {title: it => periodoEmPalavras(chaves[it[0].dataIndex], d.periodo)}}},
      scales: {x: {ticks: {maxTicksLimit: 8, autoSkip: true}},
               y: {beginAtZero: true, title: {display: true, text: d.unidade + ' por 100 mil'}}}}});
  MonitorMapas.legenda('legDesfecho', [
    {cor: MonitorMapas.cor('vazio'), rotulo: 'valor observado'},
    {cor: MonitorMapas.PALETA.serie_habitual.faixa, rotulo: 'faixa habitual para a época (2019–2025)'}]);
  pintarMapaDoDesfecho(d);
  /* O gráfico nasce antes de o mapa ocupar a segunda coluna da figura dupla: sem este ajuste, a
     tela do Chart.js guarda a largura da figura inteira e passa por cima do mapa. */
  if (__graficoDesfecho.g && typeof __graficoDesfecho.g.resize === 'function') __graficoDesfecho.g.resize();
  fonteFigura('boxDesfecho', {fontes: [(d.fonte || {}).sistema], data: d.coletado_em, url: (d.fonte || {}).url});
}

/* Desfecho em evidência que ainda não tem arquivo na forma comum não vira cartão vazio: a seção
   declara a lacuna da CLASSE numa linha, e o nome vem do catálogo dos desfechos — não daqui.
   Enquanto nenhum faltar, a linha não existe. */
function declararDesfechoSemArquivo(lidos) {
  const linha = document.getElementById('desfechosLacuna'), C = window.MonitorCatalogo;
  if (!linha || !C) return;
  const temArquivo = new Set((lidos || []).filter(Boolean).map(d => d.desfecho));
  const faltam = DESFECHOS_DA_SECAO.filter(id => !temArquivo.has(id)).map(id => NO_CATALOGO[id]);
  if (!faltam.length || !DESF_CATALOGO) { mostrarFrase(linha, ''); return; }
  const nomes = (DESF_CATALOGO.desfechos || [])
    .filter(x => faltam.indexOf(x.id) >= 0)
    .map(x => String(x.nome || '').replace(/\s*\(.*\)\s*$/, ''))
    .map((nome, i) => (i === 0 ? nome : nome.charAt(0).toLowerCase() + nome.slice(1)));
  const lista = nomes.length > 1 ? nomes.slice(0, -1).join(', ') + ' e ' + nomes[nomes.length - 1] : nomes[0];
  mostrarFrase(linha, nomes.length ? C.texto('saude.observado.registram.lacuna', {faltam: lista}) : '');
}

async function montarDesfechos() {
  const grade = document.getElementById('gradeDesfechos');
  if (!grade) return;
  if (window.MonitorCatalogo && window.MonitorCatalogo.pronto) { try { await window.MonitorCatalogo.pronto; } catch (e) {} }
  const lidos = await Promise.all(DESFECHOS_DA_SECAO.concat(SEGUNDA_CAMADA).map(id =>
    fetch('data/saude_desfechos/' + id + '.json').then(r => (r.ok ? r.json() : null)).catch(() => null)));
  DESF_CATALOGO = await fetch('data/saude_desfechos/catalogo.json')
    .then(r => (r.ok ? r.json() : null)).catch(() => null);
  DESFECHOS_LIDOS = lidos.filter(d => d && d.esquema === 1 && d.ultimo && d.por_100mil);
  const bloco = document.getElementById('desfechos');
  if (!DESFECHOS_LIDOS.length) { if (bloco) bloco.hidden = true; pintarDetalhe(null); return; }   // bloco inteiro recolhido: a lacuna não aparece sozinha numa seção sem grade
  if (bloco) bloco.hidden = false;
  declararDesfechoSemArquivo(lidos);
  const seletor = document.getElementById('ufDesfechos');
  if (seletor && !seletor.options.length) {
    seletor.innerHTML = '<option value="BR">Brasil</option>'
      + UFS.map(u => '<option value="' + u + '">' + esc(NOME_UF[u]) + '</option>').join('');
    seletor.addEventListener('change', pintarDesfechos);
  }
  grade.addEventListener('click', escolherDesfecho);
  grade.addEventListener('keydown', escolherDesfecho);
  pintarDesfechos();
}
