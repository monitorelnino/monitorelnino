// ===== pesquisadores.html · bloco 1 (extraído em 06/09/2026, CSP sem unsafe-inline) =====
window.addEventListener('load', function(){ if (window.VLibras && window.VLibras.Widget) { try { new window.VLibras.Widget('https://vlibras.gov.br/app'); } catch (e) {} } });

// ===== pesquisadores.html · bloco 2 (extraído em 06/09/2026, CSP sem unsafe-inline) =====
let DATA, TRANSFERENCIAS, META, TABELA_MUNICIPIOS, SINAIS, CONSULTAS, MPS;
const CAMADA_ROTULO = {ciclo:'Ciclo', observado:'Observado', enos:'ENOS'};   // tabela das oito fontes (migrada de Sinais)
const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const fonteFigura = MonitorMapas.credito;

// 13/09/2026 (proposta de enxugamento, Manus AI): detalhamento completo das MPs migrou de
// financiamento.html — funções copiadas como estavam (renderMpsUf precisa do ctx do mapa
// geográfico, primeira vez que pesquisadores.html renderiza um mapa de verdade).
// ===== 1 · Onde o pagamento foi feito: valor pago por UF da unidade gestora (mps_2026.json → destino) =====
function renderMpsUf(ctx){
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const mps = (MPS && MPS.mps) || []; const por = {}; let br = 0, tot = 0;
  mps.forEach(mp => { const d = (mp.destino && mp.destino.por_uf_pago) || {}; Object.entries(d).forEach(([uf, v]) => { if (uf === 'BR') br += v; else por[uf] = (por[uf] || 0) + v; tot += v; }); });
  const brl = v => 'R$ ' + (v >= 1e6 ? (v / 1e6).toFixed(1).replace('.', ',') + ' mi' : (v / 1e3).toFixed(0) + ' mil');
  const max = Math.max(1, ...Object.values(por));
  const O4 = MonitorMapas.PALETA.ordinal4; const cor = v => v == null ? MonitorMapas.NEUTRA : (v / max > .5 ? O4[3] : v / max > .2 ? O4[2] : v / max > .05 ? O4[1] : O4[0]);
  const svgEl = document.getElementById('mapaMpsUf');
  if (svgEl) MonitorMapas.ufs(ctx, 'mapaMpsUf', uf => cor(por[uf]), uf => por[uf] != null ? '<em>' + brl(por[uf]) + '</em> pagos por unidade gestora sediada na UF' : '<em>sem pagamento por unidade gestora na UF</em>');
  MonitorMapas.legenda('legMpsUf', [{cor: O4[3], rotulo: 'acima de 50% do maior valor'}, {cor: O4[2], rotulo: '20–50%'}, {cor: O4[1], rotulo: '5–20%'}, {cor: O4[0], rotulo: 'abaixo de 5% · sem pagamento'}]);
  fonteFigura('boxMpsUf', {fontes: ['Portal da Transparência', 'execução mensal por UF da unidade gestora'], data: (MPS || {}).gerado_em});
  // 13/09/2026 (auditoria de visualizações, consolidação): BR × UFs destacado primeiro (indicador
  // compacto); o mapa acima, com a mesma informação em detalhe geográfico, vem depois na ordem do DOM.
  const brPct = document.getElementById('mpsBrPct');
  if (brPct) brPct.textContent = tot ? Math.round(100 * br / tot) + '%' : '—';
  const brDen = document.getElementById('mpsBrDen');
  if (brDen) brDen.textContent = 'do pago (' + brl(br) + ') vai para sedes nacionais (BR); ' + brl(tot - br) + ' se distribuem pelas ' + Object.keys(por).length + ' UFs com execução';
  MonitorMapas.legenda('legMpsBrUf', [{cor: MonitorMapas.cor('linha'), rotulo: 'BR: sedes nacionais'}, {cor: O4[2], rotulo: 'UFs: unidade gestora local'}]);
  fonteFigura('boxMpsBrUf', {fontes: ['Portal da Transparência', 'execução mensal'], data: (MPS || {}).gerado_em});
  const bx = document.getElementById('mpsUfBarras');
  if (bx) { const ufs = Object.entries(por).sort((a, b) => b[1] - a[1]).slice(0, 12);
    bx.innerHTML = ufs.map(([uf, v]) => '<div class="msb" role="group" aria-label="' + esc(uf) + ': ' + esc(brl(v)) + '"><b>' + esc(uf) + '</b><div class="trilho"><div class="barra" style="width:' + (100 * v / max).toFixed(1) + '%; background:' + cor(v) + '"></div></div><span>' + esc(brl(v)) + '</span></div>').join('')
      + '<div class="msb" role="group" aria-label="BR sedes nacionais: ' + esc(brl(br)) + '"><b>BR</b><div class="trilho"><div class="barra" style="width:100%; background:' + MonitorMapas.cor('linha') + '"></div></div><span>' + esc(brl(br)) + '</span></div>'; }
  MonitorMapas.legenda('legMpsUfBarras', [{cor: MonitorMapas.cor('linha'), rotulo: 'BR = sedes nacionais: ' + (tot ? Math.round(100 * br / tot) : 0) + '% do pago'}]);
  fonteFigura('boxMpsUfBarras', {fontes: ['Portal da Transparência', 'execução mensal'], data: (MPS || {}).gerado_em});
}

