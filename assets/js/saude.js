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
let BR_GEOJSON, MSAUDE;
// Lote 6, §2: a frase do dado nasce oculta e só aparece com texto — nunca "—" nem linha vazia.
const mostrarFrase = (alvo, texto) => { alvo.textContent = texto; alvo.hidden = !texto; };
/* Número em texto público com vírgula decimal (A4-16); não-número passa como veio ("—", nulo).
   21/10/2026: uma casa decimal, SALVO quando ela zeraria um valor medido — 0,037 internação por
   100 mil saía "0", e dizer zero onde houve 75 internações é afirmar o que não se mediu. Abaixo de
   0,05 vale um dígito significativo ("0,04", "0,009"), que é curto e não mente. */
const decBR = v => (v == null || v === '' || isNaN(Number(v))) ? v
  : MonitorMapas.numBR(v, Number.isInteger(Number(v)) ? 0 : 1);
const umaCasa = v => Number(v || 0).toLocaleString('pt-BR', {minimumFractionDigits: 1, maximumFractionDigits: 1});
/* Texto público vem do catálogo (`conteudo/saude.json`); vazio se ele não carregou (falha segura). */
const T = (id, valores) => (window.MonitorCatalogo && window.MonitorCatalogo.texto(id, valores)) || '';

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

const UFS = ["AC","AL","AM","AP","BA","CE","DF","ES","GO","MA","MG","MS","MT","PA","PB","PE","PI","PR","RJ","RN","RO","RR","RS","SC","SE","SP","TO"];
const NOME_UF = {AC:'Acre',AL:'Alagoas',AM:'Amazonas',AP:'Amapá',BA:'Bahia',CE:'Ceará',DF:'Distrito Federal',ES:'Espírito Santo',GO:'Goiás',MA:'Maranhão',MG:'Minas Gerais',MS:'Mato Grosso do Sul',MT:'Mato Grosso',PA:'Pará',PB:'Paraíba',PE:'Pernambuco',PI:'Piauí',PR:'Paraná',RJ:'Rio de Janeiro',RN:'Rio Grande do Norte',RO:'Rondônia',RR:'Roraima',RS:'Rio Grande do Sul',SC:'Santa Catarina',SE:'Sergipe',SP:'São Paulo',TO:'Tocantins'};
const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));

async function __load(){
  [BR_GEOJSON, MSAUDE] = await Promise.all(['geo_uf', 'monitor_saude'].map(f => fetch('data/' + f + '.json').then(r => {
    if(!r.ok) throw new Error('Falha ao carregar data/' + f + '.json'); return r.json(); })));
  if (window.MonitorCatalogo) { try { await window.MonitorCatalogo.pronto; } catch (e) {} }
  medidoresDoTopo();
  mapaDosEstados();
  consultaDoMunicipio();
  listaFederal();
  montarDesfechos().catch(_erroSaude("saude:desfechos"));
}

const fonteFigura = MonitorMapas.credito;

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
const TIPOS_DE_PLANO = ['NOVO', 'READ', 'VIG', 'ELAB', 'LAC', 'NAO_VERIFICADO'];
const ufsSaude = () => (MSAUDE && MSAUDE.ufs) || {};
/* O tipo de plano de cada estado é o degrau do instrumento; estado não verificado é a sexta classe. */
const tipoDoEstado = uf => { const m = ufsSaude()[uf] || {}; return m.verificado ? (m.instrumento || {}).status || 'NAO_VERIFICADO' : 'NAO_VERIFICADO'; };
/* As funções da coordenação JÁ verificadas (as que têm ato lido): a linha "Coordenação" da ficha e da
   tabela se preenche sozinha à medida que a rotina verifica cada estado; sem nenhuma, ainda não verificada. */
const funcoesVerificadas = uf => ['f1', 'f2'].map(k => [k, ((ufsSaude()[uf] || {}).coordenacao || {})[k]]).filter(([, o]) => o && o.doc);

/* ===== O topo (HANDOVER_SAUDE_PAGINA §1.2): os dois medidores da inicial. À esquerda, o MARÉ Saúde
   NACIONAL, sobre as 27 UFs, pela mesma regra do MARÉ Legal (METODOLOGIA §115); à direita, a parcela da
   população sob decreto de emergência em saúde, com a nomenclatura e o comportamento do medidor da
   inicial (sem dado: número, "/ 100" e pílula vazios; a linha diz uma vez "sem coleta até o corte"). */
