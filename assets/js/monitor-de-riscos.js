// ===== monitor-de-riscos.html · bloco 1 (extraído em 06/09/2026, CSP sem unsafe-inline) =====
/* Sinais oficiais de risco — camada de apresentação.
   Regra desta página: nenhum valor é calculado aqui. Tudo vem de
   data/sinais_risco.json, escrito por coletar_sinais_risco.py, com fonte,
   documento e data. Fonte não coletada vira lacuna declarada na tela. */
let BR_GEOJSON, SINAIS, MARE, ALERTAS, CLIMA, FOCOS, NORMAIS;   // NORMAIS: normais do Inmet, para o DESVIO do mapa de calor
const UFS = ["AC","AL","AM","AP","BA","CE","DF","ES","GO","MA","MG","MS","MT","PA","PB","PE","PI","PR","RJ","RN","RO","RR","RS","SC","SE","SP","TO"];
const NEUTRA = MonitorMapas.cor('sem-dado');           // estado sem dado coletado
const TIPO_COR = {estiagem:MonitorMapas.PALETA.risco.seca, chuvas:MonitorMapas.PALETA.risco.chuvas, incendios:MonitorMapas.PALETA.risco.fogo, misto:MonitorMapas.PALETA.risco.multi, sem_sinal:MonitorMapas.PALETA.risco.sem_sinal};   // paleta semântica única
const FAIXAS = [
  {nome:'Estágio inicial', cor:MonitorMapas.PALETA.faixas.inicial, teste:v => v < 25},
  {nome:'Em construção',   cor:MonitorMapas.PALETA.faixas.construcao, teste:v => v < 50},
  {nome:'Consolidado',     cor:MonitorMapas.PALETA.faixas.consolidado, teste:v => v < 70},
  {nome:'Avançado',        cor:MonitorMapas.PALETA.faixas.avancado, teste:v => true},
];
const faixaDe = v => FAIXAS.find(f => f.teste(v));

