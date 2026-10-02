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
  // `corteFin` saiu da página em 02/10/2026: a data da página é a da última coleta e vive nos
  // cartões. A guarda fica porque o JS é o mesmo para quem ainda tiver o elemento.
  { const e = document.getElementById('corteFin'); if (e) e.textContent = ROTAS.corte || '—'; }
  // 16/09/2026 (handover da voz, D3): o mapa por município do fogo ainda não tem coleta — a frase diz
  // "sem coleta até {corte}" com a data real, em vez de um traço solto no meio do texto.
  { const e = document.getElementById('notaFogoCorte'); if (e) e.textContent = ROTAS.corte || 'o corte'; }
  const ctx = MonitorMapas.contexto(BR_GEOJSON, 480, 460); const projection = ctx.projection;
  const desenharMapa = (svgId, legendaId, corDe, rotuloDe, itens) => MonitorMapas.desenharMapa(ctx, svgId, legendaId, corDe, rotuloDe, itens);
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
  /* 01/10/2026: os cartões das oito rotas saíram da página (bloco B). Guarda explícita para o
     bloco inteiro não escrever no vazio. */
  const _alvoRotas = document.getElementById('rotasCards');
  if (_alvoRotas) _alvoRotas.innerHTML = ROTAS.rotas.map(r => '<div class="cartao" style="border-left:4px solid '+r.cor+'"><h3 class="figura-titulo">'+r.n+' · '+esc(r.nome)+' <span class="sub">— chave: <em>'+esc(r.chave)+'</em>'+(r.ex_ante ? '' : ' · resposta')+'</span></h3>'
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
  // 01/10/2026: a lista de programas de exemplo saiu da página (bloco B).
  const _alvoProg = document.getElementById('programasLista');
  if (_alvoProg) _alvoProg.innerHTML = PROG.map(p => '<li><strong>' + esc(p.nome) + ':</strong> ' + esc(p.base) + '. ' + esc(p.regra) + ' <span class="u-muted">· ' + esc(p.lista) + '</span></li>').join('');
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
  // 02/10/2026: a guarda era o id da seção `prometeu`, que deixou de existir quando a página foi
  // reorganizada pela pergunta do leitor — e com ela TODO este bloco deixava de desenhar: o
  // gráfico dos compromissos, a série semanal e o caso do RS ficavam com a moldura vazia. A guarda
  // passa a ser o que o bloco realmente precisa: existir ao menos uma das figuras que ele desenha.
  if (!document.getElementById('cCompromissos') && !document.getElementById('svgSerie')
      && !document.getElementById('cRS')) return;
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
  /* Transferido aos municipios, MES A MES. A fonte publica por mes: a serie semanal anterior
   * repartia o mes em semanas que a fonte nao tem, e trazia a faixa do periodo eleitoral para
   * dentro de uma figura que o contrato de layout quer descritiva. Mes ainda sendo preenchido
   * aparece declarado, nunca como queda. */
  try {
    const cv = document.getElementById('cSerieFin');
    const T = await fetch('data/financiamento/municipios/transferencias_uniao.json').then(r => r.ok ? r.json() : null);
    const meses = (T && T.meses_lidos) || null;
    if (cv && typeof Chart !== 'undefined' && meses) {
      const MES = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez'];
      const chaves = Object.keys(meses).sort();
      const rotulo = k => MES[+k.slice(4) - 1] + '/' + k.slice(2, 4);
      const parcial = k => !!(meses[k] || {}).parcial;
      MonitorMapas.padraoGraficos(window.Chart);
      new Chart(cv, {type: 'bar', data: {labels: chaves.map(rotulo), datasets: [{
          label: 'R$ milhões', data: chaves.map(k => +((meses[k].soma || 0) / 1e6).toFixed(1)),
          backgroundColor: chaves.map(k => parcial(k) ? MonitorMapas.PALETA.semDado : MonitorMapas.PALETA.serie[0])}]},
        options: {animation: false, responsive: true, maintainAspectRatio: false,
          plugins: {legend: {display: false}},
          scales: {y: {beginAtZero: true, title: {display: true, text: 'R$ milhões'}}}}});
      const temParcial = chaves.some(parcial);
      MonitorMapas.legenda('legSerie', [{cor: MonitorMapas.PALETA.serie[0], rotulo: 'mês fechado'}]
        .concat(temParcial ? [{cor: MonitorMapas.PALETA.semDado, rotulo: 'mês ainda sendo preenchido pela fonte'}] : []));
      MonitorMapas.credito('boxSerie', {fontes: ['Portal da Transparência — Transferências de Recursos (dados abertos)'], data: T.atualizado_em});
      const linha = document.getElementById('linhaSerie');
      if (linha) linha.textContent = chaves.length + ' mês(es) lido(s) de 2026';
    } else if (document.getElementById('legSerie')) {
      MonitorMapas.legenda('legSerie', [{cor: MonitorMapas.NEUTRA, rotulo: 'série por mês sem coleta até o corte'}]);
    }
  } catch(e) {}
})();


// 15/09/2026 (handover "Dinheiro preventivo por setor"): rede D3 com a mesma gramática de #boxRede — origens à esquerda,
// três faixas (saúde, fogo, seca) ao centro, três destinos à direita; traço = chave; glifos de chave no meio da aresta;
// nó de ausência da seca desenhado como ausência (contorno tracejado, sem aresta). Lê data/financiamento/preventivo_setores.json.