function medidoresDoTopo(){
  const el = id => document.getElementById(id);
  const n = v => Number(v || 0).toLocaleString('pt-BR');
  const res = MSAUDE.resumo || {}, rp = MSAUDE.resposta || {};
  const fixa = (id, v, rotulo) => { const f = el(id); f.dataset.alvo = String(v); f.style.setProperty('--galvo', String(Math.max(v, 0.1)));
    f.closest('.gauge-track').setAttribute('aria-label', 'Barra de progresso: ' + rotulo + ' em ' + umaCasa(v) + ' de 100'); };
  const media = res.indice_nacional;
  /* Ausência se escreve em palavras, inclusive no número grande (layout/regras.json, numeros). */
  if (media == null) { el('nIndiceSaude').textContent = 'sem coleta'; el('linhaPreparoSaude').textContent = T('saude.topo.preparacao.linha_reserva'); }
  else {
    el('nIndiceSaude').textContent = umaCasa(media); el('nIndiceSaude').dataset.contar = media;
    el('faixaSaude').replaceChildren(MonitorMapas.pilulaDaFaixa(media));
    fixa('gaugeFillSaude', media, 'MARÉ Saúde');
    /* A linha conta o ESTATUTO, nas palavras da classe: estado sem plano localizado e estado ainda não
       verificado são coisas distintas, e integrar o nacional não apaga a lacuna. */
    MonitorCatalogo.escrever('linhaPreparoSaude', 'saude.topo.preparacao.linha', {
      com_plano: n(res.ufs_com_plano_localizado), denominador: n(res.denominador || 27),
      sem_numero: res.nao_verificadas, corte: MSAUDE.corte || ''});
  }
  if (rp.indice != null) {
    el('respNumSaude').textContent = umaCasa(rp.indice); el('respNumSaude').dataset.contar = rp.indice;
    el('respDenSaude').textContent = '/ 100';
    fixa('respFillSaude', rp.indice, 'decretos de emergência em saúde');
    el('respBadgeSaude').innerHTML = '<span class="gfaixa-pill">' + esc(T('saude.topo.resposta.pilula', {n: rp.emergencias || 0,
      pct: umaCasa(100 * (rp.pop_sob_emergencia || 0) / (rp.pop_total || 1))})) + '</span>';
    MonitorCatalogo.escrever('linhaRespostaSaude', 'saude.topo.resposta.linha', {quando: MSAUDE.gerado_em || MSAUDE.corte || ''});
  }
  MonitorMapas.animarGauges(el('topoSaude'));
}

/* ===== "A situação de cada estado": mapa categórico por TIPO de plano (cores da paleta de status do
   instrumento, nome escrito ao lado de cada cor), a lista dos seis tipos com as siglas como botões
   (o seletor acessível do estado: teclado, leitor de tela e toque, onde DF, SE, AL e RN são pequenos
   demais no mapa) e a ficha do estado, que o mapa e a lista abrem. */
