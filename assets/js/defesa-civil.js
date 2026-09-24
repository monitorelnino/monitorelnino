// ===== defesa-civil.html · bloco 1 (extraído em 06/09/2026, CSP sem unsafe-inline) =====
let RESP, RESP_SERIE, RESP_Q;
let BR_GEOJSON, PCT_POR_UF, MAP_POINTS, MARE, DATA, TRANSFERENCIAS, CONSIST, ATOS_RESPOSTA, MUN_REF, POP_CENSO, VRESUMO,
    MUN_COD = {}, MUN_LATLON = {}, POP_UF = {};
async function __load(){
  try { const __m = (await fetch('data/meta.json').then(r => r.ok ? r.json() : null) || {}); window.__metaCorte = __m.corte; window.__metaAtualizado = __m.atualizado_em || __m.corte; } catch(e) {}
  let __ref;
  [BR_GEOJSON, PCT_POR_UF, MAP_POINTS, MARE, DATA, TRANSFERENCIAS, CONSIST, ATOS_RESPOSTA, __ref, POP_CENSO, VRESUMO] = await Promise.all(
    ['geo_uf','percentual_uf','pontos_mapa','indice','estados','transferencias','consist','atos_resposta','municipios_ibge_referencia','populacao_censo2022','verificacao_resumo']
      .map(f => fetch('data/' + f + '.json').then(r => {
        if(!r.ok) throw new Error('Falha ao carregar data/' + f + '.json');
        return r.json();
      }))
  );
  // v3.1 §3: contador de resposta (arquivos próprios; peso zero)
  try { [RESP, RESP_SERIE, RESP_Q] = await Promise.all(['data/resposta/por_uf.json','data/resposta/serie_semanal.json','data/resposta/quadrantes.json'].map(f => fetch(f).then(r => r.ok ? r.json() : null))); } catch(e) { RESP = RESP_SERIE = RESP_Q = null; }
  MUN_REF = {};
  window.REF_MUNICIPIOS = __ref; // v2.2.4: usado pelo mapa de nível de verificação
  __ref.forEach(m => (MUN_REF[m.uf] = MUN_REF[m.uf] || []).push(m.nome));
  __ref.forEach(m => {
    const c = String(m.codigo_ibge).padStart(7, '0');
    MUN_COD[m.uf + '|' + m.nome] = c;
    MUN_LATLON[m.uf + '|' + m.nome] = [m.lon, m.lat];
    POP_UF[m.uf] = (POP_UF[m.uf] || 0) + (POP_CENSO[c] || 0);
  });
  __init();
}
function __init(){
// =========================================================
// ANÁLISES — gráficos derivados do mesmo objeto DATA
// =========================================================
MonitorMapas.padraoGraficos(window.Chart);

// ---- 1. (donut nacional removido da página em 21/09/2026 — pedido editorial: consolidar mapas, ver seção "Ver mais" removida) ----

// ---- 3. Financiamento federal por área (R$ reais, calculados a partir de Registro_Federal) ----
// (gráfico 3 — financiamento federal por área — migrou para financiamento.html, E9)

// ---- 4. (status das 27 capitais removido da página em 21/09/2026 — mesmo pedido do item 1 acima) ----

// ---- 5. Timeline de reatividade (dias em relação ao Boletim nº1, 29/06/2026) ----


// =========================================================
// MAPAS GEOGRÁFICOS (D3 — projeção real das 27 UFs)
// =========================================================
const showTip = MonitorMapas.showTip, hideTip = MonitorMapas.hideTip;

const projection = d3.geoMercator().fitSize([480,460], BR_GEOJSON);
const pathGen = d3.geoPath().projection(projection);

// ---- Mapa 1: pontos por categoria de ato (Fase 1 + Fase 2) ----
const CAT_STYLE = {
  plano:            {cor:MonitorMapas.PALETA.categorias.plano, r:5.5, label:'Plano publicado'},
  plano_antigo:     {cor:MonitorMapas.PALETA.categorias.plano_antigo, r:5,   label:'Plano vigente, de ciclo anterior'},
  plano_elaboracao: {cor:MonitorMapas.PALETA.categorias.plano_elaboracao, r:5,   label:'Plano em elaboração'},
  estrutura:        {cor:MonitorMapas.PALETA.categorias.estrutura, r:5,   label:'Estrutura de coordenação'},
  decreto:          {cor:MonitorMapas.PALETA.categorias.decreto, r:4.5, label:'Decreto de emergência'},
  coberto_estadual: {cor:MonitorMapas.PALETA.categorias.coberto_estadual, r:4.5, label:'Coberto pelo estado'},
  nao_el_nino:      {cor:MonitorMapas.PALETA.categorias.nao_el_nino, r:4,   label:'Não é El Niño'},
  nao_localizado:   {cor:MonitorMapas.PALETA.categorias.nao_localizado, r:4.5, label:'Nenhum ato localizado'},
  nao_verificado:   {cor:MonitorMapas.PALETA.categorias.nao_verificado, r:4.5, label:'Ainda não verificado'},
};

// 13/09/2026 (auditoria de visualizações, consolidação): quatro mapas municipais viram dois pares
// com seletor de camada — renderiza as duas camadas do par uma vez (sem custo extra de redesenho a
// cada troca; mapNiveis em especial é caro, 5.571 pontos) e alterna a visibilidade por [hidden].
function ligarSeletorDeCamada(selId, pares){
  const sel = document.getElementById(selId);
  if (!sel) return;
  function aplicar(){
    pares.forEach(p => {
      const ativo = p.valor === sel.value;
      const svg = document.getElementById(p.svg); if (svg) svg.hidden = !ativo;
      const leg = document.getElementById(p.legenda); if (leg) leg.hidden = !ativo;
    });
  }
  sel.addEventListener('change', aplicar);
  aplicar();
}

const svgPoints = d3.select('#mapPoints');
svgPoints.append('g').selectAll('path')
  .data(BR_GEOJSON.features).join('path')
  .attr('d', pathGen).attr('fill', MonitorMapas.cor('zebra')).attr('class', 'uf-path')
  .on('mouseenter', (evt,d)=> showTip(`<strong>${d.properties.name}</strong>`, evt))
  .on('mousemove', (evt)=> showTip(tooltip.innerHTML, evt))
  .on('mouseleave', hideTip);

const contaveis = MAP_POINTS.filter(p => p.categoria==='plano' || p.categoria==='plano_antigo' || p.categoria==='decreto').length;
(document.getElementById('countComAto')||{}).textContent = contaveis;

// ordenar para desenhar "plano" por cima de "decreto" por cima de "não localizado"
const drawOrder = ['nao_verificado','nao_localizado','nao_el_nino','coberto_estadual','plano_elaboracao','estrutura','decreto','plano_antigo','plano'];
const sortedPoints = [...MAP_POINTS].sort((a,b)=> drawOrder.indexOf(a.categoria) - drawOrder.indexOf(b.categoria));

svgPoints.append('g').selectAll('circle')
  .data(sortedPoints).join('circle')
  .attr('cx', d=>projection([d.lon,d.lat])[0])
  .attr('cy', d=>projection([d.lon,d.lat])[1])
  .attr('r', d=>CAT_STYLE[d.categoria].r)
  .attr('fill', d=>CAT_STYLE[d.categoria].cor)
  .attr('stroke', d=>d.categoria==='plano' ? MonitorMapas.cor('branco') : MonitorMapas.cor('branco'))
  .attr('stroke-width', d=>d.categoria==='plano' ? 1.6 : 1)
  .attr('stroke-dasharray', d=>(d.categoria==='nao_localizado'||d.categoria==='nao_verificado') ? '2,1.5' : null)
  // 22/09/2026 (§155): tag de prioritário no tooltip — conjunto vem de data/municipios_prioritarios.json (carregado abaixo, no mapa de prioritários)
  .on('mouseenter', (evt,d)=> showTip(`<strong>${d.nome} (${d.uf})</strong>${(window.__PRIOR_SET && window.__PRIOR_SET.has(d.nome+'|'+d.uf)) ? ' <span class="tag tag--prior">prioritário</span>' : ''}<br>${CAT_STYLE[d.categoria].label}${d.fase===2?' · Fase 2':''}`, evt))
  .on('mousemove', (evt)=> showTip(tooltip.innerHTML, evt))
  .on('mouseleave', hideTip);

MonitorMapas.legenda('pointsLegend', Object.values(CAT_STYLE).map(v => ({cor: v.cor, rotulo: v.label})));
ligarSeletorDeCamada('selVerificacao', [{valor:'pontos', svg:'mapPoints', legenda:'pointsLegend'}, {valor:'niveis', svg:'mapNiveis', legenda:'legNiveis'}]);
// tabela acessível (equivalente aos dois mapas do seletor acima) — soma por UF, sem esperar o setTimeout do mapa de níveis
(function(){
  const tb = document.querySelector('#tblVerificacao tbody');
  if (!tb) return;
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const contAto = {};
  MAP_POINTS.forEach(p => { if (['plano','plano_antigo','decreto'].includes(p.categoria)) contAto[p.uf] = (contAto[p.uf]||0) + 1; });
  const ufsOrdenadas = DATA.ufs.map(u => u.uf).sort();
  tb.innerHTML = ufsOrdenadas.map(uf => {
    const niv = (VRESUMO && VRESUMO.por_uf && VRESUMO.por_uf[uf]) || {};
    return '<tr><td><strong>' + esc(uf) + '</strong></td><td>' + esc(contAto[uf] || 0) + '</td><td>' + esc(niv.municipal_completo || 0) + '</td><td>' + esc(niv.estadual || 0) + '</td><td>' + esc(niv.nacional || 0) + '</td><td>' + esc(niv.nao_verificado || 0) + '</td></tr>';
  }).join('');
})();

// ---- 1b. Nível de verificação municipal (v2.2.4, §7.3/C8) ----
// Desenho adiado (setTimeout 0) e camada padrão em UM único <path>: 5.571 nós
// individuais tornavam a página lenta e atrasavam os mapas seguintes (pego pelo
// portão de runtime em 02/09/2026).
setTimeout(function(){
  const NIV_STYLE = {
    nao_verificado:     {cor:MonitorMapas.PALETA.verificacao.nao_verificado, label:'Ainda não verificado'},
    nacional:           {cor:MonitorMapas.PALETA.verificacao.nacional, label:'Verificado em fontes nacionais'},
    estadual:           {cor:MonitorMapas.PALETA.verificacao.estadual, label:'Fontes nacionais e estaduais'},
    municipal_completo: {cor:MonitorMapas.PALETA.verificacao.municipal_completo, label:'Verificação completa'},
    fonte_suspensa:     {cor:MonitorMapas.PALETA.verificacao.fonte_suspensa, label:'Fonte suspensa (defeso)'},
  };
  const acima = (VRESUMO && VRESUMO.niveis_acima_do_padrao) || {};
  const susp  = new Set((VRESUMO && VRESUMO.fontes_suspensas_municipios) || []);
  const __ctx = MonitorMapas.contexto(BR_GEOJSON, 480, 460);
  const svg = MonitorMapas.ufs(__ctx, 'mapNiveis', uf => 'var(--surface-2, var(--osso-claro))', uf => { const p = (VRESUMO && VRESUMO.por_uf && VRESUMO.por_uf[uf]) || {}; return Object.entries(p).map(([k, v]) => v + ' ' + (NIV_STYLE[k] ? NIV_STYLE[k].label.toLowerCase() : k)).join(' · ') || 'sem dados'; });
  const pts = (window.REF_MUNICIPIOS || []).map(r => {
    const cod = String(r.codigo_ibge).padStart(7,'0');
    const niv = susp.has(cod) ? 'fonte_suspensa' : (acima[cod] || acima[String(r.codigo_ibge)] || 'nao_verificado');
    return {lat:r.lat, lon:r.lon, niv};
  }).filter(p => p.lat && p.lon);
  // camada padrão (não verificados): um único <path> de pontos — barato de renderizar
  MonitorMapas.pontosDensos(__ctx, 'mapNiveis', pts.filter(p=>p.niv==='nao_verificado'), NIV_STYLE.nao_verificado.cor, 1.4, .55);
  MonitorMapas.pontos(__ctx, 'mapNiveis', pts.filter(p=>p.niv!=='nao_verificado'), {r: () => 2.6, cor: d => NIV_STYLE[d.niv].cor, classe: 'acima'});
  MonitorMapas.legenda('legNiveis', Object.values(NIV_STYLE).map(v => ({cor: v.cor, rotulo: v.label})));
  // 13/09/2026: crédito único de boxVerificacao já sai de creditosAntecipacao() (mesmas fontes) —
  // chamada redundante removida daqui (era 'nivelverificacao', figura própria antes da consolidação).
}, 0);

// ---- Mapa dos municípios prioritários (Cadastro Nacional) — publicados vs sem nada ----
// 15/09/2026: fonte única é data/municipios_prioritarios.json (gerar_prioritarios.py) — a mesma
// aproximação populacional (documentada no arquivo) que alimenta a busca "Descubra se seu
// município é prioritário" em prefeituras.html; nunca mais recomputada em dois lugares.
const svgPrior = d3.select('#mapPrioritarios');
fetch('data/municipios_prioritarios.json').then(r => r.ok ? r.json() : null).then(PRIOR => {
  if (!PRIOR) return;
  window.__PRIOR_SET = new Set(PRIOR.municipios.map(m => m.nome + '|' + m.uf));   // §155: tag no tooltip do mapa de verificação
  svgPrior.append('g').selectAll('path')
    .data(BR_GEOJSON.features).join('path')
    .attr('d', pathGen).attr('fill', MonitorMapas.cor('zebra')).attr('class', 'uf-path')
    .on('mouseenter', (evt,d)=> showTip(`<strong>${d.properties.name}</strong>`, evt))
    .on('mousemove', (evt)=> showTip(tooltip.innerHTML, evt))
    .on('mouseleave', hideTip);
  addSiglas(svgPrior);
  const prioridadeOrdenada = [...PRIOR.municipios].sort((a,b) => (a.publicado?1:0) - (b.publicado?1:0)); // não-publicados desenhados por baixo
  svgPrior.append('g').selectAll('circle')
    .data(prioridadeOrdenada).join('circle')
    .attr('cx', d => projection([d.lon, d.lat])[0])
    .attr('cy', d => projection([d.lon, d.lat])[1])
    .attr('r', d => d.publicado ? 4 : 3)
    .attr('fill', d => d.publicado ? MonitorMapas.PALETA.preparacao : MonitorMapas.PALETA.zero)
    .attr('stroke', d => d.publicado ? MonitorMapas.cor('branco') : MonitorMapas.PALETA.resposta)
    .attr('stroke-width', d => d.publicado ? 1.6 : 1)
    .attr('stroke-dasharray', d => d.publicado ? null : '1.5,1.2')
    .on('mouseenter', (evt,d)=> showTip(`<strong>${d.nome} (${d.uf})</strong><br>Município prioritário (aproximação populacional) — `
      + (d.publicado ? 'instrumento localizado' : 'nenhum instrumento localizado até o corte'), evt))
    .on('mousemove', (evt)=> showTip(tooltip.innerHTML, evt))
    .on('mouseleave', hideTip);
  document.getElementById('legPrioritarios').innerHTML =
    `<span><i style="background:var(--musgo)"></i>Com instrumento</span>`
    + `<span><i style="background:repeating-linear-gradient(45deg,var(--osso-claro),var(--osso-claro) 3px,var(--argila) 3px,var(--argila) 4px)"></i>Sem instrumento localizado</span>`;
});

// ===========================================================
// Mapa de atos de resposta (decretos de emergência) — NUNCA pontuam no
// índice (Correção B). Junta duas fontes: municipios.json (categoria
// 'decreto', registros históricos, majoritariamente PB) e o arquivo dedicado
// data/atos_resposta.json (eventos novos, com causa/danos/fonte por registro
// — pedido de Patricia, 31/08/2026, motivado pelo temporal de granizo em SC).
const eventosAntigos = MAP_POINTS.filter(p => p.categoria === 'decreto').map(p => ({
  nome: p.nome, uf: p.uf, lat: p.lat, lon: p.lon, data: null, causa: null,
}));
const eventosNovos = (ATOS_RESPOSTA.eventos || []).map(e => ({
  nome: e.nome, uf: e.uf, lat: e.lat, lon: e.lon, data: e.data, causa: e.causa,
  danos: e.danos, decreto: e.decreto, fonte: e.fonte,
}));
const TODOS_ATOS_RESPOSTA = [...eventosAntigos, ...eventosNovos];
(document.getElementById('countAtosResposta')||{}).textContent = TODOS_ATOS_RESPOSTA.length;

const svgResp = d3.select('#mapAtosResposta');
(function(){ const ev = ATOS_RESPOSTA.eventos || []; const datas = ev.map(e => e.data).filter(Boolean).map(d => d.split('/').reverse().join('-')).sort(); const ult = datas.length ? datas[datas.length - 1].split('-').reverse().join('/') : '—';
  const el = document.getElementById('carimboAtos'); if (el) el.textContent = 'Registro: ' + ev.length + ' evento(s), último em ' + ult + '. Coleta automática (DOU/S2iD e diários oficiais) a partir de 06/09/2026: diária na semana intensiva, semanal depois; até lá, os eventos vêm da verificação manual.'; })();
svgResp.append('g').selectAll('path')
  .data(BR_GEOJSON.features).join('path')
  .attr('d', pathGen).attr('fill', MonitorMapas.cor('zebra')).attr('class', 'uf-path')
  .on('mouseenter', (evt,d)=> showTip(`<strong>${d.properties.name}</strong>`, evt))
  .on('mousemove', (evt)=> showTip(tooltip.innerHTML, evt))
  .on('mouseleave', hideTip);
svgResp.append('g').selectAll('circle')
  .data(TODOS_ATOS_RESPOSTA).join('circle')
  .attr('cx', d => projection([d.lon, d.lat])[0])
  .attr('cy', d => projection([d.lon, d.lat])[1])
  .attr('r', 4)
  .attr('fill', MonitorMapas.PALETA.resposta)
  .attr('stroke', MonitorMapas.cor('branco'))
  .attr('stroke-width', 1.6)
  .on('mouseenter', (evt,d)=> showTip(
    `<strong>${d.nome} (${d.uf})</strong><br>Decreto de emergência — ato de resposta, não pontua`
    + (d.data ? `<br>Data: ${d.data}` : '')
    + (d.causa ? `<br>Causa: ${d.causa}` : ''), evt))
  .on('mousemove', (evt)=> showTip(tooltip.innerHTML, evt))
  .on('mouseleave', hideTip);
document.getElementById('legAtosResposta').innerHTML =
  `<span><i style="background:var(--argila)"></i>Decreto de emergência</span>`;

// ---- Mapa 2a: COBERTURA (uma pergunta: quantos municípios têm algum ato?) ----
const corCobertura = (info) => {
  if (!info.com_ato) return MonitorMapas.cor('zebra');
  const k = Math.pow(Math.min(info.pct, 100)/100, 0.5);
  return d3.interpolateHcl(MonitorMapas.PALETA.rampaPreparo[0], MonitorMapas.PALETA.rampaPreparo[1])(0.15 + 0.85*k);
};
// ---- Mapa 2b: NATUREZA — 5 classes divergentes (centro neutro oliva; sem gradiente contínuo) ----
// Degradê contínuo terracota→areia→azul (mesmo eixo cromático do site inteiro),
// interpolado por d3 em vez de 5 faixas de cor fixas — a proporção real
// plano/decreto de cada estado agora tem uma cor própria na escala, não um
// "degrau" compartilhado com estados de proporção bem diferente.
const ESCALA_NATUREZA = d3.scaleLinear()
  .domain([0, 0.05, 0.35, 0.65, 0.95, 1])
  .range([MonitorMapas.PALETA.resposta, MonitorMapas.PALETA.resposta, MonitorMapas.PALETA.status.ELAB, MonitorMapas.PALETA.semDado, MonitorMapas.PALETA.status.VIG, MonitorMapas.PALETA.preparacao])
  .clamp(true);
const corNatureza = (info) => {
  const atos = (info.n_plano||0) + (info.n_decreto||0);
  if (!atos) return 'url(#hatchSemAtos)';
  return ESCALA_NATUREZA(info.n_plano / atos);
};

function mapaUF(sel, cor, tipTexto){
  const svg = d3.select(sel);
  svg.append('g').selectAll('path')
    .data(BR_GEOJSON.features).join('path')
    .attr('d', pathGen)
    .attr('class', 'uf-path')
    .attr('fill', d => cor(PCT_POR_UF[d.properties.sigla] || {}))
    .attr('tabindex', 0)
    .attr('role', 'img').attr('aria-label', d => tipTexto(PCT_POR_UF[d.properties.sigla], d.properties.name).replace(/<[^>]+>/g, ' '))
    .on('mouseenter', (evt,d)=> showTip(tipTexto(PCT_POR_UF[d.properties.sigla], d.properties.name), evt))
    .on('mousemove', (evt)=> showTip(tooltip.innerHTML, evt))
    .on('mouseleave', hideTip)
    .on('focus', function(evt,d){
      const b = this.getBoundingClientRect();
      showTip(tipTexto(PCT_POR_UF[d.properties.sigla], d.properties.name), {clientX: b.x + b.width/2, clientY: b.y});
    })
    .on('blur', hideTip);
  return svg;
}

const svgCob = mapaUF('#mapCobertura', corCobertura, (i, nome) => {
  const decl = (i.declarado_plano||0)+(i.declarado_antigo||0);
  const l = decl ? `<br>Declarada (TCE/sistema estadual): ${(100*decl/i.total).toFixed(1)}%` : '';
  return `<strong>${nome}</strong><br>${i.com_ato} de ${i.total} municípios com ato (${i.pct}%)${l}`;
});
const svgNat = mapaUF('#mapNatureza', corNatureza, (i, nome) => {
  const atos = (i.n_plano||0)+(i.n_decreto||0);
  if (!atos) return `<strong>${nome}</strong><br>Nenhum ato identificado`;
  return `<strong>${nome}</strong><br>${i.n_plano} plano(s) preventivo(s) · ${i.n_decreto} decreto(s) reativo(s)<br>${Math.round(100*i.n_plano/atos)}% preventivo`;
});
const __defsNat = svgNat.append('defs');
const __pat = __defsNat.append('pattern').attr('id','hatchSemAtos')
  .attr('width', 6).attr('height', 6)
  .attr('patternUnits','userSpaceOnUse').attr('patternTransform','rotate(45)');
__pat.append('rect').attr('width', 6).attr('height', 6).attr('fill', MonitorMapas.cor('osso-claro'));
__pat.append('line').attr('x1', 0).attr('y1', 0).attr('x2', 0).attr('y2', 6)
  .attr('stroke', MonitorMapas.cor('areia')).attr('stroke-width', 1.4);

document.getElementById('legCobertura').innerHTML =
  `<span><i style="background:linear-gradient(90deg,var(--zebra),var(--musgo)); width:44px;"></i>0% → 100% dos municípios com ato</span>`;
MonitorMapas.legendaContinua('legNatureza', 'linear-gradient(90deg, var(--argila) 0%, var(--ambar) 20%, var(--sem-dado) 50%, var(--mineral) 80%, var(--musgo) 100%)', 'só decretos reativos', 'só planos preventivos', [{cor: 'repeating-linear-gradient(45deg,var(--osso-claro),var(--osso-claro) 3px,var(--areia) 3px,var(--areia) 4px)', rotulo: 'sem atos identificados'}]);
ligarSeletorDeCamada('selCoberturaNatureza', [{valor:'cobertura', svg:'mapCobertura', legenda:'legCobertura'}, {valor:'natureza', svg:'mapNatureza', legenda:'legNatureza'}]);
// tabela acessível (equivalente aos dois mapas do seletor acima)
(function(){
  const tb = document.querySelector('#tblCoberturaNatureza tbody');
  if (!tb) return;
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const ufsOrdenadas = DATA.ufs.map(u => u.uf).sort();
  tb.innerHTML = ufsOrdenadas.map(uf => {
    const i = PCT_POR_UF[uf] || {};
    const atos = (i.n_plano || 0) + (i.n_decreto || 0);
    const pctPrev = atos ? Math.round(100 * i.n_plano / atos) + '%' : '—';
    return '<tr><td><strong>' + esc(uf) + '</strong></td><td>' + esc((i.com_ato ?? 0) + ' de ' + (i.total ?? '—')) + '</td><td>' + esc((i.pct ?? 0) + '%') + '</td><td>' + esc(i.n_plano ?? 0) + '</td><td>' + esc(i.n_decreto ?? 0) + '</td><td>' + esc(pctPrev) + '</td></tr>';
  }).join('');
})();

// ---- Mapa: risco projetado × instrumento estadual ----
const CONSIST_ROTULO = {COBRE:'Cobre o risco projetado', PARCIAL:'Cobre parte do risco', DIFERE:'Risco difere do instrumento', SEM:'Instrumento estadual não localizado', NEUTRO:'Sem sinal elevado no trimestre'};
const CONSIST_COR = {COBRE:MonitorMapas.PALETA.consistencia.COBRE, PARCIAL:MonitorMapas.PALETA.consistencia.PARCIAL, DIFERE:MonitorMapas.PALETA.consistencia.DIFERE, SEM:'url(#hatchSemInstr)', NEUTRO:MonitorMapas.PALETA.consistencia.NEUTRO};
// Cor de borda plana para a TABELA (SEM usa padrão de hachura no mapa SVG, que não
// é uma cor CSS válida para border — aqui precisa de um tom sólido equivalente).
const CONSIST_COR_TABELA = MonitorMapas.PALETA.consistencia;

// Tabela "risco × instrumento" gerada DIRETO de CONSIST — antes disso era uma cópia
// digitada à mão, que chegou a divergir de verdade do CONSIST real (PE aparecia
// duas vezes, em categorias diferentes; achado ao investigar a automação estadual,
// 31/08/2026). Gerar aqui elimina a cópia — só existe uma fonte de verdade agora.
function renderTabelaConsistencia(){
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const corpo = document.getElementById('tblConsistencia');
  if (!corpo) return;
  const porCategoria = {};
  Object.entries(CONSIST).forEach(([uf, v]) => {
    (porCategoria[v.cat] = porCategoria[v.cat] || []).push([uf, v]);
  });
  let html = '';
  Object.keys(CONSIST_ROTULO).forEach(cat => {
    const linhas = (porCategoria[cat] || []).sort((a, b) => a[0].localeCompare(b[0]));
    if (!linhas.length) return;
    html += `<tr class="grupo"><td colspan="3" style="border-bottom-color:${CONSIST_COR_TABELA[cat]};">${CONSIST_ROTULO[cat]} · ${linhas.length} estado(s)</td></tr>`;
    linhas.forEach(([uf, v]) => {
      html += `<tr><td class="nowrap"><strong>${esc(uf)}</strong></td><td>${esc(v.risco)}</td><td>${esc(v.instr)}</td></tr>`;
    });
  });
  corpo.innerHTML = html;
}
const svgConsist = d3.select('#mapConsistencia');
if (document.getElementById('mapConsistencia')) {
  const __defsC = svgConsist.append('defs');
  const __patC = __defsC.append('pattern').attr('id','hatchSemInstr')
    .attr('width', 6).attr('height', 6)
    .attr('patternUnits','userSpaceOnUse').attr('patternTransform','rotate(45)');
  __patC.append('rect').attr('width', 6).attr('height', 6).attr('fill', MonitorMapas.cor('osso-claro'));
  __patC.append('line').attr('x1', 0).attr('y1', 0).attr('x2', 0).attr('y2', 6)
    .attr('stroke', MonitorMapas.PALETA.resposta).attr('stroke-width', 1.4).attr('stroke-opacity', .55);
  svgConsist.append('g').selectAll('path')
    .data(BR_GEOJSON.features).join('path')
    .attr('d', pathGen)
    .attr('class', 'uf-path')
    .attr('fill', d => CONSIST_COR[CONSIST[d.properties.sigla].cat])
    .attr('tabindex', 0)
    .attr('role', 'img').attr('aria-label', d => { const c = CONSIST[d.properties.sigla]; return `${d.properties.name}: ${CONSIST_ROTULO[c.cat]}. Risco projetado: ${c.risco}. Instrumento: ${c.instr}`; })
    .on('mouseenter', (evt,d) => { const c = CONSIST[d.properties.sigla];
      showTip(`<strong>${d.properties.name}</strong><br><em>${CONSIST_ROTULO[c.cat]}</em><br>Risco projetado: ${c.risco}<br>Instrumento estadual: ${c.instr}`, evt); })
    .on('mousemove', (evt) => showTip(tooltip.innerHTML, evt))
    .on('mouseleave', hideTip)
    .on('focus', function(evt,d) { const b = this.getBoundingClientRect(); const c = CONSIST[d.properties.sigla];
      showTip(`<strong>${d.properties.name}</strong><br><em>${CONSIST_ROTULO[c.cat]}</em><br>Risco: ${c.risco}<br>Instrumento: ${c.instr}`, {clientX: b.x + b.width/2, clientY: b.y}); })
    .on('blur', hideTip);
  addSiglas(svgConsist);
  const __contC = {};
  Object.values(CONSIST).forEach(c => __contC[c.cat] = (__contC[c.cat]||0) + 1);
  const __legConsist = document.getElementById('legConsist');
  if (__legConsist) __legConsist.innerHTML =
    ['COBRE','PARCIAL','DIFERE','SEM','NEUTRO'].map(k =>
      `<span><i style="background:${k==='SEM' ? 'repeating-linear-gradient(45deg,var(--osso-claro),var(--osso-claro) 3px,var(--argila) 3px,var(--argila) 4px)' : CONSIST_COR[k]}"></i>${CONSIST_ROTULO[k]} (${__contC[k]})</span>`).join('');
  renderTabelaConsistencia();
}
// 17/09/2026: resumo compacto removido — o cruzamento que ele resumia saiu da inicial (pedido da editoria).

// =========================================================
// MARE — ranking com componentes ponderados
// =========================================================


// (financiamento e transferências — mapa do dinheiro e fontes de monitoramento — migraram para financiamento.html, E9)

// ---- Siglas das UFs sobre os três mapas ----
function addSiglas(svg){ MonitorMapas.siglas(MonitorMapas.contexto(BR_GEOJSON, 480, 460), svg); }
addSiglas(svgPoints); addSiglas(svgCob); addSiglas(svgNat); addSiglas(svgResp);   // svgPrior: siglas desenhadas dentro do .then() acima




  renderResposta();
  titulosFato();
}
// Auditoria de 07/09/2026: toda figura tem crédito no formato único; as de antecipação são verificação própria do Monitor.
function creditosAntecipacao(){
  const d = window.__metaAtualizado;
  [['boxVerificacao', ['MARÉ (verificação própria)', 'malha IBGE']], ['boxCoberturaNatureza', ['MARÉ (verificação própria)']],
   ['boxPrioritarios', ['MARÉ', 'Cadastro Nacional (SEDEC), aproximação por população']], ['boxAtosResposta', ['DOU/SEDEC (S2iD)', 'diários oficiais']],
   ].forEach(([id, fontes]) => MonitorMapas.credito(id, {fontes, data: d}));
}
function renderResposta(){
  creditosAntecipacao();
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const fF = id => (typeof fonteFigura === 'function' ? fonteFigura : (cid, t) => MonitorMapas.credito(cid, t));
  const N = RESP && RESP.nacional;
  const c18 = (RESP && RESP.frase_c18) || '';
  if (!N) return;
}
__load().catch(err => {
  document.body.insertAdjacentHTML('afterbegin',
    '<div id="errBanner" class="erro-carga">' +
    'Erro ao carregar os dados: ' + err.message +
    '. Sirva a pasta via HTTP (ex.: <code>npx serve</code>) — abrir o arquivo diretamente bloqueia o fetch.</div>');
});

