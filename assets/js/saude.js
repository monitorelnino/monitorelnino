// ===== saude.html · bloco 1 (extraído em 06/09/2026, CSP sem unsafe-inline) =====
let BR_GEOJSON, SUF, SSIN, SINAIS, MARE, MSAUDE, DESF, DESF_CANAL, DESF_COMP, PAINEL_LISTA, SRAG;
// 14/09/2026: chikungunya — mesmos quatro arquivos do painel, com prefixo chik_ (coletar_desfechos_saude.py --doenca chikungunya).
// Nulos enquanto o coletor não rodar: o comparador e o mapa declaram lacuna, nunca preenchem.
let DESF_CHIK = null, DESF_CANAL_CHIK = null;
let SG = null;   // 14/09/2026: síndrome gripal (sg_serie.json, mesmo coletor do SRAG); nulo = lacuna declarada
let DDA = null;  // 14/09/2026: doenças diarreicas agudas (dda_serie.json, Sivep-DDA via LAI/Zenodo); nulo = lacuna declarada
const DOENCAS_DESF = {
  dengue:      {rotulo: 'dengue',      dados: () => ({serie: DESF,      canal: DESF_CANAL}),      capitais: true},
  chikungunya: {rotulo: 'chikungunya', dados: () => ({serie: DESF_CHIK, canal: DESF_CANAL_CHIK}), capitais: false}   // sem série por capitais ainda (coletar_saude.py é só dengue)
};
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
  try { [DESF_CHIK, DESF_CANAL_CHIK] = await Promise.all(['data/saude_desfechos/chik_serie_painel.json','data/saude_desfechos/chik_canal_endemico.json'].map(f => fetch(f).then(r => r.ok ? r.json() : null))); } catch(e) { DESF_CHIK = DESF_CANAL_CHIK = null; }
  // 13/09/2026 (proposta de enxugamento, Manus AI): catálogo de 20 desfechos e tabela de gatilhos
  // migraram para pesquisadores.html — "é backlog metodológico; pertence a Pesquisadores". SRAG
  // continua aqui: alimenta o gráfico 'SRAG por semana', mantido na página principal.
  try { SRAG = await fetch('data/saude_desfechos/srag_serie.json').then(r => r.ok ? r.json() : null); } catch(e) { SRAG = null; }
  try { SG = await fetch('data/saude_desfechos/sg_serie.json').then(r => r.ok ? r.json() : null); } catch(e) { SG = null; }
  try { DDA = await fetch('data/saude_desfechos/dda_serie.json').then(r => r.ok ? r.json() : null); } catch(e) { DDA = null; }
  __init();
  renderDesfechos((document.getElementById('selDoencaDesf') || {}).value || 'dengue');
  try { titulosFatoSaude(); } catch (e) {}   // 15/09/2026 (§2.10): depois de tudo carregado
  renderSRAG((document.getElementById('selIndicadorSRAG') || {}).value || 'srag');
  renderDDA();
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

  // 0 · MARÉ · Saúde (v0.3, Metodologia §31): prontidão = média (instrumento, cobertura populacional sanitária, antecipação); não verificada = cinza, sem número
  (function(){
    const M = (MSAUDE && MSAUDE.ufs) || {};
    const FX = {'estágio inicial': MonitorMapas.PALETA.faixas.inicial, 'em construção': MonitorMapas.PALETA.faixas.construcao, 'consolidado': MonitorMapas.PALETA.faixas.consolidado, 'avançado': MonitorMapas.PALETA.faixas.avancado, 'não verificado': MonitorMapas.PALETA.faixas.nao_verificado};
    const ST_H = {NOVO:'novo, do ciclo', READ:'readaptado', VIG:'vigente-recorrente', ELAB:'em elaboração', LAC:'não localizado', NAO_VERIFICADO:'ainda não verificado'};
    desenharMapa('mapaMonitor', 'legMonitor', uf => FX[(M[uf] || {}).faixa] || FX['não verificado'],
      uf => { const m = M[uf] || {}; if (!m.verificado) return '<em>ainda não verificado</em> — sem número'; const i = m.instrumento || {}, a = m.antecipacao || {};
        const c = m.cobertura || {};
        return '<em>' + esc(m.faixa) + ' · ' + esc(m.prontidao) + '</em><br>instrumento ' + esc(i.pontos) + ' (' + esc(ST_H[i.status] || i.status) + ')' + (i.data ? ' · ' + esc(i.data) : '') + '<br>cobertura sanitária ' + esc(c.pontos ?? '—') + ' (' + esc(c.planos_lidos ?? 0) + ' plano(s) lido(s) · ' + esc(c.planos_sem_leitura ?? 0) + ' sem leitura)' + '<br>antecipação ' + esc(a.pontos) + (i.temporada ? ' (edição ' + esc(i.temporada) + ')' : ''); },
      []);
    const R = (MSAUDE && MSAUDE.resumo) || {}; const pf = R.por_faixa || {};
    MonitorMapas.legenda('legMonitor', [
      ...['avançado', 'consolidado', 'em construção', 'estágio inicial'].map(f => ({cor: FX[f], rotulo: f + ' · ' + (pf[f] || 0) + ' UF' + ((pf[f] || 0) === 1 ? '' : 's')})),
      {cor: FX['não verificado'], rotulo: 'ainda não verificado · ' + (R.nao_verificadas ?? '—') + ' UFs (sem número)'}]);
    fonteFigura('boxMonitor', {fontes: ['MARÉ', 'Monitor Saúde v0.1'], data: (MSAUDE || {}).gerado_em});
    // tabela alternativa
    const tb = document.querySelector('#tblMonitor tbody');
    if (tb) tb.innerHTML = UFS.map(uf => { const m = M[uf] || {}, i = m.instrumento || {}, a = m.antecipacao || {}, r = m.risco_atual || {};
      return '<tr><td><strong>' + uf + '</strong></td><td>' + (m.verificado ? esc(m.prontidao) : '—') + '</td><td>' + esc(m.faixa || '') + '</td><td>' + esc(ST_H[i.status] || '') + (i.data ? ' · ' + esc(i.data) : '') + '</td><td>' + ((m.cobertura || {}).pontos ?? '—') + ' · ' + esc((m.cobertura || {}).planos_lidos ?? 0) + ' lido(s) / ' + esc((m.cobertura || {}).planos_sem_leitura ?? 0) + ' sem leitura</td><td>' + (a.pontos ?? '—') + (i.temporada ? ' · ' + esc(i.temporada) : '') + '</td><td>' + (r.dengue_capital_nivel ? 'nível ' + esc(r.dengue_capital_nivel) + ' (' + esc(r.dengue_capital) + ')' : '—') + '</td><td>' + esc((m.risco_projetado || []).join('; ')) + '</td></tr>'; }).join('');
    // 13/09/2026 (auditoria de visualizações, consolidação): #monitorBarras retirado do HTML —
    // duplicava a tabela alternativa de boxMonitor. Bloco guardado por ausência do elemento.
    // ---- Medidor MARÉ · Saúde (v0.2, 14/09/2026): mesma anatomia do medidor da home; alvo = média das UFs verificadas ----
    (function(){
      const MON = (typeof MSAUDE !== "undefined" && MSAUDE) || {}; const res = MON.resumo || {}; const media = res.media_das_verificadas;
      const fill = document.getElementById('gaugeSaudeFill'), nEl = document.getElementById('gaugeSaudeNum');
      if (!fill || !nEl || media == null) return;
      fill.dataset.alvo = String(media); fill.style.setProperty('--galvo', String(Math.max(media, 0.1)));
      const tr = fill.closest('.gauge-track'); if (tr) tr.setAttribute('aria-label', 'Barra de progresso: MARÉ · Saúde em ' + media.toLocaleString('pt-BR', {minimumFractionDigits: 1}) + ' de 100 (média de ' + res.verificadas + ' estados verificados)');
      const el = (id) => document.getElementById(id);
      if (el('gaugeSaudeN')) el('gaugeSaudeN').textContent = String(res.verificadas ?? '—');
      if (el('gaugeSaudeNV')) el('gaugeSaudeNV').textContent = String(res.nao_verificadas ?? '—');
      if (el('gaugeSaudeCorte')) el('gaugeSaudeCorte').textContent = (MON.corte || (typeof META !== 'undefined' && META && META.corte) || '—');
      const temRAF = (typeof requestAnimationFrame === 'function');
      const reduz = (typeof matchMedia === 'function') && matchMedia('(prefers-reduced-motion: reduce)').matches;
      const raf = temRAF ? (f) => requestAnimationFrame(() => requestAnimationFrame(f)) : (f) => setTimeout(f, 60);
      raf(() => { fill.style.width = media + '%'; });
      if (!temRAF || reduz) { nEl.textContent = media.toFixed(1).replace('.', ','); }
      else { const dur = 1400, t0 = performance.now(); const passo = (t) => { const k = Math.min(1, (t - t0) / dur); const e = 1 - Math.pow(1 - k, 3); nEl.textContent = (media * e).toFixed(1).replace('.', ','); if (k < 1) requestAnimationFrame(passo); }; requestAnimationFrame(passo); }
      try {
        const fx = MonitorMapas.PALETA.faixaDe(media); const b = document.getElementById('faixaSaude');
        if (b) b.innerHTML = 'Preparação demonstrada (saúde)<span class="gfaixa-pill" style="background:' + MonitorMapas.PALETA.faixas[fx] + '; color:' + MonitorMapas.PALETA.faixasTexto[fx] + '">' + esc(MonitorMapas.PALETA.faixaRotulo[fx]) + '</span>';
      } catch (e) {}
    })();
    const ver = UFS.filter(uf => (M[uf] || {}).verificado).sort((x, y) => (M[y].prontidao - M[x].prontidao) || x.localeCompare(y));
    const bx = document.getElementById('monitorBarras');
    if (bx) {
      bx.innerHTML = ver.length ? ver.map(uf => { const m = M[uf]; return '<div class="msb" role="group" aria-label="' + uf + ': ' + esc(m.prontidao) + '"><b>' + uf + '</b><div class="trilho"><div class="barra" style="width:' + m.prontidao + '%; --galvo:' + Math.max(m.prontidao, 0.1) + ';"></div></div><span>' + esc(m.prontidao) + '</span></div>'; }).join('')
        : '<div class="msb"><b>—</b><div class="trilho"></div><span>nenhuma UF verificada</span></div>';
      MonitorMapas.legenda('legMonitorBarras', [{cor: MonitorMapas.PALETA.trilho, rotulo: 'trilho 0–100'}, {cor: MonitorMapas.PALETA.faixas.avancado, rotulo: 'cor = posição no degradê do índice (0 → 100)'}, {cor: MonitorMapas.PALETA.faixas.nao_verificado, rotulo: (R.nao_verificadas ?? '—') + ' UFs sem número'}]);
      fonteFigura('boxMonitorBarras', {fontes: ['MARÉ', 'Monitor Saúde v0.1'], data: (MSAUDE || {}).gerado_em});
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
  fonteFigura('boxStatus', {fontes: 'MARÉ', data: SUF.corte});
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
// 14/09/2026: parametrizada por doença (pedido de Patricia). Um só código para dengue e chikungunya —
// o conjunto de dados muda, a lógica (canal endêmico, vazamento, acumulado, mapa por nível) é a mesma.
let __comparadorChart = null;
function renderDesfechos(doenca){
  doenca = (doenca && DOENCAS_DESF[doenca]) ? doenca : 'dengue';
  const cfg = DOENCAS_DESF[doenca]; const {serie: S, canal: C} = cfg.dados();
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const selComparador = document.getElementById('selComparadorDengue');
  // opção 'semanal por capitais' só existe para dengue (coletar_saude.py); para chikungunya some, e o valor cai para o painel
  if (selComparador) { const op = selComparador.querySelector('option[value="semanal"]'); if (op) op.hidden = !cfg.capitais;
    if (!cfg.capitais && selComparador.value === 'semanal') selComparador.value = 'semanal_painel'; }
  if (__comparadorChart) { if (typeof __comparadorChart.destroy === 'function') __comparadorChart.destroy(); __comparadorChart = null; }
  const svgMapa = document.getElementById('mapaDesf'); if (svgMapa) while (svgMapa.firstChild) svgMapa.removeChild(svgMapa.firstChild);
  const M = S && S.municipios; const semColeta = {fontes: ['InfoDengue (Fiocruz/FGV), ' + cfg.rotulo, 'painel amostral'], data: null};
  if (!M || !Object.keys(M).length) {
    // lacuna declarada para ESTA doença: gráfico e mapa vazios, legenda e crédito dizem que não há coleta
    const cv = document.getElementById('cDesfAcum'); if (cv && cv.getContext) { const g = cv.getContext('2d'); g && g.clearRect && g.clearRect(0, 0, cv.width, cv.height); }
    MonitorMapas.legenda('legDesfAcum', [{cor: MonitorMapas.NEUTRA, rotulo: 'série de ' + cfg.rotulo + ' ainda não coletada — lacuna declarada'}]);
    MonitorMapas.legenda('legDesfMapa', [{cor: MonitorMapas.NEUTRA, rotulo: 'sem coleta de ' + cfg.rotulo + ' até o corte'}]);
    ['boxDesfAcum','boxDesfMapa'].forEach(id => fonteFigura(id, semColeta)); return;
  }
  const credito = {fontes: ['modelo InfoDengue (Fiocruz/FGV), ' + cfg.rotulo, 'Sinan', 'painel amostral'], data: S.gerado_em};
  MonitorMapas.padraoGraficos(window.Chart);
  // 13/09/2026 (proposta de enxugamento, Manus AI): 'Casos notificados por semana' (boxDesfSemanal,
  // painel × canal endêmico) deixou de ser figura própria — vira a 3ª opção do comparador único em
  // #cDesfAcum ('Semanal · painel × canal endêmico'), ao lado de 'Acumulado' e 'Semanal por capitais'.
  function desenharComparadorPainel(){
    const semanas = Array.from({length: 53}, (_, i) => String(i + 1).padStart(2, '0'));
    const soma = {casos: {}, med: {}, p75: {}, p90: {}, nmin: {}, nmax: {}};
    Object.entries(M).forEach(([cod, m]) => { const c = (C && C.municipios && C.municipios[cod]) || {};
      semanas.forEach(ss => { const k = '2026-' + ss; const v = (m.semanas_2026 || {})[k];
        if (v && v.casos != null) soma.casos[ss] = (soma.casos[ss] || 0) + v.casos;
        if (c[ss]) { soma.med[ss] = (soma.med[ss] || 0) + c[ss].mediana; soma.p75[ss] = (soma.p75[ss] || 0) + c[ss].p75; soma.p90[ss] = (soma.p90[ss] || 0) + c[ss].p90; }
        const n = (m.nowcasting || {})[k]; if (n && n.est_min != null) { soma.nmin[ss] = (soma.nmin[ss] || 0) + n.est_min; soma.nmax[ss] = (soma.nmax[ss] || 0) + n.est_max; } }); });
    const ate = Math.max(...Object.keys(soma.casos).concat(Object.keys(soma.nmax)).map(Number)); const labels = semanas.slice(0, ate);
    const chart = new Chart(document.getElementById('cDesfAcum'), {type: 'bar', data: {labels: labels.map(w => 'SE ' + w), datasets: [
        {type: 'bar', label: '2026 (consolidado)', data: labels.map(w => soma.casos[w] ?? null), backgroundColor: MonitorMapas.PALETA.anos['2026'], order: 3},
        {type: 'line', label: 'nowcasting (máx.)', data: labels.map(w => soma.nmax[w] ?? null), borderColor: MonitorMapas.PALETA.anos['2026'], borderDash: [4, 3], borderWidth: 1, pointRadius: 0, order: 2, spanGaps: false},
        {type: 'line', label: 'nowcasting (mín.)', data: labels.map(w => soma.nmin[w] ?? null), borderColor: MonitorMapas.PALETA.anos['2026'], borderDash: [4, 3], borderWidth: 1, pointRadius: 0, order: 2, spanGaps: false},
        {type: 'line', label: 'mediana 2019–2025', data: labels.map(w => soma.med[w] ?? null), borderColor: MonitorMapas.PALETA.anos.canal, borderWidth: 2, pointRadius: 0, order: 1},
        {type: 'line', label: 'p75', data: labels.map(w => soma.p75[w] ?? null), borderColor: MonitorMapas.PALETA.anos.p75, borderWidth: 1.5, pointRadius: 0, order: 1},
        {type: 'line', label: 'p90', data: labels.map(w => soma.p90[w] ?? null), borderColor: MonitorMapas.PALETA.anos.p90, borderWidth: 1.5, pointRadius: 0, order: 1}]},
      options: {animation: false, responsive: true, maintainAspectRatio: false, plugins: {legend: {display: false}}, scales: {x: {ticks: {maxTicksLimit: 13}}, y: {beginAtZero: true, title: {display: true, text: 'casos notificados de ' + cfg.rotulo + ' · painel'}}}}});
    MonitorMapas.legenda('legDesfAcum', [{cor: MonitorMapas.PALETA.anos['2026'], rotulo: '2026 consolidado (últimas 4 semanas excluídas)'}, {cor: MonitorMapas.PALETA.anos['2026'], opacidade: .5, rotulo: 'faixa de nowcasting (tracejado)'}, {cor: MonitorMapas.PALETA.anos.canal, rotulo: 'mediana 2019–2025 (2024 à parte)'}, {cor: MonitorMapas.PALETA.anos.p75, rotulo: 'p75'}, {cor: MonitorMapas.PALETA.anos.p90, rotulo: 'p90'}]);
    fonteFigura('boxDesfAcum', credito);
    return chart;
  }
  // escada do acumulado — opção "acum" do comparador único em #cDesfAcum
  const acum = a => Object.values(M).reduce((s, m) => s + ((m.acumulado || {})[a] || 0), 0);
  function desenharComparadorAcum(){
    const chart = new Chart(document.getElementById('cDesfAcum'), {type: 'bar', data: {labels: ['2024', '2025', '2026 (até a última SE consolidada)'], datasets: [{data: [acum('2024'), acum('2025'), acum('2026')], backgroundColor: [MonitorMapas.PALETA.anos['2024'], MonitorMapas.PALETA.anos['2025'], MonitorMapas.PALETA.anos['2026']]}]},
      options: {animation: false, responsive: true, maintainAspectRatio: false, plugins: {legend: {display: false}}, scales: {y: {beginAtZero: true, title: {display: true, text: 'casos notificados de ' + cfg.rotulo + ' · painel'}}}}});
    MonitorMapas.legenda('legDesfAcum', [{cor: MonitorMapas.PALETA.anos['2024'], rotulo: '2024 (ano epidêmico, fora do canal)'}, {cor: MonitorMapas.PALETA.anos['2025'], rotulo: '2025'}, {cor: MonitorMapas.PALETA.anos['2026'], rotulo: '2026 parcial'}]);
    fonteFigura('boxDesfAcum', credito);
    return chart;
  }
  // 13/09/2026 (auditoria de visualizações, consolidação): comparador único — "acumulado" (painel
  // amostral), "semanal por capitais" (27 capitais, ex-boxSerie) e "semanal · painel × canal endêmico"
  // (ex-boxDesfSemanal) alternam no mesmo #cDesfAcum em vez de figuras fixas. Escopos diferentes
  // (painel × capitais); por isso permanecem como opções explícitas, nunca combinadas num só número.
  function mostrarComparador(modo){
    if (__comparadorChart) { if (typeof __comparadorChart.destroy === 'function') __comparadorChart.destroy(); __comparadorChart = null; }
    __comparadorChart = modo === 'semanal' && cfg.capitais && desenharComparadorSemanal ? desenharComparadorSemanal()
      : modo === 'semanal_painel' ? desenharComparadorPainel()
      : desenharComparadorAcum();
  }
  if (selComparador && !selComparador.__ligado) { selComparador.__ligado = true; selComparador.addEventListener('change', () => mostrarComparador(selComparador.value)); }
  mostrarComparador(selComparador ? selComparador.value : 'semanal_painel');
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
// seletor de doença (14/09/2026): redesenha comparador e mapa com o conjunto escolhido
(function(){
  const sel = document.getElementById('selDoencaDesf'); if (!sel) return;
  sel.addEventListener('change', () => renderDesfechos(sel.value));
})();


// 13/09/2026 (proposta de enxugamento, Manus AI): renderEstrutura() (catálogo de 20 desfechos e
// tabela de gatilhos, §36) migrou por completo para pesquisadores.js.


// ===== SRAG por semana, Brasil (§36; InfoGripe). Peso zero. O Monitor não atribui casos ao El Niño. =====
// 14/09/2026: parametrizada por indicador (SRAG | SG) — mesmo CSV do InfoGripe, mesmo desenho; sem arquivo = lacuna declarada
const __serieCharts = {};
const INDICADORES_RESP = {
  srag: {rotulo: 'SRAG', eixo: 'casos SRAG · Brasil', fonte: ['InfoGripe (Fiocruz/FGV), Sivep-Gripe'], dados: () => SRAG, motivo: 'A fonte (InfoGripe/Fiocruz) não respondeu nas últimas tentativas de coleta.', segunda: 'nowcasting (últimas 4 semanas)', chaveSegunda: 'nowcasting'},
  sg:   {rotulo: 'síndrome gripal', eixo: 'casos de síndrome gripal · Brasil', fonte: ['InfoGripe (Fiocruz/FGV)'], dados: () => SG, motivo: 'A fonte (InfoGripe/Fiocruz) não respondeu nas últimas tentativas de coleta.', segunda: 'nowcasting (últimas 4 semanas)', chaveSegunda: 'nowcasting'}
};
// 14/09/2026: DDA usa o MESMO componente e o mesmo renderizador da figura respiratória (série nacional sobre o canal
// endêmico); só mudam os textos e a segunda barra — a fonte não publica nowcasting, então as últimas 4 semanas são
// mostradas como 'parciais' (valor bruto, atraso de digitação), nunca como estimativa.
const INDICADOR_DDA = {rotulo: 'DDA', eixo: 'atendimentos de DDA em unidades sentinela · Brasil', fonte: ['Sivep-DDA (Ministério da Saúde) via LAI, depósito Zenodo (Saldanha/Fiocruz)'], dados: () => DDA,
  motivo: 'A fonte (Sivep-DDA via LAI, depósito Zenodo) não pôde ser lida nas últimas tentativas de coleta.', segunda: 'parciais (últimas 4 semanas — sem estimativa)', chaveSegunda: 'parcial'};
function renderSerieNacional(cfg, ids){
  const D = cfg.dados();
  const cv = document.getElementById(ids.canvas), svg = document.getElementById(ids.svg);
  if (__serieCharts[ids.canvas]) { if (typeof __serieCharts[ids.canvas].destroy === 'function') __serieCharts[ids.canvas].destroy(); __serieCharts[ids.canvas] = null; }
  const br = D && D.serie && D.serie.BR;
  if (!br) {
    // 11/09/2026: sem arquivo a figura ficava como moldura vazia, sem dizer nada a quem lê — o pior desfecho possível.
    // Ausência é DECLARADA na própria mídia (o portão de figuras só admite título, legenda e crédito no cartão): canvas some, SVG de lacuna aparece.
    if (cv) cv.hidden = true;
    if (svg) { svg.hidden = false; svg.setAttribute('aria-label', 'Série de ' + cfg.rotulo + ' ainda não coletada — lacuna declarada; ' + cfg.motivo);
      const t1 = document.getElementById(ids.txt1), t2 = document.getElementById(ids.txt2);
      if (t1) { t1.textContent = 'Série de ' + cfg.rotulo + ' ainda não coletada — lacuna declarada'; t1.setAttribute('fill', MonitorMapas.cor('muted')); }
      if (t2) { t2.textContent = cfg.motivo; t2.setAttribute('fill', MonitorMapas.cor('muted')); } }
    MonitorMapas.legenda(ids.leg, [{cor: MonitorMapas.NEUTRA, rotulo: 'sem coleta de ' + cfg.rotulo + ' até o corte'}]);
    ids.credito({fontes: cfg.fonte, data: null});
    return;
  }
  if (svg) svg.hidden = true; if (cv) cv.hidden = false;
  const canal = (D.canal_endemico || {}).BR || {}; const seg = (D[cfg.chaveSegunda] || {}).BR || {};
  const ano = D.ano_corrente; const semanas = Array.from({length: 53}, (_, i) => String(i + 1).padStart(2, '0'));
  const ate = Math.max(...Object.keys(br).concat(Object.keys(seg)).filter(k => k.startsWith(String(ano))).map(k => +k.split('-')[1]));
  const labels = semanas.slice(0, ate);
  MonitorMapas.padraoGraficos(window.Chart);
  __serieCharts[ids.canvas] = new Chart(cv, {data: {labels: labels.map(w => 'SE ' + w), datasets: [
      {type: 'bar', label: 'consolidado', data: labels.map(w => (br[ano + '-' + w] ?? null)), backgroundColor: MonitorMapas.PALETA.anos['2026'] || MonitorMapas.PALETA.anos.canal, order: 2},
      {type: 'bar', label: cfg.segunda, data: labels.map(w => (seg[ano + '-' + w] ?? null)), backgroundColor: MonitorMapas.PALETA.anos['2024'], order: 2},
      {type: 'line', label: 'mediana 2019–2025', data: labels.map(w => (canal[w] || {}).mediana ?? null), borderColor: MonitorMapas.PALETA.anos.canal, borderWidth: 2, pointRadius: 0, order: 1},
      {type: 'line', label: 'p90', data: labels.map(w => (canal[w] || {}).p90 ?? null), borderColor: MonitorMapas.PALETA.anos.p90, borderWidth: 1.5, pointRadius: 0, order: 1}]},
    options: {animation: false, responsive: true, maintainAspectRatio: false, plugins: {legend: {display: false}}, scales: {x: {ticks: {maxTicksLimit: 13}}, y: {beginAtZero: true, title: {display: true, text: cfg.eixo}}}}});
  MonitorMapas.legenda(ids.leg, [{cor: MonitorMapas.PALETA.anos['2026'] || MonitorMapas.PALETA.anos.canal, rotulo: 'consolidado'}, {cor: MonitorMapas.PALETA.anos['2024'], rotulo: cfg.segunda}, {cor: MonitorMapas.PALETA.anos.canal, rotulo: 'mediana 2019–2025'}, {cor: MonitorMapas.PALETA.anos.p90, rotulo: 'p90'}]);
  ids.credito({fontes: cfg.fonte, data: D.gerado_em, url: D.fonte});
}
function renderSRAG(ind){
  ind = INDICADORES_RESP[ind] ? ind : 'srag';
  renderSerieNacional(INDICADORES_RESP[ind], {credito: p => fonteFigura('boxSRAG', p), canvas: 'cSRAG', svg: 'svgSRAGLacuna', txt1: 'txtSRAGLacuna1', txt2: 'txtSRAGLacuna2', leg: 'legSRAG'});
}
function renderDDA(){
  if (!document.getElementById('boxDDA')) return;
  renderSerieNacional(INDICADOR_DDA, {credito: p => fonteFigura('boxDDA', p), canvas: 'cDDA', svg: 'svgDDALacuna', txt1: 'txtDDALacuna1', txt2: 'txtDDALacuna2', leg: 'legDDA'});
}
(function(){ const sel = document.getElementById('selIndicadorSRAG'); if (sel) sel.addEventListener('change', () => renderSRAG(sel.value)); })();

// 15/09/2026 (auditoria editorial §2.10): títulos-fato calculados dos dados já carregados — nunca digitados.
function titulosFatoSaude(){
  const titulo = (box, txt) => { const h = document.querySelector('#' + box + ' .figura-titulo'); if (h && txt) h.textContent = txt; };
  const n = v => Number(v || 0).toLocaleString('pt-BR');
  try {   // MARÉ · Saúde: estados por categoria do plano de saúde
    const UFS = Object.keys(SUF.uf || {}); const st = uf => (SUF.uf[uf] || {}).status || 'NAO_VERIFICADO';
    const c = k => UFS.filter(u => k.includes(st(u))).length;
    titulo('boxMonitor', `Saúde: ${c(['NOVO'])} estados com plano para o ciclo, ${c(['VIG','READ'])} com o de todo ano, ${c(['ELAB'])} em elaboração, ${c(['NAO_VERIFICADO'])} não verificados` + (c(['LAC']) ? `, ${c(['LAC'])} sem plano` : ''));
    titulo('boxStatus', `Plano de saúde por estado: ${c(['NOVO'])} para o ciclo, ${c(['VIG','READ'])} de todo ano, ${c(['NAO_VERIFICADO'])} não verificados`);
  } catch (e) {}
  try {   // contador de emergências sanitárias
    const em = (SSIN && SSIN.emergencias) || []; const corte = (SUF && SUF.corte) || '—';
    titulo('boxRespostaSanitaria', `Emergências sanitárias declaradas no ciclo: ${em.length}` + (em.length ? '' : ` — nenhuma localizada até ${corte}`));
  } catch (e) {}
  // dengue: municípios em alerta laranja/vermelho na última semana consolidada (nível 3 = laranja, 4 = vermelho no InfoDengue)
  const tituloDengue = () => { try {
    const doenca = (document.getElementById('selDoencaDesf') || {}).value || 'dengue'; const M = (DESF && DESF.municipios) || {};
    if (!Object.keys(M).length) return; const se = Object.values(M).map(m => m.ultima_se).filter(Boolean).sort().pop();
    const alto = Object.values(M).filter(m => m.ultima_se === se && (m.nivel_ultima_se === 3 || m.nivel_ultima_se === 4)).length;
    const rot = doenca === 'chikungunya' ? 'Chikungunya' : 'Dengue';
    titulo('boxDesfMapa', `${rot}: ${n(alto)} municípios em alerta laranja ou vermelho na semana ${String(se || '').replace('2026-', 'SE ')} de 2026 (painel amostral)`);
  } catch (e) {} };
  tituloDengue(); const sel = document.getElementById('selDoencaDesf'); if (sel && !sel.__tituloFato) { sel.__tituloFato = true; sel.addEventListener('change', () => setTimeout(tituloDengue, 50)); }
}