/* =========================================================================
   O DINHEIRO PRÓPRIO DO MUNICÍPIO — camada A (24/09/2026)
   Despesa liquidada na subfunção 182 (Defesa Civil), declarada ao SICONFI, por habitante.
   Peso zero, como todo o financiamento.

   A regra que governa esta figura: as TRÊS classes de ausência são coisas diferentes e
   nenhuma delas é zero. "Sem lançamento na 182" não é "sem gasto em defesa civil" — muitos
   municípios lançam defesa civil em drenagem, urbanismo ou segurança. E um valor real
   pequeno NUNCA aparece como R$ 0,00: o dado guarda seis casas e a exibição diz
   "menos de R$ 0,01" em vez de arredondar para zero, que pareceria nada.
   ========================================================================= */

/* ===== Os três números do topo (bloco B do handover, 01/10/2026) =========================
 *
 * Cada um sai do dado, e cada um declara a sua fonte dentro do cartão. O que não foi coletado
 * aparece como lacuna declarada — não como zero, e não como travessão sem explicação.
 *
 * "Anunciado pela União" é o total do plano federal, e não a soma dos compromissos da lista: as
 * duas medidas provisórias estão DENTRO do plano (METODOLOGIA §73), e somá-las ao plano contaria o
 * mesmo dinheiro duas vezes. O Prepara RS e o Fecap ficam fora deste número porque são estaduais —
 * o rótulo diz "pela União".
 */
(async function numerosDoTopo(){
  const põe = (id, txt) => { const e = document.getElementById(id); if (e) e.textContent = txt; };
  const reais = v => 'R$ ' + (v / 1e9 >= 1
    ? (v / 1e9).toLocaleString('pt-BR', {maximumFractionDigits: 3}) + ' bi'
    : (v / 1e6).toLocaleString('pt-BR', {maximumFractionDigits: 1}) + ' mi');
  try {
    const C = await fetch('data/financiamento/compromissos_federais.json').then(r => r.ok ? r.json() : null);
    if (C && C.itens) {
      const federais = C.itens.filter(i => /^Federal/.test(i.esfera || ''));
      const plano = federais.find(i => /execução direta/i.test(i.esfera || ''));
      const anunciado = plano && plano.valor_total;
      põe('topoAnunciadoFonte', anunciado
        ? 'Plano federal do ciclo, no ato que o anunciou · corte de ' + (C.corte || '—')
        : 'sem valor anunciado verificado até o corte');
      /* `pago` vem da execução no Portal da Transparência. Enquanto a coleta não existir, o cartão
         DIZ que não existe: um "R$ 0" aqui afirmaria que nada foi pago, que é outra coisa. */
      const pagos = federais.map(i => i.pago).filter(v => typeof v === 'number');
      const soma = pagos.reduce((a, b) => a + b, 0);
      põe('topoPagoFonte', pagos.length
        ? 'Portal da Transparência · execução até o corte de ' + (C.corte || '—')
        : 'execução no Portal da Transparência ainda não coletada');
    }
  } catch (e) { /* lacuna: o cartão permanece em travessão, com a fonte dizendo o que falta */ }
  try {
    const D = await fetch('data/financiamento/municipios/despesa_182.json').then(r => r.ok ? r.json() : null);
    const r = D && D.resumo;
    if (r && typeof r.mediana_rs_hab === 'number') {
      põe('topoMedianaFonte', 'SICONFI e Censo 2022 · mediana de ' + (r.com_rs_hab || 0).toLocaleString('pt-BR')
        + ' municípios com lançamento na rubrica, exercício ' + (D.exercicio || '—'));
    }
  } catch (e) { /* idem */ }
})();

/* ===== "Quanto chegou à sua cidade" (01/10/2026) ==========================================
 *
 * O cartão que o bloco B não pôde publicar, porque faltava a coleta por município. Ele existe
 * agora: `coletar_transferencias_municipais.py` lê o download de dados abertos do Portal da
 * Transparência — sem chave de API — e agrega por município, mês e rota.
 *
 * Três coisas que este bloco NÃO faz, e que são a diferença entre uma consulta e uma vitrine:
 *
 *   - não soma mês marcado como `parcial` no total sem dizer que é parcial. O Portal publica o
 *     arquivo do mês e continua enchendo; setembro de 2026 veio com um décimo das linhas dos outros
 *     meses, e um total que engolisse isso mostraria uma queda do arquivo como queda do dinheiro.
 *   - não mostra "R$ 0" para cidade sem registro: diz que não há registro no período, que é outra
 *     afirmação.
 *   - não inventa a rota "emenda parlamentar": ela não é identificável nesta fonte, e a nota do
 *     cartão declara isso em vez de deixar o leitor supor que o resto é emenda.
 */