// ===== 0 · Rota do dinheiro das MPs (05/09/2026): barras de prazo + fluxo MP → órgão → uso =====
function renderRotaMPs(){
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const mps = (MPS && MPS.mps) || [];
  const brl = v => 'R$ ' + (v >= 1e9 ? (v/1e9).toFixed(2).replace('.', ',') + ' bi' : (v/1e6).toFixed(1).replace('.', ',') + ' mi');
  const dataBR = t => { const [d,m,a] = String(t).split('/').map(Number); return new Date(a, m-1, d); };
  const hoje = new Date(); hoje.setHours(0,0,0,0);
  // barras de prazo (publicação → deliberação)
  document.getElementById('mpsPrazos').innerHTML = mps.map(mp => {
    const ini = dataBR(mp.publicada_em), fim = dataBR(mp.tramitacao.deliberacao_ate);
    const dias = Math.round((fim - hoje) / 86400000), resta = Math.max(0, Math.min(1, (fim - hoje) / (fim - ini)));
    const espera = mp.id === 'mp1367' ? 'Se o Senado não votar até ' + esc(mp.tramitacao.deliberacao_ate) + ', a MP caduca: o empenhado fica, o restante do crédito cai.' : 'Se o Congresso não votar até ' + esc(mp.tramitacao.deliberacao_ate) + ', a MP caduca: o empenhado fica, o restante do crédito cai.';
    return `<div class="prazo-rel" role="group" aria-label="${esc(mp.numero)}">${MonitorMapas.relogio(resta, dias, {cor: dias < 0 ? null : mp.cor})}
      <div class="prazo-rel-txt"><div class="prazo-titulo">${esc(mp.numero)} — ${brl(mp.valor)} · ${esc(mp.tema)}</div>
      <div class="prazo-meta">deliberação · publicada em ${esc(mp.publicada_em)} → <strong>${esc(mp.tramitacao.deliberacao_ate)}</strong> · ${esc(mp.tramitacao.situacao)}</div>
      <div class="prazo-espera"><span class="k">O que se espera:</span> ${espera}</div></div></div>`; }).join('');
  // fluxo MP → órgão → uso (SVG, três colunas; larguras proporcionais ao valor)
  const box = document.getElementById('rotaMPs'); box.innerHTML = '';
  const W = Math.max(640, box.clientWidth || 900), colW = 200, gapX = (W - 3*colW) / 2, H = 330, pad = 14;
  const total = mps.reduce((s, m) => s + m.valor, 0), escala = (H - pad*(mps.length+1)) / total;
  const svg = d3.select(box).append('svg').attr('viewBox', `0 0 ${W} ${H}`).attr('width', '100%').attr('role', 'img')
    .attr('aria-label', 'Fluxo: MP → órgão executor → uso, larguras proporcionais ao valor');
  let y0 = pad;
  mps.forEach(mp => {
    const h = mp.valor * escala; const x0 = 0, x1 = colW + gapX, x2 = 2*(colW + gapX);
    svg.append('rect').attr('x', x0).attr('y', y0).attr('width', colW).attr('height', h).attr('rx', 6).attr('fill', mp.cor);
    svg.append('text').attr('class', 'rota-mp-rotulo').attr('x', x0 + 10).attr('y', y0 + Math.min(18, h/2 + 4)).text(mp.numero);
    svg.append('text').attr('class', 'rota-mp-valor').attr('x', x0 + 10).attr('y', y0 + Math.min(34, h/2 + 20)).text(brl(mp.valor));
    let yo = y0;
    mp.orgaos.forEach(org => {
      const ho = org.valor * escala;
      svg.append('path').attr('d', `M${x0+colW},${yo} C${x0+colW+gapX/2},${yo} ${x1-gapX/2},${yo} ${x1},${yo} L${x1},${yo+ho} C${x1-gapX/2},${yo+ho} ${x0+colW+gapX/2},${y0+ (yo-y0) + ho} ${x0+colW},${yo+ho} Z`)
        .attr('fill', mp.cor).attr('opacity', .35);
      svg.append('rect').attr('x', x1).attr('y', yo).attr('width', colW).attr('height', ho).attr('rx', 6).attr('fill', mp.cor).attr('opacity', .85);
      svg.append('text').attr('class', 'rota-mp-rotulo').attr('x', x1 + 10).attr('y', yo + Math.min(18, ho/2 + 4)).text(org.nome + ' · ' + brl(org.valor));
      // execução (barra escura dentro do órgão) — só quando coletada
      if (mp.execucao && mp.execucao.status === 'coletado' && mp.execucao.pago != null) {
        const frac = Math.max(0, Math.min(1, (org.execucao_pago ?? mp.execucao.pago) / (org.execucao_pago != null ? org.valor : mp.valor)));
        svg.append('rect').attr('x', x1).attr('y', yo).attr('width', colW * frac).attr('height', ho).attr('rx', 6).attr('fill', MonitorMapas.cor('abissal')).attr('opacity', .55);
      }
      let yu = yo;
      org.usos.forEach(u => {
        const hu = u.valor * escala;
        svg.append('path').attr('d', `M${x1+colW},${yu} C${x1+colW+gapX/2},${yu} ${x2-gapX/2},${yu} ${x2},${yu} L${x2},${yu+hu} C${x2-gapX/2},${yu+hu} ${x1+colW+gapX/2},${yu+hu} ${x1+colW},${yu+hu} Z`)
          .attr('fill', mp.cor).attr('opacity', .25);
        svg.append('rect').attr('x', x2).attr('y', yu).attr('width', colW).attr('height', hu).attr('rx', 6).attr('fill', MonitorMapas.cor('osso-claro')).attr('stroke', mp.cor);
        const linhas = u.nome.length > 34 ? [u.nome.slice(0, 34) + '…'] : [u.nome];
        svg.append('text').attr('class', 'rota-mp-rotulo').attr('x', x2 + 10).attr('y', yu + Math.min(18, hu/2 + 4)).text(linhas[0]);
        if (hu > 30) svg.append('text').attr('class', 'rota-mp-valor').attr('x', x2 + 10).attr('y', yu + Math.min(34, hu/2 + 20)).text(brl(u.valor));
        yu += hu;
      });
      yo += ho;
    });
    y0 += h + pad;
  });
  ['MP', 'Órgão executor', 'Uso declarado'].forEach((t, i) => svg.append('text').attr('class', 'rota-mp-valor').attr('x', i*(colW+gapX)).attr('y', H - 2).text(t));
  const exec = mps.map(mp => mp.execucao && mp.execucao.status === 'coletado' ? `${mp.numero}: ações reforçadas — pago ${brl(mp.execucao.pago)} de ${brl(mp.execucao.empenhado)} empenhado desde a MP (${mp.execucao.meses.join(', ')})` : `${mp.numero}: execução sem coleta até o corte`);
  MonitorMapas.legenda('legRotaMPs', [
    ...mps.map(mp => ({cor: mp.cor, rotulo: mp.numero + ' · ' + mp.tema})),
    {cor: MonitorMapas.cor('abissal'), rotulo: 'parcela paga nas ações reforçadas (inclui dotação ordinária da ação — teto, não a execução do crédito)'},
    ...exec.map(t => ({cor: MonitorMapas.cor('areia'), rotulo: t}))]);
  fonteFigura('boxRotaMPs', {fontes: ['Congresso Nacional', 'Agência Gov', 'Câmara', 'Conab', 'Portal da Transparência (execução)'], data: mps.some(mp => mp.execucao && mp.execucao.status === 'coletado') ? mps[0].execucao.atualizado_em : null});
}