// ===== defesa-civil.html · bloco 2 (extraído em 06/09/2026, CSP sem unsafe-inline) =====
window.addEventListener('load', function(){ if (window.VLibras && window.VLibras.Widget) { try { new window.VLibras.Widget('https://vlibras.gov.br/app'); } catch (e) {} } });

// 15/09/2026 (auditoria editorial §2.9): títulos-fato das figuras e interpretações fora das figuras (portão 19), todos
// calculados dos dados já carregados nesta página — nunca digitados. Falta de dado = título original mantido.
// 15/09/2026 (correção): antes era uma IIFE executada no carregamento do script, ANTES dos dados chegarem — os títulos ficavam
// sempre no texto original (e o portão que os checava nunca bloqueava, por outro bug, corrigido junto). Agora é chamada ao fim de __init().
function titulosFato(){
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const n = v => Number(v || 0).toLocaleString('pt-BR');
  const titulo = (box, txt) => { const h = document.querySelector('#' + box + ' .figura-titulo'); if (h && txt) h.textContent = txt; };
  // 18/09/2026 (pedido da editoria): o resumo "N estados com plano para o ciclo..." e "Por região: X
  // concentra..." saiu daqui — mora como contador na home, abaixo do índice MARÉ Legal (mesmo cálculo,
  // mesma fonte data/estados.json, ver assets/js/index.js).
  // (b) 'declarado × documentado' (boxDeclarado) saiu da página em 15/09/2026 (§59) — bloco removido.
  try {   // (c) verificação: registro federal (todos), diário oficial (varredura), planos municipais localizados
    // 15/09/2026 (correção): a contagem vinha de CONSIST (risco estadual), que não tem n_plano — sempre somava 0. A contagem
    // correta é PCT_POR_UF.n_plano (percentual_uf.json), a mesma fonte do índice (recalcular_mare.py), nunca divergente dela.
    const vd = (VRESUMO && VRESUMO.varredura_diarios) || {}; const nDiario = vd.consultados || vd.municipios_consultados || null;
    const nPlanos = Object.values(PCT_POR_UF || {}).reduce((a, i) => a + (i.n_plano || 0), 0);
    titulo('boxVerificacao', `5.571 municípios no registro federal${nDiario != null ? `; ${n(nDiario)} no diário oficial` : ''}; ${n(nPlanos)} planos municipais localizados`);
  } catch (e) {}
  try {   // (f) mapa dos decretos — 16/09/2026: título-fato não nomeia mais o estado com a maior fração
    // (revelava posição/comparação entre estados; ver pedido da editoria)
    const N = RESP && RESP.nacional;
    if (N) titulo('boxAtosResposta', `Decretos: ${n(N.n_municipios)} municípios`);
  } catch (e) {}
}