function mapaDosEstados(){
  const M = ufsSaude(), cor = t => MonitorMapas.PALETA.status[t];
  const ctx = MonitorMapas.contexto(BR_GEOJSON, 480, 460);
  MonitorMapas.desenharMapa(ctx, 'mapaMonitor', 'legMonitor', uf => cor(tipoDoEstado(uf)),
    uf => { const m = M[uf] || {}; return '<em>' + esc(T('saude.estadual.tipo.' + tipoDoEstado(uf))) + '</em>' + (m.verificado ? '<br>' + esc(decBR(m.prontidao)) + ' de 100' : ''); },
    TIPOS_DE_PLANO.map(t => ({cor: cor(t), rotulo: T('saude.estadual.tipo.' + t)})));
  d3.select('#mapaMonitor').selectAll('path.uf-path').style('cursor', 'pointer')
    .on('click', (evt, d) => abrirDetalheSaude(d.properties.sigla))
    .on('keydown', (evt, d) => { if (evt.key === 'Enter' || evt.key === ' ') { evt.preventDefault(); abrirDetalheSaude(d.properties.sigla); } });
  const lista = document.getElementById('listaTiposPlano');
  lista.innerHTML = TIPOS_DE_PLANO.map(t => { const ufs = UFS.filter(u => tipoDoEstado(u) === t);
    return '<div><dt>' + esc(T('saude.estadual.tipo.' + t)) + ' · ' + ufs.length + '</dt><dd class="chips">'
      + ufs.map(u => '<button type="button" class="chip-risco" data-uf="' + u + '" aria-pressed="false" aria-label="' + esc(NOME_UF[u]) + '">' + u + '</button>').join('') + '</dd></div>'; }).join('');
  lista.addEventListener('click', ev => { const b = ev.target.closest('button[data-uf]'); if (b) abrirDetalheSaude(b.dataset.uf); });
  document.getElementById('detailSaude').addEventListener('close', () => lista.querySelectorAll('[aria-pressed="true"]').forEach(b => b.setAttribute('aria-pressed', 'false')));
  MonitorCatalogo.escrever('notaEscadaSaude', 'saude.estadual.monitor.nota', (MSAUDE.metodo || {}).escada || {});
  // A tabela diz o que o mapa mostra: tipo, nota e coordenação, uma linha por UF.
  const coord = uf => { const fs = funcoesVerificadas(uf); return fs.length ? fs.map(([, o]) => esc(ST_COORD[o.status] || o.status) + (o.data ? ' · ' + esc(o.data) : '')).join('; ') : T('saude.ficha.coordenacao_vazia'); };
  document.querySelector('#tblMonitor tbody').innerHTML = UFS.map(uf => { const m = M[uf] || {};
    return '<tr><td><strong>' + uf + '</strong></td><td>' + esc(T('saude.estadual.tipo.' + tipoDoEstado(uf))) + '</td><td>' + (m.verificado ? esc(decBR(m.prontidao)) : 'sem número') + '</td><td>' + coord(uf) + '</td></tr>'; }).join('');
  fonteFigura('boxMonitor', {fontes: ['MARÉ Saúde'], data: MSAUDE.gerado_em});
}

/* A ficha do estado: tipo de plano, documento com link, data, órgão e coordenação. Todo rótulo vem do
   catálogo; a linha da coordenação lê `ufs.<UF>.coordenacao` do motor e se preenche sozinha. */
function abrirDetalheSaude(uf){
  const m = ufsSaude()[uf] || {}, i = m.instrumento || {};
  const linha = (k, v) => '<div class="field"><div class="k">' + esc(T('saude.ficha.' + k)) + '</div><div class="v">' + v + '</div></div>';
  const ato = o => esc(o.doc) + (o.data ? ' (' + esc(o.data) + ')' : '') + (o.url ? ' · <a href="' + esc(o.url) + '" target="_blank" rel="noopener">fonte oficial →</a>' : '');
  const fs = funcoesVerificadas(uf);
  document.getElementById('detailSaudeConteudo').innerHTML = '<div class="uf-name">' + esc(NOME_UF[uf]) + ' <span class="sub">(' + uf + ')</span></div>'
    + (m.verificado ? '<div class="gauge-mini gauge-zone"><div class="gauge-head"><span class="gnum">' + String(m.prontidao).replace('.', ',') + '</span><span class="gden">/ 100 · ' + esc(m.faixa) + '</span></div><div class="gauge-track"><div class="gauge-fill" style="--galvo:' + Math.max(m.prontidao, 0.1) + '; width:' + m.prontidao + '%"></div></div></div>' : '')
    + linha('tipo', '<span class="pill-nivel">' + esc(T('saude.estadual.tipo.' + tipoDoEstado(uf))) + '</span>')
    + (i.doc ? linha('documento', i.url ? '<a href="' + esc(i.url) + '" target="_blank" rel="noopener">' + esc(i.doc) + '</a>' : esc(i.doc)) : '')
    + (i.data ? linha('data', esc(MonitorMapas.dataBR(i.data) || i.data)) : '')
    + (i.orgao ? linha('orgao', esc(i.orgao)) : '')
    + linha('coordenacao', fs.length ? fs.map(([k, o]) => esc(T('saude.ficha.' + k)) + ': <span class="pill-nivel">' + esc(ST_COORD[o.status] || o.status) + '</span> ' + ato(o)).join('<br>') : esc(T('saude.ficha.coordenacao_vazia')));
  document.querySelectorAll('#listaTiposPlano button').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.uf === uf)));
  const dlg = document.getElementById('detailSaude');
  if (!dlg.open) { if (typeof dlg.showModal === 'function') dlg.showModal(); else dlg.open = true; }
}

