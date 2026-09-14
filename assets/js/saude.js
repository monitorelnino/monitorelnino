// ===== saude.html · bloco 1 (extraído em 06/09/2026, CSP sem unsafe-inline) =====
let BR_GEOJSON, SUF, SSIN, SINAIS, MARE, MSAUDE, DESF, DESF_CANAL, DESF_COMP, PAINEL_LISTA, SRAG;
let desenharComparadorSemanal = null;   // 13/09/2026 (auditoria de visualizações, consolidação): fechamento com o desenho do comparador "semanal por capitais", preenchido em __init(), chamado pelo seletor em renderDesfechos()
const UFS = ["AC","AL","AM","AP","BA","CE","DF","ES","GO","MA","MG","MS","MT","PA","PB","PE","PI","PR","RJ","RN","RO","RR","RS","SC","SE","SP","TO"];
const NOME_UF = {AC:'Acre',AL:'Alagoas',AM:'Amazonas',AP:'Amapá',BA:'Bahia',CE:'Ceará',DF:'Distrito Federal',ES:'Espírito Santo',GO:'Goiás',MA:'Maranhão',MG:'Minas Gerais',MS:'Mato Grosso do Sul',MT:'Mato Grosso',PA:'Pará',PB:'Paraíba',PE:'Pernambuco',PI:'Piauí',PR:'Paraná',RJ:'Rio de Janeiro',RN:'Rio Grande do Norte',RO:'Rondônia',RR:'Roraima',RS:'Rio Grande do Sul',SC:'Santa Catarina',SE:'Sergipe',SP:'São Paulo',TO:'Tocantins'};
const NEUTRA = MonitorMapas.cor('sem-dado');
const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const { showTip, hideTip } = MonitorMapas;

async function __load(){
  [BR_GEOJSON, SUF, SSIN, SINAIS, MARE, MSAUDE] = await Promise.all(
    ['geo_uf','saude_uf','saude_sinais','sinais_risco','indice','monitor_saude'].map(f => fetch('data/' + f + '.json').then(r => {
      if(!r.ok) throw new Error('Falha ao carregar data/' + f + '.json'); return r.json(); })));
  try { [DESF, DESF_CANAL, DESF_COMP, PAINEL_LISTA] = await Promise.all(['data/saude_desfechos/serie_painel.json','data/saude_desfechos/canal_endemico.json','data/saude_desfechos/completude.json','data/municipios_ibge_referencia.json'].map(f => fetch(f).then(r => r.ok ? r.json() : null))); } catch(e) { DESF = DESF_CANAL = DESF_COMP = PAINEL_LISTA = null; }
  // 13/09/2026 (proposta de enxugamento, Manus AI): catálogo de 20 desfechos e tabela de gatilhos
  // migraram para pesquisadores.html — "é backlog metodológico; pertence a Pesquisadores". SRAG
  // continua aqui: alimenta o gráfico 'SRAG por semana', mantido na página principal.
  try { SRAG = await fetch('data/saude_desfechos/srag_serie.json').then(r => r.ok ? r.json() : null); } catch(e) { SRAG = null; }
  __init();
  renderDesfechos();
  renderSRAG();
}

const fonteFigura = MonitorMapas.credito;

