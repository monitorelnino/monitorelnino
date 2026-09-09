// ===== saude.html · bloco 1 (extraído em 06/09/2026, CSP sem unsafe-inline) =====
let BR_GEOJSON, SUF, SFED, SSIN, SINAIS, MARE, MSAUDE, DESF, DESF_CANAL, DESF_COMP, PAINEL_LISTA, CATALOGO, GATILHOS, RESP_NAC, SRAG;
const UFS = ["AC","AL","AM","AP","BA","CE","DF","ES","GO","MA","MG","MS","MT","PA","PB","PE","PI","PR","RJ","RN","RO","RR","RS","SC","SE","SP","TO"];
const NEUTRA = MonitorMapas.cor('sem-dado');
const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const { showTip, hideTip } = MonitorMapas;

async function __load(){
  [BR_GEOJSON, SUF, SFED, SSIN, SINAIS, MARE, MSAUDE] = await Promise.all(
    ['geo_uf','saude_uf','saude_federal','saude_sinais','sinais_risco','indice','monitor_saude'].map(f => fetch('data/' + f + '.json').then(r => {
      if(!r.ok) throw new Error('Falha ao carregar data/' + f + '.json'); return r.json(); })));
  try { [DESF, DESF_CANAL, DESF_COMP, PAINEL_LISTA] = await Promise.all(['data/saude_desfechos/serie_painel.json','data/saude_desfechos/canal_endemico.json','data/saude_desfechos/completude.json','data/municipios_ibge_referencia.json'].map(f => fetch(f).then(r => r.ok ? r.json() : null))); } catch(e) { DESF = DESF_CANAL = DESF_COMP = PAINEL_LISTA = null; }
  try { [CATALOGO, GATILHOS, RESP_NAC, SRAG] = await Promise.all(['data/saude_desfechos/catalogo.json','data/saude_desfechos/gatilhos.json','data/resposta/por_uf.json','data/saude_desfechos/srag_serie.json'].map(f => fetch(f).then(r => r.ok ? r.json() : null))); } catch(e) { CATALOGO = GATILHOS = RESP_NAC = SRAG = null; }
  __init();
  renderDesfechos();
  renderEstrutura();
  renderSRAG();
}

const fonteFigura = MonitorMapas.credito;