(async function consultaPorCidade(){
  const sel = document.getElementById('cidadeUF');
  const entrada = document.getElementById('cidadeNome');
  const lista = document.getElementById('cidadeLista');
  const conta = document.getElementById('cidadeConta');
  const saida = document.getElementById('cidadeResultado');
  if (!sel || !entrada || !lista || !saida) return;
  const esc = v => String(v == null ? '' : v).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const reais = v => 'R$ ' + Number(v || 0).toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2});
  const ROTULO = {constitucional: 'constitucional (FPM, cotas e royalties)', saude: 'saúde',
                  assistencia_social: 'assistência social', defesa_civil: 'defesa civil',
                  outras: 'outras legais, voluntárias e específicas'};

  let T, REF;
  try {
    [T, REF] = await Promise.all([
      fetch('data/financiamento/municipios/transferencias_uniao.json').then(r => r.ok ? r.json() : null),
      fetch('data/municipios_ibge_referencia.json').then(r => r.ok ? r.json() : null),
    ]);
  } catch (e) { T = REF = null; }
  if (!T || !T.municipios || !REF) {
    if (conta) conta.textContent = 'Transferências por município: sem coleta até o corte.';
    return;
  }
  const parciais = Object.entries(T.meses_lidos || {}).filter(([, v]) => v.parcial).map(([m]) => m);
  const porUF = {};
  const codigo = {};
  REF.forEach(m => {
    const c = String(m.codigo_ibge).padStart(7, '0');
    (porUF[m.uf] = porUF[m.uf] || []).push(m.nome);
    codigo[m.uf + '|' + m.nome.toLowerCase()] = c;
  });
  Object.keys(porUF).sort().forEach(uf => sel.insertAdjacentHTML('beforeend', `<option value="${uf}">${uf}</option>`));
  const meses = Object.keys(T.meses_lidos || {}).sort();
  if (conta) {
    conta.textContent = `${Object.keys(T.municipios).length.toLocaleString('pt-BR')} municípios com registro, `
      + `${meses.length} mês(es) lido(s)` + (parciais.length ? ` · ${parciais.length} marcado(s) como parcial` : '')
      + ` · atualizado em ${T.atualizado_em || '—'}`;
  }

  sel.addEventListener('change', () => {
    const nomes = porUF[sel.value] || [];
    lista.innerHTML = nomes.slice().sort((a, b) => a.localeCompare(b, 'pt-BR'))
      .map(n => `<option value="${esc(n)}"></option>`).join('');
    entrada.disabled = !sel.value;
    entrada.value = '';
    saida.hidden = true;
  });

  function mostrar(){
    const c = codigo[sel.value + '|' + (entrada.value || '').trim().toLowerCase()];
    if (!c) { saida.hidden = true; return; }
    const reg = T.municipios[c];
    saida.hidden = false;
    if (!reg) {
      /* Sem registro NÃO é zero: é ausência de registro no período lido, e o cartão diz isso. */
      saida.innerHTML = `<p class="u-mb-0"><strong>${esc(entrada.value)} (${esc(sel.value)})</strong>: `
        + `nenhuma transferência da União registrada nos ${meses.length} mês(es) lidos.</p>`;
      return;
    }
    const rotas = Object.entries(reg.por_rota || {}).sort((a, b) => b[1] - a[1]);
    const ultimos = Object.entries(reg.meses || {}).sort().slice(-3).reverse();
    const temParcial = ultimos.some(([m]) => parciais.includes(m));
    saida.innerHTML =
      `<p class="u-mb-2"><strong>${esc(entrada.value)} (${esc(sel.value)})</strong> recebeu `
      + `<strong>${reais(reg.total)}</strong> da União nos ${meses.length} mês(es) lidos de 2026.</p>`
      + '<p class="u-mb-1">Por caminho:</p><ul class="u-mb-2">'
      + rotas.map(([r, v]) => `<li>${esc(ROTULO[r] || r)}: ${reais(v)}</li>`).join('')
      + '</ul><p class="u-mb-1">Últimos meses:</p><ul class="u-mb-2">'
      + ultimos.map(([m, rr]) => {
          const soma = Object.values(rr).reduce((a, b) => a + b, 0);
          const mes = m.slice(4) + '/' + m.slice(0, 4);
          return `<li>${mes}: ${reais(soma)}${parciais.includes(m) ? ' <em>(mês parcial no Portal)</em>' : ''}</li>`;
        }).join('')
      + '</ul>'
      + (temParcial ? '<p class="note u-mb-1">Mês marcado como parcial: o Portal publica o arquivo do mês e continua preenchendo.</p>' : '')
      + '<p class="note u-mb-0">Emenda parlamentar não é identificável nesta fonte e por isso não aparece como caminho. '
      + '<a href="https://portaldatransparencia.gov.br/download-de-dados/transferencias/" target="_blank" rel="noopener">Dados abertos do Portal da Transparência</a>.</p>';
  }
  entrada.addEventListener('change', mostrar);
  entrada.addEventListener('input', () => { if ((entrada.value || '').length > 2) mostrar(); });
})();


/* ===== Cartões da semana (bloco B.1 do handover de 02/10/2026) =====
 * Só indicador DINÂMICO entra aqui, com fonte e data. O valor anunciado saiu dos cartões e virou
 * linha de contexto, porque ele não muda a cada coleta — e cartão que não muda vira moldura.
 *
 * Os dois primeiros dizem "sem dado nesta edição", com o motivo medido. É a mesma afirmação que a
 * página Imprensa faz (#509): as medidas federais publicam empenhado e pago em agregados SEM data
 * de pagamento, e o Portal da Transparência entrega a transferência a município por MÊS. Inventar
 * um recorte semanal aqui e declarar a falta lá seria o mesmo número com duas contas.
 */
/* ===== Os cartoes do topo (contrato de layout, 02/10/2026) =====
 * Tudo vem de data/financiamento/semana.json, escrito por gerar_financiamento_semana.py: o
 * recorte de cada cartao e o que a FONTE permite — mes fechado onde o Portal publica por mes,
 * sete dias onde o ato tem data. A pagina nao recalcula nada aqui, e por isso nao pode divergir
 * do portao de coerencia.
 */
