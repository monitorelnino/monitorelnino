/* ===== financiamento.html · o dinheiro do El Niño, por risco e por lugar ==================
 *
 * Reforma de 17/10/2026 (robo-registro/notas/HANDOVER_FINANCIAMENTO_16-10-2026.md). A ordem é a do
 * contrato `layout/contratos/financiamento.json`: cinco números, o dinheiro por risco declarado no
 * ato, onde ele chega (figura principal), mês a mês, a consulta do município e a defesa civil depois
 * do reconhecimento (o que saiu da página da Defesa civil).
 *
 * Regras que atravessam a página:
 *   · o risco de uma fonte é só o que o ATO declara (`risco_declarado`, escrito pelo gerador a partir
 *     do texto do ato); fonte sem risco declarado fica fora das colunas e aparece na tabela;
 *   · etapa sem execução coletada é "não localizado até o corte", nunca barra zero;
 *   · o "Plano federal El Niño" é o anúncio que contém as duas MPs: não entra como origem própria, para
 *     não somar o mesmo dinheiro duas vezes;
 *   · valor real pequeno não vira zero ("menos de R$ 0,01").
 */
let BR_GEOJSON, MPS, COMPROMISSOS, RECURSOS, S, FNS_MUN = null,
    LATLON = {}, MUN_COD = {}, NOMES_POR_UF = {};

const PLANO_FEDERAL = /Plano federal El Niño/i;
const RISCOS = [
  {chave: 'fogo', rotulo: 'Fogo', acento: 'cartao--acento-fogo'},
  {chave: 'seca', rotulo: 'Seca', acento: 'cartao--acento-seca'},
  {chave: 'chuva', rotulo: 'Chuva forte', acento: 'cartao--acento-chuva'},
  {chave: 'saude', rotulo: 'Saúde', acento: 'cartao--acento-sintetico-topo'},
];
const ACOES = {resposta: 'Resposta', recuperacao: 'Recuperação', outra: 'Outras ações'};
const MESES = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez'];
const MESES_LONGOS = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro'];
const PREPOSICAO = {AC: 'No', AL: 'Em', AM: 'No', AP: 'No', BA: 'Na', CE: 'No', DF: 'No', ES: 'No',
  GO: 'Em', MA: 'No', MG: 'Em', MS: 'No', MT: 'No', PA: 'No', PB: 'Na', PE: 'Em', PI: 'No', PR: 'No',
  RJ: 'No', RN: 'No', RO: 'Em', RR: 'Em', RS: 'No', SC: 'Em', SE: 'Em', SP: 'Em', TO: 'No'};

/* Reais no formato do site: bilhão e milhão abreviados, mil por extenso, nunca zero para o que existe. */
function reais(v){
  if (v == null || !isFinite(v)) return null;
  const f = (x, c) => x.toLocaleString('pt-BR', {minimumFractionDigits: c, maximumFractionDigits: c});
  if (v > 0 && v < 0.01) return 'menos de R$ 0,01';
  if (v >= 1e9) return 'R$ ' + f(v / 1e9, 2) + ' bi';
  if (v >= 1e6) return 'R$ ' + f(v / 1e6, v >= 1e8 ? 0 : 1) + ' mi';
  if (v >= 1e3) return 'R$ ' + f(v / 1e3, 0) + ' mil';
  return 'R$ ' + f(v, 2);
}
const mesDe = aaaamm => MESES[Number(String(aaaamm).slice(4, 6)) - 1];

async function __load(){
  if (window.MonitorCatalogo && window.MonitorCatalogo.pronto) { try { await window.MonitorCatalogo.pronto; } catch (e) {} }
  let ref;
  [BR_GEOJSON, ref] = await Promise.all(['data/geo_uf.json', 'data/municipios_ibge_referencia.json']
    .map(f => fetch(f).then(r => { if (!r.ok) throw new Error('Falha ao carregar ' + f); return r.json(); })));
  /* Os opcionais não derrubam a página: cada bloco que depende deles declara a lacuna. */
  [MPS, COMPROMISSOS, RECURSOS, S] = await Promise.all(
    ['data/financiamento/mps_2026.json', 'data/financiamento/compromissos_federais.json',
     'data/resposta/recursos_liberados.json', 'data/financiamento/semana.json']
      .map(f => fetch(f).then(r => r.ok ? r.json() : null).catch(() => null)));
  ref.forEach(m => {
    const c = String(m.codigo_ibge).padStart(7, '0');
    LATLON[c] = [m.lon, m.lat]; MUN_COD[m.uf + '|' + m.nome] = c;
    (NOMES_POR_UF[m.uf] = NOMES_POR_UF[m.uf] || []).push(m.nome);
  });
  __init();
}