function __init(){
  document.getElementById('corteSaude').textContent = SUF.corte || '—';
  const ctx = MonitorMapas.contexto(BR_GEOJSON, 480, 460); const projection = ctx.projection;
  function desenharMapa(svgId, legendaId, corDe, rotuloDe, itens){ const svg = MonitorMapas.ufs(ctx, svgId, corDe, rotuloDe); MonitorMapas.legenda(legendaId, itens); return svg; }

  // 0 · Monitor Saúde (v0.1, Metodologia §31): prontidão = média (instrumento, antecipação); não verificada = cinza, sem número
  (function(){
    const M = (MSAUDE && MSAUDE.ufs) || {};
    const FX = {'estágio inicial': MonitorMapas.PALETA.faixas.inicial, 'em construção': MonitorMapas.PALETA.faixas.construcao, 'consolidado': MonitorMapas.PALETA.faixas.consolidado, 'avançado': MonitorMapas.PALETA.faixas.avancado, 'não verificado': MonitorMapas.PALETA.faixas.nao_verificado};
    const ST_H = {NOVO:'novo, do ciclo', READ:'readequado', VIG:'vigente, recorrente', ELAB:'em elaboração', LAC:'não localizado', NAO_VERIFICADO:'ainda não verificado'};
    desenharMapa('mapaMonitor', 'legMonitor', uf => FX[(M[uf] || {}).faixa] || FX['não verificado'],
      uf => { const m = M[uf] || {}; if (!m.verificado) return '<em>ainda não verificado</em> — sem número'; const i = m.instrumento || {}, a = m.antecipacao || {};
        return '<em>' + esc(m.faixa) + ' · ' + esc(m.prontidao) + '</em><br>instrumento ' + esc(i.pontos) + ' (' + esc(ST_H[i.status] || i.status) + ')' + (i.data ? ' · ' + esc(i.data) : '') + '<br>antecipação ' + esc(a.pontos) + (i.temporada ? ' (edição ' + esc(i.temporada) + ')' : ''); },
      []);
    const R = (MSAUDE && MSAUDE.resumo) || {}; const pf = R.por_faixa || {};
    MonitorMapas.legenda('legMonitor', [
      ...['avançado', 'consolidado', 'em construção', 'estágio inicial'].map(f => ({cor: FX[f], rotulo: f + ' · ' + (pf[f] || 0) + ' UF' + ((pf[f] || 0) === 1 ? '' : 's')})),
      {cor: FX['não verificado'], rotulo: 'ainda não verificado · ' + (R.nao_verificadas ?? '—') + ' UFs (sem número)'}]);
    fonteFigura('boxMonitor', {fontes: ['Monitor El Niño Brasil', 'Monitor Saúde v0.1'], data: (MSAUDE || {}).gerado_em});
    // tabela alternativa
    const tb = document.querySelector('#tblMonitor tbody');
    if (tb) tb.innerHTML = UFS.map(uf => { const m = M[uf] || {}, i = m.instrumento || {}, a = m.antecipacao || {}, r = m.risco_atual || {};
      return '<tr><td><strong>' + uf + '</strong></td><td>' + (m.verificado ? esc(m.prontidao) : '—') + '</td><td>' + esc(m.faixa || '') + '</td><td>' + esc(ST_H[i.status] || '') + (i.data ? ' · ' + esc(i.data) : '') + '</td><td>' + (a.pontos ?? '—') + (i.temporada ? ' · ' + esc(i.temporada) : '') + '</td><td>' + (r.dengue_capital_nivel ? 'nível ' + esc(r.dengue_capital_nivel) + ' (' + esc(r.dengue_capital) + ')' : '—') + '</td><td>' + esc((m.risco_projetado || []).join('; ')) + '</td></tr>'; }).join('');
    // barras por UF verificada
    const ver = UFS.filter(uf => (M[uf] || {}).verificado).sort((x, y) => (M[y].prontidao - M[x].prontidao) || x.localeCompare(y));
    const bx = document.getElementById('monitorBarras');
    if (bx) bx.innerHTML = ver.length ? ver.map(uf => { const m = M[uf]; return '<div class="msb" role="group" aria-label="' + uf + ': ' + esc(m.prontidao) + '"><b>' + uf + '</b><div class="trilho"><div class="barra" style="width:' + m.prontidao + '%; background:' + FX[m.faixa] + '"></div></div><span>' + esc(m.prontidao) + '</span></div>'; }).join('')
      : '<div class="msb"><b>—</b><div class="trilho"></div><span>nenhuma UF verificada</span></div>';
    MonitorMapas.legenda('legMonitorBarras', [{cor: MonitorMapas.cor('areia'), rotulo: 'trilho 0–100'}, {cor: MonitorMapas.PALETA.faixas.avancado, rotulo: 'cor = faixa'}, {cor: MonitorMapas.PALETA.faixas.nao_verificado, rotulo: (R.nao_verificadas ?? '—') + ' UFs sem número'}]);
    fonteFigura('boxMonitorBarras', {fontes: ['Monitor El Niño Brasil', 'Monitor Saúde v0.1'], data: (MSAUDE || {}).gerado_em});
    // Resposta sanitária (E17): ESPIN federal, decretos estaduais por arboviroses, créditos por portaria — contador, hoje zero de verdade
    const em = (SSIN && SSIN.emergencias) || []; const rn = document.getElementById('rsNum'); if (rn) rn.textContent = String(em.length);
    MonitorMapas.legenda('legRespostaSanitaria', [{cor: MonitorMapas.PALETA.resposta, rotulo: 'ESPIN federal: nenhuma em 2026'}, {cor: MonitorMapas.PALETA.status.ELAB, rotulo: 'decretos estaduais por arboviroses: nenhum'}, {cor: MonitorMapas.PALETA.semDado, rotulo: 'busca manual de 05/09; coleta do DOU pendente'}]);
    fonteFigura('boxRespostaSanitaria', {fontes: ['DOU (ESPIN)', 'diários estaduais'], data: '05/09/2026'});
  })();

  // 1 · federal
  const STATUS_FED = {localizado:'localizado', anunciado_nao_localizado:'anunciado, não localizado até o corte'};
  document.getElementById('cartoesFederal').innerHTML = SFED.cartoes.map(c => '<div class="cartao"><h3 class="figura-titulo">'+esc(c.titulo)+'</h3>'
    + '</div>').join('');

  // 2 · estadual
  const ST = {NOVO:['Novo, específico para o ciclo',MonitorMapas.PALETA.status.NOVO], READ:['Recorrente readaptado',MonitorMapas.PALETA.status.READ], VIG:['Vigente, sem menção ao ciclo',MonitorMapas.PALETA.status.VIG],
              ELAB:['Em elaboração',MonitorMapas.PALETA.status.ELAB], LAC:['Não localizado (bateria datada)',MonitorMapas.PALETA.status.LAC], NAO_VERIFICADO:['Ainda não verificado',MonitorMapas.PALETA.status.NAO_VERIFICADO]};
  const st = uf => (SUF.uf[uf] || {}).status || 'NAO_VERIFICADO';
  desenharMapa('mapaStatus','legStatus', uf => ST[st(uf)][1],
    uf => { const u = SUF.uf[uf]||{}; return '<em>'+esc(ST[st(uf)][0])+'</em>' + (u.doc ? '<br>'+esc(u.doc)+(u.data?' · '+esc(u.data):'') : '') + (u.data_verificacao ? '<br>verificado em '+esc(u.data_verificacao) : '<br>bateria estadual ainda não executada'); },
    Object.values(ST).map(v => ({cor:v[1], rotulo:v[0]})));
  const nv = UFS.filter(u => st(u)==='NAO_VERIFICADO').length;
  document.getElementById('contagemUF').textContent = nv + ' de 27 UFs ainda não verificadas na camada de saúde · ' + (27-nv) + ' verificada(s).';
  fonteFigura('boxStatus', {fontes: 'Monitor El Niño Brasil', data: SUF.corte});
  const FAM = {seca:['Seca / calor / fogo',MonitorMapas.PALETA.risco.seca], chuvas:['Chuvas extremas',MonitorMapas.PALETA.risco.chuvas], multi:['Mais de uma família',MonitorMapas.PALETA.risco.multi]};
  const fam = uf => { const r = ((SUF.uf[uf]||{}).risco_sanitario_projetado||[]).join(' ').toLowerCase(); const s = /calor|queimad|arbovir|estiagem/.test(r), c = /leptospir|diarre|hepatite/.test(r); return s&&c?'multi':s?'seca':c?'chuvas':null; };
  desenharMapa('mapaRiscoSan','legRiscoSan', uf => fam(uf) ? FAM[fam(uf)][1] : NEUTRA,
    uf => { const u = SUF.uf[uf]||{}; return (u.risco_sanitario_projetado||['sem risco projetado registrado']).map(esc).join('<br>'); },
    Object.values(FAM).map(v => ({cor:v[1], rotulo:v[0]})));
  fonteFigura('boxRiscoSan', {fontes: ['Painel El Niño 2026-2027 (CEMADEN/INPE)', 'boletins nº 1 a 3'], data: SUF.corte});
  document.querySelector('#tblUF tbody').innerHTML = UFS.map(uf => { const u = SUF.uf[uf]||{}; return '<tr><td><strong>'+uf+'</strong></td><td>'+esc(ST[st(uf)][0])+'</td><td>'+esc(u.doc||'—')+'</td><td>'+esc((u.risco_sanitario_projetado||[]).join('; '))+'</td><td>'+esc(u.data_verificacao||'—')+'</td></tr>'; }).join('');

  // 3 · observado
  const NIV_DENGUE = {1:['Nível 1 (baixa atividade)',MonitorMapas.PALETA.ordinal4[0]], 2:['Nível 2 (atenção)',MonitorMapas.PALETA.ordinal4[1]], 3:['Nível 3 (alerta)',MonitorMapas.PALETA.ordinal4[2]], 4:['Nível 4 (emergência)',MonitorMapas.PALETA.ordinal4[3]]};
  const svgD = desenharMapa('mapaDengue','legDengue', uf => NEUTRA, uf => { const d = (SSIN.dengue_capitais||{})[uf]; return d ? esc(d.municipio)+': nível '+esc(d.nivel)+' · SE '+esc(d.se)+'<br>'+esc(d.fonte) : 'Capital: aguardando primeira coleta'; },
    Object.values(NIV_DENGUE).map(v => ({cor:v[1], rotulo:v[0]})).concat([{cor:NEUTRA, rotulo:'aguardando coleta'}]));
  const capitais = Object.entries(SSIN.dengue_capitais||{});
  if (capitais.length && SINAIS && SINAIS.uf) {
    svgD.append('g').selectAll('circle').data(capitais).join('circle')
      .attr('cx', ([uf,d]) => projection([d.lon||0, d.lat||0])[0]).attr('cy', ([uf,d]) => projection([d.lon||0, d.lat||0])[1])
      .attr('r', 5).attr('fill', ([uf,d]) => (NIV_DENGUE[d.nivel]||['',NEUTRA])[1]);
  }
  const fD = SSIN.fontes.infodengue;
  fonteFigura('boxDengue', {fontes: 'InfoDengue (Fiocruz/FGV)', data: fD.status === 'coletado' ? (fD.ultima_coleta_ok || fD.consultado_em) : null});
  const avisos = uf => (SINAIS.uf && SINAIS.uf[uf] && SINAIS.uf[uf].avisos_inmet) || null;
  const nCalor = uf => { const a = avisos(uf); if(!a) return null; const lista = a.lista || a.avisos || []; return lista.filter(x => /calor/i.test(JSON.stringify(x))).length; };
  const CAL = [MonitorMapas.PALETA.zero, MonitorMapas.PALETA.ordinal4[1], MonitorMapas.PALETA.ordinal4[2], MonitorMapas.PALETA.ordinal4[3]];
  desenharMapa('mapaCalor','legCalor', uf => { const n = nCalor(uf); return n == null ? NEUTRA : CAL[Math.min(3, n)]; },
    uf => { const n = nCalor(uf); return n == null ? 'Aguardando coleta do INMET' : n + ' aviso(s) de calor vigente(s)'; },
    [{cor:CAL[0],rotulo:'0'},{cor:CAL[1],rotulo:'1'},{cor:CAL[2],rotulo:'2'},{cor:CAL[3],rotulo:'3+'},{cor:NEUTRA,rotulo:'aguardando coleta'}]);
  fonteFigura('boxCalor', {fontes: 'INMET', data: (SINAIS.fontes && SINAIS.fontes.inmet_avisos && SINAIS.fontes.inmet_avisos.status === 'coletado') ? SINAIS.fontes.inmet_avisos.consultado_em : null});
  desenharMapa('mapaEmerg','legEmerg', uf => NEUTRA, uf => 'Nenhuma emergência sanitária registrada até o corte (fonte: DOU e diários municipais; coleta em andamento)', [{cor:NEUTRA, rotulo:'nenhuma registrada até o corte'}]);
  fonteFigura('boxEmerg', {fontes: ['DOU', 'diários oficiais municipais'], data: '05/09/2026'});
  (function(){ const f = SSIN.fontes || {}; const c = Object.entries(f).map(([k, v]) => (v.nome || k) + ': ' + (v.consultado_em ? 'consultado em ' + v.consultado_em : (v.status === 'reuso' ? 'reuso da página de sinais' : 'ainda não consultado')));
    const el = document.getElementById('carimboSaude'); if (el) el.textContent = 'Estado das fontes — ' + c.join(' · ') + '.'; })();

  // 4 · quadrantes DC × saúde
  const dcLoc = uf => ['NOVO','READ','VIG'].includes(((MARE[uf]||{}).status_estadual||'').toUpperCase());
  const q = {ambos:[], so_dc:[], so_saude:[], nenhum:[], nv:[]};
  UFS.forEach(uf => { const s = st(uf); if (s === 'NAO_VERIFICADO') { q.nv.push(uf); return; } const sl = ['NOVO','READ','VIG'].includes(s); const d = dcLoc(uf); (d&&sl ? q.ambos : d ? q.so_dc : sl ? q.so_saude : q.nenhum).push(uf); });
  const ROT = {ambos:'Defesa civil e saúde', so_dc:'Só defesa civil', so_saude:'Só saúde', nenhum:'Nenhum localizado', nv:'Saúde ainda não verificada'};
  document.getElementById('quadrantes').innerHTML = Object.keys(ROT).map(k => '<div class="quadrante"><div class="rotulo">'+ROT[k]+' · <strong>'+q[k].length+'</strong></div><div class="lista-uf">'+(q[k].join(' · ')||'—')+'</div></div>').join('');
  fonteFigura('boxQuadrantes', {fontes: 'Monitor El Niño Brasil', data: SUF.corte});
  // Série semanal 2026 × 2025 × 2024 (05/09/2026): soma das 27 capitais no InfoDengue — não é o total nacional.
  const SER = SSIN.serie_capitais;
  if (SER && SER.anos && Object.keys(SER.anos).length && typeof Chart !== 'undefined') {
    MonitorMapas.padraoGraficos(window.Chart);
    const semanas = Array.from({length: 52}, (_, i) => String(i + 1).padStart(2, '0'));
    const cores = MonitorMapas.PALETA.anos;
    const ds = Object.keys(SER.anos).sort().reverse().map(ano => ({label: ano, data: semanas.map(w => SER.anos[ano][w] ?? null),
      borderColor: cores[ano] || MonitorMapas.PALETA.serie[1], backgroundColor: 'transparent', borderWidth: ano === '2026' ? 2.5 : 1.5, pointRadius: 0, tension: .25, spanGaps: false}));
    new Chart(document.getElementById('serieDengue'), {type: 'line', data: {labels: semanas.map(w => 'SE ' + w), datasets: ds},
      options: {animation: false, responsive: true, maintainAspectRatio: false, plugins: {legend: {display: false}},
                scales: {x: {ticks: {maxTicksLimit: 13}}, y: {title: {display: true, text: 'casos estimados · 27 capitais'}}}}});
    document.getElementById('serieDengue').setAttribute('aria-label', 'Série semanal de dengue, soma das 27 capitais, 2024 a 2026');
    MonitorMapas.legenda('legSerie', Object.keys(cores).map(a => ({cor: cores[a], rotulo: a})));
    fonteFigura('boxSerie', {fontes: ['InfoDengue (Fiocruz/FGV)', 'soma das 27 capitais'], data: SER.coletado_em});
  } else {
    fonteFigura('boxSerie', {fontes: ['InfoDengue (Fiocruz/FGV)', '27 capitais'], data: null});
  }
}
__load().catch(err => { const m = document.getElementById('subSaude'); if (m) m.insertAdjacentHTML('afterend', '<p class="note u-rust">Erro ao carregar os dados: '+esc(err.message)+'</p>'); });

