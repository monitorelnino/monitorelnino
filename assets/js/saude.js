// ===== saude.html · bloco 1 (extraído em 06/09/2026, CSP sem unsafe-inline) =====
let BR_GEOJSON, SUF, SFED, SSIN, SINAIS, MARE, MSAUDE;
const UFS = ["AC","AL","AM","AP","BA","CE","DF","ES","GO","MA","MG","MS","MT","PA","PB","PE","PI","PR","RJ","RN","RO","RR","RS","SC","SE","SP","TO"];
const NEUTRA = MonitorMapas.cor('sem-dado');
const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const { showTip, hideTip } = MonitorMapas;

async function __load(){
  [BR_GEOJSON, SUF, SFED, SSIN, SINAIS, MARE, MSAUDE] = await Promise.all(
    ['geo_uf','saude_uf','saude_federal','saude_sinais','sinais_risco','indice','monitor_saude'].map(f => fetch('data/' + f + '.json').then(r => {
      if(!r.ok) throw new Error('Falha ao carregar data/' + f + '.json'); return r.json(); })));
  __init();
}

const fonteFigura = MonitorMapas.credito;

function __init(){
  document.getElementById('corteSaude').textContent = SUF.corte || '—';
  const ctx = MonitorMapas.contexto(BR_GEOJSON, 480, 460); const projection = ctx.projection;
  function desenharMapa(svgId, legendaId, corDe, rotuloDe, itens){ const svg = MonitorMapas.ufs(ctx, svgId, corDe, rotuloDe); MonitorMapas.legenda(legendaId, itens); return svg; }

  // 0 · Monitor Saúde (v0.1, Metodologia §31): prontidão = média (instrumento, antecipação); não verificada = cinza, sem número
  (function(){
    const M = (MSAUDE && MSAUDE.ufs) || {};
    const FX = {'estágio inicial': MonitorMapas.cor('argila'), 'em construção': MonitorMapas.cor('ambar'), 'consolidado': MonitorMapas.cor('sintetico'), 'avançado': MonitorMapas.cor('musgo'), 'não verificado': MonitorMapas.cor('cinza-quente')};
    const ST_H = {NOVO:'novo, do ciclo', READ:'readequado', VIG:'vigente, recorrente', ELAB:'em elaboração', LAC:'não localizado', NAO_VERIFICADO:'ainda não verificado'};
    desenharMapa('mapaMonitor', 'legMonitor', uf => FX[(M[uf] || {}).faixa] || FX['não verificado'],
      uf => { const m = M[uf] || {}; if (!m.verificado) return '<em>ainda não verificado</em> — sem número'; const i = m.instrumento || {}, a = m.antecipacao || {};
        return '<em>' + esc(m.faixa) + ' · ' + esc(m.prontidao) + '</em><br>instrumento ' + esc(i.pontos) + ' (' + esc(ST_H[i.status] || i.status) + ')' + (i.data ? ' · ' + esc(i.data) : '') + '<br>antecipação ' + esc(a.pontos) + (i.temporada ? ' (edição ' + esc(i.temporada) + ')' : ''); },
      []);
    const R = (MSAUDE && MSAUDE.resumo) || {}; const pf = R.por_faixa || {};
    MonitorMapas.legenda('legMonitor', [
      ...['avançado', 'consolidado', 'em construção', 'estágio inicial'].map(f => ({cor: FX[f], rotulo: f + ' · ' + (pf[f] || 0) + ' UF' + ((pf[f] || 0) === 1 ? '' : 's')})),
      {cor: FX['não verificado'], rotulo: 'ainda não verificado · ' + (R.nao_verificadas ?? '—') + ' UFs (sem número)'}]);
    fonteFigura('boxMonitor', 'Fonte: Monitor El Niño Brasil · Monitor Saúde v0.1 · ' + esc((MSAUDE || {}).gerado_em || '') + ' · peso zero no índice');
    // tabela alternativa
    const tb = document.querySelector('#tblMonitor tbody');
    if (tb) tb.innerHTML = UFS.map(uf => { const m = M[uf] || {}, i = m.instrumento || {}, a = m.antecipacao || {}, r = m.risco_atual || {};
      return '<tr><td><strong>' + uf + '</strong></td><td>' + (m.verificado ? esc(m.prontidao) : '—') + '</td><td>' + esc(m.faixa || '') + '</td><td>' + esc(ST_H[i.status] || '') + (i.data ? ' · ' + esc(i.data) : '') + '</td><td>' + (a.pontos ?? '—') + (i.temporada ? ' · ' + esc(i.temporada) : '') + '</td><td>' + (r.dengue_capital_nivel ? 'nível ' + esc(r.dengue_capital_nivel) + ' (' + esc(r.dengue_capital) + ')' : '—') + '</td><td>' + esc((m.risco_projetado || []).join('; ')) + '</td></tr>'; }).join('');
    // barras por UF verificada
    const ver = UFS.filter(uf => (M[uf] || {}).verificado).sort((x, y) => (M[y].prontidao - M[x].prontidao) || x.localeCompare(y));
    const bx = document.getElementById('monitorBarras');
    if (bx) bx.innerHTML = ver.length ? ver.map(uf => { const m = M[uf]; return '<div class="msb" role="group" aria-label="' + uf + ': ' + esc(m.prontidao) + '"><b>' + uf + '</b><div class="trilho"><div class="barra" style="width:' + m.prontidao + '%; background:' + FX[m.faixa] + '"></div></div><span>' + esc(m.prontidao) + '</span></div>'; }).join('')
      : '<div class="msb"><b>—</b><div class="trilho"></div><span>nenhuma UF verificada</span></div>';
    MonitorMapas.legenda('legMonitorBarras', [{cor: MonitorMapas.cor('areia'), rotulo: 'trilho 0–100'}, {cor: MonitorMapas.cor('musgo'), rotulo: 'cor = faixa'}, {cor: MonitorMapas.cor('cinza-quente'), rotulo: (R.nao_verificadas ?? '—') + ' UFs sem número'}]);
    fonteFigura('boxMonitorBarras', 'Fonte: Monitor El Niño Brasil · Monitor Saúde v0.1 · ' + esc((MSAUDE || {}).gerado_em || ''));
    // Resposta sanitária (E17): ESPIN federal, decretos estaduais por arboviroses, créditos por portaria — contador, hoje zero de verdade
    const em = (SSIN && SSIN.emergencias) || []; const rn = document.getElementById('rsNum'); if (rn) rn.textContent = String(em.length);
    MonitorMapas.legenda('legRespostaSanitaria', [{cor: MonitorMapas.cor('argila'), rotulo: 'ESPIN federal: nenhuma em 2026'}, {cor: MonitorMapas.cor('ambar'), rotulo: 'decretos estaduais por arboviroses: nenhum'}, {cor: MonitorMapas.cor('sem-dado'), rotulo: 'busca manual de 05/09; coleta do DOU pendente'}]);
    fonteFigura('boxRespostaSanitaria', 'Fonte: DOU (ESPIN), diários estaduais · busca de 05/09/2026 · o zero é dado, não lacuna');
  })();

  // 1 · federal
  const STATUS_FED = {localizado:'localizado', anunciado_nao_localizado:'anunciado, não localizado até o corte'};
  document.getElementById('cartoesFederal').innerHTML = SFED.cartoes.map(c => '<div class="chart-box"><h3>'+esc(c.titulo)+'</h3>'
    + '</div>').join('');

  // 2 · estadual
  const ST = {NOVO:['Novo, específico para o ciclo',MonitorMapas.cor('musgo')], READ:['Recorrente readaptado',MonitorMapas.cor('sintetico')], VIG:['Vigente, sem menção ao ciclo',MonitorMapas.cor('mineral')],
              ELAB:['Em elaboração',MonitorMapas.cor('ambar')], LAC:['Não localizado (bateria datada)',MonitorMapas.cor('argila')], NAO_VERIFICADO:['Ainda não verificado',MonitorMapas.cor('cinza-quente')]};
  const st = uf => (SUF.uf[uf] || {}).status || 'NAO_VERIFICADO';
  desenharMapa('mapaStatus','legStatus', uf => ST[st(uf)][1],
    uf => { const u = SUF.uf[uf]||{}; return '<em>'+esc(ST[st(uf)][0])+'</em>' + (u.doc ? '<br>'+esc(u.doc)+(u.data?' · '+esc(u.data):'') : '') + (u.data_verificacao ? '<br>verificado em '+esc(u.data_verificacao) : '<br>bateria estadual ainda não executada'); },
    Object.values(ST).map(v => ({cor:v[1], rotulo:v[0]})));
  const nv = UFS.filter(u => st(u)==='NAO_VERIFICADO').length;
  document.getElementById('contagemUF').textContent = nv + ' de 27 UFs ainda não verificadas na camada de saúde · ' + (27-nv) + ' verificada(s).';
  fonteFigura('boxStatus', 'Fonte: Monitor El Niño Brasil · corte ' + esc(SUF.corte));
  const FAM = {seca:['Seca / calor / fogo',MonitorMapas.cor('argila')], chuvas:['Chuvas extremas',MonitorMapas.cor('musgo')], multi:['Mais de uma família',MonitorMapas.cor('areia-escura')]};
  const fam = uf => { const r = ((SUF.uf[uf]||{}).risco_sanitario_projetado||[]).join(' ').toLowerCase(); const s = /calor|queimad|arbovir|estiagem/.test(r), c = /leptospir|diarre|hepatite/.test(r); return s&&c?'multi':s?'seca':c?'chuvas':null; };
  desenharMapa('mapaRiscoSan','legRiscoSan', uf => fam(uf) ? FAM[fam(uf)][1] : NEUTRA,
    uf => { const u = SUF.uf[uf]||{}; return (u.risco_sanitario_projetado||['sem risco projetado registrado']).map(esc).join('<br>'); },
    Object.values(FAM).map(v => ({cor:v[1], rotulo:v[0]})));
  fonteFigura('boxRiscoSan', 'Fonte: Painel El Niño 2026-2027 (CEMADEN/INPE), boletins nº 1 e 2');
  document.querySelector('#tblUF tbody').innerHTML = UFS.map(uf => { const u = SUF.uf[uf]||{}; return '<tr><td><strong>'+uf+'</strong></td><td>'+esc(ST[st(uf)][0])+'</td><td>'+esc(u.doc||'—')+'</td><td>'+esc((u.risco_sanitario_projetado||[]).join('; '))+'</td><td>'+esc(u.data_verificacao||'—')+'</td></tr>'; }).join('');

  // 3 · observado
  const NIV_DENGUE = {1:['Nível 1 (baixa atividade)',MonitorMapas.cor('mineral')], 2:['Nível 2 (atenção)',MonitorMapas.cor('ambar')], 3:['Nível 3 (alerta)',MonitorMapas.cor('argila')], 4:['Nível 4 (emergência)',MonitorMapas.cor('argila')]};
  const svgD = desenharMapa('mapaDengue','legDengue', uf => NEUTRA, uf => { const d = (SSIN.dengue_capitais||{})[uf]; return d ? esc(d.municipio)+': nível '+esc(d.nivel)+' · SE '+esc(d.se)+'<br>'+esc(d.fonte) : 'Capital: aguardando primeira coleta'; },
    Object.values(NIV_DENGUE).map(v => ({cor:v[1], rotulo:v[0]})).concat([{cor:NEUTRA, rotulo:'aguardando coleta'}]));
  const capitais = Object.entries(SSIN.dengue_capitais||{});
  if (capitais.length && SINAIS && SINAIS.uf) {
    svgD.append('g').selectAll('circle').data(capitais).join('circle')
      .attr('cx', ([uf,d]) => projection([d.lon||0, d.lat||0])[0]).attr('cy', ([uf,d]) => projection([d.lon||0, d.lat||0])[1])
      .attr('r', 5).attr('fill', ([uf,d]) => (NIV_DENGUE[d.nivel]||['',NEUTRA])[1]);
  }
  const fD = SSIN.fontes.infodengue;
  fonteFigura('boxDengue', fD.status === 'coletado' ? 'Fonte: InfoDengue (Fiocruz/FGV) · consultado em '+esc(fD.ultima_coleta_ok || fD.consultado_em) : 'Fonte: InfoDengue (Fiocruz/FGV) · sem coleta até o corte');
  const avisos = uf => (SINAIS.uf && SINAIS.uf[uf] && SINAIS.uf[uf].avisos_inmet) || null;
  const nCalor = uf => { const a = avisos(uf); if(!a) return null; const lista = a.lista || a.avisos || []; return lista.filter(x => /calor/i.test(JSON.stringify(x))).length; };
  const CAL = [MonitorMapas.cor('zebra'),MonitorMapas.cor('ambar'),MonitorMapas.cor('ambar'),MonitorMapas.cor('argila')];
  desenharMapa('mapaCalor','legCalor', uf => { const n = nCalor(uf); return n == null ? NEUTRA : CAL[Math.min(3, n)]; },
    uf => { const n = nCalor(uf); return n == null ? 'Aguardando coleta do INMET' : n + ' aviso(s) de calor vigente(s)'; },
    [{cor:CAL[0],rotulo:'0'},{cor:CAL[1],rotulo:'1'},{cor:CAL[2],rotulo:'2'},{cor:CAL[3],rotulo:'3+'},{cor:NEUTRA,rotulo:'aguardando coleta'}]);
  fonteFigura('boxCalor', (SINAIS.fontes && SINAIS.fontes.inmet_avisos && SINAIS.fontes.inmet_avisos.status === 'coletado') ? 'Fonte: INMET · consultado em '+esc(SINAIS.fontes.inmet_avisos.consultado_em) : 'Fonte: INMET · sem coleta até o corte');
  desenharMapa('mapaEmerg','legEmerg', uf => NEUTRA, uf => 'Nenhuma emergência sanitária registrada até o corte (fonte: DOU e diários municipais; coleta em andamento)', [{cor:NEUTRA, rotulo:'nenhuma registrada até o corte'}]);
  fonteFigura('boxEmerg', 'Fonte: DOU e diários oficiais municipais');
  (function(){ const f = SSIN.fontes || {}; const c = Object.entries(f).map(([k, v]) => (v.nome || k) + ': ' + (v.consultado_em ? 'consultado em ' + v.consultado_em : (v.status === 'reuso' ? 'reuso da página de sinais' : 'ainda não consultado')));
    const el = document.getElementById('carimboSaude'); if (el) el.textContent = 'Estado das fontes — ' + c.join(' · ') + '.'; })();

  // 4 · quadrantes DC × saúde
  const dcLoc = uf => ['NOVO','READ','VIG'].includes(((MARE[uf]||{}).status_estadual||'').toUpperCase());
  const q = {ambos:[], so_dc:[], so_saude:[], nenhum:[], nv:[]};
  UFS.forEach(uf => { const s = st(uf); if (s === 'NAO_VERIFICADO') { q.nv.push(uf); return; } const sl = ['NOVO','READ','VIG'].includes(s); const d = dcLoc(uf); (d&&sl ? q.ambos : d ? q.so_dc : sl ? q.so_saude : q.nenhum).push(uf); });
  const ROT = {ambos:'Defesa civil e saúde', so_dc:'Só defesa civil', so_saude:'Só saúde', nenhum:'Nenhum localizado', nv:'Saúde ainda não verificada'};
  document.getElementById('quadrantes').innerHTML = Object.keys(ROT).map(k => '<div style="border:1px solid var(--line); border-radius:8px; padding:10px;"><div class="map-card-h">'+ROT[k]+' · <strong>'+q[k].length+'</strong></div><div class="lista-uf" style="margin:0; font-size:13.5px; color:var(--muted);">'+(q[k].join(' · ')||'—')+'</div></div>').join('');
  fonteFigura('boxQuadrantes', 'Fonte: Monitor El Niño Brasil · corte '+esc(SUF.corte));
  // Série semanal 2026 × 2025 × 2024 (05/09/2026): soma das 27 capitais no InfoDengue — não é o total nacional.
  const SER = SSIN.serie_capitais;
  if (SER && SER.anos && Object.keys(SER.anos).length && typeof Chart !== 'undefined') {
    MonitorMapas.padraoGraficos(window.Chart);
    const semanas = Array.from({length: 52}, (_, i) => String(i + 1).padStart(2, '0'));
    const cores = {'2026': MonitorMapas.cor('argila'), '2025': MonitorMapas.cor('ambar'), '2024': MonitorMapas.cor('mineral')};
    const ds = Object.keys(SER.anos).sort().reverse().map(ano => ({label: ano, data: semanas.map(w => SER.anos[ano][w] ?? null),
      borderColor: cores[ano] || MonitorMapas.cor('sintetico'), backgroundColor: 'transparent', borderWidth: ano === '2026' ? 2.5 : 1.5, pointRadius: 0, tension: .25, spanGaps: false}));
    new Chart(document.getElementById('serieDengue'), {type: 'line', data: {labels: semanas.map(w => 'SE ' + w), datasets: ds},
      options: {animation: false, responsive: true, maintainAspectRatio: false, plugins: {legend: {display: false}},
                scales: {x: {ticks: {maxTicksLimit: 13}}, y: {title: {display: true, text: 'casos estimados · 27 capitais'}}}}});
    document.getElementById('serieDengue').setAttribute('aria-label', 'Série semanal de dengue, soma das 27 capitais, 2024 a 2026');
    MonitorMapas.legenda('legSerie', Object.keys(cores).map(a => ({cor: cores[a], rotulo: a})));
    fonteFigura('boxSerie', 'Fonte: InfoDengue (Fiocruz/FGV), soma das 27 capitais · consultado em ' + esc(SER.coletado_em) + ' · não é o total nacional');
  } else {
    fonteFigura('boxSerie', 'Fonte: InfoDengue (Fiocruz/FGV), 27 capitais · sem coleta até o corte');
  }
}
__load().catch(err => { const m = document.getElementById('subSaude'); if (m) m.insertAdjacentHTML('afterend', '<p class="note" style="color:var(--rust)">Erro ao carregar os dados: '+esc(err.message)+'</p>'); });

window.addEventListener('load', function(){ if (window.VLibras && window.VLibras.Widget) { try { new window.VLibras.Widget('https://vlibras.gov.br/app'); } catch (e) {} } });
