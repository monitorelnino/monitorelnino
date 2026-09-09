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
const STATUS_LABEL = {NOVO:"Novo", READ:"Readaptado", ELAB:"Em elaboração", VIG:"Vigente-recorrente", LAC:"Sem plano localizado"};
// =========================================================
// ANÁLISES — 6 gráficos derivados do mesmo objeto DATA
// =========================================================
const PALETTE = MonitorMapas.PALETA.status;   // VIG era Âmbar aqui (igual a ELAB) e Mineral na Saúde — paleta única desde 09/09/2026
const LABELS  = {NOVO:'Novo', READ:'Readaptado', ELAB:'Em elaboração', VIG:'Vigente-recorrente', LAC:'Nenhum localizado'};
const STATUS_ORDER = ['NOVO','READ','ELAB','VIG','LAC'];

MonitorMapas.padraoGraficos(window.Chart);

// ---- 1. Donut nacional ----
const donutCounts = STATUS_ORDER.map(s => DATA.ufs.filter(u=>u.status===s).length);
const UFS_POR_STATUS = {}; DATA.ufs.forEach(u => (UFS_POR_STATUS[u.status] = UFS_POR_STATUS[u.status] || []).push(u.uf));
const CAP_POR_STATUS = {}; DATA.ufs.forEach(u => { const s = u.capital.status; (CAP_POR_STATUS[s] = CAP_POR_STATUS[s] || []).push(u.uf); });
const quebraLinhas = arr => { const o = []; for (let i = 0; i < arr.length; i += 9) o.push(arr.slice(i, i+9).join(' · ')); return o; };
// 03/09/2026: barras horizontais no lugar da rosca — contagem de UFs por categoria compara-se
// melhor em comprimento do que em ângulo; a soma (27) fica explícita no eixo.
new Chart(document.getElementById('chartDonut'), {
  type: 'bar',
  data: { labels: STATUS_ORDER.map(s=>LABELS[s]),
    datasets:[{ data: donutCounts, backgroundColor: STATUS_ORDER.map(s=>PALETTE[s]) }] },
  options: { indexAxis:'y', plugins:{ legend:{display:false},
    tooltip:{ callbacks:{ label: ctx => ctx.parsed.x + ' de 27 UFs', afterLabel: ctx => quebraLinhas(UFS_POR_STATUS[STATUS_ORDER[ctx.dataIndex]] || []) } } },
    scales:{ x:{ min:0, max:27, ticks:{stepSize:9}, title:{display:true, text:'nº de UFs (de 27)'} }, y:{ grid:{display:false} } } }
});

// ---- 2. Status por região (stacked horizontal) ----
const regionData = STATUS_ORDER.map(s => DATA.regions.map(r =>
  DATA.ufs.filter(u=>u.regiao===r && u.status===s).length));
new Chart(document.getElementById('chartRegion'), {
  type:'bar',
  data:{ labels: DATA.regions,
    datasets: STATUS_ORDER.map((s,i)=>({ label: LABELS[s], data: regionData[i], backgroundColor: PALETTE[s] })) },
  options:{ indexAxis:'y', maintainAspectRatio:false,
    plugins:{ legend:{ position:'bottom', labels:{boxWidth:10, padding:8, font:{size:12}} },
      tooltip:{ callbacks:{ afterLabel: ctx => quebraLinhas(DATA.ufs.filter(u => u.regiao === ctx.label && u.status === STATUS_ORDER[ctx.datasetIndex]).map(u => u.uf)) } } },
    scales:{ x:{ stacked:true, grid:{color:MonitorMapas.cor('areia')}, ticks:{stepSize:1} }, y:{ stacked:true, grid:{display:false} } } }
});

// ---- 3. Financiamento federal por área (R$ reais, calculados a partir de Registro_Federal) ----
// (gráfico 3 — financiamento federal por área — migrou para financiamento.html, E9)