async function __load(){
  [DATA, TRANSFERENCIAS, META, TABELA_MUNICIPIOS, SINAIS, CONSULTAS] = await Promise.all(['estados','transferencias','meta','municipios','sinais_risco','financiamento/consultas'].map(f => fetch('data/' + f + '.json').then(r => { if(!r.ok) throw new Error('Falha ao carregar data/' + f + '.json'); return r.json(); })));
  // 13/09/2026 (proposta de enxugamento, Manus AI): agregados do painel amostral migraram de
  // Financiamento para cá — a lista/fichas completas já viviam só em JSON; agora o resumo por
  // região × porte também tem uma leitura na página, não só o link pro arquivo cru.
  try {
    const PAINEL = await fetch('data/painel/agregados.json').then(r => r.ok ? r.json() : null);
    if (PAINEL && PAINEL.lista_publicada_em) {
      (document.getElementById('notaPainel')||{}).textContent = 'Painel de ' + PAINEL.n + ' municípios; semente ' + PAINEL.semente + ', lista publicada em ' + PAINEL.lista_publicada_em + ' (hash ' + String(PAINEL.hash_lista).slice(0,12) + '…).';
      document.getElementById('painelResumo').innerHTML = '<div class="tbl-wrap" tabindex="0" role="region" aria-label="Tabela rolável horizontalmente"><table class="mun-table"><thead><tr><th>Região × porte</th><th>Municípios</th><th>Com instrumento publicado</th><th>Ainda não verificados</th></tr></thead><tbody>'
        + (PAINEL.agregados || []).map(a => '<tr><td>' + esc(a.regiao) + ' · ' + esc(a.porte) + '</td><td>' + a.n + '</td><td>' + a.com_instrumento + '</td><td>' + a.nao_verificados + '</td></tr>').join('') + '</tbody></table></div>';
      MonitorMapas.credito('boxPainel', {fontes: ['MARÉ', 'painel amostral'], data: PAINEL.lista_publicada_em});
    } else {
      MonitorMapas.credito('boxPainel', {fontes: ['MARÉ', 'painel amostral'], data: null});
    }
  } catch(e) { MonitorMapas.credito('boxPainel', {fontes: ['MARÉ', 'painel amostral'], data: null}); }
  // 15/09/2026 (auditoria editorial, errata): o gráfico "Plano federal por área" que ficava aqui somava R$ 17,75 bi em
  // quatro áreas com valores digitados direto no JS (nunca lidos de um arquivo) — 13x o valor de TODO o plano federal
  // (R$ 1,335 bi) citado em toda a documentação do site. Sem fonte real por trás, a figura foi removida; os compromissos
  // verificados e a série semanal, com fonte por linha, estão em financiamento.html#prometeu.
document.getElementById('fontesMonitoramento').innerHTML = TRANSFERENCIAS.fontes_monitoramento
  .map(f => `<li><a href="${esc(f.url)}" target="_blank" rel="noopener">${esc(f.nome)}</a></li>`).join('');
  const ROTULO_HOST = {
  'www.diariomunicipal.com.br': 'Diários Oficiais dos Municípios (FAMUP/FEMURN/AMA/FAMEP/Sergipe)',
  'acaoinverno.recife.pe.gov.br': 'Ação Inverno · Prefeitura do Recife',
  'www.defesacivil.sc.gov.br': 'Defesa Civil de Santa Catarina',
  'defesacivil.es.gov.br': 'CEPDEC/ES — repositório estadual de planos de contingência',
  'www.gov.br': 'Portais gov.br (MIDR/SEDEC e órgãos federais)',
};
const porFonte = new Map();
TABELA_MUNICIPIOS.filter(m => m.url).forEach(m => {
  const host = new URL(m.url).hostname;
  // subcaminhos do diariomunicipal distinguem federações; demais domínios agrupam pelo host
  const chave = host === 'www.diariomunicipal.com.br' ? host + '/' + (new URL(m.url).pathname.split('/')[1] || '') : host;
  const g = porFonte.get(chave) || {host, urls: [], n: 0};
  g.urls.push(m.url); g.n++;
  porFonte.set(chave, g);
});
document.getElementById('fontesVerificadas').innerHTML =
  [...porFonte.values()]
    .map(g => {
      const nome = ROTULO_HOST[g.host] || g.host;
      const href = g.urls.sort((a,b)=>a.length-b.length)[0]; // o link mais raiz do domínio
      return {nome, href, n: g.n};
    })
    .sort((a,b)=>b.n - a.n || a.nome.localeCompare(b.nome))
    .map(f => `<li><a href="${f.href}" target="_blank" rel="noopener">${f.nome}</a> <span class="u-muted">· ${f.n} registro${f.n > 1 ? 's' : ''}</span></li>`).join('');
document.getElementById('fontesFederaisCount').textContent = document.querySelectorAll('#fontesFederais li').length;

  const CAT_LABEL_TBL = {
    plano:['Plano preventivo',MonitorMapas.PALETA.categorias.plano], plano_antigo:['Plano desatualizado',MonitorMapas.PALETA.categorias.plano_antigo],
    plano_elaboracao:['Em elaboração',MonitorMapas.PALETA.categorias.plano_elaboracao], estrutura:['Estrutura de coordenação',MonitorMapas.PALETA.categorias.estrutura], decreto:['Decreto reativo',MonitorMapas.PALETA.categorias.decreto],
    coberto_estadual:['Coberto pelo estado',MonitorMapas.PALETA.categorias.coberto_estadual], nao_el_nino:['Não é El Niño',MonitorMapas.PALETA.categorias.nao_el_nino],
    nao_localizado:['Nada localizado',MonitorMapas.PALETA.categorias.nao_localizado],
    nao_verificado:['Ainda não verificado',MonitorMapas.PALETA.categorias.nao_verificado],
  };
function renderTable(){
    const q = document.getElementById('tblSearch').value.toLowerCase();
    const cat = document.getElementById('tblCat').value;
    const rows = TABELA_MUNICIPIOS
      .filter(m => (!cat || m.categoria===cat) &&
        (!q || m.nome.toLowerCase().includes(q) || m.uf.toLowerCase().includes(q)))
      .sort((a,b)=> a.uf.localeCompare(b.uf) || a.nome.localeCompare(b.nome));
    document.getElementById('tblBody').innerHTML = rows.map(m=>{
      const [lbl,cor] = CAT_LABEL_TBL[m.categoria];
      const fonte = m.url ? `<a href="${esc(m.url)}" target="_blank" rel="noopener">${esc(m.fonte)}</a>` : esc(m.fonte);
      return `<tr><td><strong>${m.nome}</strong></td><td>${m.uf}</td>
        <td><span class="cat-pill" style="background:${cor}">${lbl}</span></td>
        <td>${m.documento}</td><td class="nowrap">${m.data}</td><td>${fonte}</td><td class="nowrap dado">${m.canal||'—'}</td></tr>`;
    }).join('');
  }
  document.getElementById('tblSearch').addEventListener('input', renderTable);
  document.getElementById('tblCat').addEventListener('change', renderTable);
  renderTable();
  
  
  (document.getElementById('munCount')||{}).textContent = TABELA_MUNICIPIOS.length;
  if (document.querySelector('#tblFontes tbody') && SINAIS && SINAIS.fontes) {
  document.querySelector('#tblFontes tbody').innerHTML = Object.entries(SINAIS.fontes).map(([id, f]) => {
    const situacao = f.status === 'coletado'
      ? '<strong>Coletada</strong> em ' + esc(f.consultado_em) + '<br><span class="note">' + esc(f.documento || '') + '</span>'
      : '<span class="note fonte-espera">Não localizamos coleta até o corte</span>';
    return '<tr><td><a href="' + esc(f.url_publica) + '" target="_blank" rel="noopener">' + esc(f.nome) + '</a><br>' +
      '<span class="note">Camada: ' + esc(CAMADA_ROTULO[f.camada]) + '</span></td><td>' + esc(f.orgao) + '</td><td>' +
      esc(f.papel) + '</td><td>' + situacao + '</td></tr>';
  }).join('');
  }
  { const fm = document.getElementById('fontesMonit'); if (fm) fm.innerHTML = (TRANSFERENCIAS.fontes_monitoramento || []).map(f => '<li><a href="' + esc(f.url) + '" target="_blank" rel="noopener">' + esc(f.nome) + '</a></li>').join(''); }
  { const cons = (CONSULTAS && CONSULTAS.consultas) || []; if (document.querySelector('#tblConsultas tbody')) {
  if (cons.length) { (document.getElementById('notaConsultas')||{}).textContent = cons.length + ' consulta(s) registrada(s).'; document.querySelector('#tblConsultas tbody').innerHTML = cons.slice(-50).map(c => '<tr><td>' + esc(c.endpoint) + '</td><td>' + esc(JSON.stringify(c.parametros)) + '</td><td>' + esc(c.data) + '</td><td>' + c.itens + '</td><td><code>' + esc(String(c.hash_resposta).slice(0,12)) + '…</code></td></tr>').join(''); }
  }
  MonitorMapas.credito('boxConsultas', {fontes: ['MARÉ', 'consultas registradas'], data: cons.length ? (META.atualizado_em || META.corte) : null}); }
  MonitorMapas.credito('boxFontesMonit', {fontes: 'as listadas', data: '25/08/2026'});
  const el = id => document.getElementById(id);
  el('pqCorte').textContent = META.corte || '—'; el('pqAtualizado').textContent = META.atualizado_em || '—';
  fetch('data/log_buscas.json').then(r => r.ok ? r.json() : null).then(l => { if (!(l && l.execucoes)) return; el('pqLog').textContent = l.execucoes.length.toLocaleString('pt-BR');
    const ult = l.execucoes.reduce((a, e) => e.data > a ? e.data : a, ''); const c = {}; l.execucoes.filter(e => e.data === ult).forEach(e => { c[e.canal] = (c[e.canal] || 0) + 1; });
    el('pqCanais').textContent = ult + ' — ' + Object.entries(c).sort((a, b) => b[1] - a[1]).map(([k, v]) => k + ' ' + v).join(' · '); });
  fetch('data/verificacao_resumo.json').then(r => r.ok ? r.json() : null).then(v => { if (!(v && v.por_uf)) return;
    document.querySelector('#tblLog tbody').innerHTML = Object.keys(v.por_uf).sort().map(uf => { const n = v.por_uf[uf]; return '<tr><td><strong>' + esc(uf) + '</strong></td><td>' + (n.nacional || 0) + '</td><td>' + (n.estadual || 0) + '</td><td>' + (n.municipal_parcial || 0) + '</td><td>' + (n.municipal_completo || 0) + '</td><td>' + (n.nao_verificado || 0) + '</td></tr>'; }).join(''); });
  fetch('data/cobertura_qd.json').then(r => r.ok ? r.json() : null).then(c => { const m = (c && c.municipios) || {}; const t = Object.values(m); el('pqCobertura').textContent = t.length ? t.filter(x => x.cobertura_qd === true).length + ' indexados · ' + t.filter(x => x.cobertura_qd === false).length + ' não indexados · ' + (5571 - t.length) + ' ainda não testados' : 'ainda não testada (a rotina preenche a partir da próxima rodada)'; });
  fetch('data/calendario/fontes_suspensas.json').then(r => r.ok ? r.json() : null).then(f => { const n = f ? Object.values(f.fontes || {}).filter(x => x.suspensa).length : 0; el('pqSuspensas').textContent = n + ' fonte(s) suspensa(s) detectada(s)'; });
  // 13/09/2026 (proposta de enxugamento, Manus AI): detalhamento completo das MPs — fetch próprio
  // de BR_GEOJSON (mapa geográfico) e MPS, independente de financiamento.js.
  try {
    const [BR_GEOJSON_MPS, MPS_DADOS] = await Promise.all(['data/geo_uf.json', 'data/financiamento/mps_2026.json'].map(f => fetch(f).then(r => r.ok ? r.json() : null)));
    if (BR_GEOJSON_MPS && MPS_DADOS && document.getElementById('boxRotaMPs')) {
      MPS = MPS_DADOS;   // renderMpsUf/renderRotaMPs (copiadas de financiamento.js) leem a MPS do módulo
      const ctx = MonitorMapas.contexto(BR_GEOJSON_MPS, 480, 460);
      renderRotaMPs();
      renderMpsUf(ctx);
    }
  } catch(e) {}
  // 13/09/2026 (proposta de enxugamento, Manus AI): 'O que a União publicou' (saúde) migrou de
  // saude.html — documentos de referência, não sinal de saúde observado na população. Renderização
  // completa (órgão, data, status, nota, link) — o original só mostrava o título.
  try {
    const SFED = await fetch('data/saude_federal.json').then(r => r.ok ? r.json() : null);
    const alvo = document.getElementById('cartoesFederalSaude');
    if (SFED && alvo) {
      const STATUS_FED = {localizado: 'localizado', anunciado_nao_localizado: 'anunciado, não localizado até o corte'};
      alvo.innerHTML = (SFED.cartoes || []).map(c => '<div class="cartao"><h3 class="figura-titulo">' + esc(c.titulo) + '</h3>'
        + '<p class="figura-sub">' + esc(c.orgao || '—') + (c.data ? ' · ' + esc(c.data) : '') + '</p>'
        + '<p class="card-body">' + esc(c.nota || '') + '</p>'
        + '<p class="note">' + esc(STATUS_FED[c.status] || c.status || '—') + '</p>'
        + (c.url ? '<div class="card-link"><a href="' + esc(c.url) + '" target="_blank" rel="noopener">Ver fonte oficial →</a></div>' : '')
        + '</div>').join('');
    }
  } catch(e) {}
  // 13/09/2026 (proposta de enxugamento, Manus AI): catálogo de 20 desfechos e tabela de gatilhos
  // migraram de saude.html — "é backlog metodológico; pertence a Pesquisadores". Código adaptado
  // de renderEstrutura() (removida de assets/js/saude.js), com fetch próprio.
  try {
    const [CATALOGO, GATILHOS, RESP_NAC] = await Promise.all(['data/saude_desfechos/catalogo.json','data/saude_desfechos/gatilhos.json','data/resposta/por_uf.json'].map(f => fetch(f).then(r => r.ok ? r.json() : null)));
    const ROT = {coletado: 'coletado', candidato: 'candidato (fonte aberta identificada)', 'sem fonte aberta identificada': 'sem fonte aberta'};
    const COR = {coletado: MonitorMapas.PALETA.coleta.coletado, candidato: MonitorMapas.PALETA.coleta.candidato, 'sem fonte aberta identificada': MonitorMapas.PALETA.coleta.sem_fonte};
    const tb = document.querySelector('#tblCatalogo tbody');
    if (tb && CATALOGO && CATALOGO.desfechos) {
      tb.innerHTML = CATALOGO.desfechos.map(d => '<tr><td><strong>' + esc(d.nome) + '</strong></td><td>' + esc(d.comprometimento) + '</td><td>' + esc(d.sistema) + '</td><td>' + esc(d.fonte_aberta) + '</td><td><span style="display:inline-block;width:9px;height:9px;border-radius:50%;background:' + COR[d.status_coleta] + ';margin-right:6px;"></span>' + esc(ROT[d.status_coleta] || d.status_coleta) + '</td></tr>').join('');
      const n = {}; CATALOGO.desfechos.forEach(d => { n[d.status_coleta] = (n[d.status_coleta] || 0) + 1; });
      MonitorMapas.legenda('legCatalogo', Object.keys(COR).map(k => ({cor: COR[k], rotulo: (ROT[k] || k) + ': ' + (n[k] || 0)})));
      const nCol = document.getElementById('nDesfechosColetados'); if (nCol) nCol.textContent = String(n.coletado || 0);
      MonitorMapas.credito('boxCatalogo', {fontes: ['MS/SVSA, Plano de Contingência por Seca e Estiagem (2026), Quadro 2'], data: (CATALOGO.fonte || {}).lido_em || null, url: (CATALOGO.fonte || {}).url});
    } else MonitorMapas.credito('boxCatalogo', {fontes: ['MS/SVSA'], data: null});
    const tg = document.querySelector('#tblGatilhos tbody');
    if (tg && GATILHOS && GATILHOS.gatilhos) {
      const N = RESP_NAC && RESP_NAC.nacional; const pct = N ? (100 * N.fracao_municipios).toFixed(1).replace('.', ',') + '% dos municípios sob decreto (todas as causas) · limiar 8%' : null;
      const valor = g => g.id === 'eme_decretos' && pct ? pct : g.id === 'cri_decretos' && N ? 'por região e causa: sem coleta · limiar 50%' : g.status_monitor === 'computavel_parcial' ? 'parcial — ' + esc(g.nota) : g.status_monitor === 'leitura_humana' ? 'leitura humana — ' + esc(g.nota) : g.status_monitor === 'nao_publico' ? 'não público (só por LAI)' : 'sem coleta' + (g.nota ? ' — ' + esc(g.nota) : '');
      const ORD = {computavel: 0, computavel_parcial: 1, leitura_humana: 2, sem_coleta: 3, nao_publico: 4};
      tg.innerHTML = GATILHOS.gatilhos.slice().sort((a, b) => ORD[a.status_monitor] - ORD[b.status_monitor]).map(g => '<tr><td>' + esc(g.estagio) + '</td><td>' + esc(g.texto) + '</td><td>' + esc(g.fonte_oficial) + '</td><td>' + valor(g) + '</td></tr>').join('');
      const c = {}; GATILHOS.gatilhos.forEach(g => { c[g.status_monitor] = (c[g.status_monitor] || 0) + 1; });
      MonitorMapas.legenda('legGatilhos', [{cor: MonitorMapas.PALETA.coleta.coletado, rotulo: 'computável agora: ' + (c.computavel || 0)}, {cor: MonitorMapas.PALETA.coleta.candidato, rotulo: 'parcial: ' + (c.computavel_parcial || 0)}, {cor: MonitorMapas.PALETA.enso.la_nina, rotulo: 'leitura humana: ' + (c.leitura_humana || 0)}, {cor: MonitorMapas.PALETA.coleta.sem_fonte, rotulo: 'sem coleta / não público: ' + ((c.sem_coleta || 0) + (c.nao_publico || 0))}]);
      MonitorMapas.credito('boxGatilhos', {fontes: ['MS/SVSA, Plano de Contingência por Seca e Estiagem (2026), Quadro 5', 'valores do Monitor no corte'], data: (GATILHOS.fonte || {}).lido_em || null, url: (GATILHOS.fonte || {}).url});
    } else MonitorMapas.credito('boxGatilhos', {fontes: ['MS/SVSA'], data: null});
  } catch(e) {}
}
__load().catch(err => { document.body.insertAdjacentHTML('afterbegin', '<div class="erro-carga">Erro ao carregar os dados: ' + err.message + '</div>'); });