function __init(){
  document.getElementById('corteSaude').textContent = SUF.corte || '—';
  const ctx = MonitorMapas.contexto(BR_GEOJSON, 480, 460); const projection = ctx.projection;
  function desenharMapa(svgId, legendaId, corDe, rotuloDe, itens){ const svg = MonitorMapas.ufs(ctx, svgId, corDe, rotuloDe); MonitorMapas.legenda(legendaId, itens); return svg; }

  // 13/09/2026 (proposta de enxugamento, Manus AI): 'Escolha um estado' logo após o título — perfil
  // resumido usando dados já carregados (MSAUDE.ufs), sem fetch novo. Não substitui as tabelas e
  // mapas nacionais abaixo (que seguem servindo a comparação entre estados); é um atalho para quem
  // já sabe qual estado quer ver primeiro.
  (function(){
    const sel = document.getElementById('selEstadoSaude');
    if (!sel) return;
    UFS.slice().sort((a, b) => (NOME_UF[a] || a).localeCompare(NOME_UF[b] || b)).forEach(uf => {
      const o = document.createElement('option'); o.value = uf; o.textContent = (NOME_UF[uf] || uf) + ' (' + uf + ')'; sel.appendChild(o);
    });
    sel.addEventListener('change', () => renderPerfilEstado(sel.value));
  })();
  function renderPerfilEstado(uf){
    const alvo = document.getElementById('perfilEstadoSaude');
    if (!alvo) return;
    if (!uf) { alvo.hidden = true; alvo.innerHTML = ''; return; }
    const m = (MSAUDE && MSAUDE.ufs && MSAUDE.ufs[uf]) || {};
    const riscos = (m.risco_projetado || []);
    const dc = m.risco_atual || {};
    const cartaoCondicoes = '<div class="cartao"><h3 class="figura-titulo">Condições de risco projetadas</h3>'
      + (riscos.length ? '<p class="card-body">' + riscos.map(esc).join(', ') + '</p>' : '<p class="card-body u-muted">Ainda não verificado.</p>') + '</div>';
    const cartaoSinal = '<div class="cartao"><h3 class="figura-titulo">Sinal mais recente: dengue na capital</h3>'
      + (dc.dengue_capital_nivel != null ? '<p class="card-body">Nível ' + dc.dengue_capital_nivel + ' (InfoDengue), ' + esc(dc.dengue_capital || '') + ', SE ' + esc(String(dc.dengue_se || '—')) + '.</p>' : '<p class="card-body u-muted">Ainda não coletado.</p>') + '</div>';
    const cartaoCobertura = '<div class="cartao"><h3 class="figura-titulo">Cobertura do dado</h3>'
      + '<p class="card-body">Sinal de dengue: só a capital, não o estado inteiro. Documento estadual: ' + (m.verificado ? 'verificado' : 'ainda não verificado') + '.</p></div>';
    const cartaoInstitucional = '<div class="cartao"><h3 class="figura-titulo">Contexto secundário: prontidão institucional</h3>'
      + (m.prontidao != null ? '<p class="card-body">' + m.prontidao + '/100 · ' + esc(m.faixa || '—') + ' — mede documento e antecipação, não o estado de saúde da população.</p>' : '<p class="card-body u-muted">Ainda não verificado.</p>') + '</div>';
    alvo.innerHTML = '<h3 class="figura-titulo u-largura-total">' + esc(NOME_UF[uf] || uf) + '</h3>' + cartaoCondicoes + cartaoSinal + cartaoCobertura + cartaoInstitucional;
    alvo.hidden = false;
  }

  // 0 · Monitor Saúde (v0.1, Metodologia §31): prontidão = média (instrumento, antecipação); não verificada = cinza, sem número
  (function(){
    const M = (MSAUDE && MSAUDE.ufs) || {};
    const FX = {'estágio inicial': MonitorMapas.PALETA.faixas.inicial, 'em construção': MonitorMapas.PALETA.faixas.construcao, 'consolidado': MonitorMapas.PALETA.faixas.consolidado, 'avançado': MonitorMapas.PALETA.faixas.avancado, 'não verificado': MonitorMapas.PALETA.faixas.nao_verificado};
    const ST_H = {NOVO:'novo, do ciclo', READ:'readaptado', VIG:'vigente-recorrente', ELAB:'em elaboração', LAC:'não localizado', NAO_VERIFICADO:'ainda não verificado'};
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
    // 13/09/2026 (auditoria de visualizações, consolidação): #monitorBarras retirado do HTML —
    // duplicava a tabela alternativa de boxMonitor. Bloco guardado por ausência do elemento.
    const ver = UFS.filter(uf => (M[uf] || {}).verificado).sort((x, y) => (M[y].prontidao - M[x].prontidao) || x.localeCompare(y));
    const bx = document.getElementById('monitorBarras');
    if (bx) {
      bx.innerHTML = ver.length ? ver.map(uf => { const m = M[uf]; return '<div class="msb" role="group" aria-label="' + uf + ': ' + esc(m.prontidao) + '"><b>' + uf + '</b><div class="trilho"><div class="barra" style="width:' + m.prontidao + '%; background:' + FX[m.faixa] + '"></div></div><span>' + esc(m.prontidao) + '</span></div>'; }).join('')
        : '<div class="msb"><b>—</b><div class="trilho"></div><span>nenhuma UF verificada</span></div>';
      MonitorMapas.legenda('legMonitorBarras', [{cor: MonitorMapas.cor('areia'), rotulo: 'trilho 0–100'}, {cor: MonitorMapas.PALETA.faixas.avancado, rotulo: 'cor = faixa'}, {cor: MonitorMapas.PALETA.faixas.nao_verificado, rotulo: (R.nao_verificadas ?? '—') + ' UFs sem número'}]);
      fonteFigura('boxMonitorBarras', {fontes: ['Monitor El Niño Brasil', 'Monitor Saúde v0.1'], data: (MSAUDE || {}).gerado_em});
    }
    // Resposta sanitária (E17): ESPIN federal, decretos estaduais por arboviroses, créditos por portaria — contador, hoje zero de verdade
    const em = (SSIN && SSIN.emergencias) || []; const rn = document.getElementById('rsNum'); if (rn) rn.textContent = String(em.length);
    MonitorMapas.legenda('legRespostaSanitaria', [{cor: MonitorMapas.PALETA.resposta, rotulo: 'ESPIN federal: nenhuma em 2026'}, {cor: MonitorMapas.PALETA.status.ELAB, rotulo: 'decretos estaduais por arboviroses: nenhum'}, {cor: MonitorMapas.PALETA.semDado, rotulo: 'busca manual de 05/09; coleta do DOU pendente'}]);
    fonteFigura('boxRespostaSanitaria', {fontes: ['DOU (ESPIN)', 'diários estaduais'], data: '05/09/2026'});
  })();

  // 13/09/2026 (proposta de enxugamento, Manus AI): 'O que a União publicou' (8 cartões federais)
  // migrou para pesquisadores.html — documentos de referência, não narrativa principal da página.
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
  (function(){ const f = SSIN.fontes || {}; const c = Object.entries(f).map(([k, v]) => (v.nome || k) + ': ' + (v.consultado_em ? 'consultado em ' + v.consultado_em : (v.status === 'reuso' ? 'reuso da página de sinais' : 'ainda não consultado')));
    const el = document.getElementById('carimboSaude'); if (el) el.textContent = 'Estado das fontes — ' + c.join(' · ') + '.'; })();

  // 13/09/2026 (proposta de enxugamento, Manus AI): quadrante 'Defesa civil × saúde' retirado —
  // "mistura prontidão documental com risco projetado e não mede efeito na população".
  // 13/09/2026 (auditoria de visualizações, consolidação): mapa/lista de emergências só aparece
  // quando há ocorrência — o contador nacional (boxRespostaSanitaria, acima) já é a leitura
  // completa enquanto for zero; duplicar como mapa sempre cinza era redundante.
  const emergenciasResposta = (SSIN && SSIN.emergencias) || [];
  const boxEmergEl = document.getElementById('boxEmerg');
  if (boxEmergEl) boxEmergEl.hidden = emergenciasResposta.length === 0;
  desenharMapa('mapaEmerg','legEmerg', uf => NEUTRA, uf => 'Nenhuma emergência sanitária registrada até o corte (fonte: DOU e diários municipais; coleta em andamento)', [{cor:NEUTRA, rotulo:'nenhuma registrada até o corte'}]);
  fonteFigura('boxEmerg', {fontes: ['DOU', 'diários oficiais municipais'], data: '05/09/2026'});
  // Série semanal 2026 × 2025 × 2024 (05/09/2026): soma das 27 capitais no InfoDengue — não é o total nacional.
  // 13/09/2026 (consolidação): não desenha mais direto — vira a opção "semanal" do comparador único
  // em #cDesfAcum (ver renderDesfechos). Guarda o crédito e o closure de desenho.
  const SER = SSIN.serie_capitais;
  if (SER && SER.anos && Object.keys(SER.anos).length && typeof Chart !== 'undefined') {
    desenharComparadorSemanal = function(){
      MonitorMapas.padraoGraficos(window.Chart);
      const semanas = Array.from({length: 52}, (_, i) => String(i + 1).padStart(2, '0'));
      const cores = MonitorMapas.PALETA.anos;
      const ds = Object.keys(SER.anos).sort().reverse().map(ano => ({label: ano, data: semanas.map(w => SER.anos[ano][w] ?? null),
        borderColor: cores[ano] || MonitorMapas.PALETA.serie[1], backgroundColor: 'transparent', borderWidth: ano === '2026' ? 2.5 : 1.5, pointRadius: 0, tension: .25, spanGaps: false}));
      const chart = new Chart(document.getElementById('cDesfAcum'), {type: 'line', data: {labels: semanas.map(w => 'SE ' + w), datasets: ds},
        options: {animation: false, responsive: true, maintainAspectRatio: false, plugins: {legend: {display: false}},
                  scales: {x: {ticks: {maxTicksLimit: 13}}, y: {title: {display: true, text: 'casos estimados · 27 capitais'}}}}});
      MonitorMapas.legenda('legDesfAcum', Object.keys(cores).map(a => ({cor: cores[a], rotulo: a})));
      fonteFigura('boxDesfAcum', {fontes: ['InfoDengue (Fiocruz/FGV)', 'soma das 27 capitais'], data: SER.coletado_em});
      return chart;
    };
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
  MonitorMapas.legenda('legDesfSemanal', [{cor: MonitorMapas.PALETA.anos['2026'], rotulo: '2026 consolidado (últimas 4 semanas excluídas)'}, {cor: MonitorMapas.PALETA.anos['2026'], opacidade: .5, rotulo: 'faixa de nowcasting (tracejado)'}, {cor: MonitorMapas.PALETA.anos.canal, rotulo: 'mediana 2019–2025 (2024 à parte)'}, {cor: MonitorMapas.PALETA.anos.p75, rotulo: 'p75'}, {cor: MonitorMapas.PALETA.anos.p90, rotulo: 'p90'}]);
  fonteFigura('boxDesfSemanal', credito);
  // escada do acumulado — vira a opção "acum" (padrão) do comparador único em #cDesfAcum
  const acum = a => Object.values(M).reduce((s, m) => s + ((m.acumulado || {})[a] || 0), 0);
  function desenharComparadorAcum(){
    const chart = new Chart(document.getElementById('cDesfAcum'), {type: 'bar', data: {labels: ['2024', '2025', '2026 (até a última SE consolidada)'], datasets: [{data: [acum('2024'), acum('2025'), acum('2026')], backgroundColor: [MonitorMapas.PALETA.anos['2024'], MonitorMapas.PALETA.anos['2025'], MonitorMapas.PALETA.anos['2026']]}]},
      options: {animation: false, responsive: true, maintainAspectRatio: false, plugins: {legend: {display: false}}, scales: {y: {beginAtZero: true, title: {display: true, text: 'casos notificados · painel'}}}}});
    MonitorMapas.legenda('legDesfAcum', [{cor: MonitorMapas.PALETA.anos['2024'], rotulo: '2024 (ano epidêmico, fora do canal)'}, {cor: MonitorMapas.PALETA.anos['2025'], rotulo: '2025'}, {cor: MonitorMapas.PALETA.anos['2026'], rotulo: '2026 parcial'}]);
    fonteFigura('boxDesfAcum', credito);
    return chart;
  }
  // 13/09/2026 (auditoria de visualizações, consolidação): comparador único — "acumulado" (painel
  // amostral) e "semanal por capitais" (27 capitais, ex-boxSerie) alternam no mesmo #cDesfAcum em vez
  // de duas figuras fixas. Escopos diferentes (painel × capitais); por isso permanecem como opções
  // explícitas, nunca combinadas num só número.
  let __comparadorChart = null;
  function mostrarComparador(modo){
    if (__comparadorChart) { __comparadorChart.destroy(); __comparadorChart = null; }
    __comparadorChart = (modo === 'semanal' && desenharComparadorSemanal) ? desenharComparadorSemanal() : desenharComparadorAcum();
  }
  const selComparador = document.getElementById('selComparadorDengue');
  if (selComparador) selComparador.addEventListener('change', () => mostrarComparador(selComparador.value));
  mostrarComparador(selComparador ? selComparador.value : 'acum');
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


// 13/09/2026 (proposta de enxugamento, Manus AI): renderEstrutura() (catálogo de 20 desfechos e
// tabela de gatilhos, §36) migrou por completo para pesquisadores.js.


// ===== SRAG por semana, Brasil (§36; InfoGripe). Peso zero. O Monitor não atribui casos ao El Niño. =====
function renderSRAG(){
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const br = SRAG && SRAG.serie && SRAG.serie.BR;
  if (!br) {
    // 11/09/2026: sem srag_serie.json a figura ficava como moldura vazia, sem dizer nada a quem lê — o pior
    // desfecho possível. O arquivo não existe porque coletar_srag_gripe.py acusa URLError desde 09/09:
    // gitlab.procc.fiocruz.br (CSV canônico do InfoGripe) não responde nem do runner nem de um navegador no
    // Brasil (ERR_CONNECTION_TIMED_OUT). Ausência de dado passa a ser DECLARADA na própria figura.
    const cv = document.getElementById('cSRAG');
    if (cv && cv.parentElement) {
      // a lacuna vai DENTRO da mídia (como em financiamento.js), não como parágrafo ao lado:
      // o portão de figuras só admite título, legenda e crédito no cartão.
      const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
      svg.setAttribute('viewBox', '0 0 900 220'); svg.setAttribute('role', 'img');
      svg.setAttribute('aria-label', 'Série de SRAG ainda não coletada — lacuna declarada; a fonte InfoGripe não respondeu nas últimas tentativas de coleta');
      const t1 = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      t1.setAttribute('x', '450'); t1.setAttribute('y', '100'); t1.setAttribute('text-anchor', 'middle');
      t1.setAttribute('font-size', '15'); t1.setAttribute('fill', MonitorMapas.cor('muted'));
      t1.textContent = 'Série ainda não coletada — lacuna declarada';
      const t2 = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      t2.setAttribute('x', '450'); t2.setAttribute('y', '126'); t2.setAttribute('text-anchor', 'middle');
      t2.setAttribute('font-size', '12.5'); t2.setAttribute('fill', MonitorMapas.cor('muted'));
      t2.textContent = 'A fonte (InfoGripe/Fiocruz) não respondeu nas últimas tentativas de coleta.';
      svg.appendChild(t1); svg.appendChild(t2);
      cv.parentElement.replaceChild(svg, cv);
    }
    fonteFigura('boxSRAG', {fontes: ['InfoGripe (Fiocruz/FGV)'], data: null});
    return;
  }
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
  MonitorMapas.legenda('legSRAG', [{cor: MonitorMapas.PALETA.anos['2026'] || MonitorMapas.PALETA.anos.canal, rotulo: 'consolidado'}, {cor: MonitorMapas.PALETA.anos['2024'], rotulo: 'nowcasting (últimas 4 semanas)'}, {cor: MonitorMapas.PALETA.anos.canal, rotulo: 'mediana 2019–2025'}, {cor: MonitorMapas.PALETA.anos.p90, rotulo: 'p90'}]);
  fonteFigura('boxSRAG', {fontes: ['InfoGripe (Fiocruz/FGV), Sivep-Gripe'], data: SRAG.gerado_em, url: SRAG.fonte});
}