// ---- 4. Status das 27 capitais ----
const capStatusCounts = {};
DATA.ufs.forEach(u=>{ const s=u.capital.status; capStatusCounts[s]=(capStatusCounts[s]||0)+1; });
const capLabels = Object.keys(capStatusCounts);
const CAP_COLOR = {'Novo':MonitorMapas.PALETA.status.NOVO,'Readaptado':MonitorMapas.PALETA.status.READ,'Em elaboração':MonitorMapas.PALETA.status.ELAB,
  'Vigente-recorrente':MonitorMapas.PALETA.status.VIG,'Coberto pelo estadual':MonitorMapas.PALETA.categorias.coberto_estadual,'Coberto pelo estado':MonitorMapas.PALETA.categorias.coberto_estadual,
  'Não é de El Niño':MonitorMapas.PALETA.categorias.nao_el_nino,'Não localizado':MonitorMapas.PALETA.status.LAC};
new Chart(document.getElementById('chartCapitals'), {
  type:'bar',
  data:{ labels: capLabels,
    datasets:[{ data: capLabels.map(l=>capStatusCounts[l]),
      backgroundColor: capLabels.map(l => CAP_COLOR[l] || MonitorMapas.cor('areia')), borderRadius:4}] },
  options:{ maintainAspectRatio:false, plugins:{legend:{display:false},
      tooltip:{ callbacks:{ afterLabel: ctx => quebraLinhas(CAP_POR_STATUS[ctx.label] || []) } }},
    scales:{ x:{ grid:{display:false}, ticks:{font:{size:9.5}, maxRotation:35, minRotation:35} }, y:{ grid:{color:MonitorMapas.cor('areia')}, ticks:{stepSize:1} } } }
});

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
  plano_antigo:     {cor:MonitorMapas.PALETA.categorias.plano_antigo, r:5,   label:'Plano desatualizado'},
  plano_elaboracao: {cor:MonitorMapas.PALETA.categorias.plano_elaboracao, r:5,   label:'Plano em elaboração'},
  estrutura:        {cor:MonitorMapas.PALETA.categorias.estrutura, r:5,   label:'Estrutura de coordenação'},
  decreto:          {cor:MonitorMapas.PALETA.categorias.decreto, r:4.5, label:'Decreto de emergência'},
  coberto_estadual: {cor:MonitorMapas.PALETA.categorias.coberto_estadual, r:4.5, label:'Coberto pelo estado'},
  nao_el_nino:      {cor:MonitorMapas.PALETA.categorias.nao_el_nino, r:4,   label:'Não é El Niño'},
  nao_localizado:   {cor:MonitorMapas.PALETA.categorias.nao_localizado, r:4.5, label:'Nenhum ato localizado'},
  nao_verificado:   {cor:MonitorMapas.PALETA.categorias.nao_verificado, r:4.5, label:'Ainda não verificado'},
};

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
  .on('mouseenter', (evt,d)=> showTip(`<strong>${d.nome} (${d.uf})</strong><br>${CAT_STYLE[d.categoria].label}${d.fase===2?' · Fase 2':''}`, evt))
  .on('mousemove', (evt)=> showTip(tooltip.innerHTML, evt))
  .on('mouseleave', hideTip);

MonitorMapas.legenda('pointsLegend', Object.values(CAT_STYLE).map(v => ({cor: v.cor, rotulo: v.label})));

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
  // crédito DEPOIS do mapa (pedido editorial de 03/09/2026), fora do parágrafo-nota inicial
  MonitorMapas.credito('nivelverificacao', {fontes: ['Monitor El Niño Brasil (verificação própria)', 'malha IBGE'], data: window.__metaAtualizado});
}, 0);