async function __load(){
  [BR_GEOJSON, SINAIS, MARE] = await Promise.all(
    ['geo_uf','sinais_risco','indice'].map(f => fetch('data/' + f + '.json').then(r => {
      if(!r.ok) throw new Error('Falha ao carregar data/' + f + '.json');
      return r.json();
    }))
  );
  /* Os alertas por município moram na Defesa civil (24/09/2026); aqui entram só como contagem na
     linha-fato. Arquivo ausente não derruba a página: a linha fica com o texto estático dela. */
  ALERTAS = await fetch('data/alertas/vigentes.json').then(r => r.ok ? r.json() : null).catch(() => null);
  /* §209: temperatura e PM2,5 dos 5.570, em arquivo próprio (compacto) — a série por capital
     continua em sinais_risco.json. Ausente, a figura segue só com as capitais. */
  CLIMA = await fetch('data/clima_municipios.json').then(r => r.ok ? r.json() : null).catch(() => null);
  /* 29/09/2026: focos do INPE agregados em grade, em arquivo próprio — são milhares de células
     e não cabem no arquivo de sinais, que toda página da seção carrega inteiro. Ausente, o mapa
     diz que não houve coleta; nunca desenha zero. */
  NORMAIS = await fetch('data/normais_capitais.json').then(r => r.ok ? r.json() : null).catch(() => null);
  FOCOS = await fetch('data/focos_pontos.json').then(r => r.ok ? r.json() : null).catch(() => null);
  window.__refMunicipios = await fetch('data/municipios_ibge_referencia.json').then(r => r.ok ? r.json() : []).catch(() => []);
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
function credito(caixaId, fonteId){
  /* 29/09/2026: a linha passou a trazer o que a tabela removida trazia — órgão, o que o dado é e a
     situação —, porque a seção "Fontes dos sinais de risco" saiu e a fonte de uma figura pertence
     à figura. Situação só aparece quando NÃO é "coletado": dizer "coletado" em toda linha seria
     ruído, e dizer nada quando a fonte falhou seria esconder. */
  const f = fonteDe(fonteId);
  const SITUACAO = {aguardando_credencial: 'aguardando credencial', falhou: 'a fonte não respondeu na última consulta',
                    nao_coletado: 'sem coleta até o corte'};
  const partes = [f.orgao, f.nome].filter(Boolean);
  const situacao = coletada(fonteId) ? null : (SITUACAO[f.status] || 'sem coleta até o corte');
  if (situacao) partes.push(situacao);
  MonitorMapas.credito(caixaId, {fontes: partes.join(' · '), url: f.url_publica,
                                 data: coletada(fonteId) ? f.consultado_em : null});
  const d = document.querySelector('#' + caixaId + ' .fonte-figura'); if (d) d.dataset.credito = fonteId;
}

/* Alternativa em lista de uma figura por UF: `celulas(uf)` devolve o array de colunas depois da
   sigla, ou null quando aquela UF não tem leitura — e aí a linha diz a lacuna, não zero. */
function preencherTabela(tabelaId, celulas){
  const corpo = document.querySelector('#' + tabelaId + ' tbody');
  if(!corpo) return;
  const nCols = (document.querySelectorAll('#' + tabelaId + ' thead th').length || 2) - 1;
  corpo.innerHTML = UFS.map(uf => {
    const cols = celulas(uf) || Array(nCols).fill('sem coleta até o corte');
    return '<tr><td><strong>' + uf + '</strong></td>' + cols.map(c => '<td>' + esc(c) + '</td>').join('') + '</tr>';
  }).join('');
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


/* ---------- desenho genérico de mapa coroplético por UF (motor único em assets/mapas.js) ---------- */
const desenharMapa = (svgId, legendaId, corDe, rotuloDe, itensLegenda, familia) =>
  MonitorMapas.desenharMapa(__ctx(), svgId, legendaId, corDe, rotuloDe, itensLegenda, familia);
// 30/09/2026 (item 8): a atmosfera de cada família. As rampas são as aprovadas pela editoria;
// elas vivem em assets/mapas.js, e aqui só se escolhe qual família o mapa é.
const ATM = MonitorMapas.PALETA.atmosfera;
/** Anel vazio na capital sem dado (30/09/2026, item 8). O ponto existe, a cor não — assim a
 *  ausência se vê, e não se confunde com o degrau mais baixo da rampa. */
function anelVazio(svgId, ufsSemDado, atm, classe){
  const ctx = __ctx();
  const itens = ufsSemDado.map(uf => ({uf, lat: coordCapital[uf].lat, lon: coordCapital[uf].lon}));
  const svg = d3.select('#' + svgId); svg.selectAll('g.' + classe).remove();
  const g = svg.append('g').attr('class', classe);
  g.selectAll('circle').data(itens).join('circle')
    .attr('cx', d => ctx.projection([d.lon, d.lat])[0])
    .attr('cy', d => ctx.projection([d.lon, d.lat])[1])
    .attr('r', 6).attr('fill', 'none')
    .attr('stroke', atm.contorno).attr('stroke-width', 1.2)
    .attr('role', 'img')
    .attr('aria-label', d => d.uf + ': capital sem dado na consulta')
    .on('mouseenter', (evt, d) => MonitorMapas.showTip(d.uf + ': capital sem dado na consulta', evt))
    .on('mouseleave', MonitorMapas.hideTip);
  return g;
}
function __ctx(){ if (!window.__ctxCache) window.__ctxCache = MonitorMapas.contexto(BR_GEOJSON, 480, 460); return window.__ctxCache; }

// ---- Mapa 1: tipo de risco projetado (dado coletado) ----
const RISCO = uf => (SINAIS.uf[uf] || {}).risco_projetado;
const TIPO_ROTULO = SINAIS._formato.tipos_de_risco;
const TIPO_CURTO = SINAIS._formato.tipos_de_risco_curto;
// 27/09/2026 (pedido da editoria): o mapa do tipo de risco projetado saiu daqui. O dado não
// foi descartado — ele passou para o cartão de cada estado na página inicial, que é onde o
// leitor procura o seu próprio estado. Ver assets/js/index.js.
// ---- R6: o mapa nacional do risco PREVISTO (30/09/2026, volta à página por decisão da editoria)
// Previsão, não observação — e a legenda diz isso em cada degrau. O detalhe de cada estado continua
// na ficha, na inicial; aqui é o retrato nacional de uma vez só.
//
// As cores são as FAMÍLIAS do site (--seca, --fogo, --chuva, e âmbar para calor), as mesmas do
// resto das páginas: quem leu "seca" na ficha do estado encontra a mesma cor aqui. "Mais de um
// risco" não inventa cor nova — recebe o cinza-quente neutro e diz quais são no texto do mouse,
// porque uma cor de mistura sugeriria um risco intermediário que não existe.
const RISCO_FAMILIA_COR = {
  estiagem: MonitorMapas.PALETA.familia.seca, seca: MonitorMapas.PALETA.familia.seca,
  incendios: MonitorMapas.PALETA.familia.fogo, fogo: MonitorMapas.PALETA.familia.fogo,
  chuvas: MonitorMapas.PALETA.familia.chuva, chuva: MonitorMapas.PALETA.familia.chuva,
  calor: MonitorMapas.PALETA.familia.calor,
};
const RISCO_FAMILIA_ROTULO = {estiagem:'Seca', seca:'Seca', incendios:'Fogo', fogo:'Fogo',
                              chuvas:'Chuva forte', chuva:'Chuva forte', calor:'Calor'};
const COR_VARIOS = MonitorMapas.cor('cinza-quente');
const riscoDe = uf => (SINAIS.uf[uf] || {}).risco_projetado || null;
const componentesDe = uf => {
  const r = riscoDe(uf); if (!r) return [];
  const c = (r.componentes && r.componentes.length ? r.componentes : [r.tipo]).filter(Boolean);
  return c.filter(x => x !== 'sem_sinal');
};
desenharMapa('mapaRiscoPrevisto', 'legRiscoPrevisto',
  uf => { const c = componentesDe(uf);
    if (!c.length) return MonitorMapas.PALETA.zero;
    if (c.length === 1) return RISCO_FAMILIA_COR[c[0]] || MonitorMapas.PALETA.zero;
    // 01/10/2026: duas famílias, as DUAS cores em hachura. O cinza liso de antes dizia "nenhuma
    // das duas" — e era a categoria mais frequente do mapa virando mancha sem informação.
    const cores = c.map(x => RISCO_FAMILIA_COR[x]).filter(Boolean);
    return cores.length >= 2
      ? MonitorMapas.hachura('mapaRiscoPrevisto', cores[0], cores[1])
      : (cores[0] || MonitorMapas.PALETA.zero); },
  uf => { const r = riscoDe(uf); if (!r) return 'Sem sinal elevado para este estado no boletim';
    const c = componentesDe(uf);
    const nomes = c.map(x => RISCO_FAMILIA_ROTULO[x] || x).join(' e ');
    return '<em>' + esc(nomes || 'Sem sinal elevado') + '</em>'
      + (r.texto ? '<br>' + esc(r.texto) : ''); },
  [{cor: MonitorMapas.PALETA.familia.seca, rotulo:'Seca'},
   {cor: MonitorMapas.PALETA.familia.fogo, rotulo:'Fogo'},
   {cor: MonitorMapas.PALETA.familia.chuva, rotulo:'Chuva forte'},
   {cor: MonitorMapas.PALETA.familia.calor, rotulo:'Calor'},
   {cor: COR_VARIOS, rotulo:'Mais de um risco', hachura:true},
   {cor: MonitorMapas.PALETA.zero, rotulo:'Sem sinal elevado'}], 'previsto');
credito('boxRiscoPrevisto', 'painel_el_nino');

(function tabelaRiscoPrevisto(){
  const tb = document.querySelector('#tblRiscoPrevisto tbody'); if (!tb) return;
  tb.innerHTML = Object.keys(SINAIS.uf).sort().map(uf => {
    const c = componentesDe(uf);
    const nomes = c.map(x => RISCO_FAMILIA_ROTULO[x] || x).join(' e ') || 'Sem sinal elevado';
    return '<tr><td>' + esc(uf) + '</td><td>' + esc(nomes) + '</td></tr>';
  }).join('');
})();

/* Alinhamento da grade de cartões (01/10/2026).
   O `min-height` em CSS reserva um PISO, não um teto: numa coluna estreita a linha do boletim da
   seca quebra em três linhas e empurra título, subtítulo e mapa daquele cartão para baixo — foi o
   que o portão de consistência visual pegou, com razão.

   Reservar um número fixo de linhas resolveria o alinhamento ao custo de cortar texto aprovado
   numa largura e deixar faixa branca em outra. Aqui a reserva é MEDIDA: cada bloco de texto recebe
   a altura do mais alto entre os seis, depois do desenho e a cada mudança de largura. Ninguém é
   cortado, e os seis começam o mapa na mesma linha em qualquer tela. */
(function alinharCartoes(){
  const BLOCOS = ['.cartao-mapa-boletim', '.figura-titulo', '.figura-sub'];
  function alinhar(){
    const cartoes = [...document.querySelectorAll('.grade-mapas > .cartao-mapa')];
    if (cartoes.length < 2) return;
    // Numa coluna só (celular) não há com que alinhar, e a reserva viraria espaço vazio.
    const umaColuna = cartoes.length > 1
      && Math.abs(cartoes[0].getBoundingClientRect().top - cartoes[1].getBoundingClientRect().top) > 4;
    for (const seletor of BLOCOS) {
      const alvos = cartoes.map(c => c.querySelector(seletor)).filter(Boolean);
      alvos.forEach(e => { e.style.minHeight = ''; });
      if (umaColuna) continue;
      const alto = Math.max(...alvos.map(e => e.getBoundingClientRect().height));
      alvos.forEach(e => { e.style.minHeight = alto + 'px'; });
    }
  }
  // Guardas: o portão de runtime roda a página num DOM sem requestAnimationFrame nem document.fonts,
  // e sem elas o alinhamento derrubava a página inteira — uma melhoria de layout não pode custar o
  // carregamento. Sem RAF, alinha direto; sem `fonts`, alinha com a fonte que houver.
  const temRAF = typeof requestAnimationFrame === 'function';
  const quando = () => temRAF
    ? requestAnimationFrame(() => requestAnimationFrame(alinhar))
    : alinhar();
  try { quando(); } catch (e) { /* layout é melhoria: nunca derruba a página */ }
  try { if (document.fonts && document.fonts.ready) document.fonts.ready.then(quando); } catch (e) {}
  try { addEventListener('resize', quando); } catch (e) {}
})();

// ---- Subtítulos das figuras, gerados do dado (30/09/2026). O HTML traz só a parte fixa da frase;
// a data, a contagem e o documento vêm daqui, para nenhum número viver escrito na página.
(function subtitulos(){
  const fonte = k => (SINAIS.fontes || {})[k] || {};
  const põe = (id, texto) => { const el = document.getElementById(id); if (el && texto) el.textContent = texto; };
  const dia = v => MonitorMapas.dataBR(v) || null;

  // R4 — o subtítulo aprovado em 30/09, com o ano final gerado do dado. Antes ele saía "1950 a —"
  // porque a parte fixa vivia no HTML e a variável nunca era preenchida.
  const roni = SINAIS.enos.roni, sr = (roni && roni.serie) || [];
  if (sr.length) põe('roniSub', 'Índice RONI, da NOAA · temperatura do Pacífico acima ou abaixo do '
    + 'normal · média de três meses · °C · 1950 a ' + sr[sr.length - 1].ano);

  // F.3 — a janela da série mensal, dos dois extremos do próprio dado.
  const an = SINAIS.enos.nino34_mensal, sa = (an && an.serie) || [];
  if (sa.length) {
    const mes = p => ['jan','fev','mar','abr','mai','jun','jul','ago','set','out','nov','dez'][p.mes - 1]
      + '/' + p.ano;
    põe('anomaliaSub', 'Região Niño 3.4 · diferença em relação ao normal · média mensal · °C · '
      + mes(sa[0]) + ' a ' + mes(sa[sa.length - 1]));
  }

  // R6 — o boletim que sustenta a previsão.
  const pe = fonte('painel_el_nino');
  põe('linhaRiscoPrevisto', 'O que os órgãos federais projetam para o ciclo, estado a estado.');
  põe('riscoPrevistoSub', 'Risco previsto até março de 2027 · por estado'
    + (pe.documento ? ' · ' + pe.documento : '')
    + (pe.consultado_em ? ', ' + pe.consultado_em : ''));

  // R7 — o mês do mapa de seca.
  const algumaSeca = Object.keys(SINAIS.uf).map(uf => (SINAIS.uf[uf].secas || {}).mapa).find(Boolean);
  // O mês vem do dado com inicial maiúscula ('Agosto de 2026'); no meio da frase ele é minúscula.
  const semCaixaAlta = t => String(t || '').charAt(0).toLowerCase() + String(t || '').slice(1);
  if (algumaSeca) põe('secasSub', 'Mapa de ' + semCaixaAlta(algumaSeca)
    + ' · categoria de seca em pelo menos metade da área do estado');

  // R8 — a hora do corte e o total de focos.
  const totalFocos = Object.keys(SINAIS.uf)
    .reduce((soma, uf) => soma + (((SINAIS.uf[uf] || {}).fogo || {}).focos_24h || 0), 0);
  const fFogo = fonte('inpe_fogo');
  if (totalFocos) põe('fogoSub', 'Últimas 24 horas, até ' + (fFogo.consultado_em || dia(SINAIS.gerado_em) || '')
    + ' · ' + totalFocos.toLocaleString('pt-BR') + ' focos · cada ponto reúne os focos de uma área de cerca de 11 km');

  // R9 — o dia da pior hora.
  const fAr = fonte('open_meteo_ar');
  põe('arSub', 'Pior hora do dia ' + (fAr.consultado_em || dia(SINAIS.gerado_em) || '')
    + ' · uma capital por estado · estimativa por modelo');

  // R10 — o dia da previsão.
  const fTemp = fonte('inmet_previsao_capitais');
  põe('temperaturaSub', 'Previsão para ' + (fTemp.consultado_em || dia(SINAIS.gerado_em) || '')
    + ' · máxima prevista e diferença para a média histórica do mês · °C · uma capital por estado');

  // R11 — a hora da consulta dos avisos.
  const fAvisos = fonte('inmet_avisos');
  // O texto aprovado é "Avisos em vigor na consulta, {dd/mm hh:mm}" e fica inteiro; o segundo
  // segmento existe porque o formato de subtítulo do site separa por "·", e ele acrescenta
  // informação (a unidade do mapa) em vez de repetir a primeira parte.
  põe('avisosSub', 'Avisos em vigor na consulta, ' + (fAvisos.consultado_em || dia(SINAIS.gerado_em) || '')
    + ' · por estado');
})();

// ---- Linha de cada bloco de família (R7, R8, R10, R11): quantos estados e quais.
// Gerada do boletim, nunca escrita à mão. Quando nenhum estado tem a família, a linha some em vez
// de dizer "0 estados" — zero estados não é informação útil aqui, e a frase aprovada pressupõe a
// lista.
(function linhasDasFamilias(){
  const ufsCom = fam => Object.keys(SINAIS.uf).sort()
    .filter(uf => componentesDe(uf).some(c => (RISCO_FAMILIA_ROTULO[c] || '') === fam));
  const escreve = (id, fam, frase) => {
    const el = document.getElementById(id); if (!el) return;
    const lista = ufsCom(fam);
    // Sem estados naquela família, a linha fica VAZIA, não escondida: esconder encurta o cartão
    // e desalinha a grade, que é o defeito que o componente único existe para corrigir.
    if (!lista.length) { el.textContent = ''; return; }
    el.textContent = frase.replace('{n}', lista.length).replace('{lista}', lista.join(', ')) + '.';
  };
  // 01/10/2026: a linha do boletim passou para DENTRO de cada cartão, e os ids acompanham o do
  // cartão. O de qualidade do ar é da mesma família do fogo e repete a linha dela — é o boletim que
  // fala da família, não do mapa. No cartão de risco previsto a linha é o próprio subtítulo da
  // previsão, escrito em `subtitulos()`.
  escreve('linhaSecas', 'Seca', 'O boletim prevê seca para {n} estados: {lista}');
  escreve('linhaFogo', 'Fogo', 'O boletim prevê risco de fogo para {n} estados: {lista}');
  escreve('linhaAr', 'Fogo', 'O boletim prevê risco de fogo para {n} estados: {lista}');
  escreve('linhaTemperatura', 'Calor',
          'O boletim prevê calor acima do normal para {n} estados: {lista}');
  escreve('linhaAvisos', 'Chuva forte',
          'O boletim prevê chuva acima do normal para {n} estados: {lista}');
})();

// ---- Mapa 2: seca observada ----
// 15/09/2026: a fonte passou a ser o RPC de dados tabulares da ANA (fração cumulativa da área da UF em cada categoria
// S0–S4, mapa mensal). O mapa mostra a categoria MEDIANA da área — a mais severa que cobre pelo menos metade da UF
// ('sem seca' quando a seca não chega à metade); o tooltip traz a distribuição completa. Nunca uma média.
// 30/09/2026 (item 8): a rampa aprovada da seca — seis degraus de papel ressecado a terra
// queimada, no lugar do ordinal genérico do site. Seis categorias pedem seis degraus; o ordinal
// tinha quatro e obrigava dois deles a dividir tom com o vizinho.
const SECA_COR = {'sem seca': ATM.seca.rampa[0], S0: ATM.seca.rampa[1], S1: ATM.seca.rampa[2],
                  S2: ATM.seca.rampa[3], S3: ATM.seca.rampa[4], S4: ATM.seca.rampa[5]};
const SECA_ROTULO = {'sem seca':'sem seca em metade ou mais da área', S0:'S0 · seca fraca', S1:'S1 · seca moderada', S2:'S2 · seca grave', S3:'S3 · seca extrema', S4:'S4 · seca excepcional'};   // vocabulário do Monitor de Secas
const seca = uf => (SINAIS.uf[uf] || {}).secas;
const secaCat = s => s ? (s.categoria_mediana || s.categoria) : null;
const pct1 = v => String(Math.round(v * 10) / 10).replace('.', ',') + '%';
desenharMapa('mapaSecas', 'legSecas',
  uf => { const s = seca(uf); const c = secaCat(s); return c ? (SECA_COR[c] || NEUTRA) : NEUTRA; },
  uf => { const s = seca(uf); if (!s) return 'Aguardando a primeira coleta desta fonte';
    const c = secaCat(s); const cob = s.cobertura_pct || {};
    const dist = ['sem seca','S0','S1','S2','S3','S4'].filter(k => (cob[k] || 0) >= 0.05).map(k => esc(k) + ' ' + pct1(cob[k])).join(' · ');
    return '<em>' + esc(SECA_ROTULO[c] || c) + '</em>' + (s.mapa ? '<br>mapa ' + esc(s.mapa) : '') + (dist ? '<br>área da UF: ' + dist : ''); },
  // R7 (30/09/2026): a legenda aprovada é em português corrente — "Fraca" em vez de "S0". O código
  // do Monitor de Secas continua no texto do mouse, para quem for conferir na fonte.
  [{cor:SECA_COR['sem seca'], rotulo:'Sem seca'}, {cor:SECA_COR.S0, rotulo:'Fraca'},
   {cor:SECA_COR.S1, rotulo:'Moderada'}, {cor:SECA_COR.S2, rotulo:'Grave'},
   {cor:SECA_COR.S3, rotulo:'Extrema'}, {cor:SECA_COR.S4, rotulo:'Excepcional'},
   {cor:NEUTRA, rotulo:'Sem coleta até o corte'}], 'seca');
credito('boxSecas', 'monitor_secas');

// ---- Mapa 3: temperatura máxima prevista nas capitais (24/09/2026) ----
/* O valor é da CAPITAL, não a média do estado: a UF é pintada para localizar, e tanto o texto do
   mouse quanto a lista dizem qual cidade foi lida. Estimativa de modelo, nunca medição de estação —
   o rótulo vem do próprio dado (campo `natureza`), não escrito à mão aqui. */
const temp = uf => (SINAIS.uf[uf] || {}).temperatura;
const serieTemp = uf => ((temp(uf) || {}).serie) || [];
/* 27/09/2026 (pedido da editoria: "temperatura reportada por um órgão competente"). O dado passou
   a vir do INMET (previsão oficial para as 27 capitais) no lugar do Open-Meteo, que roda modelos
   estrangeiros. E o mapa deixou de PINTAR O ESTADO INTEIRO a partir de um ponto na capital: a
   medida é de um ponto, então o mapa mostra um ponto. Pintar a UF afirmava visualmente uma
   cobertura estadual que o dado não tem — o que a direção de arte §10 proíbe. */
const coordCapital = {};
(window.__refMunicipios || []).forEach(m => {
  const t = temp(m.uf);
  if (t && t.capital && m.nome === t.capital && m.lat != null) coordCapital[m.uf] = {lat: m.lat, lon: m.lon};
});
const tmaxDe = uf => { const t = temp(uf); return t && typeof t.tmax === 'number' ? t.tmax : null; };
const temps = UFS.map(tmaxDe).filter(v => v != null);
const tMin = temps.length ? Math.min(...temps) : 0, tMax = temps.length ? Math.max(...temps) : 1;
// 30/09/2026 (item 8): a rampa aprovada do calor, em quatro degraus. O ESTADO NUNCA É PINTADO —
// o dado é da capital, e pintar a UF faria o leitor ler como se valesse para o território inteiro.
/* 01/10/2026 (R10): a cor passa a ser o DESVIO contra a normal 1991–2020 do Inmet, e não a
   temperatura absoluta. 35 °C é normal em Cuiabá e muito quente em Porto Alegre; pintar pela
   temperatura fazia o mapa dizer "está quente no Centro-Oeste" todo dia do ano, que é geografia e
   não notícia. Os degraus são os da legenda aprovada: normal · até 2 · 2 a 4 · mais de 4.

   Capital sem normal publicada fica SEM desvio — anel vazio, nunca estimativa. É por isso que
   `desvioDe` devolve null em vez de zero: zero significaria "está na média", que é uma afirmação,
   e nós não a temos. */
const normalDe = uf => {
  const c = (NORMAIS && NORMAIS.capitais) ? NORMAIS.capitais[uf] : null;
  if (!c || !Array.isArray(c.tmax)) return null;
  // O mês da PREVISÃO, não o de hoje: a previsão pode ser do primeiro dia do mês seguinte.
  const d = ((temp(uf) || {}).data || '').match(/(\d{2})\/(\d{2})/);
  const mes = d ? Number(d[2]) : (new Date()).getMonth() + 1;
  const v = c.tmax[mes - 1];
  return typeof v === 'number' ? v : null;
};
const desvioDe = uf => {
  const t = tmaxDe(uf), n = normalDe(uf);
  return (t == null || n == null) ? null : Math.round((t - n) * 10) / 10;
};
const DEGRAUS_DESVIO = [0, 2, 4];
const escalaTemp = d => {
  const v = desvioDe(d && d.uf ? d.uf : d);
  if (v == null) return ATM.calor.fundo;
  return ATM.calor.rampa[DEGRAUS_DESVIO.filter(l => v > l).length];
};
const rotuloTemp = uf => { const t = temp(uf); if (!t) return 'Aguardando a primeira coleta desta fonte';
  const dv = desvioDe(uf), nm = normalDe(uf);
  const linhaDesvio = dv == null
    ? '<br>Sem normal publicada para esta capital: o desvio não é calculado'
    : '<br>' + (dv >= 0 ? '+' : '') + String(dv).replace('.', ',') + ' °C em relação à média de '
      + String(nm).replace('.', ',') + ' °C do mês (normal 1991–2020, Inmet)';
  return esc(t.capital || uf) + '<br>M\u00e1xima prevista: ' + (t.tmax != null ? t.tmax + ' \u00b0C' : 'sem valor')
    + linhaDesvio
    + (t.tmin != null ? '<br>M\u00ednima prevista: ' + t.tmin + ' \u00b0C' : '')
    + (t.resumo ? '<br>' + esc(t.resumo) : '') + '<br>' + esc(t.data || '') + ' \u00b7 ' + esc(t.natureza || ''); };
// o mapa base fica NEUTRO: ele é só o contorno onde os pontos se apoiam
desenharMapa('mapaTemperatura', 'legTemperatura', () => ATM.calor.uf, rotuloTemp,
  // Nenhum degrau sem rótulo: informação que existe só por cor não existe para quem não a
  // distingue. Cada degrau recebe a faixa de temperatura que ele cobre, lida do próprio dado.
  // Legenda aprovada do R10: ela nomeia o DESVIO, não a temperatura.
  [{cor: ATM.calor.rampa[0], rotulo: 'Normal'},
   {cor: ATM.calor.rampa[1], rotulo: 'Até 2 °C acima'},
   {cor: ATM.calor.rampa[2], rotulo: '2 a 4 °C acima'},
   {cor: ATM.calor.rampa[3], rotulo: 'Mais de 4 °C acima'},
   {cor: ATM.calor.fundo, rotulo: 'Sem dado'}], 'calor');
MonitorMapas.pontos(__ctx(), 'mapaTemperatura',
  UFS.filter(uf => coordCapital[uf] && desvioDe(uf) != null)
     .map(uf => ({uf, lat: coordCapital[uf].lat, lon: coordCapital[uf].lon, v: tmaxDe(uf)})),
  // F.5 (editoria, 30/09): UM ponto por capital, do mesmo tamanho para todas. O halo translúcido
  // proporcional ao desvio aparecia como "duplo círculo", com distâncias diferentes de uma capital
  // para outra — dois círculos com raios distintos leem-se como duas medidas, e é uma só. A cor diz
  // o desvio; o número ao lado diz a máxima prevista.
  {r: () => 6, cor: d => escalaTemp(d), rotulo: d => rotuloTemp(d.uf), classe: 'pontosTemp'});
// Capital SEM dado: anel vazio no ponto da capital — nunca cor no estado, nunca ponto ausente.
// Ausência de dado e dado baixo não podem se parecer, e o estado em branco não é "sem calor".
// Sem máxima prevista OU sem normal publicada: anel vazio. Os dois casos são ausência, e a
// legenda os nomeia junto — a leitora não precisa saber qual dos dois faltou para entender que
// aquela capital não tem desvio.
anelVazio('mapaTemperatura', UFS.filter(uf => coordCapital[uf] && desvioDe(uf) == null), ATM.calor,
          'anelTemp');
credito('boxTemperatura', 'inmet_previsao_capitais');
// A visão MUNICIPAL da temperatura continua vindo do Open-Meteo (clima_municipios.json): o INMET
// publica previsão por capital, não pelos 5.571 municípios. São duas fontes para duas granularidades,
// e cada uma é creditada onde aparece.
if (document.getElementById('boxTemperaturaMun')) credito('boxTemperaturaMun', 'open_meteo_tempo');
preencherTabela('tblTemperatura', uf => { const t = temp(uf); if (!t) return null;
  return [t.capital || '', t.tmax != null ? t.tmax + ' \u00b0C' : 'sem valor',
          t.tmin != null ? t.tmin + ' \u00b0C' : 'sem valor', t.resumo || 'sem resumo']; });

// ---- Mapa 4: índice de qualidade do ar nas capitais (27/09/2026) ----
/* Decisão da editoria: a página mostra ÍNDICE, não PM2,5 — é o que interessa a quem lê. O índice
   vem PRONTO da fonte e nunca é calculado aqui: calculá-lo faria dele uma afirmação do Monitor, e
   ele precisa ser evidência de terceiro. Não existe índice nacional aberto (conferido em
   27/09/2026), por isso a escala é a europeia e a legenda diz isso. Pontos nas capitais, não
   pintura por UF, pela mesma razão da temperatura. */
const ar = uf => (SINAIS.uf[uf] || {}).qualidade_ar;
const nomeCapital = (o, uf) => (o && ((o.capital && o.capital.nome) || o.capital)) || uf;
const iqa = uf => ((ar(uf) || {}).indice || {}).valor;
const iqaVals = UFS.map(iqa).filter(v => typeof v === 'number');
const iqaMax = iqaVals.length ? Math.max(...iqaVals) : 1;
// 30/09/2026 (item 8): as cinco faixas do EAQI, na rampa aprovada. O índice europeu é ordinal e
// fechado — cinco faixas, não um contínuo —, então a escala é por degrau, e não interpolada.
const FAIXAS_EAQI = [20, 40, 60, 80];
const escalaAr = v => ATM.ar.rampa[FAIXAS_EAQI.filter(l => v > l).length];
const rotuloAr = uf => { const a = ar(uf); if (!a) return 'Aguardando a primeira coleta desta fonte';
  const i = a.indice; if (!i) return esc(nomeCapital(a, uf)) + '<br>\u00cdndice sem publica\u00e7\u00e3o nesta rodada';
  return esc(nomeCapital(a, uf)) + '<br>\u00cdndice ' + esc(i.escala) + ': ' + i.valor
    + '<br>' + esc(i.criterio) + ' (' + esc(String(i.hora).replace('T', ' \u00e0s ')) + ')'
    + '<br>publicado por ' + esc(i.publicado_por); };
desenharMapa('mapaAr', 'legAr', () => ATM.ar.uf, rotuloAr,
  [{cor: ATM.ar.rampa[0], rotulo: 'Boa'}, {cor: ATM.ar.rampa[1], rotulo: 'Razo\u00e1vel'},
   {cor: ATM.ar.rampa[2], rotulo: 'Moderada'}, {cor: ATM.ar.rampa[3], rotulo: 'Ruim'},
   {cor: ATM.ar.rampa[4], rotulo: 'Muito ruim'},
   {cor: ATM.ar.fundo, rotulo: 'Sem dado'}], 'ar');
MonitorMapas.pontos(__ctx(), 'mapaAr',
  UFS.filter(uf => coordCapital[uf] && typeof iqa(uf) === 'number')
     .map(uf => ({uf, lat: coordCapital[uf].lat, lon: coordCapital[uf].lon, v: iqa(uf)})),
  {r: () => 6, cor: d => escalaAr(d.v), rotulo: d => rotuloAr(d.uf), classe: 'pontosAr'});
anelVazio('mapaAr', UFS.filter(uf => coordCapital[uf] && typeof iqa(uf) !== 'number'), ATM.ar,
          'anelAr');
credito('boxAr', 'open_meteo_ar');


/* CAMADA MUNICIPAL (§209) — os mesmos dois fenômenos, nos 5.570 municípios.
   Pergunta igual, recorte diferente: a camada de capitais traz a série e os demais poluentes; a
   municipal traz um ponto por município. Cada uma com sua legenda e seu texto-fato; o seletor
   troca as duas coisas junto, porque número de um recorte lido como se fosse do outro é erro que
   parece dado. Município sem leitura NÃO é desenhado — ausência é ausência. */
(function camadaMunicipal(){
  if (!CLIMA || !CLIMA.municipios || !Object.keys(CLIMA.municipios).length) {
    /* Sem coleta municipal, o seletor não pode oferecer uma camada vazia: ele sai, e a figura
       segue sendo a de capitais, sem prometer o que não tem. */
    ['selTemperatura','selAr'].forEach(id => { const s = document.getElementById(id); if (s) s.remove(); });
    return;
  }
  const REF = window.__refMunicipios || [];
  const coord = {};
  REF.forEach(m => { coord[String(m.codigo_ibge).padStart(7,'0')] = [m.lon, m.lat]; });

  const casos = [
    {sel:'selTemperatura', svgCap:'mapaTemperatura', svgMun:'mapaTemperaturaMun',
     legCap:'legTemperatura', legMun:'legTemperaturaMun', campo:'tmax', unidade:'°C',
     rotulo: v => v.toFixed(0) + ' °C'},
    {sel:'selAr', svgCap:'mapaAr', svgMun:'mapaArMun',
     legCap:'legAr', legMun:'legArMun', campo:'pm25', unidade:'µg/m³',
     rotulo: v => v.toFixed(0) + ' µg/m³'},
  ];

  casos.forEach(function(caso){
    const itens = Object.entries(CLIMA.municipios)
      .filter(par => typeof par[1][caso.campo] === 'number' && coord[par[0]])
      .map(par => ({cod: par[0], v: par[1][caso.campo], ll: coord[par[0]]}));
    const sel = document.getElementById(caso.sel);
    if (!itens.length) { if (sel) sel.remove(); return; }

    const vals = itens.map(m => m.v);
    const vmin = Math.min.apply(null, vals), vmax = Math.max.apply(null, vals);
    const escala = d3.scaleLinear().domain([vmin, vmax]).range(MonitorMapas.PALETA.rampaPerigo).clamp(true);

    /* Cinco faixas iguais desenhadas como cinco camadas densas — um <path> por faixa, que é o que
       torna 5 mil pontos baratos. Classe própria por faixa: `pontosDensos` remove a camada
       anterior quando a classe se repete (achado do §208). */
    const svg = d3.select('#' + caso.svgMun);
    svg.append('g').selectAll('path').data(BR_GEOJSON.features).join('path')
      .attr('d', pathGen).attr('fill', MonitorMapas.cor('zebra')).attr('class', 'uf-path');
    const FAIXAS = 5;
    for (let f = 0; f < FAIXAS; f++) {
      const lo = vmin + (vmax - vmin) * f / FAIXAS, hi = vmin + (vmax - vmin) * (f + 1) / FAIXAS;
      const naFaixa = itens.filter(m => m.v >= lo && (f === FAIXAS - 1 ? m.v <= hi : m.v < hi))
                           .map(m => ({lon: m.ll[0], lat: m.ll[1]}));
      if (naFaixa.length) {
        MonitorMapas.pontosDensos(__ctx(), caso.svgMun, naFaixa, escala((lo + hi) / 2), 1.8, 0.85,
                                  'densos-' + caso.campo + '-' + f);
      }
    }
    MonitorMapas.siglas(__ctx(), svg);
    MonitorMapas.legendaContinua(caso.legMun,
      'linear-gradient(90deg,' + MonitorMapas.PALETA.rampaPerigo[0] + ',' + MonitorMapas.PALETA.rampaPerigo[1] + ')',
      caso.rotulo(vmin), caso.rotulo(vmax),
      [{cor: MonitorMapas.cor('zebra'), rotulo: 'sem leitura neste município'}]);

    if (sel) {
      sel.addEventListener('change', function(e){
        const mun = e.target.value === 'municipios';
        /* toggleAttribute, não `.hidden`: em SVG a propriedade não reflete no atributo (§208). */
        [[caso.svgCap, !mun], [caso.svgMun, mun], [caso.legCap, !mun], [caso.legMun, mun]]
          .forEach(par => { const el = document.getElementById(par[0]); if (el) el.toggleAttribute('hidden', !par[1]); });
      });
    }
  });

  /* Texto-fato da cobertura, uma vez, abaixo da seção: quantos municípios cada variável alcançou,
     e de QUANDO é cada leitura. Sem a contagem, um mapa com 5.570 pontos e outro com 1.700
     pareceriam a mesma coisa; sem a data, a data da coleta passaria por data de tudo — e o teto
     diário da fonte não deixa renovar as duas variáveis no mesmo dia (25/09/2026). */
  const r = CLIMA.resumo || {};
  const linha = document.getElementById('linhaAlertas');
  const datas = d => {
    const e = Object.entries(d || {}).sort((a, b) => b[1] - a[1]);
    if (!e.length) return '';
    if (e.length === 1) return ', lida em ' + e[0][0];
    return ', lida em ' + e.map(([dt, n]) => dt + ' (' + n.toLocaleString('pt-BR') + ')').join(' e ');
  };
  if (linha && r.municipios_no_pais) {
    const extra = document.createElement('p');
    extra.className = 'hint';
    extra.id = 'coberturaClima';
    const n = v => Number(v || 0).toLocaleString('pt-BR');
    extra.textContent = 'Temperatura em ' + n(r.com_temperatura) + ' de ' + n(r.municipios_no_pais)
      + ' municípios' + datas(r.temperatura_por_data)
      + '; PM2,5 em ' + n(r.com_pm25) + datas(r.pm25_por_data) + '.';
    linha.insertAdjacentElement('afterend', extra);
  }
})();

/* CAMADA DE MEDIÇÃO (24/09/2026) — pontos de estação e de monitor sobre os dois mapas de modelo.
   As duas fontes exigem credencial (OpenAQ v3 recusa com 401 sem chave; o endpoint de dados das
   estações do INMET passou a exigir token). Enquanto a credencial não existir, a figura DIZ isso
   na legenda, e nenhum ponto é desenhado: modelo e medição nunca compartilham a escala de cor, e
   ausência de medição não é medição igual ao modelo. */
(function camadaDeMedicao(){
  const casos = [
    {fonte: 'inmet_estacoes', legenda: 'legTemperatura', campo: 'temperatura_medida', svg: 'mapaTemperatura'},
    {fonte: 'openaq', legenda: 'legAr', campo: 'ar_medido', svg: 'mapaAr'},
  ];
  casos.forEach(function(caso){
    const f = fonteDe(caso.fonte);
    const pontos = UFS.map(uf => [uf, (SINAIS.uf[uf] || {})[caso.campo]]).filter(par => par[1]);
    const leg = document.getElementById(caso.legenda);
    if (!leg) return;
    // 01/10/2026: sem pontos de medição, a legenda NÃO ganha linha. O estado da coleta não é
    // categoria do mapa, e a legenda diz apenas o que o mapa é. A ausência continua declarada no
    // crédito da figura, que é onde a procedência mora.
    if (!pontos.length) return;
    const svg = d3.select('#' + caso.svg);
    svg.append('g').selectAll('circle').data(pontos).join('circle')
      .attr('cx', par => projection([par[1].coordenada.lon, par[1].coordenada.lat])[0])
      .attr('cy', par => projection([par[1].coordenada.lon, par[1].coordenada.lat])[1])
      .attr('r', 3.4).attr('fill', MonitorMapas.cor('branco'))
      .attr('stroke', MonitorMapas.cor('abissal')).attr('stroke-width', 1.4)
      .on('mouseenter', (evt, par) => showTip(
        '<strong>' + esc(par[0]) + '</strong><br>' + esc(par[1].nome || '')
        + '<br>' + esc(par[1].natureza) + ' · ' + esc(par[1].distancia_km) + ' km da capital'
        + (par[1].rede_de_origem ? '<br>rede: ' + esc(par[1].rede_de_origem) : ''), evt))
      .on('mousemove', (evt) => showTip(document.getElementById('mapTooltip').innerHTML, evt))
      .on('mouseleave', hideTip);
    // A contagem de pontos saiu da legenda pela mesma razão: ela é sobre a camada, não uma
    // categoria do mapa. Cada ponto continua se explicando no texto do mouse.
  });
})();

/* Linha-fato dos alertas: a contagem fica aqui, os alertas moram na Defesa civil. Só reescreve
   quando o arquivo carregou — sem ele, o texto estático do HTML permanece, sem número inventado. */
(function linhaDeAlertas(){
  const el = document.getElementById('linhaAlertas');
  if(!el || !ALERTAS || !ALERTAS.resumo) return;
  const r = ALERTAS.resumo;
  el.innerHTML = r.municipios_inmet + ' município(s) sob aviso do INMET e ' + r.municipios_cemaden
    + ' sob alerta do CEMADEN, em ' + esc(MonitorMapas.dataBR(ALERTAS.gerado_em) || '')
    + ' · <a href="defesa-civil.html#alertas">Defesa civil</a>';
})();
preencherTabela('tblAr', uf => { const a = ar(uf); if (!a) return null;
  const m = a.media_diaria || {}, u = (a.unidades || {}).pm2_5 || 'µg/m³';
  const num = (x) => typeof x === 'number' ? x + ' ' + u : 'sem valor';
  const i = a.indice;
  return [nomeCapital(a, uf), i ? i.escala + ' ' + i.valor : 'sem valor',
          num(m.pm2_5), num(m.pm10), num(m.ozone)]; });

// ---- Mapa 4: focos ativos, por POSIÇÃO (29/09/2026) ----
/* Era coroplético por UF: o estado inteiro pintado pela contagem. O CSV do INPE traz latitude e
   longitude de cada foco, e pintar a UF jogava fora justamente onde o fogo está — um foco no oeste
   da Bahia e outro no litoral viravam a mesma mancha. Agora é um ponto por célula de 0,1° (~11 km),
   agregado no coletor porque 26.873 focos num dia não desenham num SVG.
   A contagem por UF não saiu: ela continua na lista e no rótulo, que é o que serve a leitor de
   tela e a quem quer o número exato. */
const fogo = uf => (SINAIS.uf[uf] || {}).fogo;
(function desenharFocos(){
  const svg = d3.select('#mapaFogo');
  const base = FOCOS && Array.isArray(FOCOS.pontos) ? FOCOS.pontos : null;
  if (!base || !base.length) {
    MonitorMapas.legenda('legFogo', [{cor: NEUTRA, rotulo: 'Sem coleta até o corte'}]);
    return;
  }
  /* O mapa base fica NEUTRO: é só o contorno onde os pontos se apoiam — mesmo padrão dos mapas de
     capital desta página. Sem ele os focos flutuavam sem país, e foi o portão de runtime que pegou:
     ele exige os 27 estados desenhados, e estava certo em exigir. */
  desenharMapa('mapaFogo', 'legFogo', () => ATM.fogo.uf,
    uf => { const f = fogo(uf); const n = f ? f.focos_24h : null;
            return n == null ? 'Aguardando a primeira coleta desta fonte'
                             : n.toLocaleString('pt-BR') + ' foco(s) nas últimas 24 h'; },
    [], 'fogo');
  const itens = base.map(p => ({lat: p[0], lon: p[1], n: p[2]}));
  const maxCel = Math.max(...itens.map(p => p.n));
  /* Raiz quadrada: a área do círculo fica proporcional à contagem, que é como o olho compara
     círculo. Teto de 4,2 px para a célula mais cheia — acima disso as manchas do arco do
     desmatamento viram um borrão só. */
  const raio = d3.scaleSqrt().domain([1, maxCel]).range([0.9, 4.2]).clamp(true);
  /* 30/09/2026 (item 8, escolha A da editoria): fundo noturno e brasa. A cor do ponto sobe na
     rampa com a contagem da célula, e a célula com 30 focos ou mais recebe o núcleo claro — é o
     degrau que a legenda aprovada nomeia. A mescla `screen` faz células vizinhas somarem luz em
     vez de se taparem, que é como o fogo se vê de noite; sem ela, o arco do desmatamento vira uma
     mancha chapada. */
  const NUCLEO_A_PARTIR_DE = 30;
  const brasa = d3.scaleSqrt().domain([1, Math.max(2, maxCel)])
    .range([ATM.fogo.rampa[0], ATM.fogo.rampa[2]]).clamp(true);
  MonitorMapas.pontos(__ctx(), 'mapaFogo', itens, {
    r: d => raio(d.n),
    cor: d => d.n >= NUCLEO_A_PARTIR_DE ? ATM.fogo.nucleo : brasa(d.n),
    opacidade: .78,
    classe: 'focos',
    rotulo: d => d.n + ' foco(s) nesta célula de ~11 km · ' + d.lat.toFixed(1) + '°, ' + d.lon.toFixed(1) + '°',
  });
  d3.select('#mapaFogo').select('g.focos').attr('style', 'mix-blend-mode: screen');
  d3.select('#mapaFogo').selectAll('g.focos circle').attr('stroke', 'none');
  // Os três degraus da marca, que são as categorias do mapa e os rótulos aprovados do R8.
  MonitorMapas.legenda('legFogo', [
    {cor: ATM.fogo.rampa[0], rotulo: 'Poucos focos'},
    {cor: ATM.fogo.rampa[2], rotulo: 'Muitos focos'},
    {cor: ATM.fogo.nucleo, rotulo: 'Área com ' + NUCLEO_A_PARTIR_DE + ' focos ou mais'},
  ]);
})();
/* "Ver em lista" com a contagem por UF — a via tabular que o handover manda preservar. */
(function listaFocos(){
  const corpo = document.querySelector('#tblFogo tbody');
  if (!corpo) return;
  /* A contagem vem do MESMO arquivo dos pontos: mapa e lista discordando na mesma figura é
     defeito que ninguém percebe até alguém somar. Só se não houver, cai para sinais_risco.json. */
  const porUf = (FOCOS && FOCOS.por_uf) || null;
  const linhas = UFS.map(uf => [uf, porUf ? porUf[uf] : (fogo(uf) || {}).focos_24h])
    .filter(l => l[1] != null).sort((a, b) => b[1] - a[1]);
  /* `esc()` mesmo em número e sigla: o portão de segurança exige, e tem razão em não abrir exceção
     por "aqui o dado é confiável" — a exceção é que envelhece, não a regra. */
  corpo.innerHTML = linhas.length
    ? linhas.map(l => '<tr><td>' + esc(l[0]) + '</td><td class="dado">'
                    + esc(Number(l[1]).toLocaleString('pt-BR')) + '</td></tr>').join('')
    : '<tr><td colspan="2">Sem coleta até o corte</td></tr>';
})();
credito('boxFogo', 'inpe_fogo');

// ---- Mapa 5: avisos do INMET em vigor (29/09/2026) ----
/* Estava só na Defesa civil, e o sinal é físico: é desta página. O grau e o nome do fenômeno são
   os que o INMET escreve, sem tradução para escala própria (§23.3).
   A distinção que este card precisa fazer, e que a página de Saúde pagou caro para aprender em
   24/09: **corpo vazio servido com 200 é recusa da fonte, não ausência de aviso**. O coletor já
   falha alto nesse caso e a fonte fica sem `status: coletado`; aqui, isso vira "a fonte não
   respondeu" — nunca um mapa pintado de zero. Resposta válida com lista vazia tem texto próprio. */
(function desenharAvisos(){
  const avisos = uf => (SINAIS.uf[uf] || {}).avisos_inmet;
  const respondeu = coletada('inmet_avisos');
  const corpo = document.querySelector('#tblAvisos tbody');

  if (!respondeu) {
    MonitorMapas.legenda('legAvisos', [{cor: NEUTRA,
      rotulo: 'A fonte não respondeu nesta consulta — não quer dizer que não haja aviso em vigor'}]);
    if (corpo) corpo.innerHTML = '<tr><td colspan="4">A fonte não respondeu nesta consulta</td></tr>';
    credito('boxAvisos', 'inmet_avisos');
    return;
  }

  const total = UFS.reduce((s, uf) => s + Number((avisos(uf) || {}).total || 0), 0);
  const graus = {}, fenomenos = {};
  UFS.forEach(uf => {
    const a = avisos(uf) || {};
    Object.entries(a.graus || {}).forEach(([g, n]) => { graus[g] = (graus[g] || 0) + Number(n || 0); });
    (a.exemplos || []).forEach(f => { fenomenos[f] = (fenomenos[f] || 0) + 1; });
  });

  /* 30/09/2026 (R11 do handover): o estado passa a ser pintado pelo MAIOR GRAU de aviso em vigor,
     não pela CONTAGEM. Contagem media outra coisa — dez avisos de perigo potencial pintavam mais
     escuro do que um de grande perigo, e é o grande perigo que a leitora precisa ver primeiro. O
     número de avisos continua no texto do mouse e na lista.

     A ordem dos graus é a do próprio INMET, e a comparação é por posição nessa ordem: nada de
     inventar escala numérica para um vocabulário que já é ordenado. */
  const ORDEM_GRAU = ['Perigo Potencial', 'Perigo', 'Grande Perigo'];
  const normGrau = g => {
    const t = String(g || '').toLowerCase();
    if (t.includes('grande')) return 'Grande Perigo';
    if (t.includes('potencial')) return 'Perigo Potencial';
    if (t.includes('perigo')) return 'Perigo';
    return null;
  };
  const maiorGrau = uf => {
    const g = Object.keys((avisos(uf) || {}).graus || {}).map(normGrau).filter(Boolean);
    if (!g.length) return null;
    return g.reduce((a, b) => ORDEM_GRAU.indexOf(b) > ORDEM_GRAU.indexOf(a) ? b : a);
  };
  // Três graus, três degraus da escala ordinal do site (a mesma da seca), na ordem do INMET.
  // `rampaPerigo` tem dois extremos e serve a interpolação contínua — aqui o vocabulário é
  // ordenado e fechado, e escala contínua para vocabulário fechado inventaria tons intermediários
  // que o INMET não emite.
  // 30/09/2026 (item 8): a rampa aprovada dos avisos, em ardósia. Os três graus do INMET mais o
  // "sem aviso", que também é informação e por isso tem tom próprio em vez de ficar sem cor.
  const COR_GRAU = {'Perigo Potencial': ATM.chuva.rampa[1],
                    'Perigo': ATM.chuva.rampa[2],
                    'Grande Perigo': ATM.chuva.rampa[3]};
  const SEM_AVISO = ATM.chuva.rampa[0];
  const ordena = o => Object.entries(o).sort((a, b) => b[1] - a[1]);
  const legenda = [{cor: SEM_AVISO, rotulo: 'Sem aviso'},
                   {cor: COR_GRAU['Perigo Potencial'], rotulo: 'Perigo potencial'},
                   {cor: COR_GRAU['Perigo'], rotulo: 'Perigo'},
                   {cor: COR_GRAU['Grande Perigo'], rotulo: 'Grande perigo'}]
    .concat(total ? [] : [{cor: SEM_AVISO,
      rotulo: 'Nenhum aviso em vigor nesta consulta'}]);
  // 01/10/2026: a lista de fenômenos saiu da legenda — ela não é categoria do mapa, que pinta por
  // GRAU. O fenômeno de cada estado continua no texto do mouse e na lista.
  desenharMapa('mapaAvisos', 'legAvisos',
    uf => COR_GRAU[maiorGrau(uf)] || SEM_AVISO,
    uf => { const a = avisos(uf) || {}; const n = Number(a.total || 0); const g = maiorGrau(uf);
            return n ? '<em>' + esc(g || 'Aviso em vigor') + '</em><br>' + n + ' aviso(s) em vigor'
                     : 'Nenhum aviso em vigor nesta consulta'; },
    legenda, 'chuva');
  if (corpo) {
    const linhas = UFS.map(uf => ({uf, a: avisos(uf) || {}}))
      .filter(x => Number(x.a.total || 0) > 0)
      .sort((a, b) => Number(b.a.total || 0) - Number(a.a.total || 0));
    corpo.innerHTML = linhas.length
      ? linhas.map(x => '<tr><td>' + x.uf + '</td><td class="dado">' + Number(x.a.total) + '</td><td>' +
          esc(Object.keys(x.a.graus || {}).join(', ')) + '</td><td>' + esc((x.a.exemplos || []).join(', ')) + '</td></tr>').join('')
      : '<tr><td colspan="4">Nenhum aviso em vigor nesta consulta</td></tr>';
  }
  credito('boxAvisos', 'inmet_avisos');
})();

// =====================  Cartões do estado do ciclo  =====================
const oni = SINAIS.enos.oni, prob = SINAIS.enos.probabilidades;
const ultimoOni = oni && oni.serie && oni.serie.length ? oni.serie[oni.serie.length - 1] : null;
const ultimaProb = prob && prob.trimestres && prob.trimestres.length ? prob.trimestres[0] : null;
// ===== R2 e R3 (30/09/2026, handover do Monitor de riscos): o resumo e as três perguntas =====
// O índice de referência passa a ser o RONI, oficial da NOAA desde fevereiro de 2026 — ele mede o
// afastamento do Niño 3.4 em relação aos oceanos tropicais, e é ele que sustenta a palavra "forte".
// O ONI e a anomalia mensal saíram da página: são apoio técnico e vivem na METODOLOGIA.
//
// Nenhum número fixo: tudo o que aparece vem da série. Onde o dado não sustenta a frase, a frase
// não é escrita — a oração sobre a alta só entra se a variação de seis meses for positiva.
(function situacaoAtual(){
  const el = id => document.getElementById(id); if (!el('stResumo')) return;
  const roni = SINAIS.enos.roni;
  const serie = (roni && roni.serie) || [];
  const u = serie[serie.length - 1];
  const cls = v => v >= 2.0 ? 'muito forte' : v >= 1.5 ? 'forte' : v >= 1.0 ? 'moderado'
                 : v >= 0.5 ? 'fraco' : 'abaixo do limiar';
  const num = (v, casas) => (v >= 0 ? '+' : '') + v.toFixed(casas == null ? 2 : casas).replace('.', ',');
  // O trimestre vem da NOAA como três iniciais em inglês (JJA, SON, DJF…). Traduzir a sigla para
  // um intervalo de meses em português é o que a leitora precisa — "jul–set" se lê, "JJA" não. A
  // sigla que não casar com o calendário volta como veio, em vez de virar intervalo inventado.
  const INICIAIS = 'JFMAMJJASOND';
  const MES_ABREV = ['jan','fev','mar','abr','mai','jun','jul','ago','set','out','nov','dez'];
  const periodoDoTrimestre = t => {
    const sigla = String(t || '').toUpperCase();
    if (sigla.length !== 3) return String(t || '');
    // A sequência das iniciais dos doze meses, repetida, localiza o trimestre sem ambiguidade.
    const ciclo = INICIAIS + INICIAIS;
    const i = ciclo.indexOf(sigla);
    if (i < 0) return String(t || '');
    return MES_ABREV[i % 12] + '–' + MES_ABREV[(i + 2) % 12];
  };

  // R2 — resumo. "há El Niño" é fato datado do Painel (29/06/2026); a força e a variação vêm do RONI.
  if (u) {
    // Seis meses = dois trimestres para trás na série trimestral móvel.
    const antes = serie.length >= 3 ? serie[serie.length - 3] : null;
    const delta = antes ? u.anomalia - antes.anomalia : null;
    let txt = 'O El Niño foi declarado pelos órgãos federais em 29 de junho de 2026 e hoje é considerado '
            + esc(cls(u.anomalia)) + '. A temperatura do Pacífico, que define o fenômeno, ';
    if (delta !== null && delta > 0) {
      txt += 'subiu ' + esc(num(delta).replace('+', '')) + ' °C nos últimos seis meses';
      txt += (serie.length >= 2 && u.anomalia > serie[serie.length - 2].anomalia)
        ? ', e segue em alta.' : '.';
    } else if (delta !== null) {
      // O dado não sustenta "subiu": diz-se o que ele diz, e a oração sobre a alta não aparece.
      txt += 'variou ' + esc(num(delta)) + ' °C nos últimos seis meses.';
    } else {
      txt += 'está em ' + esc(num(u.anomalia, 1)) + ' °C.';
    }
    el('stResumo').innerHTML = txt;
  }

  // R3 — três cartões.
  const prob = SINAIS.enos.probabilidades;
  const pg = SINAIS.enos.prognostico;
  if (u) {
    const ha = u.anomalia >= 0.5;
    el('stHaElNino').textContent = ha ? 'Sim, desde junho de 2026' : 'Não';
    el('stForca').textContent = cls(u.anomalia).charAt(0).toUpperCase() + cls(u.anomalia).slice(1);
    el('stForcaNota').textContent = num(u.anomalia, 1) + ' °C acima do normal no Pacífico, '
      + periodoDoTrimestre(u.trimestre) + ' (RONI)';
  }
  // A chance de continuar é a do trimestre do verão (DJF), quando existe na série de probabilidades;
  // sem ela, o cartão não inventa número — fica com o travessão que já está no HTML.
  const trims = (prob && prob.trimestres) || [];
  const verao = trims.find(t => /DJF|NDJ/.test(String(t.trimestre || ''))) || trims[0] || null;
  if (verao && verao.el_nino != null) {
    el('stChance').textContent = verao.el_nino.toFixed(0) + '%';
    el('stChanceNota').textContent = 'chance de El Niño em dezembro–fevereiro, segundo IRI/NOAA';
  } else if (pg && pg.probabilidade != null) {
    el('stChance').textContent = String(pg.probabilidade) + '%';
    el('stChanceNota').textContent = 'chance de El Niño no trimestre publicado, segundo CPC/NOAA';
  }

  // O crédito do painel inteiro SAIU (30/09/2026): o gráfico do RONI já traz a sua linha de fonte,
  // e cada cartão diz de onde vem o seu número na linha pequena. Três créditos para as mesmas duas
  // fontes, na mesma tela, é redundância — e a regra do site é fonte POR FIGURA, não por painel.
})();

// 13/09/2026: cartoesCiclo/cartaoCiclo1-4 removidos — três dos quatro cartões duplicavam valores já
// no painel Situação Atual (ONI, Probabilidade, Prognóstico/Boletim nº 3); só 'Boletim mais recente
// do ciclo' trazia informação nova (o nome do documento), agora em stDocumento acima, com a citação
// combinada das três fontes substituindo os quatro créditos individuais.

// =============================  Gráficos  =============================
const SEM_ANIM = {animation:false, responsive:true, maintainAspectRatio:false};

function canvasEm(wrapId, canvasId){
  const w = document.getElementById(wrapId);
  const c = document.createElement('canvas'); c.id = canvasId; w.appendChild(c); return c;
}

// 30/09/2026 (handover do Monitor de riscos): os gráficos do ONI e da anomalia mensal
// SAÍRAM da página. Eles medem a mesma coisa que o RONI com outra referência, e três
// gráficos do mesmo fenômeno lado a lado pediam do leitor uma comparação técnica que
// não é a pergunta desta página. Os dois continuam coletados e vivem na METODOLOGIA,
// como apoio técnico.

// Paleta e opções do gráfico de anomalia. Vinham do bloco do ONI, que saiu da página em
// 30/09/2026; ficam aqui porque o gráfico do RONI é quem as usa agora. Vermelho acima da média,
// azul abaixo, opacidade crescendo com a intensidade — a mesma transição contínua dos medidores
// do MARÉ, aplicada a uma série histórica.
const ANOM_VERMELHO = [220, 38, 38], ANOM_AZUL = [37, 99, 235];
const alphaAnom = v => Math.min(.92, .28 + .64 * Math.min(1, Math.abs(v) / 2.0));
const corAnom = v => { const [r,g,b] = v >= 0 ? ANOM_VERMELHO : ANOM_AZUL; return `rgba(${r},${g},${b},${alphaAnom(v).toFixed(2)})`; };
const opcoesGraficoAnom = (rotuloEixoY) => ({responsive:true, maintainAspectRatio:false, animation:{duration:900, easing:'easeOutCubic'},
  plugins:{legend:{display:false}, tooltip:{backgroundColor:'#000', titleColor:'#fff', bodyColor:'#fff', borderColor:'rgba(255,255,255,.25)', borderWidth:1}},
  scales:{
    x:{ticks:{maxTicksLimit:12, color:'rgba(255,255,255,.75)'}, grid:{color:'rgba(255,255,255,.10)'}, border:{color:'rgba(255,255,255,.25)'}},
    y:{title:{display:true, text: rotuloEixoY, color:'rgba(255,255,255,.75)'}, ticks:{color:'rgba(255,255,255,.75)'}, grid:{color:ctx => ctx.tick.value === 0 ? 'rgba(255,255,255,.45)' : 'rgba(255,255,255,.10)'}, border:{color:'rgba(255,255,255,.25)'}}}});

// ---- Gráfico 1b: série RONI (17/09/2026, achado ao checar o valor do ONI atual, pedido da editoria) ----
// Mesmo padrão visual do ONI (fundo preto, vermelho/azul, transição por opacidade, animação ligada) —
// são duas medidas da mesma coisa, lado a lado, então precisam se ler como duas versões de uma
// mesma família de gráfico, não como duas figuras diferentes.
const roni = SINAIS.enos.roni;
if (roni && roni.serie && roni.serie.length) {
  new Chart(canvasEm('wrapRoni', 'cRoni'), {type:'bar', data:{
      labels: roni.serie.map(p => p.trimestre + '/' + String(p.ano).slice(2)),
      datasets:[{label:'RONI (°C)', data: roni.serie.map(p => p.anomalia),
                 backgroundColor: ctx => corAnom(ctx.raw), borderWidth:0, borderRadius:2,
                 categoryPercentage:.9, barPercentage:.95}]},
    options: opcoesGraficoAnom('°C')});
  (function leituraRoni(){
    const el = document.getElementById('roniLeitura'); const s = roni.serie; const u = s[s.length - 1]; if (!el || !u) return;
    const cls = v => v >= 2.0 ? 'muito forte' : v >= 1.5 ? 'forte' : v >= 1.0 ? 'moderado' : v >= 0.5 ? 'fraco' : 'abaixo do limiar';
    const fmt = v => (v >= 0 ? '+' : '') + v.toFixed(1).replace('.', ',');
    // 17/09/2026 (pedido da editoria): a nota deste gráfico precisa se explicar sozinha, sem depender
    // de o leitor ter lido a nota do ONI ao lado — cada figura carrega sua própria explicação completa.
    let txt = 'Afastamento da temperatura do mar na região Niño 3.4 em relação à média dos oceanos tropicais, medida oficial da NOAA desde agosto de 2026. ';
    txt += 'RONI em ' + fmt(u.anomalia) + ' °C (' + u.trimestre + '/' + u.ano + '), ' + cls(u.anomalia) + ' na mesma escala do CPC';
    if (s.length >= 3) { const d = u.anomalia - s[s.length - 3].anomalia; txt += '; ' + (d >= 0 ? '+' : '') + d.toFixed(2).replace('.', ',') + ' °C em dois trimestres'; }
    el.textContent = txt + '.'; el.hidden = false;
  })();
} else { lacuna('wrapRoni', 'A série do RONI aparece aqui assim que a rotina semanal registrar a primeira coleta no CPC/NOAA. Até lá, ela pode ser consultada na origem, no link abaixo.'); }
credito('boxRoni', 'noaa_roni');

// ---- F.1/F.3 (30/09/2026): a anomalia mensal da região Niño 3.4 VOLTA à página.
// Ela saiu em 30/09 junto com o ONI, e a editoria a trouxe de volta por uma razão de leitura, não
// de método: é o número que a imprensa divulga. O ONI continua fora, como apoio técnico.
const nino34Mensal = SINAIS.enos.nino34_mensal;
const MES_CURTO = ['jan','fev','mar','abr','mai','jun','jul','ago','set','out','nov','dez'];
if (nino34Mensal && nino34Mensal.serie && nino34Mensal.serie.length) {
  new Chart(canvasEm('wrapAnomalia', 'cAnomalia'), {type:'bar', data:{
      labels: nino34Mensal.serie.map(p => MES_CURTO[p.mes - 1] + '/' + String(p.ano).slice(2)),
      datasets:[{label:'Anomalia mensal (°C)', data: nino34Mensal.serie.map(p => p.anomalia),
                 backgroundColor: ctx => corAnom(ctx.raw), borderWidth:0, borderRadius:2,
                 categoryPercentage:.9, barPercentage:.95}]},
    options: opcoesGraficoAnom('°C')});
} else { lacuna('wrapAnomalia', 'A anomalia mensal aparece aqui assim que a rotina semanal registrar a primeira coleta no CPC/NOAA. Até lá, ela pode ser consultada na origem, no link abaixo.'); }
credito('boxAnomalia', 'noaa_nino34_mensal');

// ---- Gráfico 2: probabilidades ENOS ----
// 13/09/2026: figura "Probabilidade por trimestre" retirada do HTML (ver comentário em
// monitor-de-riscos.html, painel #graficos) — só mostrava "sem coleta". Bloco mantido desativado
// (guarda por ausência de #wrapPlume), não apagado, para reativar quando o IRI/CPC for coletado.
if (document.getElementById('wrapPlume')) {
  if(prob && prob.trimestres && prob.trimestres.length){
    const t = prob.trimestres.slice(0, 9);
    new Chart(canvasEm('wrapPlume', 'cPlume'), {type:'bar', data:{
        labels: t.map(p => p.trimestre),
        datasets:[{label:'La Niña', data:t.map(p => p.la_nina), backgroundColor:MonitorMapas.PALETA.enso.la_nina},
                  {label:'Neutro',  data:t.map(p => p.neutro),  backgroundColor:MonitorMapas.PALETA.enso.neutro},
                  {label:'El Niño', data:t.map(p => p.el_nino), backgroundColor:MonitorMapas.PALETA.enso.el_nino}]},
      options:{...SEM_ANIM, plugins:{legend:{position:'bottom'}},
        scales:{x:{stacked:true}, y:{stacked:true, max:100, title:{display:true, text:'%'}}}}});
  } else {
    // enquanto o plume IRI/CPC não é coletado: a leitura oficial do CPC via CPTEC e do Painel, como itens de legenda (dado declarado, não gráfico)
    const pg = SINAIS.enos.prognostico; const wp = document.getElementById('wrapPlume'); if (wp) wp.innerHTML = '';
    if (pg && pg.enso) MonitorMapas.legenda('legPlume', [{cor: MonitorMapas.PALETA.enso.el_nino, rotulo: 'El Niño: > 90% para SON/2026 (CPC/NOAA, ago/2026)'}, {cor: MonitorMapas.PALETA.enso.el_nino, opacidade: .55, rotulo: '100% de permanência até início de 2027 (Boletim nº 3)'}, {cor: MonitorMapas.PALETA.semDado, rotulo: 'plume por trimestre: sem coleta'}]);
  }
  credito('boxPlume', 'iri_plume');
}

// ---- Gráfico 3: estados por tipo de risco ----
// 17/09/2026 (pedido da editoria): a barra "Misto" só informava uma contagem, sem dizer do quê — o
// gráfico não comunicava nada além de "N estados têm mais de um risco". Cada estado com risco misto
// passa a contar em CADA risco que o compõe (um estado com estiagem + incêndios soma nas duas barras),
// não numa categoria à parte. A soma das barras pode passar de 27 — é o esperado, não um erro: um
// mesmo estado pode aparecer em mais de uma barra. O mapa não muda (mesma cor "misto" nos estados com
// mais de um risco); só o gráfico ao lado e o texto do mouse sobre o mapa mudam.
const TIPOS_CONTAVEIS = ['estiagem', 'chuvas', 'incendios', 'sem_sinal'];
const contagemPorTipo = {};
TIPOS_CONTAVEIS.forEach(t => contagemPorTipo[t] = 0);
UFS.forEach(uf => {
  const r = RISCO(uf); if (!r) return;
  if (r.tipo === 'misto' && r.componentes && r.componentes.length) r.componentes.forEach(c => { if (c in contagemPorTipo) contagemPorTipo[c]++; });
  else if (r.tipo in contagemPorTipo) contagemPorTipo[r.tipo]++;
});
const ordemTipos = TIPOS_CONTAVEIS.filter(t => contagemPorTipo[t] > 0);
const contagem = ordemTipos.map(t => contagemPorTipo[t]);
new Chart(document.getElementById('cTipos'), {type:'bar', data:{
    labels: ordemTipos.map(t => TIPO_CURTO[t]),
    datasets:[{data:contagem, backgroundColor:ordemTipos.map(t => TIPO_COR[t]), borderWidth:0}]},
  options:{...SEM_ANIM, indexAxis:'y', plugins:{legend:{display:false}},
    scales:{x:{title:{display:true, text:'estados (um estado com mais de um risco conta em cada um)'}, ticks:{precision:0}}}}});
// 15/09/2026: a contagem por família mora na figura dupla boxTipoRisco (mapa + gráfico, uma legenda) — o crédito é o da figura.
// 17/09/2026: o cruzamento "tipo de risco × estágio" (que morava na home, #cCruz) saiu do site — pedido da editoria.

// =============================  Tabela de fontes  =============================
const CAMADA_ROTULO = {ciclo:'Ciclo', observado:'Observado', enos:'ENOS'};
}
__load();

// ===== monitor-de-riscos.html · bloco 2 (extraído em 06/09/2026, CSP sem unsafe-inline) =====
window.addEventListener('load', function(){ if (window.VLibras && window.VLibras.Widget) { try { new window.VLibras.Widget('https://vlibras.gov.br/app'); } catch (e) {} } });