window.addEventListener('load', function(){ if (window.VLibras && window.VLibras.Widget) { try { new window.VLibras.Widget('https://vlibras.gov.br/app'); } catch (e) {} } });
__load().catch(err => { const m = document.getElementById('subSaude'); if (m) m.insertAdjacentHTML('afterend', '<p class="note u-rust">Erro ao carregar os dados: '+esc(err.message)+'</p>'); });


/* ===== Cartões do topo (bloco A.1 do handover de 02/10/2026) =====
 * Cinco indicadores que mudam a cada coleta. Os dois primeiros vêm da FONTE PRIMÁRIA (SINAN e
 * SIVEP-Gripe) e trazem, no próprio cartão, a ressalva de parcialidade.
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

/* ===== Consulta do município (HANDOVER_SAUDE_PAGINA §4): uma só, no componente comum. Dengue,
   chikungunya, calor e plano vêm de `data/saude_municipio/<UF>.json`, por código IBGE; município sem
   bloco não foi lido pela fonte, e é dito assim, nunca zero. Respiratória grave e o MARÉ Saúde são do
   estado, e a linha diz que são. */
function consultaDoMunicipio(){
  const n = v => Number(v || 0).toLocaleString('pt-BR');
  const NIVEL = {1: 'nível 1 (baixa atividade)', 2: 'nível 2 (atenção)', 3: 'nível 3 (alerta)', 4: 'nível 4 (emergência)'};
  const semana = v => { const m = /(\d{4})-(\d{1,2})/.exec(String(v || '')); return (m && MonitorSemana.porExtenso(+m[1], +m[2], true)) || ''; };
  const porUF = {}, S = fetch('data/saude_desfechos/srag_serie.json').then(r => r.ok ? r.json() : null).catch(() => null);
  const linha = (rotulo, valor, fonte) => '<tr><th scope="row">' + esc(rotulo) + '</th> <td>' + valor + '</td> <td class="dica-fonte">' + esc(fonte) + '</td></tr>';
  ConsultaMunicipio.montar({uf: 'consultaSaudeUF', municipio: 'consultaSaudeMun', lista: 'consultaSaudeLista', cartao: 'consultaSaudeCard',
    estados: Object.fromEntries(BR_GEOJSON.features.map(f => [f.properties.sigla, f.properties.name])), semLista: 'Consulta do estado: sem coleta até o corte.',
    municipios: uf => (porUF[uf] = porUF[uf] || Promise.all([fetch('data/saude_municipio/' + uf + '.json').then(r => r.ok ? r.json() : null).catch(() => null), S]))
      .then(([D, srag]) => { porUF[uf].dados = {D, S: srag}; return D && Object.values(D.municipios).map(x => x.nome); }),
    mostrar: (uf, nome, card) => {
      const {D, S} = porUF[uf].dados, MS = MSAUDE, o = D.origens || {}, m = Object.values(D.municipios).find(x => x.nome === nome);
      const arbo = (x, fonte) => x ? esc(NIVEL[x.nivel] || 'nível ' + x.nivel) + (semana(x.semana) ? ', semana ' + esc(semana(x.semana)) : '')
          + (x.notificacoes ? ' · ' + n(x.notificacoes.casos) + (x.notificacoes.casos === 1 ? ' notificação' : ' notificações') + (semana(x.notificacoes.semana) ? ' na semana ' + esc(semana(x.notificacoes.semana)) : '') : '')
        : 'município não lido pelo ' + esc(fonte) + ' na semana';
      const ano = String((S && S.ano_corrente) || ''), su = S && S.serie && S.serie[uf];
      const srag = su ? Object.entries(su).filter(([k, v]) => k.startsWith(ano) && typeof v === 'number').reduce((t, [, v]) => t + v, 0) : null;
      const e = ufsSaude()[uf] || {}, pl = m.saude_no_plano;
      card.innerHTML = '<h4>' + esc(nome) + ' · ' + esc(uf) + '</h4><div class="tbl-wrap"><table class="mun-table"><tbody>'
        + linha('Dengue', arbo(m.dengue, 'InfoDengue'), (o.dengue || {}).fonte + ' · ' + ((o.dengue || {}).gerado_em || ''))
        + linha('Chikungunya', arbo(m.chikungunya, 'InfoDengue'), (o.chikungunya || {}).fonte + ' · ' + ((o.chikungunya || {}).gerado_em || ''))
        + linha('Excesso de calor', m.calor ? 'classe ' + esc(m.calor) : 'município não lido na consulta mais recente', (o.calor || {}).fonte + ' · ' + (MonitorMapas.dataBR((o.calor || {}).data) || ''))
        + linha('Síndrome respiratória grave (estado)', srag == null ? 'sem coleta até o corte' : n(srag) + ' internações no estado em ' + esc(ano), 'SIVEP-Gripe (Ministério da Saúde)' + (S && S.gerado_em ? ' · ' + S.gerado_em : ''))
        + linha('MARÉ Saúde (estado)', (e.verificado ? umaCasa(e.prontidao) + ' de 100 · ' + esc(e.faixa || '') : 'estado ainda não verificado') + ' · <a href="#estadual">ver a ficha do estado</a>', 'MARÉ' + (MS && MS.corte ? ' · ' + MS.corte : ''))
        + linha('Plano de contingência do município', (pl ? 'trata a saúde (leitura automática' + (pl.pagina_citada ? ', p. ' + esc(pl.pagina_citada) : '') + ')' + (pl.url ? ' · <a href="' + esc(pl.url) + '" target="_blank" rel="noopener">abrir o plano</a>' : '') : 'sem leitura da saúde no plano até o corte')
          + ' · <a href="index.html#' + esc(uf) + '">ver a ficha na página inicial</a>', (o.saude_no_plano || {}).fonte || 'MARÉ Legal')
        + '</tbody></table></div>';
    }});
}