window.addEventListener('load', function(){ if (window.VLibras && window.VLibras.Widget) { try { new window.VLibras.Widget('https://vlibras.gov.br/app'); } catch (e) {} } });


// ===== 3 · O que aconteceu — desfechos em saúde (§8, 07/09/2026). Peso zero. O Monitor não atribui casos ao El Niño. =====
function renderDesfechos(){
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const M = DESF && DESF.municipios; const semColeta = {fontes: ['InfoDengue (Fiocruz/FGV)', 'painel amostral'], data: null};
  if (!M || !Object.keys(M).length) { ['boxDesfSemanal','boxDesfAcum','boxDesfMapa'].forEach(id => fonteFigura(id, semColeta)); return; }
  const credito = {fontes: ['modelo InfoDengue (Fiocruz/FGV)', 'Sinan', 'painel amostral'], data: DESF.gerado_em};
  // soma do painel por SE de 2026 (consolidadas) + canal (soma das medianas/p75/p90) + nowcasting (soma das faixas)
  const semanas = Array.from({length: 53}, (_, i) => String(i + 1).padStart(2, '0'));
  const soma = {casos: {}, med: {}, p75: {}, p90: {}, nmin: {}, nmax: {}};
  Object.entries(M).forEach(([cod, m]) => { const c = (DESF_CANAL && DESF_CANAL.municipios && DESF_CANAL.municipios[cod]) || {};
    semanas.forEach(ss => { const k = '2026-' + ss; const v = (m.semanas_2026 || {})[k];
      if (v && v.casos != null) soma.casos[ss] = (soma.casos[ss] || 0) + v.casos;
      if (c[ss]) { soma.med[ss] = (soma.med[ss] || 0) + c[ss].mediana; soma.p75[ss] = (soma.p75[ss] || 0) + c[ss].p75; soma.p90[ss] = (soma.p90[ss] || 0) + c[ss].p90; }
      const n = (m.nowcasting || {})[k]; if (n && n.est_min != null) { soma.nmin[ss] = (soma.nmin[ss] || 0) + n.est_min; soma.nmax[ss] = (soma.nmax[ss] || 0) + n.est_max; } }); });
  const ate = Math.max(...Object.keys(soma.casos).concat(Object.keys(soma.nmax)).map(Number)); const labels = semanas.slice(0, ate);
  MonitorMapas.padraoGraficos(window.Chart);
  new Chart(document.getElementById('cDesfSemanal'), {type: 'bar', data: {labels: labels.map(w => 'SE ' + w), datasets: [
      {type: 'bar', label: '2026 (consolidado)', data: labels.map(w => soma.casos[w] ?? null), backgroundColor: MonitorMapas.PALETA.anos['2026'], order: 3},
      {type: 'line', label: 'nowcasting (máx.)', data: labels.map(w => soma.nmax[w] ?? null), borderColor: MonitorMapas.PALETA.anos['2026'], borderDash: [4, 3], borderWidth: 1, pointRadius: 0, order: 2, spanGaps: false},
      {type: 'line', label: 'nowcasting (mín.)', data: labels.map(w => soma.nmin[w] ?? null), borderColor: MonitorMapas.PALETA.anos['2026'], borderDash: [4, 3], borderWidth: 1, pointRadius: 0, order: 2, spanGaps: false},
      {type: 'line', label: 'mediana 2019–2025', data: labels.map(w => soma.med[w] ?? null), borderColor: MonitorMapas.PALETA.anos.canal, borderWidth: 2, pointRadius: 0, order: 1},
      {type: 'line', label: 'p75', data: labels.map(w => soma.p75[w] ?? null), borderColor: MonitorMapas.PALETA.anos.p75, borderWidth: 1.5, pointRadius: 0, order: 1},
      {type: 'line', label: 'p90', data: labels.map(w => soma.p90[w] ?? null), borderColor: MonitorMapas.PALETA.anos.p90, borderWidth: 1.5, pointRadius: 0, order: 1}]},
    options: {animation: false, responsive: true, maintainAspectRatio: false, plugins: {legend: {display: false}}, scales: {x: {ticks: {maxTicksLimit: 13}}, y: {beginAtZero: true, title: {display: true, text: 'casos notificados · painel'}}}}});
  MonitorMapas.legenda('legDesfSemanal', [{cor: MonitorMapas.PALETA.anos['2026'], rotulo: '2026 consolidado (últimas 4 SE vazadas)'}, {cor: MonitorMapas.PALETA.anos['2026'], opacidade: .5, rotulo: 'faixa de nowcasting (tracejado)'}, {cor: MonitorMapas.PALETA.anos.canal, rotulo: 'mediana 2019–2025 (2024 à parte)'}, {cor: MonitorMapas.PALETA.anos.p75, rotulo: 'p75'}, {cor: MonitorMapas.PALETA.anos.p90, rotulo: 'p90'}]);
  fonteFigura('boxDesfSemanal', credito);
  // escada do acumulado
  const acum = a => Object.values(M).reduce((s, m) => s + ((m.acumulado || {})[a] || 0), 0);
  new Chart(document.getElementById('cDesfAcum'), {type: 'bar', data: {labels: ['2024', '2025', '2026 (até a última SE consolidada)'], datasets: [{data: [acum('2024'), acum('2025'), acum('2026')], backgroundColor: [MonitorMapas.PALETA.anos['2024'], MonitorMapas.PALETA.anos['2025'], MonitorMapas.PALETA.anos['2026']]}]},
    options: {animation: false, responsive: true, maintainAspectRatio: false, plugins: {legend: {display: false}}, scales: {y: {beginAtZero: true, title: {display: true, text: 'casos notificados · painel'}}}}});
  MonitorMapas.legenda('legDesfAcum', [{cor: MonitorMapas.PALETA.anos['2024'], rotulo: '2024 (ano epidêmico, fora do canal)'}, {cor: MonitorMapas.PALETA.anos['2025'], rotulo: '2025'}, {cor: MonitorMapas.PALETA.anos['2026'], rotulo: '2026 parcial'}]);
  fonteFigura('boxDesfAcum', credito);
  // mapa: pontos do painel coloridos pelo nível da última SE consolidada
  const ctx = MonitorMapas.contexto(BR_GEOJSON, 480, 460);
  const NIV = {1: MonitorMapas.PALETA.ordinal4[0], 2: MonitorMapas.PALETA.ordinal4[1], 3: MonitorMapas.PALETA.ordinal4[2], 4: MonitorMapas.PALETA.ordinal4[3]};   // mesmo ordinal do mapa de dengue por UF (Figura acima)
  const ref = Array.isArray(PAINEL_LISTA) ? PAINEL_LISTA : Object.values(PAINEL_LISTA || {}); const coord = {}; ref.forEach(r => { coord[String(r.codigo_ibge).padStart(7, '0')] = r; });
  const pontos = Object.entries(M).filter(([cod]) => coord[cod] && coord[cod].lat != null).map(([cod, d]) => ({lat: coord[cod].lat, lon: coord[cod].lon, nivel: d.nivel_ultima_se, nome: d.nome, uf: d.uf, ultima: d.ultima_se}));
  MonitorMapas.ufs(ctx, 'mapaDesf', () => MonitorMapas.NEUTRA, uf => uf);
  if (pontos.length) MonitorMapas.pontos(ctx, 'mapaDesf', pontos, {r: () => 4, cor: d => NIV[d.nivel] || MonitorMapas.NEUTRA, rotulo: d => esc(d.nome) + '/' + esc(d.uf) + ' · nível ' + esc(d.nivel ?? '—') + ' · ' + esc(d.ultima || '')});
  MonitorMapas.legenda('legDesfMapa', [{cor: NIV[1], rotulo: 'nível 1 (baixa atividade)'}, {cor: NIV[2], rotulo: 'nível 2 (atenção)'}, {cor: NIV[3], rotulo: 'nível 3 (alerta)'}, {cor: NIV[4], rotulo: 'nível 4 (emergência)'}, {cor: MonitorMapas.NEUTRA, rotulo: (pontos.length ? pontos.length + ' municípios do painel' : 'painel sem coordenadas')}]);
  fonteFigura('boxDesfMapa', credito);
}