/* "Ver em tabela" no rodapé da figura: tabela recolhida, sem busca. */
function tabela(figuraId, colunas, linhas){
  const alvo = document.querySelector('#' + figuraId + ' [data-busca]');
  if (!alvo) return;
  const esc = MonitorMapas.esc;
  alvo.insertAdjacentHTML('afterbegin', '<details class="cartao-mapa-dados"><summary>Ver em tabela</summary>'
    + '<div class="tbl-wrap" tabindex="0" role="region" aria-label="Tabela rolável horizontalmente"><table class="mun-table"><thead><tr>'
    + colunas.map(c => '<th>' + esc(c) + '</th>').join('') + '</tr></thead><tbody>'
    + (linhas.map(l => '<tr>' + l.map(c => '<td>' + c + '</td>').join('') + '</tr>').join('')
       || '<tr><td colspan="' + colunas.length + '">nenhum registro até o corte</td></tr>')
    + '</tbody></table></div></details>');
}

function __init(){
  MonitorMapas.padraoGraficos(window.Chart);
  const esc = MonitorMapas.esc, cor = MonitorMapas.cor, C = window.MonitorCatalogo, P = MonitorMapas.PALETA;
  const n = v => Number(v || 0).toLocaleString('pt-BR');
  const texto = (id, v) => { const e = document.getElementById(id); if (e) e.textContent = v; };
  const molde = (id, chave, valores) => C && C.escrever(id, chave, valores);
  const tx = (chave, valores) => (C && C.texto(chave, valores)) || '';
  const cred = (id, fontes, data, url) => MonitorMapas.credito(id, {fontes: fontes, data: data, url: url});
  const link = (url, rot) => url ? '<a href="' + esc(url) + '" target="_blank" rel="noopener">' + esc(rot) + '</a>' : esc(rot);
  const NAO_LOCALIZADO = 'não localizado até o corte';
  const NOME_UF = Object.fromEntries(BR_GEOJSON.features.map(f => [f.properties.sigla, f.properties.name]));
  const FONTE_DC = 'Defesa Civil nacional, portarias no Diário Oficial da União';
  const FONTE_TRANSP = 'Portal da Transparência';

  // ---------------------------------------------------------
  // As origens: medidas provisórias, compromissos com valor no ato e o FNS de emergência; o topo, do gerador
  // ---------------------------------------------------------
  const mps = (MPS && MPS.mps) || [];
  const comp = ((COMPROMISSOS && COMPROMISSOS.itens) || []).filter(i => !PLANO_FEDERAL.test(i.nome || ''));
  const riscoDe = o => (o.risco_declarado && o.risco_declarado.risco) || null;
  /* Os números do topo vêm prontos do gerador (`semana.json` → `topo`): uma definição só, a mesma que a
     Imprensa lê. Cartão ausente ou sem coleta fica com a lacuna da classe. */
  const topo = id => (((S && S.topo) || []).find(c => c.id === id) || null);
  const anunciado = topo('anunciado_atos'), pago = topo('pago_ate_agora'), direto = topo('gasto_direto_uniao');
  const dcTopo = topo('defesa_civil_ciclo'), sus = topo('sus_emergencia');
  const origens = mps.map(m => ({nome: m.numero + ' · ' + (m.tema || ''), ato: m.numero, data: m.publicada_em, orgao: (m.orgaos || []).map(o => o.nome).join(', ') || m.beneficiario,
      risco: riscoDe(m), anunciado: m.valor, empenhado: (m.execucao || {}).empenhado, pago: (m.execucao || {}).pago,
      fonte: (m.execucao || {}).fonte, url: ((m.fontes || [])[0] || {}).url, notaMp: true, acimaDoAto: !!(m.execucao || {}).acima_do_valor_do_ato}))
    .concat(comp.map(i => ({nome: i.nome, ato: i.instrumento, data: null, orgao: i.esfera, risco: riscoDe(i),
      anunciado: i.valor_total, empenhado: null, pago: null, fonte: /^http/.test(i.fonte || '') ? 'ato oficial' : 'documento não localizado até o corte', url: /^http/.test(i.fonte || '') ? i.fonte : null})))
    .concat(sus && !sus.sem_coleta ? [{nome: 'Fundo Nacional de Saúde, linhas ligadas a emergência', ato: 'repasses fundo a fundo', data: null, orgao: 'Ministério da Saúde',
      risco: 'saude', anunciado: null, empenhado: null, pago: sus.valor, fonte: FONTE_TRANSP, url: sus.url_fonte}] : []);

  // =========================================================
  // 1. Cinco números
  // =========================================================
  const usa = c => c && !c.sem_coleta && c.valor != null;
  if (usa(anunciado)) { texto('topoAnunciado', reais(anunciado.valor)); molde('topoAnunciadoApoio', 'financiamento.dc-topo.topo_anunciado.apoio.molde', {n: anunciado.n_atos || 0}); }
  if (usa(pago)) { texto('topoPago', reais(pago.valor)); texto('topoPagoApoio', tx('financiamento.dc-topo.topo_pago.apoio')); }
  texto('topoDireto', usa(direto) ? Number(direto.valor).toLocaleString('pt-BR') + '%' : 'não calculado até o corte');
  if (usa(direto)) texto('topoDiretoApoio', tx('financiamento.dc-topo.topo_direto.apoio'));
  if (usa(dcTopo)) { texto('topoDefesaCivil', reais(dcTopo.valor)); molde('topoDefesaCivilApoio', 'financiamento.dc-topo.topo_defesa_civil.apoio.molde', {n: dcTopo.municipios || 0, recuperacao: reais((dcTopo.por_acao || {}).recuperacao) || NAO_LOCALIZADO}); }
  if (usa(sus)) { texto('topoSus', reais(sus.valor)); molde('topoSusApoio', 'financiamento.dc-topo.topo_sus.apoio.molde', {n: sus.municipios || 0}); }
  [['topoAnunciadoFonte', anunciado], ['topoPagoFonte', pago], ['topoDiretoFonte', direto], ['topoDefesaCivilFonte', dcTopo], ['topoSusFonte', sus]]
    .forEach(([id, c]) => cred(id, [(c && c.fonte) || FONTE_TRANSP], S && S.corte));
  const tpa = (dcTopo && dcTopo.por_acao) || null;
  /* Nove dos 89 atos do consolidado (22/10) chegam sem número e sem data: o documento tem link no DOU,
     o que falta é o número lido dele. Uma função para a coluna e para o cartão, nunca "nº null". */
  const atoNum = a => a.portaria ? 'nº ' + a.portaria : 'sem número localizado até o corte';

  // =========================================================
  // 2. De onde vem o dinheiro, pelo caminho do dinheiro
  // =========================================================
  /* Uma escala para a seção: o maior valor de qualquer linha. A MP cujo empenhado passa do valor do ato
     (a fonte mede a ação inteira, `execucao.acima_do_valor_do_ato`) não mostra o empenhado ao lado dele. */
  const linhasMp = origens.filter(o => o.notaMp);
  const susPago = usa(sus) ? sus.valor : null;
  const escala = Math.max(1, ...linhasMp.flatMap(o => [o.anunciado, o.acimaDoAto ? null : o.empenhado, o.pago]).filter(v => v != null), ...Object.values(tpa || {}), susPago || 0);
  const barra = (rotulo, v, corBarra) => '<div class="barra-linha"><span class="barra-rotulo">' + esc(rotulo) + '</span><span class="barra-trilho">'
    + (v == null ? '<span class="barra-valor">' + NAO_LOCALIZADO + '</span>'
       : '<span class="barra" style="width:calc((100% - 4em) * ' + Math.max(0.005, v / escala).toFixed(4) + ');background:' + corBarra + '"></span><span class="barra-valor">' + esc(reais(v)) + '</span>')
    + '</span></div>';
  const cartaoDinheiro = (acento, etiqueta, nome, apoio, corpo) => '<div class="cartao ' + acento + '"' + '><p class="cartao-k">' + esc(etiqueta) + '</p>'
    + '<b class="cartao-t">' + esc(nome) + '</b>' + apoio + corpo + '</div>';
  const etiquetaDe = o => (RISCOS.find(r => r.chave === o.risco) || {}).rotulo || tx('financiamento.caminhos.etiqueta.sem_risco');
  const linhasMps = document.getElementById('linhasMps');
  if (linhasMps) linhasMps.innerHTML = linhasMp.map(o => cartaoDinheiro('cartao--acento-argila', etiquetaDe(o), o.nome,
    '<span class="cartao-s">' + esc(tx('financiamento.caminhos.mp.orgaos_data.molde', {orgaos: o.orgao || '', data: o.data || NAO_LOCALIZADO})) + '</span>',
    '<div class="barras-painel">' + barra(tx('financiamento.caminhos.barra.valor_do_ato'), o.anunciado, P.resposta)
      + (o.acimaDoAto ? '' : barra(tx('financiamento.caminhos.barra.empenhado'), o.empenhado, P.resposta))
      + barra(tx('financiamento.caminhos.barra.desembolsado'), o.pago, P.resposta) + '</div>'
      + '<span class="cartao-s">' + esc(tx('financiamento.caminhos.nota_mp')) + '</span>')).join('');
  /* Do decreto ao recurso: os números vêm prontos do gerador (`semana.json` → `funil_defesa_civil`). */
  const F = (S && S.funil_defesa_civil) || {};
  const linhaFunil = F.n_decretaram == null ? '' : '<p class="cartao-s">' + esc(tx('financiamento.caminhos.funil.linha', {n_decretaram: n(F.n_decretaram),
    n_reconhecidos: n(F.n_reconhecidos), n_com_recurso: n(F.n_com_recurso)})) + '</p>';
  const linhasRepasses = document.getElementById('linhasRepasses');
  if (linhasRepasses) linhasRepasses.innerHTML = cartaoDinheiro('cartao--acento-chuva', tx('financiamento.caminhos.etiqueta.todos_os_riscos'),
      tx('financiamento.caminhos.faixa_resposta.titulo'), linhaFunil,
      tpa ? '<div class="barras-painel">' + Object.keys(ACOES).map(k => barra(tx('financiamento.caminhos.barra.autorizado', {acao: ACOES[k].toLowerCase()}), tpa[k], P.resposta)).join('') + '</div>'
          : '<span class="cartao-s">' + NAO_LOCALIZADO + '</span>')
    + cartaoDinheiro('cartao--acento-chuva', RISCOS.find(r => r.chave === 'saude').rotulo.toLowerCase(), tx('financiamento.caminhos.sus.titulo'), '',
      '<div class="barras-painel">' + barra(tx('financiamento.caminhos.barra.desembolsado'), susPago, P.setores.saude) + '</div>');
  const corpo = document.querySelector('#tblOrigens tbody');
  if (corpo) corpo.innerHTML = origens.map(o => '<tr>' + [esc(o.nome), esc(o.ato || ''), esc(o.data || NAO_LOCALIZADO), esc(o.orgao || ''),
      esc((RISCOS.find(r => r.chave === o.risco) || {}).rotulo || 'risco não declarado no ato'),
      esc(reais(o.anunciado) || NAO_LOCALIZADO), esc(reais(o.empenhado) || NAO_LOCALIZADO), esc(reais(o.pago) || NAO_LOCALIZADO),
      link(o.url, o.fonte || 'fonte')].map(c => '<td>' + c + '</td>').join('') + '</tr>').join('');

  // =========================================================
  // 3. Onde o dinheiro chega: círculos proporcionais (figura principal)
  // =========================================================
  const ctx = MonitorMapas.contexto(BR_GEOJSON, 480, 460);
  MonitorMapas.desenharMapa(ctx, 'mapChega', null, () => cor('branco'), uf => esc(NOME_UF[uf] || uf), [], 'contagem');
  /* Os círculos vêm prontos do gerador (`semana.json` → `mapa`, com a sede de cada município). */
  const ORIGENS_MAPA = {defesa_civil: {rotulo: 'defesa civil', cor: P.resposta}, saude: {rotulo: 'saúde', cor: P.setores.saude}};
  const circulos = ((S && S.mapa) || []).filter(x => ORIGENS_MAPA[x.origem] && x.repassado > 0 && x.lat != null);
  const maxV = Math.max(1, ...circulos.map(x => x.repassado)), R_MAX = 14;
  MonitorMapas.pontos(ctx, 'mapChega', circulos.slice().sort((a, b) => b.repassado - a.repassado), {
    r: x => Math.max(1.5, R_MAX * Math.sqrt(x.repassado / maxV)), cor: x => ORIGENS_MAPA[x.origem].cor, opacidade: 0.6, classe: 'circulos-valor',
    tabela: {sel: '#boxChega', chave: x => [x.nome || '', x.uf || '', ORIGENS_MAPA[x.origem].rotulo]},
    rotulo: x => '<strong>' + esc(x.nome || '') + ' · ' + esc(x.uf || '') + '</strong><br>' + esc(ORIGENS_MAPA[x.origem].rotulo) + ' · ' + esc(x.ato || '')
      + '<br>' + esc(reais(x.repassado))});
  const totalOrigem = o => circulos.filter(x => x.origem === o).reduce((s, x) => s + x.repassado, 0);
  MonitorMapas.legenda('legChega', circulos.length ? Object.entries(ORIGENS_MAPA).map(([k, o]) => ({cor: o.cor, rotulo: o.rotulo + ' · ' + reais(totalOrigem(k))}))
    .concat([{cor: cor('linha'), rotulo: 'maior círculo: ' + reais(maxV)}]) : [{cor: cor('sem-dado'), rotulo: 'sem coleta até o corte'}]);
  if (direto && direto.valor != null) molde('chegaDestaque', 'financiamento.chega.destaque.molde', {pct: Number(direto.valor).toLocaleString('pt-BR')});
  const RES = (S && S.mapa_resumo) || {}, comps = RES.competencias || [], ASR = (S && S.autorizado_sem_repasse) || {};
  const PERIODO_MAPA = comps.length ? mesDe(comps[0]) + '–' + mesDe(comps[comps.length - 1]) + '/' + String(comps[comps.length - 1]).slice(0, 4) : NAO_LOCALIZADO;
  if (comps.length) molde('subChega', 'financiamento.chega.mapa.legenda', {mes: MESES_LONGOS[Number(String(comps[comps.length - 1]).slice(4, 6)) - 1]});
  if (ASR.n != null) molde('chegaSemRepasse', 'financiamento.chega.sem_repasse.molde', {n: ASR.n, data: ASR.corte});
  cred('boxChega', [FONTE_TRANSP + ', transferências da União (defesa civil)', 'Fundo Nacional de Saúde, no ' + FONTE_TRANSP], S && S.corte);
  tabela('boxChega', ['Município', 'UF', 'Origem', 'Repassado desde 29/06/2026', 'Autorizado em portaria (defesa civil)', 'Ato', 'Período'], circulos.slice().sort((a, b) => (a.nome || '').localeCompare(b.nome || '', 'pt-BR'))
    .map(x => ['<strong>' + esc(x.nome || '') + '</strong>', esc(x.uf || ''), esc(ORIGENS_MAPA[x.origem].rotulo), esc(reais(x.repassado)),
      esc(x.origem === 'saude' ? 'não se aplica' : reais(x.autorizado) || NAO_LOCALIZADO), link(x.url, x.ato || ''), esc(PERIODO_MAPA)]));

  // =========================================================
  // 4. Mês a mês: só o pago, fogo e seca
  // =========================================================
  /* Série do gerador (`semana.json` → `mes_a_mes`): só o pago, por MP, com o mês parcial marcado. */
  /* O risco de uma série é o que o ATO declara. Enquanto `risco_declarado` não vier, a série se
     nomeia pelo tema do próprio ato e usa a paleta de séries, que não carrega significado de risco:
     dizer "fogo" e "seca" por id de MP seria classificação nossa, e as colunas acima dizem, com
     razão, que essa classificação ainda não foi coletada. */
  const SERIES_MES = ((S && S.mes_a_mes) || []).map((m, i) => {
    const fam = riscoDe(m);
    return {numero: m.numero, rotulo: fam || m.tema, cor: P.familia[fam] || P.serie[i % P.serie.length],
      meses: Object.fromEntries((m.meses || []).map(x => [x.mes, x]))};
  });
  const meses = [...new Set(SERIES_MES.flatMap(s => Object.keys(s.meses)))].sort();
  const rotMes = k => mesDe(k) + (SERIES_MES.some(s => (s.meses[k] || {}).parcial) ? ' (parcial)' : '');
  const pagoMes = (s, k) => (s.meses[k] || {}).pago;
  const cvM = document.getElementById('cMesAMes');
  if (cvM && window.Chart && meses.length) new Chart(cvM, {type: 'bar',
    data: {labels: meses.map(rotMes), datasets: SERIES_MES.map(s => ({label: s.rotulo, backgroundColor: s.cor,
      data: meses.map(k => pagoMes(s, k) == null ? null : Math.round(pagoMes(s, k) / 1e5) / 10)}))},
    options: {responsive: true, maintainAspectRatio: false, plugins: {legend: {display: false}}, scales: {y: {beginAtZero: true}}}});
  /* Série nenhuma é o mesmo fato que figura sem legenda: a classe sai em palavras, como em `legChega`. */
  MonitorMapas.legenda('legMesAMes', SERIES_MES.length ? SERIES_MES.map(s => ({cor: s.cor, rotulo: s.rotulo + ' · ' + s.numero}))
    : [{cor: cor('sem-dado'), rotulo: 'sem coleta até o corte'}]);
  cred('boxMesAMes', [FONTE_TRANSP, 'execução da despesa'], S && S.corte);
  tabela('boxMesAMes', ['Mês'].concat(SERIES_MES.map(s => s.rotulo + ' · ' + s.numero)),
    meses.map(k => [esc(rotMes(k) + ' de ' + k.slice(0, 4))].concat(SERIES_MES.map(s => esc(reais(pagoMes(s, k)) || NAO_LOCALIZADO)))));

  // =========================================================
  // 5. Quanto chegou ao seu município
  // =========================================================
  let TRANSF = null, DESPESA = null, carga = null;
  const carregarConsulta = () => (carga = carga || Promise.all(['data/financiamento/municipios/transferencias_uniao.json', 'data/financiamento/municipios/despesa_182.json',
    'data/financiamento/municipios/fns_municipios_2026.json'].map(f => fetch(f).then(r => r.ok ? r.json() : null).catch(() => null))).then(([t, d, f]) => { TRANSF = t; DESPESA = d; FNS_MUN = f; }));
  /* A mesma data de consulta da página em todos os cartões e linhas (o corte do gerador). */
  const consultado = S && S.corte;
  const cartao = (classe, titulo, corpo) => '<div class="cartao ' + classe + '"><p class="cartao-k">' + esc(titulo) + '</p>' + corpo + '</div>';
  const linhaT = (t, s) => '<b class="cartao-t">' + t + '</b>' + (s ? '<span class="cartao-s">' + s + '</span>' : '');
  const fonteT = chave => '<span class="cartao-s">' + esc(tx(chave, {data: consultado || 'sem registro'})) + '</span>';
  const faixa = (chave, valores) => '<p class="hint">' + esc(tx(chave, Object.assign({data: consultado || 'sem registro'}, valores))) + '</p>';
  function mostrar(uf, nome, card){
    const cod = MUN_COD[uf + '|' + nome];
    const doMapa = origem => ((S && S.mapa) || []).find(x => String(x.cod_ibge) === cod && x.origem === origem);
    const dc = ((RECURSOS && RECURSOS.municipios) || {})[cod];
    const primeira = dc && (dc.atos || []).map(x => x.data).filter(Boolean).sort()[0];
    const corpoDc = (dc
      ? linhaT(esc(reais(dc.total_autorizado)), (primeira ? esc(tx('financiamento.municipio.defesa_civil.valor.apoio.molde', {data: MonitorMapas.dataBR(primeira)})) + '<br>' : '')
        + (dc.atos || []).map(x => esc(ACOES[x.acao] || x.acao_no_ato || '') + ' · '
          + link(x.url, 'Portaria ' + atoNum(x)) + (MonitorMapas.dataBR(x.data) ? ', de ' + esc(MonitorMapas.dataBR(x.data)) : '')).join('<br>'))
      : linhaT(esc(tx('financiamento.municipio.defesa_civil.lacuna')))) + fonteT('financiamento.municipio.defesa_civil.fonte.molde');
    const sm = doMapa('saude');
    const corpoSus = (sm ? linhaT(esc(reais(sm.repassado)), esc(sm.periodo || '')) : linhaT(esc(tx('financiamento.municipio.sus.lacuna'))))
      + fonteT('financiamento.municipio.sus.fonte.molde');
    /* Contexto, abaixo dos cartões: tudo o que a União transferiu ao município no ano e o gasto próprio. Os três
       estados do gasto próprio (com valor, zero lançado, balanço não entregue) são distintos: zero ≠ ausência. */
    const t = ((TRANSF && TRANSF.municipios) || {})[cod];
    const mesesT = Object.keys((TRANSF && TRANSF.meses_lidos) || {}).sort();
    const ultimoT = mesesT[mesesT.length - 1];
    const ctxT = t && ultimoT
      ? faixa('financiamento.municipio.contexto.transferencias.molde', {ano: ultimoT.slice(0, 4), total: reais(t.total),
          mes: MESES_LONGOS[Number(ultimoT.slice(4, 6)) - 1], constitucional: reais((t.por_rota || {}).constitucional || 0)})
      : faixa('financiamento.municipio.contexto.transferencias.lacuna.molde', {ano: ultimoT ? ultimoT.slice(0, 4) : '2026', corte: (TRANSF && TRANSF.atualizado_em) || 'sem registro'});
    const d = ((DESPESA && DESPESA.municipios) || {})[cod], ano = DESPESA && String(DESPESA.exercicio);
    const gasto = d && d.valores ? (d.valores.liquidada != null ? d.valores.liquidada : d.valores.paga != null ? d.valores.paga : d.valores.empenhada) : null;
    const ctxD = !d ? faixa('financiamento.municipio.contexto.gasto_proprio.sem_coleta.molde', {ano: ano})
      : d.classe === 'com_lancamento' && gasto != null ? faixa('financiamento.municipio.contexto.gasto_proprio.valor.molde', {valor: reais(gasto), ano: ano})
      : d.classe === 'sem_lancamento_182' ? faixa('financiamento.municipio.contexto.gasto_proprio.zero.molde', {ano: ano})
      : d.nota ? faixa('financiamento.municipio.contexto.gasto_proprio.nota.molde', {nota: d.nota})
      : faixa('financiamento.municipio.contexto.gasto_proprio.nao_entregue.molde', {ano: ano});
    const doUF = Object.values((RECURSOS && RECURSOS.municipios) || {}).filter(m => m.uf === uf);
    const estaduais = comp.filter(i => new RegExp('Estadual \\(' + uf + '\\)').test(i.esfera || '') && i.valor_total);
    const estado = !RECURSOS ? '' : tx('financiamento.municipio.estado.molde', {no_estado: (PREPOSICAO[uf] || 'Em') + ' ' + (NOME_UF[uf] || uf),
      valor: reais(doUF.reduce((s, m) => s + (m.total_autorizado || 0), 0)), n_mun: doUF.length,
      estaduais: estaduais.map(i => '; ' + i.nome.split(' — ')[0] + ', ' + reais(i.valor_total) + ' declarados no ato estadual').join('')});
    card.innerHTML = '<h4>' + esc(nome) + ' · ' + esc(uf) + '</h4><p class="selo">' + esc(tx('financiamento.municipio.faixa.titulo_el_nino')) + '</p><div class="grade-cartoes">'
      + cartao('cartao--acento-argila', tx('financiamento.municipio.defesa_civil.titulo'), corpoDc)
      + cartao('cartao--acento-neutro', tx('financiamento.municipio.sus.titulo'), corpoSus)
      + '</div>' + ctxT + ctxD + (estado ? '<p class="hint">' + estado + '</p>' : '');
  }
  ConsultaMunicipio.montar({uf: 'consultaUF', municipio: 'consultaMun', lista: 'consultaLista', cartao: 'consultaCard',
    estados: NOME_UF, mostrar, semLista: 'Lista de municípios do estado: sem coleta até o corte.',
    municipios: uf => carregarConsulta().then(() => (NOMES_POR_UF[uf] || []).slice().sort((x, y) => x.localeCompare(y, 'pt-BR')))});
}

__load().catch(err => {
  document.body.insertAdjacentHTML('afterbegin', '<div id="errBanner" class="erro-carga">Erro ao carregar os dados: '
    + err.message + '. Sirva a pasta via HTTP (ex.: <code>npx serve</code>) — abrir o arquivo diretamente bloqueia o fetch.</div>');
});

window.addEventListener('load', function(){
  if (window.VLibras && window.VLibras.Widget) { try { new window.VLibras.Widget('https://vlibras.gov.br/app'); } catch (e) {} }
});
