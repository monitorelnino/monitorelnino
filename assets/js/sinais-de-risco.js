// ===== sinais-de-risco.html · bloco 1 (extraído em 06/09/2026, CSP sem unsafe-inline) =====
/* Sinais oficiais de risco — camada de apresentação.
   Regra desta página: nenhum valor é calculado aqui. Tudo vem de
   data/sinais_risco.json, escrito por coletar_sinais_risco.py, com fonte,
   documento e data. Fonte não coletada vira lacuna declarada na tela. */
let BR_GEOJSON, SINAIS, MARE;
const UFS = ["AC","AL","AM","AP","BA","CE","DF","ES","GO","MA","MG","MS","MT","PA","PB","PE","PI","PR","RJ","RN","RO","RR","RS","SC","SE","SP","TO"];
const NEUTRA = MonitorMapas.cor('sem-dado');           // estado sem dado coletado
const TIPO_COR = {estiagem:MonitorMapas.cor('ambar'), chuvas:MonitorMapas.cor('musgo'), incendios:MonitorMapas.cor('argila'), misto:MonitorMapas.cor('mineral'), sem_sinal:MonitorMapas.cor('areia')};
const FAIXAS = [
  {nome:'Estágio inicial', cor:MonitorMapas.cor('argila'), teste:v => v < 25},
  {nome:'Em construção',   cor:MonitorMapas.cor('ambar'), teste:v => v < 50},
  {nome:'Consolidado',     cor:MonitorMapas.cor('musgo'), teste:v => v < 70},
  {nome:'Avançado',        cor:MonitorMapas.cor('musgo'), teste:v => true},
];
const faixaDe = v => FAIXAS.find(f => f.teste(v));

async function __load(){
  [BR_GEOJSON, SINAIS, MARE] = await Promise.all(
    ['geo_uf','sinais_risco','indice'].map(f => fetch('data/' + f + '.json').then(r => {
      if(!r.ok) throw new Error('Falha ao carregar data/' + f + '.json');
      return r.json();
    }))
  );
  __init();
}

const showTip = MonitorMapas.showTip, hideTip = MonitorMapas.hideTip;
const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));