// ===== O que o plano nacional manda acompanhar (§36, 09/09/2026): catálogo e gatilhos, dos JSONs; peso zero =====
function renderEstrutura(){
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const ROT = {coletado: 'coletado', candidato: 'candidato (fonte aberta identificada)', 'sem fonte aberta identificada': 'sem fonte aberta'};
  const COR = {coletado: MonitorMapas.PALETA.coleta.coletado, candidato: MonitorMapas.PALETA.coleta.candidato, 'sem fonte aberta identificada': MonitorMapas.PALETA.coleta.sem_fonte};
  const tb = document.querySelector('#tblCatalogo tbody');
  if (tb && CATALOGO && CATALOGO.desfechos) {
    tb.innerHTML = CATALOGO.desfechos.map(d => '<tr><td><strong>' + esc(d.nome) + '</strong></td><td>' + esc(d.comprometimento) + '</td><td>' + esc(d.sistema) + '</td><td>' + esc(d.fonte_aberta) + '</td><td><span style="display:inline-block;width:9px;height:9px;border-radius:50%;background:' + COR[d.status_coleta] + ';margin-right:6px;"></span>' + esc(ROT[d.status_coleta] || d.status_coleta) + '</td></tr>').join('');
    const n = {}; CATALOGO.desfechos.forEach(d => { n[d.status_coleta] = (n[d.status_coleta] || 0) + 1; });
    MonitorMapas.legenda('legCatalogo', Object.keys(COR).map(k => ({cor: COR[k], rotulo: (ROT[k] || k) + ': ' + (n[k] || 0)})));
    fonteFigura('boxCatalogo', {fontes: ['MS/SVSA, Plano de Contingência por Seca e Estiagem (2026), Quadro 2'], data: (CATALOGO.fonte || {}).lido_em || null, url: (CATALOGO.fonte || {}).url});
  } else fonteFigura('boxCatalogo', {fontes: ['MS/SVSA'], data: null});
  const tg = document.querySelector('#tblGatilhos tbody');
  if (tg && GATILHOS && GATILHOS.gatilhos) {
    const N = RESP_NAC && RESP_NAC.nacional; const pct = N ? (100 * N.fracao_municipios).toFixed(1).replace('.', ',') + '% dos municípios sob decreto (todas as causas) · limiar 8%' : null;
    const valor = g => g.id === 'eme_decretos' && pct ? pct : g.id === 'cri_decretos' && N ? 'por região e causa: a filtrar · limiar 50%' : g.status_monitor === 'computavel_parcial' ? 'parcial — ' + esc(g.nota) : g.status_monitor === 'leitura_humana' ? 'leitura humana — ' + esc(g.nota) : g.status_monitor === 'nao_publico' ? 'não público (só por LAI)' : 'sem coleta' + (g.nota ? ' — ' + esc(g.nota) : '');
    const ORD = {computavel: 0, computavel_parcial: 1, leitura_humana: 2, sem_coleta: 3, nao_publico: 4};
    tg.innerHTML = GATILHOS.gatilhos.slice().sort((a, b) => ORD[a.status_monitor] - ORD[b.status_monitor]).map(g => '<tr><td>' + esc(g.estagio) + '</td><td>' + esc(g.texto) + '</td><td>' + esc(g.fonte_oficial) + '</td><td>' + valor(g) + '</td></tr>').join('');
    const c = {}; GATILHOS.gatilhos.forEach(g => { c[g.status_monitor] = (c[g.status_monitor] || 0) + 1; });
    MonitorMapas.legenda('legGatilhos', [{cor: MonitorMapas.PALETA.coleta.coletado, rotulo: 'computável agora: ' + (c.computavel || 0)}, {cor: MonitorMapas.PALETA.coleta.candidato, rotulo: 'parcial: ' + (c.computavel_parcial || 0)}, {cor: MonitorMapas.PALETA.enso.la_nina, rotulo: 'leitura humana: ' + (c.leitura_humana || 0)}, {cor: MonitorMapas.PALETA.coleta.sem_fonte, rotulo: 'sem coleta / não público: ' + ((c.sem_coleta || 0) + (c.nao_publico || 0))}]);
    fonteFigura('boxGatilhos', {fontes: ['MS/SVSA, Plano de Contingência por Seca e Estiagem (2026), Quadro 5', 'valores do Monitor no corte'], data: (GATILHOS.fonte || {}).lido_em || null, url: (GATILHOS.fonte || {}).url});
  } else fonteFigura('boxGatilhos', {fontes: ['MS/SVSA'], data: null});
}


