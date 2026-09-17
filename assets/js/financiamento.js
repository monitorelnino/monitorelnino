// ===== financiamento.html · bloco 1 (extraído em 06/09/2026, CSP sem unsafe-inline) =====
let BR_GEOJSON, ROTAS, PORUF, EMENDAS, CONSULTAS, TRANSF, ATOS, POP, MPS, CONTADORES, RESP_FIN = null;

// ===== 3b · Contadores por estado (v3.1 §11; redesenhado 13/09/2026 — auditoria de visualizações) =====
function renderContadores(){
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const C = (CONTADORES && CONTADORES.uf) || {}; if (!document.getElementById('mapaContadores')) return;   // 15/09/2026: figura retirada (pedido da editoria)
  const brl = v => v == null ? 'sem coleta' : 'R$ ' + v.toFixed(2).replace('.', ',');
  const ufsComR5 = Object.keys(C).filter(uf => (C[uf].por_habitante_2026 || {}).r5 != null);
  const r5 = uf => ((C[uf] || {}).por_habitante_2026 || {}).r5;
  const maxR5 = Math.max(1, ...ufsComR5.map(uf => r5(uf)));
  const escala = d3.scaleLinear().domain([0, maxR5]).range(MonitorMapas.PALETA.rampaPreparo);
  const ctx = MonitorMapas.contexto(BR_GEOJSON, 480, 460);
  MonitorMapas.ufs(ctx, 'mapaContadores', uf => r5(uf) == null ? MonitorMapas.NEUTRA : escala(r5(uf)), uf => r5(uf) == null ? 'sem coleta' : esc(brl(r5(uf))) + ' por habitante · rota 5 (voluntárias)');
  MonitorMapas.siglas(ctx, d3.select('#mapaContadores'));
  MonitorMapas.legenda('legContadores', [{cor: MonitorMapas.PALETA.rampaPreparo[0], rotulo: 'R$ 0/hab.'}, {cor: MonitorMapas.PALETA.rampaPreparo[1], rotulo: 'R$ ' + maxR5.toFixed(2).replace('.', ',') + '/hab. (máximo)'}, {cor: MonitorMapas.PALETA.semDado, rotulo: 'sem coleta'}]);
  fonteFigura('boxContadores', {fontes: ['TransfereGov (r5)', 'Censo 2022'], data: (CONTADORES || {}).gerado_em});
  // resumo de cobertura das métricas planejadas com dado pontual (não viram coluna — ver hint do painel)
  const preventivo = Object.entries(C).filter(([, c]) => (c.municipios_cobertos || {}).preventivo != null);
  const notaEl = document.getElementById('notaContadoresCobertura');
  if (notaEl) {
    let partes = [esc(ufsComR5.length) + ' de 27 UFs com R$/hab. de rota 5 coletado.'];
    if (preventivo.length) {
      partes.push(preventivo.map(([uf, c]) => {
        const m = c.municipios_cobertos;
        return esc(uf) + ': ' + esc(m.preventivo) + ' município(s) com recurso preventivo' + (m.preventivo_valor ? ' (R$ ' + esc((m.preventivo_valor / 1e6).toFixed(1).replace('.', ',')) + ' mi)' : '');
      }).join(' · '));
    } else {
      partes.push('Municípios com recurso preventivo: sem coleta em nenhuma UF até o corte.');
    }
    partes.push('Municípios com recurso de resposta, razão depois/antes e represado: métricas planejadas, ainda sem fonte aberta com cobertura — não entram como coluna para não sugerir uma tabela majoritariamente vazia.');
    notaEl.innerHTML = partes.join(' ');
  }
}

// 13/09/2026 (proposta de enxugamento, Manus AI): detalhamento completo das MPs (fluxo MP → órgão →
// uso, BR × UFs, mapa geográfico) migrou para pesquisadores.html — "na página principal, no máximo
// um aviso curto quando a MP alterar uma rota". renderMpsUf/renderRotaMPs viraram esta nota curta.
function renderNotaMPs(){
  const mps = (MPS && MPS.mps) || [];
  const brl = v => 'R$ ' + (v >= 1e9 ? (v/1e9).toFixed(2).replace('.', ',') + ' bi' : (v/1e6).toFixed(1).replace('.', ',') + ' mi');
  const el = document.getElementById('notaMPs');
  if (!el) return;
  if (!mps.length) { el.textContent = 'MP 1.367 (incêndios) e MP 1.384 (alimentos): sem coleta até o corte.'; return; }
  el.innerHTML = mps.map(mp => '<strong>' + mp.numero + '</strong> (' + mp.tema + ', ' + brl(mp.valor) + ')'
    + (mp.execucao && mp.execucao.status === 'coletado' ? ': ' + brl(mp.execucao.pago) + ' pagos até ' + esc(mp.execucao.atualizado_em) : ': execução sem coleta até o corte')).join(' · ')
    + '. Detalhamento completo (fluxo por órgão, execução por UF) em <a href="pesquisadores.html#mps-federais">Pesquisadores</a>.';
}