// ---- Mapa dos municípios prioritários (Cadastro Nacional) — publicados vs sem nada (31/08/2026) ----
// LIMITAÇÃO DECLARADA: a lista NOMINAL dos 2.095 municípios do Cadastro Nacional de
// Municípios Suscetíveis (Nota Técnica 1/2025/SADJ-VI/SEPAC/CC/PR) exige login no
// portal do MDR e não é publicamente acessível (verificado em 31/08/2026). Este mapa
// usa uma PROXY documentada: em cada UF, os N municípios de MAIOR POPULAÇÃO, onde N é
// a contagem OFICIAL de municípios prioritários daquela UF (fonte: mesma nota técnica,
// Tabela 2 — pública). Não é a lista real nome a nome; é a aproximação mais defensável
// disponível sem acesso autenticado, e está rotulada como tal na página e no tooltip.
const CADASTRO_UF_N = {AC:20,AL:47,AM:59,AP:14,BA:144,CE:80,DF:1,ES:71,GO:25,MA:113,
  MG:306,MS:33,MT:40,PA:97,PB:43,PE:108,PI:47,PR:84,RJ:76,RN:32,RO:14,RR:5,RS:206,
  SC:218,SE:17,SP:177,TO:18};
const CATS_PUBLICADO = new Set(['plano','plano_antigo','plano_elaboracao','estrutura','decreto','coberto_estadual']);
const publicadosSet = new Set(MAP_POINTS.filter(p => CATS_PUBLICADO.has(p.categoria)).map(p => p.uf+'|'+p.nome));
const prioritariosProxy = [];
Object.entries(CADASTRO_UF_N).forEach(([uf, n]) => {
  const candidatos = (MUN_REF[uf] || []).map(nome => {
    const cod = MUN_COD[uf+'|'+nome];
    return {nome, uf, pop: POP_CENSO[cod] || 0, latlon: MUN_LATLON[uf+'|'+nome]};
  }).filter(x => x.latlon).sort((a,b) => b.pop - a.pop).slice(0, n);
  candidatos.forEach(x => prioritariosProxy.push({
    nome: x.nome, uf: x.uf, lon: x.latlon[0], lat: x.latlon[1],
    publicado: publicadosSet.has(x.uf+'|'+x.nome),
  }));
});
const nPublicados = prioritariosProxy.filter(x => x.publicado).length;
(document.getElementById('countPrioritariosPublicados')||{}).textContent = nPublicados;
(document.getElementById('countPrioritariosTotal')||{}).textContent = prioritariosProxy.length;

const svgPrior = d3.select('#mapPrioritarios');
svgPrior.append('g').selectAll('path')
  .data(BR_GEOJSON.features).join('path')
  .attr('d', pathGen).attr('fill', MonitorMapas.cor('zebra')).attr('class', 'uf-path')
  .on('mouseenter', (evt,d)=> showTip(`<strong>${d.properties.name}</strong>`, evt))
  .on('mousemove', (evt)=> showTip(tooltip.innerHTML, evt))
  .on('mouseleave', hideTip);
const prioridadeOrdenada = [...prioritariosProxy].sort((a,b) => (a.publicado?1:0) - (b.publicado?1:0)); // não-publicados desenhados por baixo
svgPrior.append('g').selectAll('circle')
  .data(prioridadeOrdenada).join('circle')
  .attr('cx', d => projection([d.lon, d.lat])[0])
  .attr('cy', d => projection([d.lon, d.lat])[1])
  .attr('r', d => d.publicado ? 4 : 3)
  .attr('fill', d => d.publicado ? MonitorMapas.PALETA.preparacao : MonitorMapas.PALETA.zero)
  .attr('stroke', d => d.publicado ? MonitorMapas.cor('branco') : MonitorMapas.PALETA.resposta)
  .attr('stroke-width', d => d.publicado ? 1.6 : 1)
  .attr('stroke-dasharray', d => d.publicado ? null : '1.5,1.2')
  .on('mouseenter', (evt,d)=> showTip(`<strong>${d.nome} (${d.uf})</strong><br>Município prioritário (proxy populacional) — `
    + (d.publicado ? 'JÁ TEM instrumento localizado' : 'nenhum instrumento localizado ainda'), evt))
  .on('mousemove', (evt)=> showTip(tooltip.innerHTML, evt))
  .on('mouseleave', hideTip);