/* A lista do governo federal, sem cartão (o contrato pede lista simples). */
function listaFederal(){
  fetch('data/saude_federal.json').then(r => r.ok ? r.json() : null).then(F => {
    const alvo = document.getElementById('listaFederalSaude');
    if (!alvo) return;
    // 11/10/2026 (HANDOVER_SAUDE item 2): o arquivo guarda a lista em `cartoes`; a página procurava
    // `itens`/`documentos` e dizia "nenhum documento localizado" com oito no arquivo.
    const itens = (F && (F.cartoes || F.itens || F.documentos)) || [];
    if (!itens.length) {
      alvo.innerHTML = '<li>Nenhum documento federal localizado até o corte.</li>';
      return;
    }
    alvo.innerHTML = itens.map(x => {
      // Travessão como pontuação reprova no portão 19; no título do documento vira dois-pontos.
      const nome = esc(String(x.nome || x.titulo || x.documento || 'documento').replace(/\s+—\s+/g, ': '));
      const meta = [x.orgao, x.data].filter(v => v && v !== '—').map(esc).join(' · ');
      const alvoTxt = x.url ? '<a href="' + esc(x.url) + '" target="_blank" rel="noopener">' + nome + '</a>' : nome;
      const nl = x.status === 'anunciado_nao_localizado'
        ? '. Anunciado; documento não localizado até ' + esc(F.corte || 'o corte') + '.' : '';
      return '<li>' + alvoTxt + (meta ? ' <span class="u-muted">(' + meta + ')</span>' : '') + nl + '</li>';
    }).join('');
  }).catch(_erroSaude("saude:federal"));
}

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
/* A FAMÍLIA do desfecho, pelo cenário do El Niño que o traz (a abertura da página): fumaça e fogo,
   chuva forte, calor; dengue e chikungunya aparecem nos três, e têm a cor de "mais de uma família".
   A faixa habitual do desfecho se pinta na cor da família, bem clara, para não disputar com a linha do
   valor observado; desfecho sem família na paleta (óbitos) fica no mineral do recorrente. */
const FAMILIA_DO_DESFECHO = {dengue: 'multi', chikungunya: 'multi', srag: 'fogo', internacoes_respiratorias: 'fogo',
  internacoes_fumaca: 'fogo', diarreias: 'chuva', hepatite_a: 'chuva', leptospirose: 'chuva',
  internacoes_desidratacao: 'seca', internacoes_cardio: 'calor', internacoes_renal: 'calor', internacoes_calor: 'calor'};
