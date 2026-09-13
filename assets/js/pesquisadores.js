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
    const espera = mp.id === 'mp1367' ? 'Se o Senado não votar até ' + esc(mp.tramitacao.deliberacao_ate) + ', a MP caduca: o empenhado fica, o restante do crédito cai.' : 'Se o Congresso não votar até ' + esc(mp.tramitacao.deliberacao_ate) + ', a MP caduca — e a maior parte do crédito ainda não foi empenhada.';
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
      MonitorMapas.credito('boxPainel', {fontes: ['Monitor El Niño Brasil', 'painel amostral'], data: PAINEL.lista_publicada_em});
    } else {
      MonitorMapas.credito('boxPainel', {fontes: ['Monitor El Niño Brasil', 'painel amostral'], data: null});
    }
  } catch(e) { MonitorMapas.credito('boxPainel', {fontes: ['Monitor El Niño Brasil', 'painel amostral'], data: null}); }
  // 13/09/2026 (proposta de enxugamento, Manus AI): 'Compromissos federais' migrou de
  // financiamento.html — apêndice metodológico, não narrativa principal de rotas.
  try {
    const brl = v => (v == null) ? '—' : 'R$ ' + Number(v).toLocaleString('pt-BR', {maximumFractionDigits: 0});
    const [ROTAS_FIN, COMP] = await Promise.all(['data/financiamento/rotas.json', 'data/financiamento/compromissos_federais.json'].map(f => fetch(f).then(r => r.ok ? r.json() : null)));
    if (COMP) {
      document.querySelector('#tblCompromissos tbody').innerHTML = (COMP.itens || []).map(c => '<tr><td>' + esc(c.nome) + '</td><td>' + esc(c.esfera || '—') + '</td><td>' + esc(c.instrumento || '—') + (c.fonte ? ' <a href="' + esc(c.fonte) + '" target="_blank" rel="noopener">fonte</a>' : '') + '</td><td>' + brl(c.valor_total) + '</td><td>' + esc(((ROTAS_FIN && ROTAS_FIN.rotas || []).find(r => r.id === c.rota) || {}).nome || c.rota) + '</td><td>' + esc((c.execucao || {}).status === 'aguardando_coleta' ? 'aguardando coleta' : (c.execucao || {}).status || '—') + '</td></tr>').join('');
      MonitorMapas.credito('boxCompromissos', {fontes: ['as citadas em cada linha', 'Portal da Transparência (execução)'], data: (ROTAS_FIN && ROTAS_FIN.corte) || null});
    }
    const financeData = [
      {label:'Segurança Hídrica', value:14217500000},
      {label:'Saúde', value:1335000000},
      {label:'Segurança Alimentar', value:1335000000},
      {label:'Incêndios Florestais', value:858000000},
    ];
    new Chart(document.getElementById('chartFinance'), {
      type:'bar',
      data:{ labels: financeData.map(d=>d.label),
        datasets:[{ data: financeData.map(d=>d.value),
          backgroundColor: financeData.map(d => /h[íi]dric/i.test(d.label) ? MonitorMapas.PALETA.temas.hidrico
            : /inc[êe]ndi|fogo|queimad/i.test(d.label) ? MonitorMapas.PALETA.temas.fogo
            : /aliment|agr[íi]cola|safra/i.test(d.label) ? MonitorMapas.PALETA.temas.alimentar
            : /sa[úu]de/i.test(d.label) ? MonitorMapas.PALETA.temas.saude : MonitorMapas.PALETA.temas.outro),
          borderRadius:4 }] },
      options:{ indexAxis:'y', maintainAspectRatio:false, plugins:{ legend:{display:false} },
        scales:{ x:{ grid:{color:MonitorMapas.cor('areia')}, ticks:{ callback:v => 'R$ '+(v/1e9).toFixed(1)+'bi' } }, y:{ grid:{display:false} } } }
    });
    MonitorMapas.credito('boxFinance', {fontes: ['Plano federal El Niño 2026/2027', 'valores anunciados'], data: (ROTAS_FIN && ROTAS_FIN.corte) || null});
  } catch(e) {}
  // 13/09/2026 (proposta de enxugamento, Manus AI): 'Brasil, por semana' migrou de
  // financiamento.html — monitoramento temporal de execução, não explicação de rota.
  try {
    const [ROTAS_SER, SERIE] = await Promise.all(['data/financiamento/rotas.json', 'data/financiamento/serie_nacional.json'].map(f => fetch(f).then(r => r.ok ? r.json() : null)));
    if (ROTAS_SER && SERIE) {
      const svg = d3.select('#svgSerie'), W = 900, H = 260, m = {t: 16, r: 16, b: 34, l: 60};
      const x = d3.scaleTime().domain([new Date(2026,0,1), new Date(2026,11,31)]).range([m.l, W - m.r]);
      const d0 = new Date(SERIE.defeso.inicio + 'T00:00:00'), d1 = new Date(SERIE.defeso.fim + 'T00:00:00');
      svg.append('rect').attr('x', x(d0)).attr('y', m.t).attr('width', x(d1) - x(d0)).attr('height', H - m.t - m.b).attr('fill', MonitorMapas.PALETA.defeso).attr('fill-opacity', .13);
      svg.append('text').attr('x', (x(d0) + x(d1)) / 2).attr('y', m.t + 16).attr('text-anchor','middle').attr('font-size', 12).attr('fill', MonitorMapas.PALETA.defeso)
        .attr('font-family', "'Archivo Narrow', Arial, sans-serif").text('Período eleitoral 04/07–25/10: voluntárias suspensas por lei (art. 73, VI, a) — não é inação');
      const semanas = SERIE.semanas || [];
      if (!semanas.length) {
        svg.append('text').attr('x', W/2).attr('y', H/2 + 8).attr('text-anchor','middle').attr('font-size', 14).attr('fill', MonitorMapas.cor('muted')).text('Série ainda não coletada — lacuna declarada');
      } else {
        const y = d3.scaleLinear().domain([0, d3.max(semanas, s => ROTAS_SER.rotas.reduce((a, r) => a + (s[r.id] || 0), 0))]).nice().range([H - m.b, m.t]);
        const pilha = d3.stack().keys(ROTAS_SER.rotas.map(r => r.id))(semanas.map(s => Object.assign({}, s)));
        svg.selectAll('g.rota').data(pilha).join('g').attr('fill', d => ROTAS_SER.rotas.find(r => r.id === d.key).cor)
          .selectAll('rect').data(d => d).join('rect').attr('x', d => x(new Date(d.data.semana))).attr('width', 10)
          .attr('y', d => y(d[1])).attr('height', d => y(d[0]) - y(d[1]));
        svg.append('g').attr('transform', 'translate(' + m.l + ',0)').call(d3.axisLeft(y).ticks(5).tickFormat(v => 'R$ ' + (v/1e6).toFixed(0) + ' mi'));
      }
      svg.append('g').attr('transform', 'translate(0,' + (H - m.b) + ')').call(d3.axisBottom(x).ticks(d3.timeMonth.every(1)).tickFormat(d3.timeFormat('%b')));
      MonitorMapas.legenda('legSerie', ROTAS_SER.rotas.map(r => ({cor: r.cor, rotulo: r.n + ' · ' + r.nome})).concat([{cor: MonitorMapas.PALETA.defeso, opacidade: .35, rotulo: 'faixa do defeso'}]));
      MonitorMapas.credito('boxSerie', {fontes: 'TransfereGov — Dados Abertos', data: semanas.length ? (SERIE.carga_da_fonte || SERIE.corte) : null});
    }
  } catch(e) {}
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
  MonitorMapas.credito('boxConsultas', {fontes: ['Monitor El Niño Brasil', 'consultas registradas'], data: cons.length ? (META.atualizado_em || META.corte) : null}); }
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
}
__load().catch(err => { document.body.insertAdjacentHTML('afterbegin', '<div class="erro-carga">Erro ao carregar os dados: ' + err.message + '</div>'); });

// ===== pesquisadores.html · bloco 3 (extraído em 06/09/2026, CSP sem unsafe-inline) =====
window.addEventListener('load', function(){ if (window.VLibras && window.VLibras.Widget) { try { new window.VLibras.Widget('https://vlibras.gov.br/app'); } catch (e) {} } });