function __init(){
  MonitorMapas.padraoGraficos(window.Chart);
const projection = __ctx().projection;
const pathGen = __ctx().path;
const fonteDe = id => (SINAIS.fontes || {})[id] || {};
const coletada = id => fonteDe(id).status === 'coletado';

/* Crédito de UMA linha ao pé do cartão (04/09/2026): "Fonte: nome · data" ou "· sem coleta até o corte". */
function credito(caixaId, fonteId, extra){
  const f = fonteDe(fonteId), caixa = document.getElementById(caixaId);
  if(!caixa || caixa.querySelector('.fonte-figura')) return;
  const d = document.createElement('div');
  d.className = 'fonte-figura'; d.dataset.credito = fonteId;
  d.innerHTML = 'Fonte: <a href="' + esc(f.url_publica) + '" target="_blank" rel="noopener">' + esc(f.nome) + '</a> · ' +
    (coletada(fonteId) ? 'consultado em ' + esc(f.consultado_em) : 'sem coleta até o corte');
  caixa.appendChild(d);
}

/* Marca visualmente uma figura que espera a primeira coleta. */
function lacuna(alvoId, texto){
  const alvo = document.getElementById(alvoId);
  if(!alvo) return;
  const d = document.createElement('div');
  d.className = 'lacuna';
  d.textContent = texto;
  alvo.appendChild(d);
}


/* ---------- desenho genérico de mapa coroplético por UF ---------- */
function desenharMapa(svgId, legendaId, corDe, rotuloDe, itensLegenda){
  const svg = MonitorMapas.ufs(__ctx(), svgId, corDe, rotuloDe); MonitorMapas.legenda(legendaId, itensLegenda); return svg;
}
function __ctx(){ if (!window.__ctxCache) window.__ctxCache = MonitorMapas.contexto(BR_GEOJSON, 480, 460); return window.__ctxCache; }

// ---- Mapa 1: tipo de risco projetado (dado coletado) ----
const RISCO = uf => (SINAIS.uf[uf] || {}).risco_projetado;
const TIPO_ROTULO = SINAIS._formato.tipos_de_risco;
const TIPO_CURTO = SINAIS._formato.tipos_de_risco_curto;
desenharMapa('mapaTipoRisco', 'legTipoRisco',
  uf => { const r = RISCO(uf); return r ? TIPO_COR[r.tipo] : NEUTRA; },
  uf => { const r = RISCO(uf); return r ? '<em>' + esc(TIPO_ROTULO[r.tipo]) + '</em><br>' + esc(r.texto) : 'Sem registro localizado até o corte'; },
  Object.keys(TIPO_COR).map(t => ({cor:TIPO_COR[t], rotulo:TIPO_ROTULO[t]})));
credito('boxTipoRisco', 'painel_el_nino');

const corpoTipo = document.querySelector('#tblTipoRisco tbody');
corpoTipo.innerHTML = UFS.map(uf => { const r = RISCO(uf);
  return '<tr><td><strong>' + uf + '</strong></td><td>' + esc(r ? r.texto : 'não localizado até o corte') +
         '</td><td>' + esc(r ? TIPO_ROTULO[r.tipo] : '—') + '</td></tr>'; }).join('');

// ---- Mapa 2: seca observada ----
const SECA_COR = {S0:MonitorMapas.cor('zebra'), S1:MonitorMapas.cor('ambar'), S2:MonitorMapas.cor('ambar'), S3:MonitorMapas.cor('ambar-escuro'), S4:MonitorMapas.cor('argila')};
const seca = uf => (SINAIS.uf[uf] || {}).secas;
desenharMapa('mapaSecas', 'legSecas',
  uf => { const s = seca(uf); return s ? (SECA_COR[s.categoria] || NEUTRA) : NEUTRA; },
  uf => { const s = seca(uf); return s ? 'Categoria ' + esc(s.categoria) : 'Aguardando a primeira coleta desta fonte'; },
  Object.keys(SECA_COR).map(c => ({cor:SECA_COR[c], rotulo:c})).concat([{cor:NEUTRA, rotulo:'Sem coleta até o corte'}]));
credito('boxSecas', 'monitor_secas');

// ---- Mapa 3: avisos INMET ----
const aviso = uf => (SINAIS.uf[uf] || {}).avisos_inmet;
const maxAvisos = Math.max(1, ...UFS.map(uf => (aviso(uf) || {}).total || 0));
const escalaAviso = d3.scaleLinear().domain([0, maxAvisos]).range([MonitorMapas.cor('zebra'), MonitorMapas.cor('musgo')]);
desenharMapa('mapaAvisos', 'legAvisos',
  uf => { const a = aviso(uf); return a ? escalaAviso(a.total) : NEUTRA; },
  uf => { const a = aviso(uf); if(!a) return 'Aguardando a primeira coleta desta fonte';
    const graus = Object.entries(a.graus || {}).map(([g, n]) => esc(g) + ': ' + n).join(' · ');
    return a.total + ' aviso(s) vigente(s)' + (graus ? '<br>' + graus : ''); },
  [{cor:MonitorMapas.cor('zebra'), rotulo:'Menos avisos'}, {cor:MonitorMapas.cor('musgo'), rotulo:'Mais avisos'}, {cor:NEUTRA, rotulo:'Sem coleta até o corte'}]);
credito('boxAvisos', 'inmet_avisos');

// ---- Mapa 4: focos ativos ----
const fogo = uf => (SINAIS.uf[uf] || {}).fogo;
const maxFogo = Math.max(1, ...UFS.map(uf => (fogo(uf) || {}).focos_24h || 0));
const escalaFogo = d3.scaleSqrt().domain([0, maxFogo]).range([MonitorMapas.cor('osso-claro'), MonitorMapas.cor('argila')]);
desenharMapa('mapaFogo', 'legFogo',
  uf => { const f = fogo(uf); return f ? escalaFogo(f.focos_24h) : NEUTRA; },
  uf => { const f = fogo(uf); return f ? f.focos_24h + ' foco(s) nas últimas 24 h' : 'Aguardando a primeira coleta desta fonte'; },
  [{cor:MonitorMapas.cor('osso-claro'), rotulo:'Menos focos'}, {cor:MonitorMapas.cor('argila'), rotulo:'Mais focos'}, {cor:NEUTRA, rotulo:'Sem coleta até o corte'}]);
credito('boxFogo', 'inpe_fogo');

// ---- Mapa 5: alertas vigentes do CEMADEN ----
const alerta = uf => (SINAIS.uf[uf] || {}).alertas_cemaden;
const maxAlerta = Math.max(1, ...UFS.map(uf => (alerta(uf) || {}).total || 0));
const escalaAlerta = d3.scaleLinear().domain([0, maxAlerta]).range([MonitorMapas.cor('zebra'), MonitorMapas.cor('musgo')]);
desenharMapa('mapaCemaden', 'legCemaden',
  uf => { const a = alerta(uf); return a ? escalaAlerta(a.total) : NEUTRA; },
  uf => { const a = alerta(uf); if(!a) return 'Aguardando a primeira coleta desta fonte';
    const niveis = Object.entries(a.niveis || {}).map(([n, q]) => esc(n) + ': ' + q).join(' · ');
    return a.total + ' alerta(s) vigente(s)' + (niveis ? '<br>' + niveis : ''); },
  [{cor:MonitorMapas.cor('zebra'), rotulo:'Menos alertas'}, {cor:MonitorMapas.cor('musgo'), rotulo:'Mais alertas'}, {cor:NEUTRA, rotulo:'Sem coleta até o corte'}]);
// CEMADEN: "nenhum alerta vigente" é informação da fonte, não lacuna — vai na LEGENDA, não em parágrafo.
(function(){
  const temAlerta = Object.values((SINAIS && SINAIS.uf) || {}).some(u => u.alertas_cemaden && u.alertas_cemaden.total);
  const leg = document.getElementById('legCemaden');
  if (leg && coletada('cemaden_alertas') && !temAlerta) MonitorMapas.legenda('legCemaden', [{cor:MonitorMapas.cor('sem-dado'), rotulo:'nenhum alerta vigente na consulta'}, {cor:MonitorMapas.cor('musgo'), rotulo:'com alertas (quando houver)'}]);
})();
credito('boxCemaden', 'cemaden_alertas');

// =====================  Cartões do estado do ciclo  =====================
const oni = SINAIS.enos.oni, prob = SINAIS.enos.probabilidades;
const ultimoOni = oni && oni.serie && oni.serie.length ? oni.serie[oni.serie.length - 1] : null;
const ultimaProb = prob && prob.trimestres && prob.trimestres.length ? prob.trimestres[0] : null;
const cartoes = [
  {t:'Boletim mais recente do ciclo', v: coletada('painel_el_nino') ? fonteDe('painel_el_nino').documento : null, f:'painel_el_nino'},
  {t:'ONI observado', v: ultimoOni ? (ultimoOni.anomalia > 0 ? '+' : '') + ultimoOni.anomalia.toFixed(1) + ' °C · ' + ultimoOni.trimestre + '/' + ultimoOni.ano : null, f:'noaa_oni'},
  {t:'Probabilidade de El Niño', v: ultimaProb ? ultimaProb.el_nino.toFixed(0) + '% em ' + ultimaProb.trimestre : (SINAIS.enos.prognostico && SINAIS.enos.prognostico.enso ? '> 90% em SON/2026 (CPC, via CPTEC)' : null), f:'iri_plume'},
  {t:'Prognóstico trimestral', v: (SINAIS.enos.prognostico ? SINAIS.enos.prognostico.trimestre + ' · chuva abaixo da normal no Norte, Nordeste e centro-norte; acima no Sul; calor acima da normal em quase todo o País' : null), f:'cptec_prognostico'},
];
document.getElementById('cartoesCiclo').innerHTML = cartoes.map((c, i) =>
  '<div class="chart-box" id="cartaoCiclo' + i + '"><h3>' + esc(c.t) + '</h3>' +
  '<div class="cartao-ciclo-valor">' +
  (c.v ? esc(c.v) : '<span class="lacuna">sem coleta até o corte</span>') +
  '</div></div>').join('');
cartoes.forEach((c, i) => credito('cartaoCiclo' + i, c.f));

// =============================  Gráficos  =============================
const SEM_ANIM = {animation:false, responsive:true, maintainAspectRatio:false};

function canvasEm(wrapId, canvasId){
  const w = document.getElementById(wrapId);
  const c = document.createElement('canvas'); c.id = canvasId; w.appendChild(c); return c;
}

// ---- Gráfico 1: série ONI ----
if(oni && oni.serie && oni.serie.length){
  new Chart(canvasEm('wrapOni', 'cOni'), {type:'line', data:{
      labels: oni.serie.map(p => p.trimestre + '/' + String(p.ano).slice(2)),
      datasets:[{label:'ONI (°C)', data: oni.serie.map(p => p.anomalia), borderColor:MonitorMapas.cor('musgo'),
                 backgroundColor:'rgba(46,61,48,.12)', borderWidth:2, pointRadius:0, fill:true, tension:.25}]},
    options:{...SEM_ANIM, plugins:{legend:{display:false}}, scales:{
      x:{ticks:{maxTicksLimit:12}}, y:{title:{display:true, text:'°C'}}}}});
} else { lacuna('wrapOni', 'A série do ONI aparece aqui assim que a rotina semanal registrar a primeira coleta no CPC/NOAA. Até lá, ela pode ser consultada na origem, no link abaixo.'); }
credito('boxOni', 'noaa_oni');

// ---- Gráfico 2: probabilidades ENSO ----
if(prob && prob.trimestres && prob.trimestres.length){
  const t = prob.trimestres.slice(0, 9);
  new Chart(canvasEm('wrapPlume', 'cPlume'), {type:'bar', data:{
      labels: t.map(p => p.trimestre),
      datasets:[{label:'La Niña', data:t.map(p => p.la_nina), backgroundColor:MonitorMapas.cor('sintetico')},
                {label:'Neutro',  data:t.map(p => p.neutro),  backgroundColor:MonitorMapas.cor('areia')},
                {label:'El Niño', data:t.map(p => p.el_nino), backgroundColor:MonitorMapas.cor('argila')}]},
    options:{...SEM_ANIM, plugins:{legend:{position:'bottom'}},
      scales:{x:{stacked:true}, y:{stacked:true, max:100, title:{display:true, text:'%'}}}}});
} else {
  // enquanto o plume IRI/CPC não é coletado: a leitura oficial do CPC via CPTEC e do Painel, como itens de legenda (dado declarado, não gráfico)
  const pg = SINAIS.enos.prognostico; const wp = document.getElementById('wrapPlume'); if (wp) wp.innerHTML = '';
  if (pg && pg.enso) MonitorMapas.legenda('legPlume', [{cor: MonitorMapas.cor('argila'), rotulo: 'El Niño: > 90% para SON/2026 (CPC/NOAA, ago/2026)'}, {cor: MonitorMapas.cor('ambar'), rotulo: '100% de permanência até início de 2027 (Boletim nº 3)'}, {cor: MonitorMapas.cor('sem-dado'), rotulo: 'plume por trimestre: sem coleta'}]);
}
credito('boxPlume', 'iri_plume');

// ---- Gráfico 3: estados por tipo de risco ----
const ordemTipos = Object.keys(TIPO_ROTULO).filter(t => UFS.some(uf => RISCO(uf) && RISCO(uf).tipo === t));
const contagem = ordemTipos.map(t => UFS.filter(uf => RISCO(uf) && RISCO(uf).tipo === t).length);
new Chart(document.getElementById('cTipos'), {type:'bar', data:{
    labels: ordemTipos.map(t => TIPO_CURTO[t]),
    datasets:[{data:contagem, backgroundColor:ordemTipos.map(t => TIPO_COR[t]), borderWidth:0}]},
  options:{...SEM_ANIM, indexAxis:'y', plugins:{legend:{display:false}},
    scales:{x:{title:{display:true, text:'estados'}, ticks:{precision:0}}}}});
credito('boxTipos', 'painel_el_nino');

// ---- Gráfico 4: tipo de risco × faixa MARÉ ----
const dados = FAIXAS.map(fx => ({label:fx.nome, backgroundColor:fx.cor, data: ordemTipos.map(t =>
  UFS.filter(uf => RISCO(uf) && RISCO(uf).tipo === t && MARE[uf] && faixaDe(MARE[uf].total).nome === fx.nome).length)}));
new Chart(document.getElementById('cCruz'), {type:'bar', data:{labels: ordemTipos.map(t => TIPO_CURTO[t]), datasets:dados},
  options:{...SEM_ANIM, plugins:{legend:{position:'bottom'}},
    scales:{x:{stacked:true}, y:{stacked:true, title:{display:true, text:'estados'}, ticks:{precision:0}}}}});
credito('boxCruz', 'painel_el_nino',
  'O estágio do arcabouço público vem do índice MARÉ; o tipo de risco, do boletim. O cruzamento é de leitura, e não entra no índice MARÉ.');

// =============================  Tabela de fontes  =============================
const CAMADA_ROTULO = {ciclo:'Ciclo', observado:'Observado', enos:'ENOS'};
}
__load();

// ===== sinais-de-risco.html · bloco 2 (extraído em 06/09/2026, CSP sem unsafe-inline) =====
window.addEventListener('load', function(){ if (window.VLibras && window.VLibras.Widget) { try { new window.VLibras.Widget('https://vlibras.gov.br/app'); } catch (e) {} } });