(function cartoesDoTopo(){
  const el = id => document.getElementById(id);
  const reais = v => 'R$ ' + Number(v || 0).toLocaleString('pt-BR', {maximumFractionDigits: 0});
  const n = v => Number(v || 0).toLocaleString('pt-BR');
  /* Valor de cartao em forma CURTA. O valor cheio de uma transferencia mensal passa de doze
   * digitos e estourava a largura em 390 px — e um numero que sai da tela nao e um numero lido.
   * O valor exato continua na linha de fonte do cartao. */
  const reaisCurto = v => {
    const x = Number(v || 0);
    if (x >= 1e9) return 'R$ ' + (x / 1e9).toLocaleString('pt-BR', {maximumFractionDigits: 1}) + ' bi';
    if (x >= 1e6) return 'R$ ' + (x / 1e6).toLocaleString('pt-BR', {maximumFractionDigits: 1}) + ' mi';
    if (x >= 1e3) return 'R$ ' + (x / 1e3).toLocaleString('pt-BR', {maximumFractionDigits: 0}) + ' mil';
    return 'R$ ' + x.toLocaleString('pt-BR', {maximumFractionDigits: 0});
  };
  const esc = v => String(v == null ? '' : v).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

  fetch('data/financiamento/semana.json').then(r => r.ok ? r.json() : null).then(S => {
    const por = {};
    ((S || {}).cartoes || []).forEach(c => { por[c.id] = c; });
    const escrever = (ident, idValor, idRotulo, idFonte, formata, rotuloBase) => {
      const c = por[ident];
      if (!c) { if (el(idValor)) el(idValor).textContent = 'sem coleta'; return; }
      if (c.sem_coleta) {
        if (el(idValor)) el(idValor).textContent = 'sem coleta';
        if (el(idFonte)) el(idFonte).textContent = c.detalhe || '';
        return;
      }
      if (el(idValor)) el(idValor).textContent = formata(c.valor);
      if (idRotulo && el(idRotulo)) el(idRotulo).textContent = rotuloBase + ', no ' + c.periodo;
      if (el(idFonte)) {
        const exato = typeof c.valor === 'number' && c.unidade === 'reais' ? reais(c.valor) + ' · ' : '';
        el(idFonte).textContent = exato + c.fonte + (c.detalhe ? ' · ' + c.detalhe : '');
      }
    };
    escrever('pago_periodo_mp', 'topoPagoMes', 'topoPagoMesRotulo', 'topoPagoMesFonte', reaisCurto,
             'pago pelas ações reforçadas pelas medidas provisórias');
    escrever('transferido_municipios_periodo', 'topoTransfMes', 'topoTransfMesRotulo',
             'topoTransfMesFonte', reaisCurto, 'transferido pela União aos municípios');
    escrever('resposta_liberado_semana', 'topoRespostaSemana', null, 'topoRespostaFonte', reaisCurto, null);
    const resp = por['resposta_liberado_semana'];
    if (resp && !resp.sem_coleta && el('topoRespostaMunicipios')) {
      el('topoRespostaMunicipios').textContent = 'autorizado em portarias de resposta nos últimos '
        + 'sete dias' + (resp.detalhe ? ' · ' + resp.detalhe : '');
    }
    /* O cartao de atos SO aparece quando e maior que zero — e a regra e do contrato: grade de
     * tres com um quarto cartao vazio e pior que grade de tres. */
    const atos = por['atos_federais_semana'];
    if (atos && !atos.sem_coleta && Number(atos.valor) > 0) {
      if (el('cartaoAtosSemana')) el('cartaoAtosSemana').hidden = false;
      if (el('topoAtosSemana')) el('topoAtosSemana').textContent = n(atos.valor);
      if (el('topoAtosSemanaFonte')) {
        el('topoAtosSemanaFonte').textContent = atos.fonte + (atos.detalhe ? ' · ' + atos.detalhe : '');
      }
    }
  }).catch(() => {});

  /* O anunciado vira CONTEXTO, nao cartao: ele nao muda a cada coleta. */
  fetch('data/financiamento/compromissos_federais.json').then(r => r.ok ? r.json() : null).then(C => {
    const itens = (C || {}).itens || [];
    const anunciado = itens.reduce((a, x) => a + Number(x.valor_total || 0), 0);
    const ctx = el('finContexto');
    if (ctx && anunciado) {
      ctx.textContent = 'Contexto: os atos federais lidos até agora somam ' + reais(anunciado)
        + ' anunciados para o ciclo. Anúncio não é pagamento, e o valor anunciado não muda a cada '
        + 'coleta.';
    }
  }).catch(() => {});
})();

/* ===== Quanto chegou a cada estado (bloco B.2) =====
 * Mapa por habitante, grade dos 27 e ficha ao clicar — o desenho da inicial. Por habitante porque
 * o total bruto só diz que São Paulo é grande: a pergunta do leitor é quanto chegou onde ele mora.
 */