const corDaFamilia = id => { const P = MonitorMapas.PALETA, f = FAMILIA_DO_DESFECHO[id];
  return P.familia[f] || P.risco[f] || P.serie_habitual.faixa; };
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
function serieEmSvg(valores, faixas, rotulo, estado, cor) {
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
    + (temFaixa ? '<polygon points="' + faixaCima + ' ' + faixaBaixo + '" fill="' + cor + '" fill-opacity="0.2"></polygon>' : '')
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
  const f = doAno(c.periodo);
  /* Três posições, cada uma dita como é: acima do maior valor esperado, dentro da faixa, ou
     abaixo do menor. Dizer "dentro" de um valor que está abaixo da faixa seria descrever errado
     o que o leitor vê no gráfico. */
  /* A comparação é feita nos MESMOS números que o leitor lê (uma casa decimal): comparar no valor
     cheio escreve "abaixo da faixa habitual (0,2 a 0,2)" para um cartão que mostra 0,2. */
  /* Comparar NO NÚMERO EXIBIDO, lendo de volta o que `decBR` escreveu: a precisão do rótulo varia
     com o tamanho do valor, e repetir aqui a régua do decBR seria copiar a mesma decisão em dois
     lugares — o jeito de os dois nunca divergirem é só um deles decidir. */
  const uma = x => Number(String(decBR(x)).replace(/\./g, '').replace(',', '.'));
  const dentro = !f || f.p90 == null ? null
    : (uma(c.por_100mil) > uma(f.p90) ? 'acima' : (uma(c.por_100mil) < uma(f.mediana) ? 'abaixo' : 'dentro'));
  const texto = T('saude.observado.registram.posicao.' + (dentro || 'sem'));
  /* Só o desfecho em evidência abre detalhe (§2): o cartão da segunda camada não é botão, não entra
     na ordem de tabulação e não promete um mapa que a seção não desenha para ele. */
  return '<div class="cartao-numero cartao-numero--saude"'
    + (EM_EVIDENCIA(d) ? ' role="button" tabindex="0" data-desfecho="' + esc(d.desfecho)
        + '" aria-pressed="' + (d.desfecho === DESFECHO_ESCOLHIDO) + '"' : '') + '>'
    + '<p class="cartao-numero-familia">' + esc(d.rotulo) + '</p>'
    + '<p class="cartao-numero-valor">' + esc(_qtdCartao(c.por_100mil)) + '</p>'
    + '<p class="cartao-numero-rotulo">' + esc(d.unidade) + ' por 100 mil' + cadencia
    + esc(periodoEmPalavras(c.periodo, d.periodo)) + '</p>'
    + '<p class="cartao-numero-variacao cartao-numero-variacao--' + (dentro || 'sem') + '">' + esc(texto) + '</p>'
    + serieEmSvg(chaves.map(ch => serie[ch]), chaves.map(doAno),
        d.rotulo + ', ' + (d.periodo === 'semana' ? 'últimas 52 semanas' : 'últimos 24 meses')
        + ', sobre a faixa habitual para a época', dentro, corDaFamilia(d.desfecho))
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
  const familia = corDaFamilia(d.desfecho);
  const campo = (id, texto) => { const el = document.getElementById(id); if (el) el.textContent = texto; };
  const molde = (chave, vals) => T('saude.observado.registram.detalhe.' + chave, vals);
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
       data: chaves.map(ch => doAno(ch).p90 ?? null), borderColor: familia + '66',
       backgroundColor: familia + '2E', borderWidth: 1, pointRadius: 0, order: 2},
      {type: 'line', label: 'faixa habitual para a época',
       data: chaves.map(ch => doAno(ch).mediana ?? null), borderColor: familia + '66',
       borderWidth: 1, pointRadius: 0, order: 2}]},
    options: {animation: false, responsive: true, maintainAspectRatio: false,
      plugins: {legend: {display: false},
        tooltip: {callbacks: {title: it => periodoEmPalavras(chaves[it[0].dataIndex], d.periodo)}}},
      scales: {x: {ticks: {maxTicksLimit: 8, autoSkip: true}},
               y: {beginAtZero: true, title: {display: true, text: d.unidade + ' por 100 mil'}}}}});
  MonitorMapas.legenda('legDesfecho', [
    {cor: MonitorMapas.cor('vazio'), rotulo: 'valor observado'},
    {cor: familia + '66', rotulo: 'faixa habitual para a época (2019–2025)'}]);
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