// ===== SRAG por semana, Brasil (§36; InfoGripe). Peso zero. O Monitor não atribui casos ao El Niño. =====
function renderSRAG(){
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const br = SRAG && SRAG.serie && SRAG.serie.BR;
  if (!br) { fonteFigura('boxSRAG', {fontes: ['InfoGripe (Fiocruz/FGV)'], data: null}); return; }
  const canal = (SRAG.canal_endemico || {}).BR || {}; const now = (SRAG.nowcasting || {}).BR || {};
  const ano = SRAG.ano_corrente; const semanas = Array.from({length: 53}, (_, i) => String(i + 1).padStart(2, '0'));
  const ate = Math.max(...Object.keys(br).concat(Object.keys(now)).filter(k => k.startsWith(String(ano))).map(k => +k.split('-')[1]));
  const labels = semanas.slice(0, ate);
  MonitorMapas.padraoGraficos(window.Chart);
  new Chart(document.getElementById('cSRAG'), {data: {labels: labels.map(w => 'SE ' + w), datasets: [
      {type: 'bar', label: 'consolidado', data: labels.map(w => (br[ano + '-' + w] ?? null)), backgroundColor: MonitorMapas.PALETA.anos['2026'] || MonitorMapas.PALETA.anos.canal, order: 2},
      {type: 'bar', label: 'nowcasting', data: labels.map(w => (now[ano + '-' + w] ?? null)), backgroundColor: MonitorMapas.PALETA.anos['2024'], order: 2},
      {type: 'line', label: 'mediana 2019–2025', data: labels.map(w => (canal[w] || {}).mediana ?? null), borderColor: MonitorMapas.PALETA.anos.canal, borderWidth: 2, pointRadius: 0, order: 1},
      {type: 'line', label: 'p90', data: labels.map(w => (canal[w] || {}).p90 ?? null), borderColor: MonitorMapas.PALETA.anos.p90, borderWidth: 1.5, pointRadius: 0, order: 1}]},
    options: {animation: false, responsive: true, maintainAspectRatio: false, plugins: {legend: {display: false}}, scales: {x: {ticks: {maxTicksLimit: 13}}, y: {beginAtZero: true, title: {display: true, text: 'casos SRAG · Brasil'}}}}});
  MonitorMapas.legenda('legSRAG', [{cor: MonitorMapas.PALETA.anos['2026'] || MonitorMapas.PALETA.anos.canal, rotulo: 'consolidado'}, {cor: MonitorMapas.PALETA.anos['2024'], rotulo: 'nowcasting (últimas 4 SE)'}, {cor: MonitorMapas.PALETA.anos.canal, rotulo: 'mediana 2019–2025'}, {cor: MonitorMapas.PALETA.anos.p90, rotulo: 'p90'}]);
  fonteFigura('boxSRAG', {fontes: ['InfoGripe (Fiocruz/FGV), Sivep-Gripe'], data: SRAG.gerado_em, url: SRAG.fonte});
}