const UFS = ["AC","AL","AM","AP","BA","CE","DF","ES","GO","MA","MG","MS","MT","PA","PB","PE","PI","PR","RJ","RN","RO","RR","RS","SC","SE","SP","TO"];
const NEUTRA = MonitorMapas.cor('sem-dado');
const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const brl = v => (v == null) ? '—' : 'R$ ' + Number(v).toLocaleString('pt-BR', {maximumFractionDigits: 0});
const { showTip, hideTip } = MonitorMapas;
const fonteFigura = MonitorMapas.credito;
// Regra estrutural (portão): soma de PREPARAÇÃO só com rotas ex_ante; resposta (r3/r4) nunca entra.
function somaPreparacao(valoresPorRota){
  return ROTAS.rotas.filter(r => r.ex_ante).reduce((s, r) => s + (Number(valoresPorRota[r.id]) || 0), 0);
}
async function __load(){
  const carregar = f => fetch(f).then(r => { if(!r.ok) throw new Error('Falha ao carregar ' + f); return r.json(); });
  [BR_GEOJSON, ROTAS, PORUF, EMENDAS, CONSULTAS, TRANSF, ATOS, POP, MPS, CONTADORES] = await Promise.all([
    'data/geo_uf.json','data/financiamento/rotas.json','data/financiamento/por_uf.json',
    'data/financiamento/emendas.json','data/financiamento/consultas.json','data/transferencias.json',
    'data/atos_resposta.json','data/populacao_censo2022.json','data/financiamento/mps_2026.json','data/financiamento/contadores_uf.json'].map(carregar));
  try { RESP_FIN = await fetch('data/resposta/por_uf.json').then(r => r.ok ? r.json() : null); } catch (e) { RESP_FIN = null; }
  // Cor das rotas e das MPs vem da paleta semântica única (assets/mapas.js), não do JSON:
  // o dado carrega a ordem e a chave; a cor é decisão de design e vale igual em todas as figuras.
  (ROTAS.rotas || []).forEach(r => { r.cor = MonitorMapas.PALETA.rotas[r.id] || r.cor; });
  renderContadores();
  renderNotaMPs();
  __init();
}
function __init(){
  MonitorMapas.padraoGraficos(window.Chart);
  document.getElementById('corteFin').textContent = ROTAS.corte || '—';
  // 16/09/2026 (handover da voz, D3): o mapa por município do fogo ainda não tem coleta — a frase diz
  // "sem coleta até {corte}" com a data real, em vez de um traço solto no meio do texto.
  { const e = document.getElementById('notaFogoCorte'); if (e) e.textContent = ROTAS.corte || 'o corte'; }
  const ctx = MonitorMapas.contexto(BR_GEOJSON, 480, 460); const projection = ctx.projection;
  function desenharMapa(svgId, legendaId, corDe, rotuloDe, itens){ const svg = MonitorMapas.ufs(ctx, svgId, corDe, rotuloDe); MonitorMapas.legenda(legendaId, itens); return svg; }
  // 1 · rede do dinheiro (decisão de design de 03/09/2026: rede em vez de cartões; cartões ficam em texto dobrável)
  (function(){
    const svg = d3.select('#redeRotas'), W = 960, H = 420;
    const ORIG = [{id: 'uniao', nome: 'União', y: 130}, {id: 'estado', nome: 'Estado', y: 310}];
    const rotas = ROTAS.rotas; const passo = (H - 40) / rotas.length;
    const nos = rotas.map((r, i) => ({...r, x: 480, y: 30 + passo * i + passo / 2}));
    const destino = {id: 'mun', nome: 'Município', x: 880, y: H / 2};
    const arestas = [];
    // Três níveis (03/09/2026): a União alcança o ESTADO pelas mesmas rotas (FPE, fundo a fundo
    // estadual, defesa civil, emergência setorial, convênios, especiais); o estado alimenta a
    // rota estadual e repassa cotas ao município. Aresta União→Estado desenhada como ramo curto
    // na cor da rota, para cima do nó do estado.
    rotas.forEach(r => {
      if (r.id === 'rE') { arestas.push({de: 'estado', para: r.id}); }
      else { arestas.push({de: 'uniao', para: r.id}); if (r.alcanca_estado) arestas.push({de: 'uniao', para: 'estado', rota: r.id, via: true}); }
      arestas.push({de: r.id, para: 'mun'});
    });
    const pos = id => id === 'mun' ? destino : (ORIG.find(o => o.id === id) ? {x: 100, y: ORIG.find(o => o.id === id).y} : nos.find(n => n.id === id));
    const dash = r => r.chave === 'decreto' ? '8,5' : r.chave === 'discricionária' ? '2,4' : r.chave === 'direta' ? '1,0' : null;
    const curva = (p, q) => `M${p.x},${p.y} C${(p.x + q.x) / 2},${p.y} ${(p.x + q.x) / 2},${q.y} ${q.x},${q.y}`;
    const gA = svg.append('g').attr('class', 'arestas');
    arestas.forEach(a => {
      const r = rotas.find(x => x.id === (a.rota || (a.de.startsWith('r') ? a.de : a.para))); const p = pos(a.de), q = pos(a.para);
      if (a.via) { // União → Estado: feixe curto e discreto entre os dois nós de origem
        const i = rotas.indexOf(r); const x = 100 - 48 + i * 14;
        gA.append('path').attr('d', `M${x},${p.y + 22} L${x},${q.y - 22}`).attr('fill', 'none').attr('stroke', r.cor).attr('stroke-width', 2.5).attr('stroke-opacity', .7).attr('stroke-dasharray', dash(r)).attr('class', 'aresta via ' + r.id);
        return;
      }
      gA.append('path').attr('d', curva({x: p.x + 88, y: p.y}, {x: q.x - 70, y: q.y})).attr('fill', 'none').attr('stroke', r.cor)
        .attr('stroke-width', r.chave === 'direta' ? 5 : 3).attr('stroke-opacity', r.ex_ante ? .75 : .9).attr('stroke-dasharray', dash(r))
        .attr('class', 'aresta ' + r.id);
      if (r.chave === 'direta') gA.append('path').attr('d', curva({x: p.x + 88, y: p.y}, {x: q.x - 70, y: q.y})).attr('fill', 'none').attr('stroke', MonitorMapas.cor('branco')).attr('stroke-width', 1.5);
    });
    const no = (g, n, w, h, cor, texto, sub) => {
      g.append('rect').attr('x', n.x - w / 2).attr('y', n.y - h / 2).attr('width', w).attr('height', h).attr('rx', 8).attr('fill', cor).attr('stroke', MonitorMapas.cor('branco')).attr('stroke-width', 1.2);
      g.append('text').attr('x', n.x).attr('y', n.y - (sub ? 5 : 0)).attr('text-anchor', 'middle').attr('dominant-baseline', 'middle').attr('fill', MonitorMapas.cor('branco'))
        .attr('font-family', "'Archivo', Arial, sans-serif").attr('font-size', 12).attr('font-weight', 600).text(texto);
      if (sub) g.append('text').attr('x', n.x).attr('y', n.y + 11).attr('text-anchor', 'middle').attr('dominant-baseline', 'middle').attr('fill', MonitorMapas.cor('branco')).attr('fill-opacity', .9)
        .attr('font-family', "'Archivo Narrow', Arial, sans-serif").attr('font-size', 12).text(sub);
    };
    const gN = svg.append('g').attr('class', 'nos');
    ORIG.forEach(o => no(gN, {x: 100, y: o.y}, 176, 46, MonitorMapas.cor('abissal'), o.nome, o.id === 'estado' ? 'recebe e repassa' : 'origem federal'));
    svg.append('text').attr('x', 100).attr('y', 352).attr('text-anchor', 'middle').attr('font-size', 12).attr('fill', MonitorMapas.cor('muted')).attr('font-family', "'Archivo Narrow', Arial, sans-serif").text('as linhas verticais: o que a União repassa ao estado');
    svg.append('text').attr('x', 100).attr('y', 368).attr('text-anchor', 'middle').attr('font-size', 12).attr('fill', MonitorMapas.cor('muted')).attr('font-family', "'Archivo Narrow', Arial, sans-serif").text('(FPE · fundo a fundo · defesa civil · convênios)');
    no(gN, destino, 130, 44, MonitorMapas.cor('abissal'), 'Município', null);
    nos.forEach(n => {
      const g = gN.append('g').attr('tabindex', 0).attr('role', 'img').attr('aria-label', n.n + ' · ' + n.nome + ' — chave: ' + n.chave + (n.ex_ante ? '' : ' (resposta)'))
        .on('mouseenter', evt => showTip('<strong>' + n.n + ' · ' + esc(n.nome) + '</strong><br><em>chave: ' + esc(n.chave) + (n.ex_ante ? '' : ' · resposta') + '</em><br>' + esc(n.base_legal) + (n.base_estado ? '<br><em>Nível estadual:</em> ' + esc(n.base_estado) : '') + '<br><em>O decreto destranca:</em> ' + esc(n.decreto_destranca), evt))
        .on('mousemove', evt => showTip('<strong>' + n.n + ' · ' + esc(n.nome) + '</strong><br><em>chave: ' + esc(n.chave) + '</em><br>' + esc(n.base_legal), evt))
        .on('focus', () => showTip('<strong>' + n.n + ' · ' + esc(n.nome) + '</strong><br>' + esc(n.base_legal), {clientX: 24, clientY: 24}))
        .on('mouseleave', hideTip).on('blur', hideTip)
        .on('mouseenter.realce', () => svg.selectAll('.aresta').attr('stroke-opacity', .15).filter('.' + n.id).attr('stroke-opacity', 1))
        .on('mouseleave.realce', () => svg.selectAll('.aresta').attr('stroke-opacity', .75));
      no(g, n, 300, passo - 8, n.cor, n.n + ' · ' + n.nome, 'chave: ' + n.chave + (n.ex_ante ? '' : ' · resposta'));
    });
    MonitorMapas.legenda('legRede', [{cor: MonitorMapas.PALETA.chaves.regra, rotulo: 'contínuo: regra'}, {cor: MonitorMapas.PALETA.chaves.decreto, rotulo: 'tracejado: decreto (resposta)'}, {cor: MonitorMapas.PALETA.chaves.discricionaria, rotulo: 'pontilhado: discricionária'}, {cor: MonitorMapas.PALETA.chaves.direta, rotulo: 'duplo: execução direta'}]);
    fonteFigura('boxRede', {fontes: ['MARÉ', 'base legal citada por rota'], data: ROTAS.corte});
  })();
  document.getElementById('rotasCards').innerHTML = ROTAS.rotas.map(r => '<div class="cartao" style="border-left:4px solid '+r.cor+'"><h3 class="figura-titulo">'+r.n+' · '+esc(r.nome)+' <span class="sub">— chave: <em>'+esc(r.chave)+'</em>'+(r.ex_ante ? '' : ' · resposta')+'</span></h3>'
    + '</div>').join('');
  // 13/09/2026 (proposta de enxugamento, Manus AI): agrupamento legível das 8 rotas em 4 famílias,
  // acima do diagrama — não substitui as distinções jurídicas (nome e chave seguem por rota, nunca
  // digitados à mão: vêm de ROTAS.rotas). Família é mapeada por id (estrutura estável); nome e chave
  // de cada rota, e a legenda de família, vêm sempre do registro.
  const FAMILIA_POR_ROTA = {r1:'Automáticas e regulares', r2:'Automáticas e regulares', r3:'Emergência e resposta', r4:'Emergência e resposta',
    r5:'Discricionárias', r6:'Discricionárias', r7:'Execução no território', rE:'Execução no território'};
  const ORDEM_FAMILIA = ['Automáticas e regulares', 'Emergência e resposta', 'Discricionárias', 'Execução no território'];
  const porFamilia = {}; ROTAS.rotas.forEach(r => { const f = FAMILIA_POR_ROTA[r.id] || 'Outras'; (porFamilia[f] = porFamilia[f] || []).push(r); });
  const tbFam = document.querySelector('#tblFamiliasRotas tbody');
  if (tbFam) tbFam.innerHTML = ORDEM_FAMILIA.filter(f => porFamilia[f]).map(f => {
    const rs = porFamilia[f];
    const chaves = [...new Set(rs.map(r => r.chave))].join(' · ');
    return '<tr><td><strong>' + esc(f) + '</strong></td><td>' + rs.map(r => esc(r.n + ' · ' + r.nome)).join('<br>') + '</td><td>' + esc(chaves) + '</td></tr>';
  }).join('');
  // 13/09/2026 (proposta de enxugamento, Manus AI): 'Brasil, por semana' (série semanal por rota)
  // migrou para pesquisadores.html — "é monitoramento temporal de execução, não explicação de rota
  // nem de solicitação".
  // 3 · por estado
  const FUNDO = {localizado:['Localizado',MonitorMapas.PALETA.status.NOVO], em_elaboracao:['Em elaboração',MonitorMapas.PALETA.status.ELAB], nao_localizado:['Não localizado (bateria datada)',MonitorMapas.PALETA.status.LAC], nao_verificado:['Ainda não verificado',MonitorMapas.PALETA.status.NAO_VERIFICADO]};
  const fundo = uf => ((PORUF.uf[uf] || {}).fundo_a_fundo_preventivo || {}).status || 'nao_verificado';
  if (document.getElementById('mapaFundo')) desenharMapa('mapaFundo','legFundo', uf => (FUNDO[fundo(uf)] || FUNDO.nao_verificado)[1],
    uf => { const f = (PORUF.uf[uf] || {}).fundo_a_fundo_preventivo || {}; return '<em>' + esc((FUNDO[fundo(uf)] || FUNDO.nao_verificado)[0]) + '</em>' + (f.instrumento ? '<br>' + esc(f.instrumento) + (f.norma ? ' · ' + esc(f.norma) : '') : '') + (f.condicionalidade ? '<br>Condição: ' + esc(f.condicionalidade) : '') + (f.verificado_em ? '<br>verificado em ' + esc(f.verificado_em) : '<br>bateria estadual ainda não executada'); },
    Object.values(FUNDO).map(v => ({cor: v[1], rotulo: v[0]})));
  if (document.getElementById('boxFundoEstadual')) fonteFigura('boxFundoEstadual', {fontes: 'MARÉ', data: PORUF.corte});   // 15/09/2026: mapa retirado da página (pedido da editoria)
  // 13/09/2026: mapa "por habitante, por rota" retirado do HTML (ver comentário em financiamento.html,
  // painel #porestado) — só a rota 5 tinha cobertura real. Bloco mantido desativado (guarda por
  // ausência do <select>), não apagado, para reativar assim que outras rotas tiverem dado.
  const sel = document.getElementById('selRota');
  if (sel) {
    sel.innerHTML = ROTAS.rotas.map(r => '<option value="'+r.id+'">'+r.n+' · '+esc(r.nome)+'</option>').join('');
    function valorHab(uf, rota){ const v = (((PORUF.uf[uf] || {}).rotas || {})[rota] || {}).valor_2026; const pop = UFS.includes(uf) ? Object.entries(POP).filter(([c]) => String(c).startsWith(String(UFS.indexOf(uf)))).length : 0; return (v == null) ? null : v; }
    function desenharHab(){
      const rota = sel.value; const vals = UFS.map(uf => valorHab(uf, rota)).filter(v => v != null);
      const cor = d3.scaleSequential(d3.interpolateBlues).domain([0, d3.max(vals) || 1]);
      desenharMapa('mapaHab','legHab', uf => { const v = valorHab(uf, rota); return v == null ? NEUTRA : cor(v); },
        uf => { const v = valorHab(uf, rota); return v == null ? 'Aguardando coleta (rota ' + esc(rota) + ')' : brl(v); },
        vals.length ? [{cor: cor(0), rotulo: 'menor'}, {cor: cor(d3.max(vals)), rotulo: 'maior'}] : [{cor: NEUTRA, rotulo: 'aguardando coleta'}]);
    }
    desenharHab(); sel.addEventListener('change', desenharHab);
    fonteFigura('boxPorHab', {fontes: ['Portal da Transparência', 'Tesouro', 'FNS', 'FNAS', 'Censo 2022 (IBGE)'], data: null});
  }
  // 15/09/2026: painel 'Por estado' (mapa do dinheiro, R$/hab., barras de resposta) retirado da página (pedido da editoria); bloco guardado por ausência do elemento
  if (document.getElementById('mapDinheiro')) {
  // 4 · resposta por decreto
  const svgDin = desenharMapa('mapDinheiro','legDinheiro', uf => NEUTRA, uf => 'Sem repasse ou reconhecimento nomeado até o corte',
    [{cor:MonitorMapas.PALETA.preparacao, rotulo:'Repasse preventivo confirmado (Prepara RS)'}, {cor:MonitorMapas.PALETA.resposta, rotulo:'Reconhecimento federal (rota 3, resposta)'}]);
  const repassesGeo = (TRANSF.repasses_rs || []).filter(r => r.lat);
  const rEsc = d3.scaleSqrt().domain([0, d3.max(repassesGeo, r => r.valor) || 1]).range([1.5, 9]);
  svgDin.append('g').selectAll('circle').data(repassesGeo).join('circle')
    .attr('cx', r => projection([r.lon, r.lat])[0]).attr('cy', r => projection([r.lon, r.lat])[1]).attr('r', r => rEsc(r.valor))
    .attr('fill', MonitorMapas.PALETA.preparacao).attr('fill-opacity', .75).attr('stroke', MonitorMapas.cor('branco')).attr('stroke-width', .6)
    .on('mouseenter', (evt, r) => showTip('<strong>' + esc(r.municipio || r.nome) + ' (RS)</strong><br>' + brl(r.valor) + ' · Prepara RS', evt)).on('mouseleave', hideTip);
  const recs = (ATOS.eventos || []).filter(e => e.causa === 'reconhecimento federal' && e.lat);
  svgDin.append('g').selectAll('circle.rec').data(recs).join('circle').attr('class','rec')
    .attr('cx', e => projection([e.lon, e.lat])[0]).attr('cy', e => projection([e.lon, e.lat])[1]).attr('r', 4).attr('fill', MonitorMapas.PALETA.resposta).attr('fill-opacity', .85);
  // 04/09/2026: os totais são dado de legenda, não nota — entram na própria legenda do mapa.
  MonitorMapas.legenda('legDinheiro', [
    {cor:MonitorMapas.PALETA.preparacao, rotulo:'Repasse preventivo confirmado (Prepara RS): ' + brl(repassesGeo.reduce((s, r) => s + r.valor, 0)) + ' · ' + repassesGeo.length + ' municípios'},
    {cor:MonitorMapas.PALETA.resposta, rotulo:'Reconhecimento federal (rota 3, resposta): ' + recs.length}]);
  (document.getElementById('dinTotalRS')||{}).textContent = brl(repassesGeo.reduce((s, r) => s + r.valor, 0));
  (document.getElementById('dinNumRS')||{}).textContent = repassesGeo.length;
  (document.getElementById('dinNumFed')||{}).textContent = recs.length;
  fonteFigura('boxDinheiro', {fontes: ['FUNDEC/RS', 'DOU (SEDEC/MIDR)'], data: ROTAS.corte});
  // 16/09/2026: bloco morto removido — cResposta e boxResposta não existem mais no HTML desde os
  // cortes de 15/09 (§70); o gráfico ordenava estados por municípios sob decreto, do maior ao menor.
  }
  // 5 · painel amostral: migrou para pesquisadores.html em 13/09/2026 (proposta de enxugamento,
  // Manus AI) — "não responde quem pediu ou não pediu no universo monitorado".
  // 6 · programas permanentes
  const PROG = [
    {nome: 'Garantia-Safra', base: 'Lei 10.420/2002 · MDA', regra: 'adesão municipal anual antes do plantio; cota municipal 6%; pagamento por perda verificada, sem decreto', lista: 'relação de municípios aderentes: sem coleta até o corte (MDA)'},
    {nome: 'Programa Cisternas', base: 'MDS', regra: 'adesão e projeto; contínuo', lista: 'execução por município: sem coleta até o corte (MDS)'},
    {nome: 'Operação Carro-Pipa', base: 'Exército (CMNE) / MIDR', regra: 'inclusão condicionada, na maior parte dos casos, a reconhecimento federal', lista: 'relação de municípios atendidos não publicada pelo Exército; sem coleta até o corte'},
    {nome: 'CISC · Centros Integrados de Saúde e Clima', base: 'Ministério da Saúde', regra: '8 cidades-piloto em 5 regiões', lista: 'relação nominal das cidades não localizada até o corte'},
    {nome: 'Monitoramento do Cemaden', base: 'MCTI/Cemaden', regra: '1.037 municípios monitorados', lista: 'lista: em coleta'},
  ];
  document.getElementById('programasLista').innerHTML = PROG.map(p => '<li><strong>' + esc(p.nome) + ':</strong> ' + esc(p.base) + '. ' + esc(p.regra) + ' <span class="u-muted">· ' + esc(p.lista) + '</span></li>').join('');
  fonteFigura('boxSemDecretar', {fontes: 'as bases legais citadas em cada item', data: ROTAS.corte});
  // 13/09/2026 (proposta de enxugamento, Manus AI): 'Compromissos federais' (tabela + gráfico por
  // área) migrou para pesquisadores.html — apêndice metodológico, não narrativa principal de rotas.
  // 8 · fontes e consultas
  const cons = CONSULTAS.consultas || [];
}
window.__finPronto = __load().catch(err => { const m = document.getElementById('subFin'); if (m) m.insertAdjacentHTML('afterend', '<p class="note u-rust">Erro ao carregar os dados: ' + esc(err.message) + '</p>'); });