(async function porEstado(){
  const svg = document.getElementById('mapaTransfUF');
  const grade = document.getElementById('regionsFin');
  if (!svg && !grade) return;
  const esc = v => String(v == null ? '' : v).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const reais = v => 'R$ ' + Number(v || 0).toLocaleString('pt-BR', {maximumFractionDigits: 0});
  const umaCasa = v => Number(v || 0).toLocaleString('pt-BR', {minimumFractionDigits: 1, maximumFractionDigits: 1});
  let T, REF, POP, GEO;
  try {
    [T, REF, POP, GEO] = await Promise.all([
      fetch('data/financiamento/municipios/transferencias_uniao.json').then(r => r.ok ? r.json() : null),
      fetch('data/municipios_ibge_referencia.json').then(r => r.ok ? r.json() : null),
      fetch('data/populacao_censo2022.json').then(r => r.ok ? r.json() : null),
      fetch('data/geo_uf.json').then(r => r.ok ? r.json() : null),
    ]);
  } catch (e) { T = null; }
  const leg = document.getElementById('legTransfUF');
  if (!T || !T.municipios || !REF || !POP) {
    if (leg) leg.innerHTML = '<span class="escala">Transferências por município: sem coleta até o corte.</span>';
    return;
  }
  const ref = Array.isArray(REF) ? REF : Object.values(REF);
  const ufDe = {};
  ref.forEach(m => { ufDe[String(m.codigo_ibge).padStart(7, '0')] = m.uf; });
  const porUF = {}, popUF = {};
  Object.entries(T.municipios).forEach(([cod, m]) => {
    const uf = ufDe[cod]; if (!uf) return;
    porUF[uf] = (porUF[uf] || 0) + Number(m.total || Object.values(m.por_rota || {}).reduce((a, b) => a + Number(b || 0), 0));
    popUF[uf] = (popUF[uf] || 0) + Number(POP[cod] || 0);
  });
  const porHab = {};
  Object.keys(porUF).forEach(uf => { if (popUF[uf]) porHab[uf] = porUF[uf] / popUF[uf]; });
  const valores = Object.values(porHab);
  const max = valores.length ? Math.max(...valores) : 0;
  if (svg && GEO && window.MonitorMapas) {
    const ctx = MonitorMapas.contexto(GEO, 480, 460);
    const rampa = MonitorMapas.PALETA.atmosfera.chuva_claro.rampa;
    const cor = uf => {
      const v = porHab[uf];
      if (v == null || !max) return MonitorMapas.NEUTRA;
      return rampa[Math.min(rampa.length - 1, Math.floor(v / max * rampa.length))];
    };
    MonitorMapas.fundo && MonitorMapas.fundo('mapaTransfUF', 'chuva_claro');
    MonitorMapas.ufs(ctx, 'mapaTransfUF', cor, uf => porHab[uf] == null
      ? uf + ': sem mês lido'
      : uf + ': ' + reais(porHab[uf]) + ' por habitante');
    MonitorMapas.credito('boxTransfUF', {
      fontes: ['Portal da Transparência (transferências a municípios)', 'Censo 2022 (IBGE)'],
      data: T.atualizado_em});
    MonitorMapas.legenda('legTransfUF', [
      ...rampa.map((c, i) => ({cor: c, rotulo: i === 0 ? 'menor' : (i === rampa.length - 1 ? 'maior' : '·')})),
      {cor: MonitorMapas.NEUTRA, rotulo: 'sem mês lido'}]);
  }
  const linha = document.getElementById('linhaTransfUF');
  if (linha) {
    const meses = Object.keys(T.meses_lidos || {}).sort();
    linha.textContent = meses.length + ' mês(es) lido(s) de 2026 · atualizado em ' + (T.atualizado_em || '—');
  }
  /* A lista dos 27, cartao proprio pelo contrato: o mapa ordena pela cor, a lista ordena pelo
   * numero — e quem procura o seu estado procura numa lista. */
  const dlLista = document.getElementById('dlListaEstadosFin');
  if (dlLista) {
    const UFS27 = ('AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO').split(' ');
    const ordem = UFS27.slice().sort((a, b) => (porHab[b] || -1) - (porHab[a] || -1));
    dlLista.innerHTML = ordem.map(uf => '<dt>' + esc(uf) + '</dt><dd>' + (porHab[uf] == null
      ? 'sem mês lido até o corte'
      : reais(porHab[uf]) + ' por habitante · ' + reais(porUF[uf]) + ' no total') + '</dd>').join('');
    const comDado = UFS27.filter(uf => porHab[uf] != null).length;
    const lin = document.getElementById('linhaListaEstadosFin');
    if (lin) lin.textContent = comDado + ' de 27 estados com mês lido';
    if (window.MonitorMapas) {
      MonitorMapas.legenda('legListaEstadosFin', [{cor: MonitorMapas.NEUTRA, rotulo: 'estado sem mês lido aparece como tal, nunca como R$ 0'}]);
      MonitorMapas.credito('boxListaEstadosFin', {
        fontes: ['Portal da Transparência (transferências a municípios)', 'Censo 2022 (IBGE)'],
        data: T.atualizado_em});
    }
  }
  const dl = document.getElementById('dlTransfUF');
  if (dl) {
    dl.innerHTML = Object.keys(porHab).sort((a, b) => porHab[b] - porHab[a]).map(uf =>
      '<dt>' + esc(uf) + '</dt><dd>' + reais(porHab[uf]) + ' por habitante · ' + reais(porUF[uf]) + ' no total</dd>').join('');
  }
  if (grade) {
    /* Os 27, SEMPRE. A versao anterior listava Object.keys(porHab) e entregava 26 celulas quando
     * um estado nao tinha mes lido: o leitor via 26 estados e nao tinha como saber qual faltava.
     * Estado sem mes lido aparece, e aparece dizendo que nao tem mes lido. */
    const UFS27 = ('AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO').split(' ');
    grade.innerHTML = UFS27.map(uf =>
      '<button type="button" class="tile" data-uf="' + esc(uf) + '">'
      + '<span class="tile-uf">' + esc(uf) + '</span>'
      + '<span class="tile-face">' + (porHab[uf] == null
          ? '<span>sem mês lido</span><span>&nbsp;</span>'
          : '<span>' + reais(porHab[uf]) + ' por hab.</span>'
            + '<span>' + reais(porUF[uf]) + ' no total</span>')
      + '</span></button>').join('');
    const dlg = document.getElementById('detailFin');
    const corpo = document.getElementById('detailFinConteudo');
    const fechar = document.getElementById('detailFinFechar');
    if (fechar && dlg) fechar.addEventListener('click', () => dlg.close());
    grade.addEventListener('click', ev => {
      const b = ev.target.closest('.tile'); if (!b || !dlg) return;
      const uf = b.dataset.uf;
      if (porHab[uf] == null) {
        corpo.innerHTML = '<h3>' + esc(uf) + '</h3><p>Nenhum mês de transferência lido para este '
          + 'estado até o corte. Sem mês lido não é R$ 0.</p>';
        dlg.showModal();
        return;
      }
      corpo.innerHTML = '<h3>' + esc(uf) + '</h3>'
        + '<p>Transferido pela União aos municípios nos meses lidos de 2026: <strong>'
        + reais(porUF[uf]) + '</strong>, ou <strong>' + reais(porHab[uf])
        + '</strong> por habitante (Censo 2022: ' + Number(popUF[uf]).toLocaleString('pt-BR')
        + ' habitantes).</p>'
        + '<p class="note">Soma das rotas constitucional, saúde, assistência social, defesa civil e '
        + 'outras. Transferido não é gasto: o que a prefeitura fez com o dinheiro é outro registro.</p>';
      dlg.showModal();
    });
  }
})();