// ===== pesquisadores.html · bloco 3 (extraído em 06/09/2026, CSP sem unsafe-inline) =====
window.addEventListener('load', function(){ if (window.VLibras && window.VLibras.Widget) { try { new window.VLibras.Widget('https://vlibras.gov.br/app'); } catch (e) {} } });

// 14/09/2026 (auditoria editorial §1.4 / Anexo A #17): áreas temáticas COBRADE dos planos estaduais — saiu da face de
// Defesa civil e vive aqui como tabela de prova. (Observação registrada: a lista de UFs por área é constante no código,
// não dado em data/ — candidata a migrar para o registro estadual.)
(function(){
  const tb = document.getElementById('tblAreas'); if (!tb) return;
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const AREAS = [
  {label:'Grupo Seca (COBRADE 1.4.1): estiagem, seca e segurança hídrica', cor:MonitorMapas.PALETA.risco.seca, ufs:['AC','AL','AM','AP','BA','CE','DF','GO','PA','PE','PI','SE']},
  {label:'Grupo Seca · frente de incêndio florestal (1.4.1.3)', cor:MonitorMapas.PALETA.risco.fogo, ufs:['BA','GO','MA','MS','MT','RO','RR','TO']},
  {label:'Família das chuvas (1.2-1.3): chuvas intensas e enchentes', cor:MonitorMapas.PALETA.risco.chuvas, ufs:['ES','MG','PR','RJ','RS','SP']},
  {label:'Multirrisco integrado', cor:MonitorMapas.PALETA.risco.multi, ufs:['SC']},
];
  tb.querySelector('tbody').innerHTML = AREAS.map(a => `<tr><td>${esc(a.label)}</td><td>${a.ufs.length}</td><td>${esc(a.ufs.join(', '))}</td></tr>`).join('');
  MonitorMapas.credito('boxAreas', {fontes: ['MARÉ', 'classificação COBRADE'], data: (typeof META !== 'undefined' && META && (META.atualizado_em || META.corte)) || null});
})();