window.addEventListener('load', function(){ if (window.VLibras && window.VLibras.Widget) { try { new window.VLibras.Widget('https://vlibras.gov.br/app'); } catch (e) {} } });

// 14/09/2026 — Rota preventiva do fogo (handover; METODOLOGIA §28/§38). Peso zero. Tudo vem de data/financiamento/rotas_preventivas.json;
// nenhum número é digitado aqui. As camadas do mapa exigem coleta própria (áreas declaradas no DOU, transferências no Portal,
// requerimentos só por LAI/MMA): sem os arquivos, o mapa DECLARA a lacuna em vez de fingir dado.
(function rotaPreventivaFogo(){
  const tt = document.getElementById('fogoTitulo'); if (!tt) return;
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const fmtR = v => v == null ? '—' : 'R$ ' + (v >= 1e6 ? (v / 1e6).toLocaleString('pt-BR', {maximumFractionDigits: 1}) + ' mi' : v.toLocaleString('pt-BR'));
  const lacuna = (t1, t2) => { if (!document.getElementById('legFogoMapa')) return; const a = document.getElementById('txtFogoLacuna1'), b = document.getElementById('txtFogoLacuna2');
    if (a) { a.textContent = t1; a.setAttribute('fill', MonitorMapas.cor('muted')); } if (b) { b.textContent = t2; b.setAttribute('fill', MonitorMapas.cor('muted')); }
    MonitorMapas.legenda('legFogoMapa', [{cor: MonitorMapas.NEUTRA, rotulo: 'camadas sem coleta até o corte'}]); };
  Promise.all(['data/financiamento/rotas_preventivas.json', 'data/financiamento/fogo/areas_declaradas.json', 'data/financiamento/fogo/transferencias.json', 'data/financiamento/fogo/requerimentos.json']
    .map(f => fetch(f).then(r => r.ok ? r.json() : null).catch(() => null))).then(([RP, AREAS, TRANSF, REQ]) => {
    if (!RP || !Array.isArray(RP.rotas)) { tt.textContent = 'Rotas preventivas ainda não carregadas.'; lacuna('Dados não carregados', ''); if (document.getElementById('boxFogoMapa')) fonteFigura('boxFogoMapa', {fontes: 'MARÉ', data: null}); return; }
    const edital = RP.rotas.find(r => r.id === 'fogo_edital_2025'), fa = RP.rotas.find(r => r.id === 'fogo_fundo_amazonia');
    const riscos = RP.riscos_com_rota_preventiva || []; const soFogo = riscos.length === 1 && riscos[0] === 'incendio';
    const nAreas = AREAS && Array.isArray(AREAS.municipios) ? AREAS.municipios.length : null, nRec = TRANSF && Array.isArray(TRANSF.transferencias) ? new Set(TRANSF.transferencias.map(t => t.ibge || t.ente)).size : null;
    tt.innerHTML = 'Dinheiro preventivo federal existe para o fogo' + (edital && edital.valores ? ': edital de 2025 com <strong>' + edital.valores.elegiveis + '</strong> municípios elegíveis e <strong>' + edital.valores.contemplados + '</strong> contemplados (' + esc(fmtR(edital.valores.total_reais)) + ')' : '') +
      (nAreas != null ? '; <strong>' + nAreas.toLocaleString('pt-BR') + '</strong> municípios em área de emergência ambiental declarada' : '') + (nRec != null ? '; <strong>' + nRec.toLocaleString('pt-BR') + '</strong> com transferência do FNMA' : '') +
      (fa && fa.valores ? '; Fundo Amazônia com ' + esc(fmtR(fa.valores.total_reais)) + ' para bombeiros e brigadas estaduais' : '') + (soFogo ? '. Não existe rota equivalente para seca nem para chuva.' : '.');
    // tabela: uma linha por rota, em linguagem da tela
    const NOME = {r1: 'rota 1', r2: 'rota 2', r3: 'rota 3', r4: 'rota 4', r5: 'rota 5', r6: 'rota 6', r7: 'rota 7', rE: 'rota estadual', rF: 'fundos extraorçamentários'};
    // 15/09/2026: cartões em vez de tabela — quem pode, o que precisa, o que paga, valores e situação no defeso
    const cards = document.getElementById('fogoRotasCards');
    if (cards) cards.innerHTML = RP.rotas.map(r => '<div class="cartao cartao--acento-musgo"><h3 class="figura-titulo">' + esc(r.nome) + '</h3><p class="card-body"><strong>' + esc(NOME[r.rota] || r.rota) + (r.subrota ? ' · ' + esc(r.subrota) : '') + '</strong> · ' + esc(r.lei) + (r.artigo ? ' (' + esc(r.artigo) + ')' : '') + '</p>'
      + '<p class="card-body"><strong>Quem pode:</strong> ' + esc(r.quem_pode || '—') + '<br><strong>O que precisa:</strong> ' + esc((r.condicoes || []).join('; ') || '—') + '<br><strong>O que paga:</strong> ' + esc(r.o_que_paga || '—')
      + (r.valores ? '<br><strong>Valores:</strong> ' + esc(fmtR(r.valores.total_reais)) + (r.valores.elegiveis != null ? ' · ' + esc(r.valores.elegiveis) + ' elegíveis' : '') + (r.valores.contemplados != null ? ' · ' + esc(r.valores.contemplados) + ' contemplados' : '') : '')
      + (r.situacao_defeso ? '<br><strong>No período eleitoral:</strong> ' + esc(r.situacao_defeso) : '') + '</p></div>').join('');
    const fr = document.getElementById('fogoRotasFonte'); if (fr && !fr.querySelector('.fonte-figura')) fr.innerHTML = '<p class="note u-mb-0">Fonte: leis e portarias citadas em cada cartão · MARÉ · Atualização: ' + esc(RP.corte || '—') + '</p>';
    if (!AREAS && !TRANSF) { lacuna('Camadas ainda não coletadas — lacuna declarada', 'Áreas declaradas (DOU/MMA) e transferências (Portal da Transparência) dependem de coleta própria; requerimentos só chegam por LAI/MMA.'); fonteFigura('boxFogoMapa', {fontes: ['DOU/MMA', 'Portal da Transparência', 'LAI/MMA'], data: null}); return; }
    // quando houver dado: mapa em três camadas (a implementar junto do coletor; até lá, contagens na legenda)
    if (document.getElementById('legFogoMapa')) MonitorMapas.legenda('legFogoMapa', [{cor: MonitorMapas.PALETA.verificacao.nacional, rotulo: 'área declarada' + (nAreas != null ? ' · ' + nAreas : '')}, {cor: MonitorMapas.PALETA.categorias.decreto, rotulo: 'recebeu' + (nRec != null ? ' · ' + nRec : '')}, {cor: MonitorMapas.NEUTRA, rotulo: 'requereu: ' + (REQ ? 'conhecidos por LAI/MMA' : 'sem informação')}]);
    if (document.getElementById('boxFogoMapa')) fonteFigura('boxFogoMapa', {fontes: ['DOU/MMA', 'Portal da Transparência', 'LAI/MMA'], data: (AREAS && AREAS.gerado_em) || (TRANSF && TRANSF.gerado_em) || null});
  });
})();