document.getElementById('legPrioritarios').innerHTML =
  `<span><i style="background:var(--musgo)"></i>Com instrumento</span>`
  + `<span><i style="background:repeating-linear-gradient(45deg,var(--osso-claro),var(--osso-claro) 3px,var(--argila) 3px,var(--argila) 4px)"></i>Sem instrumento ainda</span>`;

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

// ---- Mapa: risco projetado × instrumento estadual ----
const CONSIST_ROTULO = {COBRE:'Cobre o risco projetado', PARCIAL:'Cobre parte do risco', DIFERE:'Risco difere do instrumento', SEM:'Sem instrumento estadual', NEUTRO:'Sem sinal elevado no trimestre'};
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
document.getElementById('legConsist').innerHTML =
  ['COBRE','PARCIAL','DIFERE','SEM','NEUTRO'].map(k =>
    `<span><i style="background:${k==='SEM' ? 'repeating-linear-gradient(45deg,var(--osso-claro),var(--osso-claro) 3px,var(--argila) 3px,var(--argila) 4px)' : CONSIST_COR[k]}"></i>${CONSIST_ROTULO[k]} (${__contC[k]})</span>`).join('');
renderTabelaConsistencia();

// =========================================================
// MARE — ranking com componentes ponderados
// =========================================================

// =========================================================
// Áreas temáticas cobertas pelos instrumentos estaduais
// =========================================================
const AREAS = [
  {label:'Grupo Seca (COBRADE 1.4.1): estiagem, seca e segurança hídrica', cor:MonitorMapas.PALETA.risco.seca, ufs:['AC','AL','AM','AP','BA','CE','DF','GO','PA','PE','PI','SE']},
  {label:'Grupo Seca · frente de incêndio florestal (1.4.1.3)', cor:MonitorMapas.PALETA.risco.fogo, ufs:['BA','GO','MA','MS','MT','RO','RR','TO']},
  {label:'Família das chuvas (1.2-1.3): chuvas intensas e enchentes', cor:MonitorMapas.PALETA.risco.chuvas, ufs:['ES','MG','PR','RJ','RS','SP']},
  {label:'Multirrisco integrado', cor:MonitorMapas.PALETA.risco.multi, ufs:['SC']},
];
new Chart(document.getElementById('chartAreas'), {
  type:'bar',
  data:{ labels: AREAS.map(a=>a.label),
    datasets:[{ data: AREAS.map(a=>a.ufs.length), backgroundColor: AREAS.map(a=>a.cor), borderRadius:4 }] },
  options:{ indexAxis:'y', maintainAspectRatio:false, plugins:{legend:{display:false},
      tooltip:{ callbacks:{ afterLabel: ctx => quebraLinhas(AREAS[ctx.dataIndex].ufs) } }},
    scales:{ x:{ grid:{color:MonitorMapas.cor('areia')}, ticks:{stepSize:2}, title:{display:true, text:'nº de UFs', color:MonitorMapas.cor('muted'), font:{size:12}} },
      y:{ grid:{display:false}, ticks:{font:{size:12.5}} } } }
});

// (financiamento e transferências — mapa do dinheiro e fontes de monitoramento — migraram para financiamento.html, E9)

// ---- Siglas das UFs sobre os três mapas ----
function addSiglas(svg){ MonitorMapas.siglas(MonitorMapas.contexto(BR_GEOJSON, 480, 460), svg); }
addSiglas(svgPoints); addSiglas(svgCob); addSiglas(svgNat); addSiglas(svgPrior); addSiglas(svgResp);