// 15/09/2026 (auditoria editorial, errata): a lista de portais das Defesas Civis estava digitada à mão aqui e
// desatualizada desde a correção de 15/09 em proteja-se.html — faltavam AC, AM, MS, PA, PB e SP, e RJ apontava
// para uma URL antiga. Passa a ler data/contatos_uf.json, a mesma fonte de "Quem chamar no seu estado" — nunca
// mais duas listas divergentes do mesmo diretório oficial.
(function(){
  const lista = document.getElementById('portaisDCLista'), hint = document.getElementById('portaisDCHint'); if (!lista) return;
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  fetch('data/contatos_uf.json').then(r => r.ok ? r.json() : null).then(D => {
    if (!D || !D.uf) { hint.textContent = 'Lista não carregada.'; return; }
    const ufs = Object.keys(D.uf).sort();
    const comPortal = ufs.filter(uf => D.uf[uf].portal);
    const semPortal = ufs.filter(uf => !D.uf[uf].portal);
    hint.innerHTML = 'Conforme o diretório oficial do MIDR' + (D.fonte && D.fonte.atualizado_pelo_orgao_em ? ', atualizado pelo órgão em ' + esc(D.fonte.atualizado_pelo_orgao_em) : '') + '. ' + (semPortal.length ? 'Estados sem portal listado no diretório: ' + esc(semPortal.join(', ')) + '.' : 'Todos os 27 estados têm portal listado no diretório.');
    lista.innerHTML = comPortal.map(uf => '<a href="' + esc(D.uf[uf].portal) + '" target="_blank" rel="noopener">' + uf + '</a>').join(' · ');
  }).catch(() => { hint.textContent = 'Lista não carregada.'; });
})();