// 15/09/2026 (auditoria editorial §1.7 e §1.6, quarta porta): "O que a União prometeu — e o que pagou" volta para cá.
// Compromissos verificados (tabela) + série semanal por rota (miniatura, com a faixa do período eleitoral). Título-fato do dado.
(async function prometeuEPagou(){
  if (!document.getElementById('prometeu')) return;
  try { await window.__finPronto; } catch (e) {}   // 15/09/2026: os gráficos abaixo usam MPS, PORUF, RESP_FIN e a malha — esperam a carga principal
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  try {
    const brl = v => (v == null) ? '—' : 'R$ ' + Number(v).toLocaleString('pt-BR', {maximumFractionDigits: 0});
    const [ROTAS_FIN, COMP] = await Promise.all(['data/financiamento/rotas.json', 'data/financiamento/compromissos_federais.json'].map(f => fetch(f).then(r => r.ok ? r.json() : null)));
    if (COMP) {
      (function(){ const cv = document.getElementById('cCompromissos'); if (!cv || typeof Chart === 'undefined') return;
        const mps = (MPS && MPS.mps) || []; const itens = (COMP.itens || []).slice();
        // os dois créditos extraordinários (MPs) entram na mesma leitura, com execução do Portal
        const linhas = mps.map(m => ({nome: m.numero + ' · ' + (m.tema || '').split(' e ')[0], anunciado: m.valor, empenhado: (m.execucao || {}).empenhado, pago: (m.execucao || {}).pago, status: (m.execucao || {}).status}))
          .concat(itens.map(c => ({nome: c.nome, anunciado: c.valor_total, empenhado: (c.execucao || {}).empenhado, pago: (c.execucao || {}).pago, status: (c.execucao || {}).status})));
        const mi = v => v == null ? null : +(v / 1e6).toFixed(1);
        MonitorMapas.padraoGraficos(window.Chart);
        new Chart(cv, {type: 'bar', data: {labels: linhas.map(l => l.nome.replace(/ — .*$/, '').length > 34 ? l.nome.replace(/ — .*$/, '').slice(0, 32) + '…' : l.nome.replace(/ — .*$/, '')), datasets: [
            {label: 'anunciado', data: linhas.map(l => mi(l.anunciado)), backgroundColor: MonitorMapas.PALETA.serie[4]},
            {label: 'empenhado', data: linhas.map(l => mi(l.empenhado)), backgroundColor: MonitorMapas.PALETA.serie[2]},
            {label: 'pago', data: linhas.map(l => mi(l.pago)), backgroundColor: MonitorMapas.PALETA.serie[0]}]},
          options: {indexAxis: 'y', animation: false, responsive: true, maintainAspectRatio: false, plugins: {legend: {display: false}, tooltip: {callbacks: {afterBody: items => { const l = linhas[items[0].dataIndex]; return l.status === 'coletado' ? 'execução: Portal da Transparência' : 'execução: ' + (l.status || 'aguardando coleta').replace(/_/g, ' '); }}}},
            scales: {x: {beginAtZero: true, title: {display: true, text: 'R$ milhões'}}, y: {ticks: {font: {size: 11}}}}}});
        MonitorMapas.legenda('legCompromissos', [{cor: MonitorMapas.PALETA.serie[4], rotulo: 'anunciado'}, {cor: MonitorMapas.PALETA.serie[2], rotulo: 'empenhado (Portal)'}, {cor: MonitorMapas.PALETA.serie[0], rotulo: 'pago (Portal)'}, {cor: MonitorMapas.PALETA.semDado, rotulo: 'sem barra de execução: aguardando coleta'}]);
        MonitorMapas.credito('boxCompromissosGrafico', {fontes: ['as citadas em cada compromisso', 'Portal da Transparência (execução)'], data: (MPS && MPS.gerado_em) || (ROTAS_FIN && ROTAS_FIN.corte) || null});
        // mapas: onde o pagamento chegou (valor pago por UF da unidade gestora), uma MP por mapa
        const ctx = MonitorMapas.contexto(BR_GEOJSON, 480, 460); const fmt = v => 'R$ ' + (v >= 1e6 ? (v / 1e6).toFixed(1).replace('.', ',') + ' mi' : (v / 1e3).toFixed(0) + ' mil');
        [['mp1367', 'mapaMPsUF', 'legMPsUF', 'boxMPsUF'], ['mp1384', 'mapaMP1384UF', 'legMP1384UF', 'boxMP1384UF']].forEach(([id, mapa, leg, box]) => {
          const m = mps.find(x => x.id === id); const por = (m && m.destino && m.destino.por_uf_pago) || null; if (!document.getElementById(mapa)) return;
          if (!por) { MonitorMapas.ufs(ctx, mapa, () => MonitorMapas.NEUTRA, () => 'sem coleta'); MonitorMapas.legenda(leg, [{cor: MonitorMapas.NEUTRA, rotulo: 'sem coleta até o corte'}]); MonitorMapas.credito(box, {fontes: 'Portal da Transparência', data: null}); return; }
          const max = Math.max(1, ...Object.entries(por).filter(([k]) => k !== 'BR').map(([, v]) => v)); const esc2 = d3.scaleSqrt().domain([0, max]).range(MonitorMapas.PALETA.rampaPreparo);
          MonitorMapas.ufs(ctx, mapa, uf => por[uf] ? esc2(por[uf]) : MonitorMapas.PALETA.zero, uf => por[uf] ? esc(fmt(por[uf])) + ' pagos por unidade gestora no estado' : 'nenhum pagamento por unidade gestora no estado');
          MonitorMapas.siglas(ctx, d3.select('#' + mapa));
          MonitorMapas.legenda(leg, [{cor: MonitorMapas.PALETA.zero, rotulo: 'nenhum pagamento no estado'}, {cor: MonitorMapas.PALETA.rampaPreparo[1], rotulo: 'até ' + fmt(max)}, {cor: MonitorMapas.PALETA.semDado, rotulo: 'unidade nacional (BR): ' + fmt(por.BR || 0) + ', fora do mapa'}]);
          MonitorMapas.credito(box, {fontes: ['Portal da Transparência — execução da despesa', m.numero], data: (m.execucao || {}).atualizado_em || null});
        });
      })();
      // RS: repasse preventivo × resposta por decreto
      (function(){ const cv = document.getElementById('cRS'); if (!cv || typeof Chart === 'undefined') return;
        const rs = (PORUF && PORUF.uf && PORUF.uf.RS && PORUF.uf.RS.fundo_a_fundo_preventivo) || {}; const r = (RESP_FIN && RESP_FIN.uf && RESP_FIN.uf.RS) || null;
        const dados = [{r: 'com repasse preventivo (Prepara RS)', v: rs.repasses || 0, c: MonitorMapas.PALETA.preparacao}, {r: 'sob decreto de emergência no ciclo', v: r ? r.n_municipios : 0, c: MonitorMapas.PALETA.resposta}, {r: 'reconhecidos pela União', v: r ? r.tons.reconhecido : 0, c: MonitorMapas.PALETA.status.ELAB}];
        MonitorMapas.padraoGraficos(window.Chart);
        new Chart(cv, {type: 'bar', data: {labels: dados.map(d => d.r), datasets: [{data: dados.map(d => d.v), backgroundColor: dados.map(d => d.c)}]},
          options: {indexAxis: 'y', animation: false, responsive: true, maintainAspectRatio: false, plugins: {legend: {display: false}}, scales: {x: {beginAtZero: true, max: 497, title: {display: true, text: 'municípios (de 497)'}}}}});
        MonitorMapas.legenda('legRS', [{cor: MonitorMapas.PALETA.preparacao, rotulo: 'repasse preventivo: ' + (rs.valor_total ? 'R$ ' + (rs.valor_total / 1e6).toFixed(1).replace('.', ',') + ' mi · ' : '') + (rs.repasses || 0) + ' municípios'}, {cor: MonitorMapas.PALETA.resposta, rotulo: 'sob decreto: ' + (r ? r.n_municipios : 0)}, {cor: MonitorMapas.PALETA.status.ELAB, rotulo: 'reconhecidos: ' + (r ? r.tons.reconhecido : 0)}]);
        fonteFigura('boxRSGrafico', {fontes: ['FUNDEC/RS (Resolução 008/2026)', 'DOU/SEDEC (S2iD)'], data: (RESP_FIN && RESP_FIN.gerado_em) || null});
      })();
    }
  } catch(e) {}
  try {
    const [ROTAS_SER, SERIE] = await Promise.all(['data/financiamento/rotas.json', 'data/financiamento/serie_nacional.json'].map(f => fetch(f).then(r => r.ok ? r.json() : null)));
    if (ROTAS_SER && SERIE) {
      const svg = d3.select('#svgSerie'), W = 900, H = 180, m = {t: 16, r: 16, b: 34, l: 60};
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
  try {
    const [COMP, SERIE] = await Promise.all(['data/financiamento/compromissos_federais.json', 'data/financiamento/serie_nacional.json'].map(f => fetch(f).then(r => r.ok ? r.json() : null)));
    const n = (COMP && COMP.itens || []).length; const sem = (SERIE && SERIE.semanas || []);
    const total = sem.reduce((a, s) => a + Object.keys(s).filter(k => /^r/.test(k)).reduce((b, k) => b + (+s[k] || 0), 0), 0);
    const ate = sem.length ? sem[sem.length - 1].semana : null;
    document.getElementById('prometeuTitulo').innerHTML = '<strong>' + n + '</strong> compromissos federais verificados, com dinheiro e prazo' + (sem.length ? '; <strong>R$ ' + (total / 1e6).toLocaleString('pt-BR', {maximumFractionDigits: 0}) + ' mi</strong> transferidos a municípios em 2026 até a semana de ' + esc(ate) : '; série semanal ainda não coletada') + '.';
  } catch(e) { const t = document.getElementById('prometeuTitulo'); if (t) t.textContent = 'Compromissos e série: dados não carregados.'; }
})();

// 15/09/2026: ficha "Como ler as rotas" em popup (mesmo <dialog> da inicial); chaves, termos, cartões das rotas e a rota do fogo
(function(){
  const link = document.getElementById('linkComoLerRotas'), fonte = document.getElementById('comolerRotas'), dlg = document.getElementById('detailFin');
  if (!link || !fonte || !dlg) return;
  const fechar = () => { if (typeof dlg.close === 'function') dlg.close(); else dlg.open = false; };
  link.addEventListener('click', e => { e.preventDefault(); document.getElementById('detailFinConteudo').innerHTML = fonte.innerHTML; if (!dlg.open) { if (typeof dlg.showModal === 'function') dlg.showModal(); else dlg.open = true; } });
  const bt = document.getElementById('detailFinFechar'); if (bt) bt.addEventListener('click', fechar); dlg.addEventListener('click', evt => { if (evt.target === dlg) fechar(); });
})();

// 15/09/2026 (handover "Dinheiro preventivo por setor"): rede D3 com a mesma gramática de #boxRede — origens à esquerda,
// três faixas (saúde, fogo, seca) ao centro, três destinos à direita; traço = chave; glifos de chave no meio da aresta;
// nó de ausência da seca desenhado como ausência (contorno tracejado, sem aresta). Lê data/financiamento/preventivo_setores.json.
(function preventivoPorSetor(){
  const svg = d3.select('#preventivoSetor'); if (svg.empty()) return;
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const { showTip, hideTip } = MonitorMapas;
  fetch('data/financiamento/preventivo_setores.json').then(r => r.ok ? r.json() : null).then(P => {
    if (!P) { MonitorMapas.legenda('legPreventivoSetor', [{cor: MonitorMapas.NEUTRA, rotulo: 'dado não carregado'}]); fonteFigura('boxPreventivoSetor', {fontes: 'MARÉ', data: null}); return; }
    const CH = MonitorMapas.PALETA.chaves, SET = MonitorMapas.PALETA.setores;
    const dash = ch => ch === 'decreto' ? '8,5' : ch === 'discricionaria' ? '2,4' : null;
    const curva = (p, q) => `M${p.x},${p.y} C${(p.x + q.x) / 2},${p.y} ${(p.x + q.x) / 2},${q.y} ${q.x},${q.y}`;
    const no = (g, n, w, h, cor, texto, sub, tracejado) => {
      g.append('rect').attr('x', n.x - w / 2).attr('y', n.y - h / 2).attr('width', w).attr('height', h).attr('rx', 8).attr('fill', tracejado ? 'none' : cor).attr('stroke', tracejado ? MonitorMapas.cor('muted') : MonitorMapas.cor('branco')).attr('stroke-width', 1.2).attr('stroke-dasharray', tracejado ? '5,4' : null);
      g.append('text').attr('x', n.x).attr('y', n.y - (sub ? 5 : 0)).attr('text-anchor', 'middle').attr('dominant-baseline', 'middle').attr('fill', tracejado ? MonitorMapas.cor('muted') : MonitorMapas.cor('branco')).attr('font-family', "'Archivo', Arial, sans-serif").attr('font-size', 11.5).attr('font-weight', 600).text(texto);
      if (sub) g.append('text').attr('x', n.x).attr('y', n.y + 10).attr('text-anchor', 'middle').attr('dominant-baseline', 'middle').attr('fill', tracejado ? MonitorMapas.cor('muted') : MonitorMapas.cor('branco')).attr('fill-opacity', .9).attr('font-family', "'Archivo Narrow', Arial, sans-serif").attr('font-size', 11).text(sub);
    };
    // glifos de chave, monocromáticos, 14 px, centrados em (0,0)
    const glifo = (g, tipo, cor) => {
      const s = g.append('g').attr('class', 'glifo').attr('fill', 'none').attr('stroke', cor).attr('stroke-width', 1.4).attr('stroke-linejoin', 'round');
      s.append('circle').attr('r', 9).attr('fill', MonitorMapas.cor('branco')).attr('stroke', cor);
      if (tipo === 'plano') { s.append('path').attr('d', 'M-4,-5 H2 L4,-3 V5 H-4 Z'); s.append('path').attr('d', 'M2,-5 V-3 H4'); }
      else if (tipo === 'risco') { s.append('path').attr('d', 'M-5,2 A5,5 0 0 1 5,2'); s.append('path').attr('d', 'M0,2 L3,-2'); }
      else if (tipo === 'calendario') { s.append('rect').attr('x', -5).attr('y', -4).attr('width', 10).attr('height', 9).attr('rx', 1); s.append('path').attr('d', 'M-5,-1 H5 M-3,-6 V-3 M3,-6 V-3'); }
      else if (tipo === 'obra') { s.append('path').attr('d', 'M-5,4 H5 M-3,4 V-2 H3 V4 M0,-2 V-5'); }
      else if (tipo === 'credito') { s.append('path').attr('d', 'M2,-3 C0,-5 -3,-4 -3,-2 C-3,1 3,0 3,2 C3,4 0,5 -2,3 M0,-5 V5'); }
      return s;
    };
    const rotas = P.setores.flatMap(s => s.rotas.map(r => Object.assign({setor: s.id}, r)));
    const ausencia = (P.setores.find(s => s.ausencia) || {}).ausencia;
    // posições
    const ORIG = P.origens.map((o, i) => Object.assign({y: 120 + i * 150}, o));
    const DEST = P.destinos.map((d, i) => Object.assign({y: 120 + i * 150}, d));
    const nos = []; let y = 44;
    P.setores.forEach(s => {
      svg.append('text').attr('x', 480).attr('y', y).attr('text-anchor', 'middle').attr('font-size', 11).attr('letter-spacing', 1.5).attr('fill', SET[s.id]).attr('font-family', "'Archivo Narrow', Arial, sans-serif").attr('font-weight', 700).text(s.nome.toUpperCase());
      y += 12;
      s.rotas.forEach(r => { nos.push(Object.assign({x: 480, y: y + 14, setor: s.id}, r)); y += 32; });
      if (s.ausencia) { nos.push({x: 480, y: y + 14, setor: s.id, ausencia: true, id: s.ausencia.id, nome: s.ausencia.rotulo, nota: s.ausencia.nota}); y += 32; }
      y += 12;
    });
    const gA = svg.append('g').attr('class', 'arestas'), gN = svg.append('g').attr('class', 'nos');
    const byO = Object.fromEntries(ORIG.map(o => [o.id, o])), byD = Object.fromEntries(DEST.map(d => [d.id, d]));
    nos.filter(n => !n.ausencia).forEach(n => {
      const cor = n.objeto === 'resposta' ? CH.decreto : (CH[n.chave] || SET[n.setor]); n.cor = cor;
      const o = byO[n.origem] || byO.uniao, d = byD[n.destino] || byD.mun;
      const p1 = {x: 100 + 88, y: o.y}, p2 = {x: 480 - 160, y: n.y}, p3 = {x: 480 + 160, y: n.y}, p4 = {x: 880 - 65, y: d.y};
      [[p1, p2], [p3, p4]].forEach(([a, b]) => {
        gA.append('path').attr('d', curva(a, b)).attr('fill', 'none').attr('stroke', cor).attr('stroke-width', n.chave === 'direta' ? 5 : 3).attr('stroke-opacity', n.objeto === 'resposta' ? .9 : .75).attr('stroke-dasharray', dash(n.chave)).attr('class', 'aresta ' + n.id);
        if (n.chave === 'direta') gA.append('path').attr('d', curva(a, b)).attr('fill', 'none').attr('stroke', MonitorMapas.cor('branco')).attr('stroke-width', 1.5).attr('class', 'aresta ' + n.id);
      });
      (n.glifos || []).forEach((t, i) => { const g = gA.append('g').attr('class', 'aresta ' + n.id).attr('transform', `translate(${p3.x + 22 + i * 24},${n.y})`); glifo(g, t, cor); });
    });
    ORIG.forEach(o => no(gN, {x: 100, y: o.y}, 176, 46, MonitorMapas.cor('abissal'), o.nome, o.sub));
    DEST.forEach(d => no(gN, {x: 880, y: d.y}, 150, 46, MonitorMapas.cor('abissal'), d.nome, d.sub));
    nos.forEach(n => {
      const g = gN.append('g').attr('tabindex', 0).attr('role', 'img').attr('aria-label', n.ausencia ? n.nome : n.nome + ' — chave: ' + n.chave + ' · destino: ' + (byD[n.destino] || {}).nome + (n.objeto === 'resposta' ? ' (resposta)' : ''));
      const tip = n.ausencia ? '<strong>' + esc(n.nome) + '</strong><br>' + esc(n.nota)
        : '<strong>' + esc(n.nome) + '</strong><br><em>chave: ' + esc(n.chave) + (n.glifos && n.glifos.length ? ' (' + n.glifos.map(esc).join(' + ') + ')' : '') + ' · destino: ' + esc((byD[n.destino] || {}).nome) + ' · ' + esc(n.objeto) + '</em><br>' + esc(n.base_legal) + (n.nota ? '<br>' + esc(n.nota) : '') + '<br>Período eleitoral: ' + esc(n.defeso) + (n.verificado_em ? '<br>fonte verificada em ' + esc(n.verificado_em) : '<br><em>fonte a verificar</em>');
      g.on('mouseenter', evt => showTip(tip, evt)).on('mousemove', evt => showTip(tip, evt)).on('focus', () => showTip(tip, {clientX: 24, clientY: 24})).on('mouseleave', hideTip).on('blur', hideTip)
        .on('mouseenter.realce', () => svg.selectAll('.aresta').attr('stroke-opacity', .15).filter('.' + n.id).attr('stroke-opacity', 1)).on('mouseleave.realce', () => svg.selectAll('.aresta').attr('stroke-opacity', .75));
      no(g, n, 320, 26, n.ausencia ? null : n.cor, n.nome, null, n.ausencia);
    });
    MonitorMapas.legenda('legPreventivoSetor', [
      {cor: CH.regra, rotulo: 'contínuo: regra'}, {cor: CH.decreto, rotulo: 'tracejado: decreto (resposta)'}, {cor: CH.discricionaria, rotulo: 'pontilhado: discricionária'}, {cor: CH.direta, rotulo: 'duplo: execução direta'},
      ...Object.entries(P.glifos || {}).map(([k, v]) => ({cor: MonitorMapas.cor('abissal'), rotulo: 'glifo ' + k + ': ' + v})),
      {cor: MonitorMapas.NEUTRA, rotulo: 'contorno tracejado: ausência de rota'}]);
    // alternativa acessível: lista de definição
    const dl = document.getElementById('dlPreventivoSetor');
    if (dl) dl.innerHTML = P.setores.map(s => '<dt>' + esc(s.nome) + '</dt>' + s.rotas.map(r => '<dd><strong>' + esc(r.nome) + '</strong> — de ' + esc((byO[r.origem] || {}).nome) + ' para ' + esc((byD[r.destino] || {}).nome) + '; chave: ' + esc(r.chave) + (r.glifos && r.glifos.length ? ' (' + r.glifos.join(' + ') + ')' : '') + '; ' + esc(r.base_legal) + '; ' + esc(r.objeto) + '.</dd>').join('') + (s.ausencia ? '<dd><em>' + esc(s.ausencia.rotulo) + '</em> — ' + esc(s.ausencia.nota) + '</dd>' : '')).join('');
    // título-fato do dado
    const n = id => (P.setores.find(s => s.id === id) || {rotas: []}).rotas;
    const h = document.querySelector('#boxPreventivoSetor .figura-titulo');
    if (h) h.textContent = 'Saúde: ' + n('saude').filter(r => r.destino === 'mun').length + ' rotas ao município · Fogo: ' + n('fogo').length + ', uma por risco e plano · Seca: ' + n('seca').length + ', nenhuma por plano ou risco';
    fonteFigura('boxPreventivoSetor', {fontes: ['MARÉ', 'base legal citada por rota'], data: P.corte});
    const link = document.getElementById('linkComoLerPreventivo'), fonte = document.getElementById('comolerPreventivo'), dlg = document.getElementById('detailFin');
    if (link && fonte && dlg) link.addEventListener('click', e => { e.preventDefault(); document.getElementById('detailFinConteudo').innerHTML = fonte.innerHTML; if (!dlg.open) { if (typeof dlg.showModal === 'function') dlg.showModal(); else dlg.open = true; } });
  }).catch(() => { MonitorMapas.legenda('legPreventivoSetor', [{cor: MonitorMapas.NEUTRA, rotulo: 'dado não carregado'}]); fonteFigura('boxPreventivoSetor', {fontes: 'MARÉ', data: null}); });
})();