/* ===== Cartoes criados pelo contrato de layout (02/10/2026) =====
 * Cada lista responde a uma pergunta que o mapa nao responde: qual e o meu, quanto foi, por que
 * ato. Em todas, ausencia aparece como ausencia — nunca como R$ 0.
 */
(function cartoesDoContratoFin(){
  const el = id => document.getElementById(id);
  const esc = v => String(v == null ? '' : v).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const reais = v => 'R$ ' + Number(v || 0).toLocaleString('pt-BR', {maximumFractionDigits: 0});
  const umaCasa = v => Number(v || 0).toLocaleString('pt-BR', {minimumFractionDigits: 1, maximumFractionDigits: 1});
  const UFS27 = ('AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO').split(' ');
  const MES = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto',
               'setembro', 'outubro', 'novembro', 'dezembro'];
  const mesLegivel = k => (/^\d{6}$/.test(String(k)) ? MES[+String(k).slice(4) - 1] + ' de ' + String(k).slice(0, 4) : String(k));

  /* 1 · Cada compromisso federal, com o ato que o criou. */
  Promise.all([
    fetch('data/financiamento/compromissos_federais.json').then(r => r.ok ? r.json() : null),
    fetch('data/financiamento/mps_2026.json').then(r => r.ok ? r.json() : null),
  ]).then(([C, MPS]) => {
    const dl = el('dlListaCompromissos');
    if (!dl) return;
    const linhas = ((MPS || {}).mps || []).map(m => ({
      nome: m.numero + ' · ' + (m.tema || ''), url: (m.fontes || [])[0],
      anunciado: m.valor, pago: (m.execucao || {}).pago, data: m.publicada_em,
    })).concat(((C || {}).itens || []).map(c => ({
      nome: c.nome, url: c.url, anunciado: c.valor_total, pago: (c.execucao || {}).pago,
      data: c.data || c.instrumento,
    })));
    if (!linhas.length) {
      dl.innerHTML = '<dt>Sem coleta</dt><dd>Nenhum compromisso federal lido até o corte.</dd>';
      return;
    }
    dl.innerHTML = linhas.map(l => {
      const nome = l.url ? '<a href="' + esc(l.url) + '" target="_blank" rel="noopener">' + esc(l.nome) + '</a>' : esc(l.nome);
      const pago = l.pago == null ? 'pago: sem coleta até o corte' : 'pago: ' + reais(l.pago);
      return '<dt>' + nome + '</dt><dd>anunciado: ' + reais(l.anunciado) + ' · ' + pago
        + (l.data ? ' · ' + esc(l.data) : '') + '</dd>';
    }).join('');
    if (el('linhaListaCompromissos')) el('linhaListaCompromissos').textContent = linhas.length + ' compromisso(s) lido(s)';
    if (window.MonitorMapas) {
      MonitorMapas.legenda('legListaCompromissos', [{cor: MonitorMapas.PALETA.semDado, rotulo: 'compromisso sem execução coletada aparece como tal'}]);
      MonitorMapas.credito('boxListaCompromissos', {fontes: ['as citadas em cada compromisso', 'Portal da Transparência (execução)'],
                                                    data: (C || {}).corte || (MPS || {}).gerado_em});
    }
  }).catch(() => {});

  /* 2 · Municipios com recursos autorizados por portaria, do maior ao menor. */
  fetch('data/resposta/recursos_liberados.json').then(r => r.ok ? r.json() : null).then(R => {
    const dl = el('dlRespostaMunicipios');
    if (!dl) return;
    const muns = Object.values((R || {}).municipios || {});
    if (!muns.length) {
      dl.innerHTML = '<dt>Sem coleta</dt><dd>Nenhuma portaria de recursos lida até o corte.</dd>';
      if (el('linhaRespostaMunicipios')) el('linhaRespostaMunicipios').textContent = 'sem coleta até o corte';
      return;
    }
    const ordem = muns.slice().sort((a, b) => Number(b.total_autorizado || 0) - Number(a.total_autorizado || 0));
    dl.innerHTML = ordem.map(m => {
      const acoes = Object.entries(m.por_acao || {}).map(([k, v]) => esc(k) + ': ' + reais(v)).join(' · ');
      const atos = (m.atos || []).map(a => a.url
        ? '<a href="' + esc(a.url) + '" target="_blank" rel="noopener">Portaria ' + esc(a.portaria) + '</a>'
        : 'Portaria ' + esc(a.portaria)).join(', ');
      return '<dt>' + esc(m.nome) + ' (' + esc(m.uf) + ')</dt><dd>' + reais(m.total_autorizado)
        + (acoes ? ' · ' + acoes : '') + (atos ? ' · ' + atos : '') + '</dd>';
    }).join('');
    if (el('linhaRespostaMunicipios')) {
      el('linhaRespostaMunicipios').textContent = ordem.length + ' município(s) com portaria no ciclo';
    }
    if (window.MonitorMapas) {
      MonitorMapas.legenda('legRespostaMunicipios', [{cor: MonitorMapas.NEUTRA, rotulo: 'autorizado por portaria; a saída do dinheiro é outro registro'}]);
      MonitorMapas.credito('boxRespostaMunicipios', {fontes: ['Portarias da Defesa Civil nacional no Diário Oficial da União'],
                                                     data: (R || {}).atualizado_em});
    }
  }).catch(() => {});

  /* 3 · Os municipios que mais receberam no ultimo mes FECHADO. Mes parcial nao entra: ele
   * ordenaria a lista pelo que a planilha ainda nao preencheu. */
  Promise.all([
    fetch('data/financiamento/municipios/transferencias_uniao.json').then(r => r.ok ? r.json() : null),
    fetch('data/populacao_censo2022.json').then(r => r.ok ? r.json() : null),
    fetch('data/municipios_ibge_referencia.json').then(r => r.ok ? r.json() : null),
  ]).then(([T, POP, REF]) => {
    const dl = el('dlTransfRecentes');
    if (!dl) return;
    const meses = (T || {}).meses_lidos || {};
    const fechados = Object.keys(meses).filter(k => !(meses[k] || {}).parcial).sort();
    if (!fechados.length || !T.municipios || !REF) {
      dl.innerHTML = '<dt>Sem coleta</dt><dd>Nenhum mês fechado de transferências lido até o corte.</dd>';
      return;
    }
    const mes = fechados[fechados.length - 1];
    const nome = {};
    (Array.isArray(REF) ? REF : Object.values(REF)).forEach(m => {
      nome[String(m.codigo_ibge).padStart(7, '0')] = m.nome + ' (' + m.uf + ')';
    });
    const linhas = [];
    Object.entries(T.municipios).forEach(([cod, m]) => {
      const doMes = (m.meses || {})[mes];
      if (!doMes) return;
      const total = Object.values(doMes).reduce((a, b) => a + Number(b || 0), 0);
      if (!total) return;
      const pop = Number((POP || {})[cod] || 0);
      linhas.push({cod: cod, total: total, hab: pop ? total / pop : null});
    });
    linhas.sort((a, b) => b.total - a.total);
    dl.innerHTML = linhas.slice(0, 30).map(l => '<dt>' + esc(nome[l.cod] || l.cod) + '</dt><dd>'
      + reais(l.total) + (l.hab == null ? '' : ' · ' + reais(l.hab) + ' por habitante') + '</dd>').join('');
    if (el('linhaTransfRecentes')) {
      el('linhaTransfRecentes').textContent = 'mês de ' + mesLegivel(mes) + ' · '
        + linhas.length.toLocaleString('pt-BR') + ' municípios com transferência';
    }
    if (window.MonitorMapas) {
      MonitorMapas.legenda('legTransfRecentes', [{cor: MonitorMapas.NEUTRA, rotulo: 'os 30 maiores do mês; a lista completa está nos dados abertos'}]);
      MonitorMapas.credito('boxTransfRecentes', {fontes: ['Portal da Transparência (transferências a municípios)', 'Censo 2022 (IBGE)'],
                                                 data: (T || {}).atualizado_em});
    }
  }).catch(() => {});

  /* 4 · O que o municipio gasta do proprio bolso: mapa POR ESTADO (media dos municipios com
   * lancamento), lista por municipio e o cartao de como ler. Municipio sem lancamento na
   * subfuncao 182 nao entra na media: ele nao gastou zero, ele lancou em outro lugar. */
  Promise.all([
    fetch('data/financiamento/municipios/despesa_182.json').then(r => r.ok ? r.json() : null),
    fetch('data/geo_uf.json').then(r => r.ok ? r.json() : null),
  ]).then(([D, GEO]) => {
    const muns = Object.values((D || {}).municipios || {});
    const comValor = muns.filter(m => m.rs_hab != null);
    if (!comValor.length) {
      if (el('legDespesaUF')) el('legDespesaUF').innerHTML = '<span class="escala">Despesa própria em defesa civil: sem coleta até o corte.</span>';
      return;
    }
    const soma = {}, conta = {};
    comValor.forEach(m => {
      soma[m.uf] = (soma[m.uf] || 0) + Number(m.rs_hab);
      conta[m.uf] = (conta[m.uf] || 0) + 1;
    });
    const media = {};
    Object.keys(soma).forEach(uf => { media[uf] = soma[uf] / conta[uf]; });
    if (el('mapaDespesaUF') && GEO && window.MonitorMapas) {
      const ctx = MonitorMapas.contexto(GEO, 480, 460);
      const rampa = MonitorMapas.PALETA.rampaPreparo;
      const max = Math.max(...Object.values(media));
      MonitorMapas.ufs(ctx, 'mapaDespesaUF',
        uf => media[uf] == null ? MonitorMapas.NEUTRA : rampa[Math.min(rampa.length - 1, Math.floor(media[uf] / max * rampa.length))],
        uf => media[uf] == null
          ? uf + ': nenhum município com lançamento na subfunção 182'
          : uf + ': ' + reais(media[uf]) + ' por habitante, média de ' + conta[uf] + ' município(s) com lançamento');
      MonitorMapas.legenda('legDespesaUF', [
        ...rampa.map((c, i) => ({cor: c, rotulo: i === 0 ? 'menor' : (i === rampa.length - 1 ? 'maior' : '·')})),
        {cor: MonitorMapas.NEUTRA, rotulo: 'sem município com lançamento'}]);
      MonitorMapas.credito('boxDespesaUF', {fontes: ['Siconfi — Declaração de Contas Anuais (Anexo I-E)', 'Censo 2022 (IBGE)'],
                                            data: (D || {}).gerado_em});
    }
    if (el('dlDespesaUF')) {
      el('dlDespesaUF').innerHTML = UFS27.map(uf => '<dt>' + esc(uf) + '</dt><dd>' + (media[uf] == null
        ? 'nenhum município com lançamento na subfunção 182'
        : reais(media[uf]) + ' por habitante · ' + conta[uf] + ' município(s) com lançamento') + '</dd>').join('');
    }
    if (el('linhaDespesaUF')) {
      el('linhaDespesaUF').textContent = comValor.length.toLocaleString('pt-BR') + ' de '
        + muns.length.toLocaleString('pt-BR') + ' municípios com lançamento · exercício '
        + ((D || {}).exercicio || '—');
    }
    const dlM = el('dlDespesaMunicipios');
    if (dlM) {
      const ordem = comValor.slice().sort((a, b) => Number(b.rs_hab) - Number(a.rs_hab)).slice(0, 30);
      dlM.innerHTML = ordem.map(m => '<dt>' + esc(m.nome) + ' (' + esc(m.uf) + ')</dt><dd>'
        + reais(m.rs_hab) + ' por habitante</dd>').join('');
      if (el('linhaDespesaMunicipios')) {
        el('linhaDespesaMunicipios').textContent = 'os 30 maiores por habitante · exercício '
          + ((D || {}).exercicio || '—');
      }
      if (window.MonitorMapas) {
        MonitorMapas.legenda('legDespesaMunicipios', [{cor: MonitorMapas.NEUTRA, rotulo: 'município sem lançamento na subfunção 182 não aparece como zero'}]);
        MonitorMapas.credito('boxDespesaMunicipios', {fontes: ['Siconfi — Declaração de Contas Anuais (Anexo I-E)', 'Censo 2022 (IBGE)'],
                                                      data: (D || {}).gerado_em});
      }
    }
    if (el('linhaComoLerDespesa')) el('linhaComoLerDespesa').textContent = 'exercício ' + ((D || {}).exercicio || '—');
    if (window.MonitorMapas) {
      MonitorMapas.legenda('legComoLerDespesa', [{cor: MonitorMapas.NEUTRA, rotulo: 'sem lançamento não é gasto zero'}]);
      MonitorMapas.credito('boxComoLerDespesa', {fontes: ['Siconfi — Declaração de Contas Anuais (Anexo I-E)'], data: (D || {}).gerado_em});
    }
    const resumo = el('proprioResumo');
    if (resumo) {
      resumo.textContent = comValor.length.toLocaleString('pt-BR') + ' de '
        + muns.length.toLocaleString('pt-BR') + ' municípios declararam despesa na subfunção 182 '
        + 'no exercício ' + ((D || {}).exercicio || '—') + '. Os demais lançaram a defesa civil em '
        + 'outra rubrica ou não declararam: não localizamos lançamento até o corte.';
    }
  }).catch(() => {});

  /* 5 · O credito do cartao de busca: ele tem figura e precisa dizer de onde vem. */
  fetch('data/financiamento/municipios/transferencias_uniao.json').then(r => r.ok ? r.json() : null).then(T => {
    if (!window.MonitorMapas) return;
    const meses = Object.keys((T || {}).meses_lidos || {}).length;
    if (el('linhaBuscaCidade')) el('linhaBuscaCidade').textContent = meses + ' mês(es) lido(s) de 2026';
    MonitorMapas.legenda('legBuscaCidade', [{cor: MonitorMapas.NEUTRA, rotulo: 'cidade sem registro no período lido aparece como tal, nunca como R$ 0'}]);
    MonitorMapas.credito('boxBuscaCidade', {fontes: ['Portal da Transparência (transferências a municípios)', 'Portarias da Defesa Civil nacional no DOU'],
                                            data: (T || {}).atualizado_em});
  }).catch(() => {});

  /* 6 · O credito do caso do fogo: texto com fonte, como qualquer figura. */
  if (window.MonitorMapas && el('boxCasoFogo')) {
    if (el('linhaCasoFogo')) el('linhaCasoFogo').textContent = 'edital de 2025 e Decreto 13.013/2026';
    MonitorMapas.legenda('legCasoFogo', [{cor: MonitorMapas.NEUTRA, rotulo: 'resultado por município não localizado até o corte'}]);
    MonitorMapas.credito('boxCasoFogo', {fontes: ['Fundo Nacional do Meio Ambiente (edital de 2025)', 'Lei 15.143/2025 e Decreto 13.013/2026'],
                                         data: 'sem coleta até o corte'});
  }
})();
