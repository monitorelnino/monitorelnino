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
let BR_GEOJSON, MPS, COMPROMISSOS, RECURSOS, DECRETADOS, FNS, FNS_MUN,
    LATLON = {}, MUN_COD = {}, NOMES_POR_UF = {};

const INICIO_CICLO = '2026-06-29';
const DIAS_PENDENCIA = 30;
const PLANO_FEDERAL = /Plano federal El Niño/i;
const RISCOS = [
  {chave: 'fogo', rotulo: 'Fogo', acento: 'cartao--acento-fogo'},
  {chave: 'seca', rotulo: 'Seca', acento: 'cartao--acento-seca'},
  {chave: 'chuva', rotulo: 'Chuva forte', acento: 'cartao--acento-chuva'},
  {chave: 'saude', rotulo: 'Saúde', acento: 'cartao--acento-sintetico-topo'},
];
const ACOES = {resposta: 'Resposta', recuperacao: 'Recuperação', outra: 'Outra'};
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
  [MPS, COMPROMISSOS, RECURSOS, DECRETADOS, FNS, FNS_MUN] = await Promise.all(
    ['data/financiamento/mps_2026.json', 'data/financiamento/compromissos_federais.json',
     'data/resposta/recursos_liberados.json', 'data/resposta/municipios_decretados.json',
     'data/financiamento/fns_2026.json', 'data/financiamento/municipios/fns_municipios_2026.json']
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
  // As origens: medidas provisórias, compromissos com valor no ato e o FNS de emergência
  // ---------------------------------------------------------
  const mps = (MPS && MPS.mps) || [];
  const comp = ((COMPROMISSOS && COMPROMISSOS.itens) || []).filter(i => !PLANO_FEDERAL.test(i.nome || ''));
  const riscoDe = o => (o.risco_declarado && (o.risco_declarado.risco || o.risco_declarado)) || null;
  const mesesFns = Object.keys((FNS && FNS.meses) || {}).sort();
  const ultimoFns = mesesFns[mesesFns.length - 1];
  const fnsEmergencia = mesesFns.reduce((s, k) => s + ((FNS.meses[k].emergencia || []).reduce((a, e) => a + (e.valor || 0), 0)), 0);
  const fnsMun = Object.entries((FNS_MUN && FNS_MUN.municipios) || {}).filter(([, v]) => v.emergencia > 0);
  const origens = mps.map(m => ({nome: m.numero + ' · ' + (m.tema || ''), ato: m.numero, data: m.publicada_em, orgao: (m.orgaos || []).map(o => o.nome).join(', ') || m.beneficiario,
      risco: riscoDe(m), anunciado: m.valor, empenhado: (m.execucao || {}).empenhado, pago: (m.execucao || {}).pago,
      fonte: (m.execucao || {}).fonte, url: ((m.fontes || [])[0] || {}).url, notaMp: true}))
    .concat(comp.map(i => ({nome: i.nome, ato: i.instrumento, data: null, orgao: i.esfera, risco: riscoDe(i),
      anunciado: i.valor_total, empenhado: null, pago: null, fonte: /^http/.test(i.fonte || '') ? 'ato oficial' : 'documento não localizado até o corte', url: /^http/.test(i.fonte || '') ? i.fonte : null})))
    .concat(FNS ? [{nome: 'Fundo Nacional de Saúde, linhas ligadas a emergência', ato: 'repasses fundo a fundo', data: null, orgao: 'Ministério da Saúde',
      risco: 'saude', anunciado: null, empenhado: null, pago: fnsEmergencia, fonte: FONTE_TRANSP, url: FNS.fonte}] : []);
  const comValor = origens.filter(o => o.anunciado != null);

  // =========================================================
  // 1. Cinco números
  // =========================================================
  const somaPago = mps.reduce((s, m) => s + ((m.execucao || {}).pago || 0), 0);
  const ultimoMes = mps.flatMap(m => Object.keys((m.execucao || {}).por_mes || {})).sort().pop();
  const pagoUltimo = mps.reduce((s, m) => s + ((((m.execucao || {}).por_mes || {})[ultimoMes] || {}).pago || 0), 0);
  const parcial = mps.some(m => ((m.execucao || {}).meses_parciais || []).includes(ultimoMes));
  const atualizadoMps = mps.map(m => (m.execucao || {}).atualizado_em).filter(Boolean)[0] || (MPS && MPS.gerado_em);
  if (comValor.length) {
    texto('topoAnunciado', reais(comValor.reduce((s, o) => s + o.anunciado, 0)));
    molde('topoAnunciadoApoio', 'financiamento.dc-topo.topo_anunciado.apoio.molde', {n: comValor.length});
  }
  cred('topoAnunciadoFonte', ['atos oficiais', 'Diário Oficial da União'], (MPS && MPS.gerado_em) || null);
  if (mps.length) {
    texto('topoPago', reais(somaPago));
    if (ultimoMes && parcial) molde('topoPagoApoio', 'financiamento.dc-topo.topo_pago.apoio.molde', {valor: reais(pagoUltimo), mes: MESES_LONGOS[Number(ultimoMes.slice(4)) - 1]});
  }
  cred('topoPagoFonte', [FONTE_TRANSP], atualizadoMps);
  /* O que a União gasta diretamente vem do gerador (`pct_gasto_direto`, modalidade de aplicação 90). */
  const pctDireto = MPS && MPS.pct_gasto_direto;
  texto('topoDireto', pctDireto != null ? (Math.round(pctDireto * 1000) / 10).toLocaleString('pt-BR') + '%' : 'não calculado até o corte');
  if (pctDireto != null) texto('topoDiretoApoio', tx('financiamento.dc-topo.topo_direto.apoio'));
  cred('topoDiretoFonte', [FONTE_TRANSP], atualizadoMps);
  const tpa = (RECURSOS && RECURSOS.total_por_acao) || null;
  if (tpa) {
    texto('topoDefesaCivil', reais(Object.values(tpa).reduce((s, v) => s + v, 0)));
    molde('topoDefesaCivilApoio', 'financiamento.dc-topo.topo_defesa_civil.apoio.molde', {n: RECURSOS.municipios_com_ato || 0});
  }
  cred('topoDefesaCivilFonte', [FONTE_DC], RECURSOS && RECURSOS.atualizado_em);
  if (FNS) {
    texto('topoSus', reais(fnsEmergencia));
    molde('topoSusApoio', 'financiamento.dc-topo.topo_sus.apoio.molde', {mes: mesDe(ultimoFns), n: fnsMun.length});
  }
  cred('topoSusFonte', ['Fundo Nacional de Saúde', FONTE_TRANSP], FNS && FNS.atualizado_em);

  // =========================================================
  // 2. Para cada risco, de onde vem o dinheiro
  // =========================================================
  /* Uma escala para a página inteira: a maior etapa de qualquer fonte, inclusive a faixa da resposta. */
  const escala = Math.max(1, ...origens.flatMap(o => [o.anunciado, o.empenhado, o.pago]).filter(v => v != null), ...Object.values(tpa || {}));
  const barra = (rotulo, v, corBarra) => '<div class="barra-linha"><span class="barra-rotulo">' + esc(rotulo) + '</span><span class="barra-trilho">'
    + (v == null ? '<span class="barra-valor">' + NAO_LOCALIZADO + '</span>'
       : '<span class="barra" style="width:calc((100% - 4em) * ' + Math.max(0.005, v / escala).toFixed(4) + ');background:' + corBarra + '"></span><span class="barra-valor">' + esc(reais(v)) + '</span>')
    + '</span></div>';
  const colunas = document.getElementById('colunasRisco');
  if (colunas) colunas.innerHTML = RISCOS.map(r => {
    const fontes = origens.filter(o => o.risco === r.chave);
    const corR = r.chave === 'saude' ? P.setores.saude : P.familia[r.chave];
    return '<div class="cartao ' + r.acento + '"><p class="cartao-k">' + esc(r.rotulo) + '</p>'
      + (fontes.map(o => '<b class="cartao-t">' + esc(o.nome) + '</b><span class="cartao-s">' + esc([o.orgao, o.data].filter(Boolean).join(' · ')) + '</span>'
          + '<div class="barras-painel">' + barra('anunciado', o.anunciado, corR) + barra('empenhado', o.empenhado, corR) + barra('pago', o.pago, corR) + '</div>'
          + (o.notaMp ? '<span class="cartao-s">' + esc(tx('financiamento.caminhos.nota_mp')) + '</span>' : '')).join('')
         || '<span class="cartao-s">Nenhuma fonte com este risco declarado no ato, até o corte.</span>')
      + '</div>';
  }).join('');
  const faixa = document.getElementById('faixaResposta');
  if (faixa) faixa.innerHTML = '<p class="cartao-k">' + esc(tx('financiamento.caminhos.faixa_resposta.titulo')) + '</p>'
    + (tpa ? '<div class="barras-painel">' + Object.keys(ACOES).map(k => barra(ACOES[k].toLowerCase() + ', autorizado', tpa[k], P.resposta)).join('') + '</div>'
           : '<span class="cartao-s">' + NAO_LOCALIZADO + '</span>');
  const corpo = document.querySelector('#tblOrigens tbody');
  if (corpo) corpo.innerHTML = origens.map(o => '<tr>' + [esc(o.nome), esc(o.ato || ''), esc(o.data || ''), esc(o.orgao || ''),
      esc((RISCOS.find(r => r.chave === o.risco) || {}).rotulo || 'risco não declarado no ato'),
      esc(reais(o.anunciado) || NAO_LOCALIZADO), esc(reais(o.empenhado) || NAO_LOCALIZADO), esc(reais(o.pago) || NAO_LOCALIZADO),
      link(o.url, o.fonte || 'fonte')].map(c => '<td>' + c + '</td>').join('') + '</tr>').join('');

  // =========================================================
  // 3. Onde o dinheiro chega: círculos proporcionais (figura principal)
  // =========================================================
  const ctx = MonitorMapas.contexto(BR_GEOJSON, 480, 460);
  MonitorMapas.desenharMapa(ctx, 'mapChega', null, () => cor('branco'), uf => esc(NOME_UF[uf] || uf), [], 'contagem');
  const ORIGENS_MAPA = {dc: {rotulo: 'defesa civil', cor: P.resposta}, saude: {rotulo: 'saúde', cor: P.setores.saude}};
  const circulos = Object.entries((RECURSOS && RECURSOS.municipios) || {}).map(([c, v]) => ({cod: c, nome: v.nome, uf: v.uf, origem: 'dc', valor: v.total_autorizado,
      ato: (v.atos || []).map(a => 'Portaria nº ' + a.portaria).join(', '), data: (v.atos || []).map(a => MonitorMapas.dataBR(a.data)).filter(Boolean).sort().pop()}))
    .concat(fnsMun.map(([c, v]) => ({cod: c, nome: null, uf: null, origem: 'saude', valor: v.emergencia, ato: 'repasses do FNS ligados a emergência', data: null})))
    .filter(x => LATLON[x.cod] && x.valor > 0)
    .map(x => Object.assign(x, {lon: LATLON[x.cod][0], lat: LATLON[x.cod][1]}));
  const nomeDe = {}; Object.entries(MUN_COD).forEach(([k, c]) => { const [uf, nome] = k.split('|'); nomeDe[c] = {uf: uf, nome: nome}; });
  circulos.forEach(x => { if (!x.nome) Object.assign(x, nomeDe[x.cod] || {}); });
  const maxV = Math.max(1, ...circulos.map(x => x.valor)), R_MAX = 14;
  MonitorMapas.pontos(ctx, 'mapChega', circulos.sort((a, b) => b.valor - a.valor), {
    r: x => Math.max(1.5, R_MAX * Math.sqrt(x.valor / maxV)), cor: x => ORIGENS_MAPA[x.origem].cor, opacidade: 0.6, classe: 'circulos-valor',
    rotulo: x => '<strong>' + esc(x.nome || '') + ' · ' + esc(x.uf || '') + '</strong><br>' + esc(ORIGENS_MAPA[x.origem].rotulo) + ' · ' + esc(x.ato)
      + (x.data ? '<br>' + esc(x.data) : '') + '<br>' + esc(reais(x.valor))});
  const totalOrigem = o => circulos.filter(x => x.origem === o).reduce((s, x) => s + x.valor, 0);
  MonitorMapas.legenda('legChega', Object.entries(ORIGENS_MAPA).map(([k, o]) => ({cor: o.cor, rotulo: o.rotulo + ' · ' + reais(totalOrigem(k))}))
    .concat([{cor: cor('linha'), rotulo: 'maior círculo: ' + reais(maxV)}]));
  if (pctDireto != null) molde('chegaDestaque', 'financiamento.chega.destaque.molde', {pct: (Math.round(pctDireto * 1000) / 10).toLocaleString('pt-BR')});
  if (ultimoFns) molde('subChega', 'financiamento.chega.mapa.legenda', {mes: mesDe(ultimoFns)});
  cred('boxChega', [FONTE_DC, 'Fundo Nacional de Saúde, no ' + FONTE_TRANSP], (RECURSOS && RECURSOS.atualizado_em) || (FNS && FNS.atualizado_em));
  tabela('boxChega', ['Município', 'UF', 'Origem', 'Ato', 'Data', 'Valor'], circulos.slice().sort((a, b) => (a.nome || '').localeCompare(b.nome || '', 'pt-BR'))
    .map(x => ['<strong>' + esc(x.nome || '') + '</strong>', esc(x.uf || ''), esc(ORIGENS_MAPA[x.origem].rotulo), esc(x.ato), esc(x.data || ''), esc(reais(x.valor))]));

  // =========================================================
  // 4. Mês a mês: só o pago, fogo e seca
  // =========================================================
  const mpFogo = mps.find(m => riscoDe(m) === 'fogo') || mps.find(m => m.id === 'mp1367');
  const mpSeca = mps.find(m => riscoDe(m) === 'seca') || mps.find(m => m.id === 'mp1384');
  const meses = [...new Set(mps.flatMap(m => Object.keys((m.execucao || {}).por_mes || {})))].sort();
  const SERIES_MES = [[mpFogo, 'fogo', P.familia.fogo], [mpSeca, 'seca', P.familia.seca]].filter(s => s[0]);
  const rotMes = k => mesDe(k) + (mps.some(m => ((m.execucao || {}).meses_parciais || []).includes(k)) ? ' (parcial)' : '');
  const pagoMes = (m, k) => ((((m.execucao || {}).por_mes || {})[k] || {}).pago);
  const cvM = document.getElementById('cMesAMes');
  if (cvM && window.Chart && meses.length) new Chart(cvM, {type: 'bar',
    data: {labels: meses.map(rotMes), datasets: SERIES_MES.map(([m, r, c]) => ({label: r, backgroundColor: c,
      data: meses.map(k => pagoMes(m, k) == null ? null : Math.round(pagoMes(m, k) / 1e5) / 10)}))},
    options: {responsive: true, maintainAspectRatio: false, plugins: {legend: {display: false}}, scales: {y: {beginAtZero: true}}}});
  MonitorMapas.legenda('legMesAMes', SERIES_MES.map(([m, r, c]) => ({cor: c, rotulo: r + ' · ' + m.numero})));
  cred('boxMesAMes', [FONTE_TRANSP, 'execução da despesa'], atualizadoMps);
  tabela('boxMesAMes', ['Mês'].concat(SERIES_MES.map(([m, r]) => r + ' · ' + m.numero)),
    meses.map(k => [esc(rotMes(k) + ' de ' + k.slice(0, 4))].concat(SERIES_MES.map(([m]) => esc(reais(pagoMes(m, k)) || NAO_LOCALIZADO)))));

  // =========================================================
  // 5. Quanto chegou ao seu município
  // =========================================================
  let TRANSF = null, DESPESA = null, carga = null;
  const carregarConsulta = () => (carga = carga || Promise.all(['data/financiamento/municipios/transferencias_uniao.json', 'data/financiamento/municipios/despesa_182.json']
    .map(f => fetch(f).then(r => r.ok ? r.json() : null).catch(() => null))).then(([t, d]) => { TRANSF = t; DESPESA = d; }));
  const lacuna = corte => tx('financiamento.municipio.lacuna.molde', {corte: corte || 'sem registro'}) || 'Não localizado até o corte (' + (corte || 'sem registro') + ')';
  const cartao = (classe, titulo, corpo) => '<div class="cartao ' + classe + '"><p class="cartao-k">' + esc(titulo) + '</p>' + corpo + '</div>';
  const linhaT = (t, s) => '<b class="cartao-t">' + t + '</b>' + (s ? '<span class="cartao-s">' + s + '</span>' : '');
  const ROTAS = {constitucional: 'constitucional', saude: 'saúde', assistencia_social: 'assistência social', defesa_civil: 'defesa civil', outras: 'outras'};
  function mostrar(uf, nome, card){
    const cod = MUN_COD[uf + '|' + nome];
    const dc = ((RECURSOS && RECURSOS.municipios) || {})[cod];
    const corpoDc = dc ? linhaT(esc(reais(dc.total_autorizado)), (dc.atos || []).map(a => esc(ACOES[a.acao] || a.acao_no_ato || '') + ' · '
        + link(a.url, 'Portaria nº ' + a.portaria) + ', de ' + esc(MonitorMapas.dataBR(a.data) || '')).join('<br>'))
      : linhaT(esc(lacuna(RECURSOS && RECURSOS.atualizado_em)));
    const fm = ((FNS_MUN && FNS_MUN.municipios) || {})[cod];
    const corpoSus = !FNS_MUN ? linhaT(esc(lacuna(null))) : fm && fm.emergencia > 0 ? linhaT(esc(reais(fm.emergencia)), 'jan–' + esc(mesDe(ultimoFns)) + '/2026')
      : linhaT(esc(tx('financiamento.municipio.sus.nenhum')), 'jan–' + esc(mesDe(ultimoFns)) + '/2026');
    const t = ((TRANSF && TRANSF.municipios) || {})[cod];
    const mesesT = Object.keys((TRANSF && TRANSF.meses_lidos) || {}).sort();
    const corpoT = t ? linhaT(esc(reais(t.total)), Object.entries(t.por_rota || {}).sort((a, b) => b[1] - a[1]).map(([k, v]) => esc((ROTAS[k] || k) + ' ' + reais(v))).join(' · ')
        + (mesesT.length ? '<br>até ' + esc(mesDe(mesesT[mesesT.length - 1])) + '/2026' : '')) : linhaT(esc(lacuna(TRANSF && TRANSF.atualizado_em)));
    const d = ((DESPESA && DESPESA.municipios) || {})[cod];
    const classes = ((DESPESA && DESPESA._formato) || {}).classes_de_ausencia || {};
    const corpoD = !d ? linhaT(esc(lacuna(DESPESA && DESPESA.gerado_em)))
      : d.rs_hab != null ? linhaT(esc((d.rs_hab < 0.01 ? 'menos de R$ 0,01' : 'R$ ' + d.rs_hab.toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2})) + ' por habitante'),
          esc(DESPESA.exercicio + ' · ' + tx('financiamento.municipio.gasto_proprio.ressalva')))
      : linhaT(esc(classes[d.classe] || d.classe), esc(String(DESPESA.exercicio)));
    const doUF = Object.values((RECURSOS && RECURSOS.municipios) || {}).filter(m => m.uf === uf);
    const estaduais = comp.filter(i => new RegExp('Estadual \\(' + uf + '\\)').test(i.esfera || '') && i.valor_total);
    const estado = tx('financiamento.municipio.estado.molde', {no_estado: (PREPOSICAO[uf] || 'Em') + ' ' + (NOME_UF[uf] || uf),
      valor: reais(doUF.reduce((s, m) => s + (m.total_autorizado || 0), 0)) || 'R$ 0', n_mun: doUF.length,
      estaduais: estaduais.map(i => '; ' + i.nome.split(' — ')[0] + ', ' + reais(i.valor_total) + ' declarados no ato estadual').join('')});
    card.innerHTML = '<h4>' + esc(nome) + ' · ' + esc(uf) + '</h4><div class="grade-cartoes grade-cartoes--4">'
      + cartao('cartao--acento-argila', tx('financiamento.municipio.defesa_civil.titulo'), corpoDc)
      + cartao('cartao--acento-neutro', tx('financiamento.municipio.sus.titulo'), corpoSus)
      + cartao('cartao--acento-musgo', tx('financiamento.municipio.transferencias.titulo'), corpoT)
      + cartao('cartao--acento-neutro', tx('financiamento.municipio.gasto_proprio.titulo'), corpoD)
      + '</div>' + (estado ? '<p class="hint">' + estado + '</p>' : '');
  }
  ConsultaMunicipio.montar({uf: 'consultaUF', municipio: 'consultaMun', lista: 'consultaLista', cartao: 'consultaCard',
    estados: NOME_UF, mostrar, semLista: 'Lista de municípios do estado: sem coleta até o corte.',
    municipios: uf => carregarConsulta().then(() => (NOMES_POR_UF[uf] || []).slice().sort((x, y) => x.localeCompare(y, 'pt-BR')))});

  // =========================================================
  // 6. Defesa civil, depois do reconhecimento
  // =========================================================
  const paraISO = v => { const s = String(v || ''); let m = s.match(/(\d{2})\/(\d{2})\/(\d{4})/); if (m) return m[3] + '-' + m[2] + '-' + m[1]; m = s.match(/\d{4}-\d{2}-\d{2}/); return m ? m[0] : null; };
  const decretados = Object.values((DECRETADOS && DECRETADOS.municipios) || {}).filter(m => m.decreto);
  const recursoPorCod = {};
  Object.entries((RECURSOS && RECURSOS.municipios) || {}).forEach(([c, v]) => { const d = (v.atos || []).map(a => paraISO(a.data)).filter(Boolean).sort()[0]; if (d) recursoPorCod[c] = d; });
  const semanas = [];
  for (let d = new Date(INICIO_CICLO + 'T12:00:00'); d <= new Date(); d = new Date(d.getTime() + 7 * 864e5)) semanas.push(d.toISOString().slice(0, 10));
  const acumulado = datas => { const base = new Date(INICIO_CICLO + 'T12:00:00'), por = {};
    datas.filter(Boolean).forEach(iso => { const i = iso < INICIO_CICLO ? 0 : Math.floor((new Date(iso + 'T12:00:00') - base) / (7 * 864e5)); por[i] = (por[i] || 0) + 1; });
    let s = 0; return semanas.map((x, i) => (s += por[i] || 0)); };
  const RAMPA = P.atmosfera.resposta.rampa;
  const SERIES = [
    {rotulo: 'decretaram', cor: RAMPA[1], dados: acumulado(decretados.map(m => paraISO(m.primeiro_decreto)))},
    {rotulo: 'reconhecidos pela União', cor: RAMPA[RAMPA.length - 1], dados: acumulado(decretados.filter(m => m.reconhecido).map(m => paraISO(m.primeiro_reconhecimento)))},
    {rotulo: 'com recurso autorizado', cor: P.setores.saude, dados: acumulado(Object.values(recursoPorCod))},
  ];
  const cvS = document.getElementById('cSerieSemanal');
  if (cvS && window.Chart && semanas.length) new Chart(cvS, {type: 'line',
    data: {labels: semanas.map(s => s.slice(8) + '/' + s.slice(5, 7)), datasets: SERIES.map(s => ({label: s.rotulo, data: s.dados, borderColor: s.cor, backgroundColor: s.cor, tension: 0.2, pointRadius: 2}))},
    options: {responsive: true, maintainAspectRatio: false, plugins: {legend: {display: false}}, scales: {y: {beginAtZero: true}}}});
  MonitorMapas.legenda('legSerieSemanal', SERIES.map(s => ({cor: s.cor, rotulo: s.rotulo})));
  const corteDec = (DECRETADOS && DECRETADOS.gerado_em) || null;
  cred('boxSerieSemanal', [FONTE_DC, 'diários oficiais dos estados e dos municípios'], (RECURSOS && RECURSOS.atualizado_em) || corteDec);
  tabela('boxSerieSemanal', ['Semana', 'Decretaram', 'Reconhecidos', 'Com recurso autorizado'],
    semanas.map((s, i) => [s.slice(8) + '/' + s.slice(5, 7) + '/' + s.slice(0, 4)].concat(SERIES.map(x => n(x.dados[i])))));

  const alvoAcoes = document.getElementById('wrapAcoes');
  if (alvoAcoes) alvoAcoes.innerHTML = tpa ? '<div class="barras-painel">' + Object.keys(ACOES).map(k => barra(ACOES[k], tpa[k], P.resposta)).join('') + '</div>'
    : '<div class="lacuna">' + NAO_LOCALIZADO + '</div>';
  if (RECURSOS) molde('subAcoes', 'financiamento.defesaCivil.acoes.legenda', {n: RECURSOS.municipios_com_ato || 0});
  cred('boxAcoes', [FONTE_DC], RECURSOS && RECURSOS.atualizado_em);
  tabela('boxAcoes', ['Município', 'UF', 'Portaria', 'Data', 'Ação', 'Valor autorizado'],
    Object.values((RECURSOS && RECURSOS.municipios) || {}).flatMap(m => (m.atos || []).map(a => ({m: m, a: a})))
      .sort((x, y) => String(y.a.data).localeCompare(String(x.a.data)))
      .map(({m, a}) => ['<strong>' + esc(m.nome) + '</strong>', esc(m.uf), link(a.url, 'nº ' + a.portaria), esc(MonitorMapas.dataBR(a.data) || ''), esc(ACOES[a.acao] || a.acao_no_ato || ''), esc(reais(a.valor_autorizado) || NAO_LOCALIZADO)]));

  /* Pendência: reconhecido pela União há mais de 30 dias e sem portaria de recurso localizada. */
  const ref = paraISO(corteDec);
  const dias = iso => Math.floor((new Date(ref + 'T12:00:00') - new Date(iso + 'T12:00:00')) / 864e5);
  const pendentes = ref ? decretados.filter(m => m.reconhecido && paraISO(m.primeiro_reconhecimento) && !recursoPorCod[m.ibge] && dias(paraISO(m.primeiro_reconhecimento)) > DIAS_PENDENCIA)
    .map(m => Object.assign({dias: dias(paraISO(m.primeiro_reconhecimento))}, m)).sort((a, b) => b.dias - a.dias) : [];
  texto('topoSemRecurso', !DECRETADOS || !RECURSOS ? 'sem coleta até o corte' : (pendentes.length ? n(pendentes.length) : 'nenhum'));
  if (corteDec) molde('subSemRecurso', 'financiamento.defesaCivil.sem_recurso.legenda', {data: corteDec});
  cred('topoSemRecursoFonte', [FONTE_DC], corteDec);
  cred('boxSemRecurso', [FONTE_DC], corteDec);
  tabela('boxSemRecurso', ['Município', 'UF', 'Reconhecimento', 'Dias sem recurso autorizado'],
    pendentes.map(m => ['<strong>' + esc(m.nome) + '</strong>', esc(m.uf), esc(m.primeiro_reconhecimento), n(m.dias)]));
}

__load().catch(err => {
  document.body.insertAdjacentHTML('afterbegin', '<div id="errBanner" class="erro-carga">Erro ao carregar os dados: '
    + err.message + '. Sirva a pasta via HTTP (ex.: <code>npx serve</code>) — abrir o arquivo diretamente bloqueia o fetch.</div>');
});

window.addEventListener('load', function(){
  if (window.VLibras && window.VLibras.Widget) { try { new window.VLibras.Widget('https://vlibras.gov.br/app'); } catch (e) {} }
});