// ---- Declarada × Documentada ----
const UFS_DECL = ['PR','SC','RS'];
new Chart(document.getElementById('chartDeclarado'), {
  type:'bar',
  data:{ labels: UFS_DECL.map(uf => {
      const i = PCT_POR_UF[uf];
      return `${uf} · ${i.fonte_declarada.split('—')[0].split(',')[0].trim()}`;
    }),
    datasets:[
      {label:'Declarada (a TCE / sistema estadual)', data: UFS_DECL.map(uf => {
        const i = PCT_POR_UF[uf];
        return +(100*((i.declarado_plano||0)+(i.declarado_antigo||0))/i.total).toFixed(1);
      }), backgroundColor:MonitorMapas.PALETA.status.VIG, borderRadius:4},
      {label:'Documentada (esta verificação)', data: UFS_DECL.map(uf => PCT_POR_UF[uf].pct), backgroundColor:MonitorMapas.PALETA.preparacao, borderRadius:4},
    ]},
  options:{ indexAxis:'y', maintainAspectRatio:false,
    plugins:{ legend:{position:'bottom'},
      tooltip:{ callbacks:{ footer:(items)=>{
        const uf = items[0].label.slice(0,2);
        const i = PCT_POR_UF[uf];
        return [
          `${i.declarado_plano||0} municípios com plano declarado${i.declarado_antigo?` + ${i.declarado_antigo} com plano declarado desatualizado`:''}`,
          `${i.com_ato} com documento localizado, de ${i.total} municípios`,
          `Fonte da camada declarada: ${i.fonte_declarada}`,
        ];
      }}}},
    scales:{ x:{max:100, grid:{color:MonitorMapas.cor('areia')}, ticks:{callback:v=>v+'%'}}, y:{grid:{display:false}} } }
});




  renderResposta();
}
// Auditoria de 07/09/2026: toda figura tem crédito no formato único; as de antecipação são verificação própria do Monitor.
function creditosAntecipacao(){
  const d = window.__metaAtualizado;
  [['boxPoints', ['Monitor El Niño Brasil (verificação própria)', 'malha IBGE']], ['boxCobertura', ['Monitor El Niño Brasil (verificação própria)']],
   ['boxNatureza', ['Monitor El Niño Brasil (verificação própria)']], ['riscoinstrumento', ['Monitor El Niño Brasil', 'Boletins nº 1–2 do Painel El Niño']],
   ['boxPrioritarios', ['Monitor El Niño Brasil', 'Cadastro Nacional (SEDEC), aproximação por população']], ['boxAtosResposta', ['DOU/SEDEC (S2iD)', 'diários oficiais']],
   ['boxDonut', ['Monitor El Niño Brasil', 'instrumentos estaduais verificados']], ['boxRegion', ['Monitor El Niño Brasil', 'instrumentos estaduais verificados']],
   ['boxCapitals', ['Monitor El Niño Brasil', '27 capitais verificadas']], ['boxDeclarado', ['MUNIC/IBGE', 'ICM/SEDEC', 'Monitor El Niño Brasil']],
   ['boxAreas', ['Monitor El Niño Brasil', 'classificação COBRADE']]].forEach(([id, fontes]) => MonitorMapas.credito(id, {fontes, data: d}));
}
function renderResposta(){
  creditosAntecipacao();
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const fF = id => (typeof fonteFigura === 'function' ? fonteFigura : (cid, t) => MonitorMapas.credito(cid, t));
  const N = RESP && RESP.nacional;
  const c18 = (RESP && RESP.frase_c18) || '';
  if (!N) { ['boxDispersao','boxSerieResp','boxDecRec'].forEach(id => MonitorMapas.credito(id, {fontes: 'Monitor El Niño Brasil', data: null})); return; }
  // dispersão (C20): x = antecipação (MARÉ), y = % municípios sob decreto; forma = evento observado (sem dado → círculo vazio)
  const pts = ((RESP_Q && RESP_Q.pontos) || []).filter(p => p.antecipacao != null);
  new Chart(document.getElementById('cDispersao'), {type: 'scatter', data: {datasets: [{label: 'UF', data: pts.map(p => ({x: p.antecipacao, y: +(100 * p.resposta).toFixed(1), uf: p.uf})),
      pointStyle: 'circle', pointRadius: 6, borderColor: MonitorMapas.PALETA.resposta, backgroundColor: 'transparent', borderWidth: 2}]},
    options: {animation: false, responsive: true, maintainAspectRatio: false, plugins: {legend: {display: false}, tooltip: {callbacks: {label: c => c.raw.uf + ' · antecipação ' + c.raw.x + ' · ' + c.raw.y + '% dos municípios sob decreto'}}},
      scales: {x: {min: 0, max: 100, title: {display: true, text: 'Antecipação (MARÉ, 0–100)'}}, y: {min: 0, title: {display: true, text: '% dos municípios sob decreto'}}}}});
  MonitorMapas.legenda('legDispersao', [{cor: MonitorMapas.PALETA.resposta, rotulo: 'um ponto por UF'}, {cor: MonitorMapas.PALETA.semDado, rotulo: 'círculo vazio: evento sem dado'}]);
  MonitorMapas.credito('boxDispersao', {fontes: ['Monitor El Niño Brasil', 'índice MARÉ e contador de resposta'], data: RESP.gerado_em});
  // série semanal com faixa do defeso
  const S = (RESP_SERIE && RESP_SERIE.semanas) || [];
  new Chart(document.getElementById('cSerieResp'), {type: 'bar', data: {labels: S.map(x => x.semana.slice(5)), datasets: [
      {label: 'municípios', data: S.map(x => x.municipios), backgroundColor: S.map(x => x.defeso ? MonitorMapas.PALETA.defeso : MonitorMapas.PALETA.antes_defeso)}]},
    options: {animation: false, responsive: true, maintainAspectRatio: false, plugins: {legend: {display: false}}, scales: {x: {ticks: {maxTicksLimit: 10}}, y: {beginAtZero: true, title: {display: true, text: 'municípios (primeiro decreto)'}}}}});
  MonitorMapas.legenda('legSerieResp', [{cor: MonitorMapas.PALETA.antes_defeso, rotulo: 'antes do período eleitoral'}, {cor: MonitorMapas.PALETA.defeso, rotulo: 'no período eleitoral'}]);
  MonitorMapas.credito('boxSerieResp', {fontes: ['DOU/SEDEC (S2iD)', 'diários oficiais'], data: RESP.gerado_em});
  // tabela decretado × reconhecido
  const tb = document.querySelector('#tblDecRec tbody');
  tb.innerHTML = Object.keys(RESP.uf).sort((a, b) => RESP.uf[b].n_municipios - RESP.uf[a].n_municipios || a.localeCompare(b)).map(uf => { const r = RESP.uf[uf];
    return '<tr><td><strong>' + uf + '</strong></td><td>' + r.n_municipios + ' de ' + r.total_municipios + '</td><td>' + (100 * r.fracao_municipios).toFixed(1).replace('.', ',') + '%</td><td>' + (100 * r.fracao_populacao).toFixed(1).replace('.', ',') + '%</td><td>' + r.tons.reconhecido + '</td><td>' + r.tons.decretado_sem_reconhecimento + '</td><td>' + esc(r.primeiro_decreto || '—') + '</td></tr>'; }).join('');
  MonitorMapas.legenda('legDecRec', [{cor: MonitorMapas.PALETA.resposta, rotulo: 'reconhecido pela União (S2iD)'}, {cor: MonitorMapas.PALETA.status.ELAB, rotulo: 'decretado sem reconhecimento'}]);
  MonitorMapas.credito('boxDecRec', {fontes: ['DOU/SEDEC (S2iD)', 'diários oficiais'], data: RESP.gerado_em});
}
__load().catch(err => {
  document.body.insertAdjacentHTML('afterbegin',
    '<div id="errBanner" class="erro-carga">' +
    'Erro ao carregar os dados: ' + err.message +
    '. Sirva a pasta via HTTP (ex.: <code>npx serve</code>) — abrir o arquivo diretamente bloqueia o fetch.</div>');
});

// ===== defesa-civil.html · bloco 2 (extraído em 06/09/2026, CSP sem unsafe-inline) =====
window.addEventListener('load', function(){ if (window.VLibras && window.VLibras.Widget) { try { new window.VLibras.Widget('https://vlibras.gov.br/app'); } catch (e) {} } });
