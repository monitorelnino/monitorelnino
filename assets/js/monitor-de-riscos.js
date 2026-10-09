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
  /* 07/10/2026: o CATÁLOGO antes do desenho. O texto do topo e dos dois gráficos do Pacífico vive
     em conteudo/monitor-de-riscos.json, e `assets/catalogo.js` o carrega por conta própria, em
     paralelo com este fetch. Sem esta espera, quem chegasse primeiro decidia o que o leitor via:
     com o dado na frente, o título do gráfico saía sem os anos e os cartões ficavam no texto de
     reserva. A espera é tolerante — catálogo que não carrega não trava a página, e o texto de
     reserva do HTML continua lá, que é o desenho de falha segura do próprio leitor. */
  if (window.MonitorCatalogo && window.MonitorCatalogo.pronto) {
    try { await window.MonitorCatalogo.pronto; } catch (e) {}
  }
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
const ROTULOS_DOS_MAPAS = {};
const desenharMapa = (svgId, legendaId, corDe, rotuloDe, itensLegenda, familia) => {
  ROTULOS_DOS_MAPAS[svgId] = rotuloDe;
  return MonitorMapas.desenharMapa(__ctx(), svgId, legendaId, corDe, rotuloDe, itensLegenda, familia);
};
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
    .attr('aria-label', d => semDadoNaCapital(d.uf, atm).replace(/<[^>]+>/g, ' '))
    .on('mouseenter', (evt, d) => MonitorMapas.showTip(semDadoNaCapital(d.uf, atm), evt))
    .on('mouseleave', MonitorMapas.hideTip);
  return g;
}
// ===== Texto do mouse (09/10/2026, ajuste 6): uma anatomia em todos os mapas — título, valor,
// contexto, data e fonte —, pela função compartilhada `MonitorMapas.dica`. Nunca data ISO, ponto
// decimal, caixa alta da fonte, coordenada, código interno ou campo cru.
const nomeUF = uf => { const f = (BR_GEOJSON.features || []).find(x => x.properties.sigla === uf);
  return f ? f.properties.name : uf; };
const n1 = v => MonitorMapas.numBR(v, Number.isInteger(Number(v)) ? 0 : 1);
const plural = (n, um, varios) => n1(n) + ' ' + (Number(n) === 1 ? um : varios);
const dataCurta = v => { const m = /(\d{2})\/(\d{2})\/(\d{4})/.exec(String(v || '')) || null;
  if (m) return m[1] + '/' + m[2] + '/' + m[3];
  const i = /(\d{4})-(\d{2})-(\d{2})/.exec(String(v || ''));
  return i ? i[3] + '/' + i[2] + '/' + i[1] : ''; };
const diaMes = v => dataCurta(v).slice(0, 5);
const fonteLinha = id => { const f = fonteDe(id); return [f.consultado_em ? 'consulta de ' + f.consultado_em : '', f.orgao || '']; };
const capitalUF = (uf, nome) => (nome || nomeUF(uf)) + ' (' + uf + ')';
function semDadoNaCapital(uf, atm){
  const id = atm === ATM.ar ? 'open_meteo_ar' : 'inmet_previsao_capitais';
  const f = fonteDe(id);
  return MonitorMapas.dica({titulo: capitalUF(uf, (temp(uf) || {}).capital),
    linhas: ['Sem dado de ' + (f.orgao || 'a fonte') + ' para a capital na consulta'
             + (f.consultado_em ? ' de ' + f.consultado_em : '')]});
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
  uf => { const r = riscoDe(uf); const [d, o] = fonteLinha('painel_el_nino');
    if (!r) return MonitorMapas.dica({semTitulo: true, linhas: ['Sem sinal elevado para este estado no boletim'], data: d, fonte: o});
    const c = componentesDe(uf);
    const nomes = c.map(x => RISCO_FAMILIA_ROTULO[x] || x).join(' e ');
    return MonitorMapas.dica({semTitulo: true, linhas: ['Risco previsto: ' + (nomes || 'sem sinal elevado').toLowerCase(), r.texto], data: d, fonte: o}); },
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
  const BLOCOS = ['.figura-titulo', '.figura-sub'];
  // 09/10/2026 (ajuste 5): o alinhamento é POR GRADE — previsto, observado e agora são faixas
  // diferentes, e igualar as três reservava espaço de uma faixa na outra.
  function alinhar(){ document.querySelectorAll('.grade-mapas').forEach(alinharGrade); }
  function alinharGrade(grade){
    const cartoes = [...grade.querySelectorAll(':scope > .cartao-mapa')];
    if (cartoes.length < 2) { cartoes.forEach(c => BLOCOS.forEach(s => { const e = c.querySelector(s); if (e) e.style.minHeight = ''; })); return; }
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

  // 07/10/2026: os subtítulos dos dois gráficos do Pacífico saíram daqui, e com eles um defeito
  // que estava publicado: este bloco escrevia "1950 a 2026" numa série que começa em 2013 — o
  // "1950" era parte fixa da frase, não do dado. Agora a legenda e a nota vivem no catálogo, e o
  // título com os anos é composto no bloco do Pacífico, que é quem tem a série em mão.

  // 09/10/2026 (ajustes 5 e 6): o TÍTULO diz o que é e quando; o subtítulo diz o critério e a fonte.
  const pe = fonte('painel_el_nino');
  põe('riscoPrevistoSub', 'Por estado'
    + (pe.documento ? ' · ' + pe.documento : '')
    + (pe.consultado_em ? ', ' + pe.consultado_em : ''));

  const algumaSeca = Object.keys(SINAIS.uf).map(uf => (SINAIS.uf[uf].secas || {}).mapa).find(Boolean);
  if (algumaSeca) põe('tituloSecas', 'Seca observada, ' + String(algumaSeca).toLowerCase());
  põe('secasSub', 'Categoria de seca em pelo menos metade da área do estado · mapa mensal');

  const totalFocos = Object.keys(SINAIS.uf)
    .reduce((soma, uf) => soma + (((SINAIS.uf[uf] || {}).fogo || {}).focos_24h || 0), 0);
  const fFogo = fonte('inpe_fogo');
  if (totalFocos) põe('fogoSub', 'Até ' + (fFogo.consultado_em || dia(SINAIS.gerado_em) || '')
    + ' · ' + totalFocos.toLocaleString('pt-BR') + ' focos · cada ponto reúne os focos de uma área de cerca de 11 km');

  const fAr = fonte('open_meteo_ar');
  if (fAr.consultado_em) põe('tituloAr', 'Qualidade do ar nas capitais, ' + String(fAr.consultado_em).slice(0, 10));
  põe('arSub', 'Hora de maior concentração do dia · uma capital por estado · estimativa por modelo');

  const fTemp = fonte('inmet_previsao_capitais');
  const diaPrev = (SINAIS.uf.SP && SINAIS.uf.SP.temperatura && SINAIS.uf.SP.temperatura.data) || fTemp.consultado_em;
  if (diaPrev) põe('tituloTemperatura', 'Temperatura máxima prevista nas capitais, ' + String(diaPrev).slice(0, 10));
  põe('temperaturaSub', 'Cor: diferença para a média histórica do mês · número: máxima prevista · °C');

  const fAvisos = fonte('inmet_avisos');
  if (fAvisos.consultado_em) põe('tituloAvisos', 'Avisos de tempo severo em vigor, ' + fAvisos.consultado_em);
  põe('avisosSub', 'Maior grau de aviso do INMET em vigor · por estado');
})();

// ---- "Ver estados" (09/10/2026, ajuste 5): a lista que estava no texto visível do cartão vai
// para a descrição acessível do mapa e para um "Ver estados" fechado. Ela é gerada do MESMO texto
// do mouse de cada estado, sem as marcas: o leitor de tela e a lista dizem o que o mapa diz.
function escreverEstados(alvoId, rotuloDe, filtro){
  const el = document.getElementById(alvoId); if (!el) return;
  const limpo = h => String(h || '').replace(/<span class="dica-fonte">.*?<\/span>/g, '')
    .replace(/<[^>]+>/g, ' ').replace(/&amp;/g, '&').replace(/\s+/g, ' ').trim();
  const linhas = UFS.filter(uf => !filtro || filtro(uf)).map(uf => nomeUF(uf) + ': ' + limpo(rotuloDe(uf)));
  el.textContent = linhas.length ? linhas.join('; ') + '.' : 'Nenhum estado nesta consulta.';
}

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
  uf => { const s = seca(uf); const [d, o] = fonteLinha('monitor_secas');
    if (!s) return MonitorMapas.dica({semTitulo: true, linhas: ['Sem dado do Monitor de Secas para o estado na consulta'], data: d, fonte: o});
    const cob = s.cobertura_pct || {};
    const NOME = {'sem seca': 'sem seca', S0: 'seca fraca', S1: 'seca moderada', S2: 'seca grave', S3: 'seca extrema', S4: 'seca excepcional'};
    const partes = ['S4','S3','S2','S1','S0','sem seca'].filter(k => (cob[k] || 0) >= 0.5)
      .map(k => NOME[k] + ' em ' + n1(Math.round(cob[k])) + '% da área');
    const linha = partes.length ? partes[0].charAt(0).toUpperCase() + partes[0].slice(1)
      + (partes.length > 1 ? '; ' + partes.slice(1).join('; ') : '') : '';
    return MonitorMapas.dica({semTitulo: true, linhas: [linha, s.mapa ? 'Mapa de ' + String(s.mapa).toLowerCase() : ''], data: d, fonte: o}); },
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
const medidaDe = uf => { const m = (SINAIS.uf[uf] || {}).temperatura_medida; return m && m.medida ? m : null; };
const linhaMedida = uf => {
  const m = (SINAIS.uf[uf] || {}).temperatura_medida;
  if (!m) return '';
  if (!m.medida || m.medida.tmax == null) return 'Sem medição da estação do INMET' + (m.consultado_em ? ' em ' + diaMes(m.consultado_em) : '');
  return 'Medido em ' + diaMes(m.medida.data) + ' na estação do INMET a ' + n1(m.distancia_km) + ' km do centro: máxima '
    + n1(m.medida.tmax) + ' °C' + (m.medida.tmin != null ? ', mínima ' + n1(m.medida.tmin) + ' °C' : '');
};
const rotuloTemp = uf => { const t = temp(uf); const [d, o] = fonteLinha('inmet_previsao_capitais');
  if (!t) return semDadoNaCapital(uf, ATM.calor);
  const dv = desvioDe(uf), nm = normalDe(uf);
  const maxima = t.tmax != null
    ? 'Máxima prevista para ' + diaMes(t.data) + ': ' + n1(t.tmax) + ' °C'
      + (dv == null ? '; sem normal publicada para esta capital'
         : ', ' + (dv >= 0 ? '+' : '−') + n1(Math.abs(dv)) + ' °C ' + (dv >= 0 ? 'acima' : 'abaixo')
           + ' da normal do mês (normal 1991–2020: ' + n1(nm) + ' °C)')
    : 'Sem máxima prevista';
  return MonitorMapas.dica({titulo: capitalUF(uf, t.capital), linhas: [maxima,
    t.tmin != null ? 'Mínima prevista: ' + n1(t.tmin) + ' °C' : '', linhaMedida(uf)], data: d, fonte: o}); };
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
  const m = medidaDe(uf);
  return [t.capital || '', t.tmax != null ? n1(t.tmax) + ' \u00b0C' : 'sem valor',
          t.tmin != null ? n1(t.tmin) + ' \u00b0C' : 'sem valor',
          m && m.medida.tmax != null ? n1(m.medida.tmax) + ' \u00b0C' : 'sem medição']; });

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
const FAIXA_EAQI_NOME = ['boa', 'razoável', 'moderada', 'ruim', 'muito ruim'];
const rotuloAr = uf => { const a = ar(uf); const [d, o] = fonteLinha('open_meteo_ar');
  if (!a) return semDadoNaCapital(uf, ATM.ar);
  const i = a.indice;
  if (!i) return MonitorMapas.dica({titulo: capitalUF(uf, nomeCapital(a, uf)), linhas: ['Índice sem publicação nesta consulta'], data: d, fonte: o});
  const h = /(\d{4})-(\d{2})-(\d{2})T(\d{2})/.exec(String(i.hora || ''));
  return MonitorMapas.dica({titulo: capitalUF(uf, nomeCapital(a, uf)), linhas: [
    'Índice europeu de qualidade do ar: ' + n1(i.valor) + ' (' + FAIXA_EAQI_NOME[FAIXAS_EAQI.filter(l => i.valor > l).length] + ')',
    h ? 'Hora de maior concentração: ' + Number(h[4]) + 'h de ' + h[3] + '/' + h[2] : ''], data: d, fonte: o}); };
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
/* 09/10/2026 (ajuste 6b): a CAMADA DE MEDIÇÃO saiu do mapa. Ela punha um segundo marcador ao lado
   de cada capital, que dizia a distância da estação e nenhuma medida. A medição entra no texto do
   mouse da capital e na lista; ela nunca muda a cor (modelo e medição não compartilham escala). */

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
    uf => { const f = fogo(uf); const n = f ? f.focos_24h : null; const [d, o] = fonteLinha('inpe_fogo');
            return MonitorMapas.dica({semTitulo: true, linhas: [n == null
              ? 'Sem dado do INPE para o estado na consulta'
              : plural(n, 'foco', 'focos') + ' nas últimas 24 horas'], data: d, fonte: o}); },
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
    rotulo: d => MonitorMapas.dica({linhas: [plural(d.n, 'foco', 'focos') + ' num raio de cerca de 5 km'],
                                    data: fonteLinha('inpe_fogo')[0], fonte: 'INPE'}),
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
  const COR_GRAU = {'Perigo Potencial': ATM.avisos.rampa[1],
                    'Perigo': ATM.avisos.rampa[2],
                    'Grande Perigo': ATM.avisos.rampa[3]};
  const SEM_AVISO = ATM.avisos.rampa[0];
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
            const [d, o] = fonteLinha('inmet_avisos');
            return MonitorMapas.dica({semTitulo: true, linhas: n
              ? ['Maior grau em vigor: ' + String(g || 'aviso').toLowerCase(), plural(n, 'aviso em vigor', 'avisos em vigor')
                 + ((a.exemplos || []).length ? ': ' + a.exemplos.join(', ').toLowerCase() : '')]
              : ['Nenhum aviso em vigor na consulta'], data: d, fonte: o}); },
    legenda, 'avisos');
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
// ===== O topo "Situação atual" (07/10/2026, handover "Monitor de riscos, parte 1") ==========
// SAIU A RÉGUA DE FORÇA. As faixas "fraco/moderado/forte/muito forte" que este bloco aplicava
// (`cls()`) não são definição da NOAA/CPC: ela define os LIMIARES de El Niño (+0,5 °C) e de La
// Niña (−0,5 °C) e o critério de cinco médias trimestrais seguidas para caracterizar um episódio,
// e nada mais. Classificar o ciclo por faixa própria era interpretação nossa vestida de dado.
// "Muito forte" só aparece citado e atribuído, dentro da frase da própria NOAA/CPC.
//
// Saíram junto os três quadros com ícone: "Há El Niño agora?" não muda até o fim do ciclo, e os
// outros dois diziam uma faixa e um "100%" sem período. Entram quatro números, cada um gerado do
// dado, com fonte e data na linha de baixo do cartão.
//
// O TEXTO não vive aqui: vive em `conteudo/monitor-de-riscos.json`. Este bloco traz o DADO.
const PAC = (function pacificoComum(){
  // O trimestre da NOAA vem como três iniciais (DJF, JAS…). A leitora precisa do intervalo de
  // meses, não da sigla: "jul–set" se lê, "JAS" não. A sigla que não casar com o calendário
  // volta como veio, em vez de virar intervalo inventado.
  const MES = ['jan','fev','mar','abr','mai','jun','jul','ago','set','out','nov','dez'];
  // Centro do trimestre, em mês do ANO que o dado declara: DJF/2015 é dez/2014–fev/2015, centro
  // jan/2015. É esta convenção que faz a série de 160 médias móveis mensais se ordenar sozinha.
  const CENTRO = {DJF:0, JFM:1, FMA:2, MAM:3, AMJ:4, MJJ:5, JJA:6, JAS:7, ASO:8, SON:9, OND:10, NDJ:11};
  const centro = p => CENTRO[String(p.trimestre || '').toUpperCase()];
  const temCentro = p => centro(p) !== undefined;
  // Ordem absoluta em meses, para varrer a série sem depender da ordem do arquivo.
  const ordem = p => p.ano * 12 + centro(p);
  const num = (v, casas) => (v > 0 ? '+' : v < 0 ? '−' : '')
    + Math.abs(v).toFixed(casas == null ? 1 : casas).replace('.', ',');
  // "jul–set 2026" quando o trimestre não vira o ano; "nov 2015–jan 2016" quando vira.
  function periodo(p){
    const c = centro(p);
    if (c === undefined) return String(p.trimestre || '');
    const ini = (c + 11) % 12, fim = (c + 1) % 12;
    const anoIni = c === 0 ? p.ano - 1 : p.ano, anoFim = c === 11 ? p.ano + 1 : p.ano;
    return anoIni === anoFim ? MES[ini] + '–' + MES[fim] + ' ' + p.ano
                             : MES[ini] + ' ' + anoIni + '–' + MES[fim] + ' ' + anoFim;
  }
  // O mesmo, sem ano: "jul–set". Serve à comparação entre anos, em que o ano é a outra coluna.
  function periodoCurto(p){
    const c = centro(p);
    if (c === undefined) return String(p.trimestre || '');
    return MES[(c + 11) % 12] + '–' + MES[(c + 1) % 12];
  }
  // Episódio de El Niño pelo critério da NOAA/CPC: cinco ou mais médias trimestrais CONSECUTIVAS
  // acima de +0,5 °C. Nunca escrito à mão — a lista sai do dado, e muda sozinha quando ele muda.
  // O trecho que alcança o último ponto da série é o CICLO EM CURSO, e não entra na lista: ele
  // pode ainda não ter completado as cinco, e chamá-lo de episódio seria afirmar o que falta provar.
  function episodios(serie){
    const s = (serie || []).filter(temCentro).slice().sort((a, b) => ordem(a) - ordem(b));
    const trechos = [];
    let atual = [];
    for (let i = 0; i < s.length; i++) {
      const contiguo = !atual.length || ordem(s[i]) === ordem(atual[atual.length - 1]) + 1;
      if (s[i].anomalia > 0.5 && contiguo) { atual.push(s[i]); continue; }
      if (atual.length) trechos.push(atual);
      atual = s[i].anomalia > 0.5 ? [s[i]] : [];
    }
    if (atual.length) trechos.push(atual);
    const ultimo = s.length ? s[s.length - 1] : null;
    const emCurso = trechos.find(t => ultimo && t[t.length - 1] === ultimo) || null;
    const fechados = trechos.filter(t => t !== emCurso && t.length >= 5);
    const anoDe = t => t[0].ano;
    const rotuloDe = t => anoDe(t) + '–' + String(anoDe(t) + 1).slice(2);
    return {
      serie: s,
      ultimo: ultimo,
      episodios: fechados.map(t => ({ano: anoDe(t), rotulo: rotuloDe(t), pontos: t})),
      emCurso: emCurso ? {ano: anoDe(emCurso), rotulo: String(anoDe(emCurso)), pontos: emCurso} : null,
    };
  }
  // A janela de um ciclo: de janeiro do ano de início a junho do ano seguinte — 18 médias móveis.
  function janela(serie, ano){
    return (serie || []).filter(temCentro)
      .map(p => ({k: (p.ano - ano) * 12 + centro(p), p}))
      .filter(x => x.k >= 0 && x.k <= 17)
      .sort((a, b) => a.k - b.k);
  }
  return {MES, centro, temCentro, ordem, num, periodo, periodoCurto, episodios, janela};
})();

// Texto do catálogo, com reserva. O catálogo é a fonte; a reserva existe para que uma falha de
// rede não deixe um cartão vazio — e cartão vazio é o que o portão de números reprova.
function txtCat(id, valores, reserva){
  const c = window.MonitorCatalogo;
  const t = c && c.texto ? c.texto(id, valores) : null;
  return (t == null || t === '') ? (reserva == null ? null : reserva) : t;
}
function põeCat(elId, id, valores, reserva){
  const el = document.getElementById(elId); if (!el) return null;
  const t = txtCat(id, valores, reserva);
  if (t == null) return null;
  el.textContent = t;
  el.setAttribute('data-conteudo-fixado', '1');
  return t;
}

(function situacaoAtual(){
  const el = id => document.getElementById(id); if (!el('situacaoGrade')) return;
  const I = 'monitor-de-riscos.situacao.';
  const roni = SINAIS.enos.roni;
  const serie = ((roni && roni.serie) || []).filter(PAC.temCentro);
  const u = serie.length ? serie[serie.length - 1] : null;
  const fonte = k => (SINAIS.fontes || {})[k] || {};

  // 1 — a frase de abertura. A segunda oração só aparece quando o dado trouxer a data em que a
  // NOAA/CPC passou a manter o alerta; hoje ele não a traz, e a frase não a inventa.
  const alerta = (SINAIS.enos.prognostico || {}).alerta_desde;
  if (alerta) põeCat('stResumo', I + 'abertura.molde_com_alerta', {desde: alerta});

  // 2 — o RONI mais recente, e a variação para a média móvel ANTERIOR: a série anda de mês em
  // mês, então o trimestre anterior a jul–set é jun–ago, e não jan–mar.
  if (u) {
    põeCat('stRoniRotulo', I + 'roni.molde_rotulo', {trimestre: PAC.periodo(u)});
    põeCat('stRoniValor', I + 'roni.molde_valor', {valor: PAC.num(u.anomalia)});
    const antes = serie.length >= 2 ? serie[serie.length - 2] : null;
    if (antes) põeCat('stRoniVariacao', I + 'roni.molde_variacao',
      {variacao: PAC.num(u.anomalia - antes.anomalia), anterior: PAC.periodo(antes)});
    const f = fonte('noaa_roni');
    põeCat('stRoniFonte', I + 'roni.molde_fonte', {orgao: f.orgao, data: f.consultado_em});
  }

  // 3 — a probabilidade do IRI/CPC (09/10/2026, ajuste 3: o valor cabe numa linha — "99%" — e o
  // trimestre vai para o rótulo). O último trimestre publicado com 90% ou mais é o marco; o último
  // da série entra na linha de baixo. O rótulo de trimestre do IRI vem com o ano ("MAM 2027") ou
  // sem ele; sem ano não há como datar, e trimestre que não se data não vira número na tela.
  const trims = ((SINAIS.enos.probabilidades || {}).trimestres || [])
    .map(t => {
      const m = /^([A-Z]{3})\s*(\d{4})$/.exec(String(t.trimestre || '').trim().toUpperCase());
      return m ? {el_nino: t.el_nino, periodo: PAC.periodo({trimestre: m[1], ano: Number(m[2])}),
                  ordem: Number(m[2]) * 12 + PAC.centro({trimestre: m[1]})} : null;
    }).filter(t => t && t.el_nino != null).sort((a, b) => a.ordem - b.ordem);
  if (trims.length) {
    const altos = trims.filter(t => t.el_nino >= 90);
    const marco = altos.length ? altos[altos.length - 1] : trims[0];
    const fim = trims[trims.length - 1];
    const f = fonte('iri_plume');
    põeCat('stDuracaoRotulo', I + 'duracao.molde_rotulo', {trimestre: marco.periodo});
    põeCat('stDuracaoValor', I + 'duracao.molde_valor_curto', {probabilidade: Math.round(marco.el_nino)});
    if (fim !== marco) põeCat('stDuracaoVariacao', I + 'duracao.molde_variacao',
      {probabilidade_final: Math.round(fim.el_nino), trimestre_final: fim.periodo});
    põeCat('stDuracaoFonte', I + 'duracao.molde_fonte', {orgao: f.orgao, data: f.consultado_em});
  }

  // 4 — a previsão da NOAA/CPC entra no MESMO cartão, como linha de apoio com fonte própria
  // (ajuste 3: saiu o cartão próprio). O número vem do campo; a frase longa só entra quando a
  // sinopse é a que ela descreve. Sem "Hemisfério Norte": o período em meses diz o mesmo fato.
  // A data da próxima discussão SAIU: uma data já passada aparecia como futura (09/10, "a próxima
  // sai em 08/10/2026"), e a página não tem como saber se a seguinte já saiu.
  const pg = SINAIS.enos.prognostico;
  if (pg && pg.probabilidade != null) {
    const sinopse = String(pg.sinopse || '').toLowerCase();
    const reconhecida = /very strong/.test(sinopse) && /fall and winter/.test(sinopse);
    const f = fonte('cpc_ensodisc');
    põeCat('stPrevisaoVariacao',
      I + (reconhecida ? 'previsao.molde_apoio' : 'previsao.molde_apoio_curto'),
      {limiar: pg.limiar === 'acima de' ? 'acima de' : 'de', probabilidade: pg.probabilidade,
       orgao: f.orgao || 'NOAA/CPC', emitido: pg.emitido_em});
  }

  // 5 — o Brasil: os TRÊS riscos com a mesma hierarquia (ajuste 3). Um estado com mais de um risco
  // conta em CADA um deles, como o resto do site já conta. Ordem alfabética: chuva, fogo, seca.
  (function brasil(){
    const conta = {estiagem: 0, chuvas: 0, incendios: 0};
    UFS.forEach(uf => {
      const r = (SINAIS.uf[uf] || {}).risco_projetado; if (!r) return;
      const comps = (r.componentes && r.componentes.length) ? r.componentes : [r.tipo];
      comps.forEach(c => { if (c in conta) conta[c]++; });
    });
    const f = fonte('painel_el_nino');
    // O número do boletim sai do documento declarado pela fonte ("Boletins nº 1 e 3 …"): o mais
    // alto é o que sustenta a previsão em vigor. Só os números que vêm DEPOIS do "nº".
    const trecho = /n[ºo°]\s*([\d\s,eo]+)/i.exec(String(f.documento || ''));
    const ns = trecho ? (trecho[1].match(/\d+/g) || []) : [];
    if (ns.length) põeCat('stBrasilRotulo', I + 'brasil.molde_rotulo',
      {boletim: String(Math.max.apply(null, ns.map(Number)))});
    põeCat('stBrasilChuva', I + 'brasil.molde_numero', {n: conta.chuvas});
    põeCat('stBrasilFogo', I + 'brasil.molde_numero', {n: conta.incendios});
    põeCat('stBrasilSeca', I + 'brasil.molde_numero', {n: conta.estiagem});
    const pe = document.getElementById('stBrasilFonte');
    const base = txtCat(I + 'brasil.molde_fonte', {orgao: f.orgao, data: f.consultado_em}, null);
    const ponte = txtCat(I + 'brasil.ponte', null, null);
    if (pe && base && ponte) {
      pe.textContent = base;
      const a = document.createElement('a'); a.href = '#riscos'; a.textContent = ponte;
      pe.appendChild(a);
      pe.setAttribute('data-conteudo-fixado', '1');
    }
  })();
})();

// 13/09/2026: cartoesCiclo/cartaoCiclo1-4 removidos — três dos quatro cartões duplicavam valores já
// no painel Situação Atual (ONI, Probabilidade, Prognóstico/Boletim nº 3); só 'Boletim mais recente
// do ciclo' trazia informação nova (o nome do documento), agora em stDocumento acima, com a citação
// combinada das três fontes substituindo os quatro créditos individuais.

// =============================  Gráficos  =============================
const SEM_ANIM = {animation:false, responsive:true, maintainAspectRatio:false};

function canvasEm(wrapId, canvasId, rotulo){
  const w = document.getElementById(wrapId);
  const c = document.createElement('canvas'); c.id = canvasId;
  /* Rótulo acessível na própria criação: gráfico sem rótulo é figura muda para quem usa leitor de
     tela, e o portão de conformidade (03/10/2026) passou a cobrar. Sem rótulo dado, cai no título
     da figura — que é a descrição que já está aprovada. */
  const fig = w && w.closest('figure');
  const titulo = fig && fig.querySelector('.figura-titulo');
  c.setAttribute('role', 'img');
  c.setAttribute('aria-label', rotulo || (titulo ? titulo.textContent.trim() : 'Gráfico'));
  w.appendChild(c); return c;
}

// 30/09/2026 (handover do Monitor de riscos): os gráficos do ONI e da anomalia mensal
// SAÍRAM da página. Eles medem a mesma coisa que o RONI com outra referência, e três
// gráficos do mesmo fenômeno lado a lado pediam do leitor uma comparação técnica que
// não é a pergunta desta página. Os dois continuam coletados e vivem na METODOLOGIA,
// como apoio técnico.

// =====  Os dois gráficos do Pacífico (07/10/2026, maquete rev. 2)  ==========================
//
// POR QUE SVG, E NÃO CANVAS. O pedido tem uma exigência que o canvas não cumpre: letra de 12 px
// TAMBÉM no celular. Um canvas de 560 unidades encolhido para 343 px de tela reduz toda a
// tipografia na mesma proporção — a figura do desktop vista de longe, não uma figura para
// celular. Aqui a figura é desenhada na LARGURA REAL do contêiner, redesenhada quando ela muda, e
// 12 px são 12 px em qualquer tela. De quebra, some o erro de runtime "can't acquire context",
// que era do canvas e só aparecia onde o contexto 2D não existe.
//
// Cor nenhuma aqui: tudo é classe de `assets/base.css`, que lê os tokens de `assets/tokens.css`.
const SVGNS = 'http://www.w3.org/2000/svg';
const RONI_MIN = -2.0, RONI_MAX = 2.5;            // a escala é a MESMA nos dois gráficos
const RONI_LIMIARES = [[0.5, 'marca_el_nino'], [-0.5, 'marca_la_nina']];

function svgEl(nome, attrs, texto){
  const e = document.createElementNS(SVGNS, nome);
  for (const k in (attrs || {})) if (attrs[k] != null) e.setAttribute(k, attrs[k]);
  if (texto != null) e.textContent = texto;
  return e;
}
/** Valor com rótulo ao passar o mouse, ao tocar e ao focar — e `<title>` para o leitor de tela. */
function comValor(el, texto){
  el.appendChild(svgEl('title', null, texto));
  el.addEventListener('mouseenter', evt => MonitorMapas.showTip(esc(texto), evt));
  el.addEventListener('mouseleave', MonitorMapas.hideTip);
  el.addEventListener('focus', evt => MonitorMapas.showTip(esc(texto), evt));
  el.addEventListener('blur', MonitorMapas.hideTip);
  return el;
}

/** A moldura comum: escala, linha do zero e os DOIS limiares oficiais. Nada além disso — a régua
 *  de força não é da NOAA, e por isso não há faixa nenhuma no fundo destes gráficos. */
function molduraPacifico(g, geo){
  const {L, T, pw, ph, y, estreito} = geo;
  for (let v = RONI_MIN; v <= RONI_MAX + 1e-9; v += 0.5) {
    const r = Math.round(v * 10) / 10;
    g.appendChild(svgEl('text', {x: L - 8, y: (y(r) + 4).toFixed(1), class: 'tk',
                                 'text-anchor': 'end'}, r === 0 ? '0' : PAC.num(r)));
  }
  g.appendChild(svgEl('line', {x1: L, x2: L + pw, y1: y(0).toFixed(1), y2: y(0).toFixed(1), class: 'zero'}));
  RONI_LIMIARES.forEach(([v, id]) => {
    g.appendChild(svgEl('line', {x1: L, x2: L + pw, y1: y(v).toFixed(1), y2: y(v).toFixed(1), class: 'lim'}));
    const rotulo = txtCat('monitor-de-riscos.pacifico.episodios.' + id, null,
                          PAC.num(v) + ' · ' + (v > 0 ? 'El Niño' : 'La Niña'));
    // Numa coluna estreita não há margem à direita para o rótulo do limiar: ele passa a ficar
    // ACIMA da própria linha tracejada, encostado à esquerda. Mesma informação, outro lugar.
    g.appendChild(estreito
      ? svgEl('text', {x: L + 4, y: (y(v) - 5).toFixed(1), class: 'limt'}, rotulo)
      : svgEl('text', {x: L + pw + 6, y: (y(v) + 4).toFixed(1), class: 'limt'}, rotulo));
  });
}

/** Geometria do desenho, na largura real. `baixo` reserva espaço extra sob o eixo horizontal. */
function geometriaPacifico(largura, baixo){
  const W = Math.max(280, Math.round(largura || 0) || 560);
  const estreito = W < 480;
  const L = 42, R = estreito ? 14 : 104, T = estreito ? 24 : 16, B = 36 + (baixo || 0);
  const H = Math.max(260, Math.min(360, Math.round(W * 0.62))) + (baixo || 0);
  const pw = Math.max(40, W - L - R), ph = Math.max(40, H - T - B);
  return {W, H, L, R, T, B, pw, ph, estreito,
          y: v => T + (RONI_MAX - v) / (RONI_MAX - RONI_MIN) * ph};
}

/** Desenha dentro do contêiner e redesenha quando a largura muda. `pinta(g, geo)` faz a figura. */
function desenharNaLargura(wrapId, baixo, rotulo, pinta){
  const wrap = document.getElementById(wrapId); if (!wrap) return;
  let ultimaLargura = null;
  function render(){
    const largura = wrap.clientWidth || wrap.getBoundingClientRect().width || 560;
    if (ultimaLargura !== null && Math.abs(largura - ultimaLargura) < 8) return;
    ultimaLargura = largura;
    const geo = geometriaPacifico(largura, baixo);
    const svg = svgEl('svg', {viewBox: '0 0 ' + geo.W + ' ' + geo.H, width: geo.W, height: geo.H,
                              class: 'g-pac', role: 'img', 'aria-label': rotulo});
    molduraPacifico(svg, geo);
    pinta(svg, geo);
    wrap.innerHTML = '';
    wrap.appendChild(svg);
  }
  render();
  // Redesenhar é melhoria de leitura: uma falha aqui não pode derrubar a figura já desenhada.
  try {
    if (typeof ResizeObserver === 'function') new ResizeObserver(() => { try { render(); } catch (e) {} }).observe(wrap);
    else addEventListener('resize', () => { try { render(); } catch (e) {} });
  } catch (e) {}
}

const RONI = SINAIS.enos.roni;
const PACIFICO = PAC.episodios((RONI && RONI.serie) || []);
const IP = 'monitor-de-riscos.pacifico.';

// A fonte dos dois é a mesma, e diz qual é o último dado — não só quando consultamos.
function creditoPacifico(caixaId){
  const f = (SINAIS.fontes || {})['noaa_roni'] || {};
  MonitorMapas.credito(caixaId, {
    fontes: [f.orgao, f.nome].filter(Boolean).join(' · ')
      + (PACIFICO.ultimo ? ' · último dado: ' + PAC.periodo(PACIFICO.ultimo) : ''),
    url: f.url_publica, data: f.consultado_em});
  const d = document.querySelector('#' + caixaId + ' .fonte-figura');
  if (d) d.dataset.credito = 'noaa_roni';
}

if (PACIFICO.serie.length) {
  const serie = PACIFICO.serie;
  const primeiro = serie[0], ultimo = PACIFICO.ultimo;
  const maximo = serie.reduce((a, b) => b.anomalia > a.anomalia ? b : a, serie[0]);
  // O título traz os anos DO DADO: quando a série passar a começar em 1950, ele diz 1950 sozinho.
  // ANO É RÓTULO, NÃO QUANTIDADE: o catálogo formata número em pt-BR, e `2026` chegaria à tela
  // como "2.026". Tudo o que é ano entra no molde já como texto.
  const anos = {inicio: String(primeiro.ano), fim: String(ultimo.ano)};
  põeCat('roniTitulo', IP + 'roni.molde_titulo', anos);

  // ---- Gráfico 1: a série inteira, em barras ----
  desenharNaLargura('wrapRoni', 0,
    txtCat(IP + 'roni.rotulo_acessivel', anos, 'Barras do RONI por trimestre'),
    function (g, geo) {
      const {L, T, pw, ph, y, estreito} = geo;
      const n = serie.length, bw = pw / n;
      // Um rótulo de ano a cada 2 anos na série curta e a cada 10 na série desde 1950 — e a cada
      // 5 na coluna estreita, onde os rótulos se tocariam. O passo sai do TAMANHO da série.
      const amplitude = ultimo.ano - primeiro.ano;
      const passo = amplitude > 40 ? 10 : (estreito ? 5 : 2);
      serie.forEach((pt, i) => {
        const x = L + i * bw, v = pt.anomalia;
        const y0 = Math.min(y(0), y(v)), y1 = Math.max(y(0), y(v));
        const barra = svgEl('rect', {x: (x + 0.4).toFixed(2), y: y0.toFixed(2),
          width: Math.max(bw - 0.8, 0.6).toFixed(2), height: Math.max(y1 - y0, 0.5).toFixed(2),
          class: v >= 0 ? 'q' : 'f'});
        g.appendChild(comValor(barra, PAC.periodo(pt) + ': ' + PAC.num(v) + ' °C'));
        if (PAC.centro(pt) === 0 && pt.ano % passo === 0) {
          g.appendChild(svgEl('line', {x1: x.toFixed(1), x2: x.toFixed(1), y1: T + ph, y2: T + ph + 5, class: 'tkl'}));
          g.appendChild(svgEl('text', {x: x.toFixed(1), y: T + ph + 18, class: 'tk',
                                       'text-anchor': 'middle'}, String(pt.ano)));
        }
      });
      // Duas anotações literais, e nenhuma interpretação: o maior valor da série e o último.
      const iMax = serie.indexOf(maximo);
      const annMax = txtCat(IP + 'roni.molde_anotacao_maximo',
        {periodo: PAC.periodo(maximo), valor: PAC.num(maximo.anomalia)}, null);
      // Perto da borda direita a anotação sairia da figura: ela vira para a esquerda do pico.
      const maxADireita = (iMax + 1) * bw > pw * 0.62;
      if (annMax && !estreito) g.appendChild(svgEl('text', {
        x: (L + (iMax + (maxADireita ? 0 : 1)) * bw + (maxADireita ? -6 : 6)).toFixed(1),
        y: (y(maximo.anomalia) + 4).toFixed(1), class: 'ann',
        'text-anchor': maxADireita ? 'end' : 'start'}, annMax));
      const cx = L + (n - 0.5) * bw, cy = y(ultimo.anomalia);
      g.appendChild(svgEl('circle', {cx: cx.toFixed(1), cy: cy.toFixed(1), r: 3.5, class: 'agora'}));
      const annU = txtCat(IP + 'roni.molde_anotacao_ultimo',
        {periodo: PAC.periodo(ultimo), valor: PAC.num(ultimo.anomalia)}, null);
      if (annU && !estreito) g.appendChild(svgEl('text', {x: (cx - 8).toFixed(1),
        y: (cy - 9).toFixed(1), class: 'ann ann-agora', 'text-anchor': 'end'}, annU));
    });
  // A frase sob o gráfico diz os dois mesmos valores por extenso — é ela que serve a quem não
  // alcança a anotação dentro da figura, no celular.
  põeCat('roniLeitura', IP + 'roni.molde_leitura', {
    maximo: PAC.num(maximo.anomalia), maximo_periodo: PAC.periodo(maximo),
    ultimo: PAC.num(ultimo.anomalia), ultimo_periodo: PAC.periodo(ultimo)});

  // ---- Gráfico 2: o ciclo em curso e os episódios que o dado define ----
  // A lista NUNCA é escrita à mão: sai do critério da NOAA/CPC aplicado à própria série.
  // O RECORTE, decidido em 07/10/2026 com a série desde 1950 já no registro: NENHUM episódio sai.
  // O critério da NOAA/CPC encontra 22 na série, e as três saídas possíveis se resolvem assim:
  // escolher os "maiores" seria ranking, que a página não constrói; escolher os mais recentes
  // seria recorte nosso, sem o dado pedir; e nomear 22 numa legenda não se lê. Então todos são
  // desenhados como CONTEXTO, no mesmo traço fino e no mesmo tom — a nuvem dentro da qual o ciclo
  // em curso se vê —, e só ele é destacado e rotulado, porque é o assunto da página. Nada é
  // omitido: cada linha diz o seu episódio e o seu valor ao passar o mouse ou tocar.
  const linhas = [];
  if (PACIFICO.emCurso) linhas.push({ano: PACIFICO.emCurso.ano, rotulo: PACIFICO.emCurso.rotulo, classe: 'l-agora', agora: true});
  PACIFICO.episodios.forEach(e => linhas.push({ano: e.ano, rotulo: e.rotulo, classe: 'l-contexto', agora: false}));
  // 09/10/2026 (ajuste 4, editoria): cada episódio com o seu pico na janela desenhada. Rótulo
  // direto só nos de pico de +1,5 °C ou mais — o critério de "forte" da NOAA/CPC, regra fixa e
  // declarada na nota da figura, não escolha nossa. Na coluna estreita (celular), só os três
  // maiores picos; os demais se nomeiam ao passar o mouse, ao tocar, pelo teclado e na lista.
  const PICO_ROTULADO = 1.5;
  linhas.forEach(l => {
    const pts = PAC.janela(serie, l.ano);
    l.pico = pts.length ? pts.reduce((a, b) => b.p.anomalia > a.p.anomalia ? b : a, pts[0]) : null;
  });
  const fortes = linhas.filter(l => !l.agora && l.pico && l.pico.p.anomalia >= PICO_ROTULADO);
  const tresMaiores = fortes.slice().sort((a, b) => b.pico.p.anomalia - a.pico.p.anomalia).slice(0, 3);
  const descreveEpisodio = l => l.rotulo + ' · pico ' + PAC.num(l.pico.p.anomalia) + ' °C em '
    + PAC.periodoCurto(l.pico.p);
  const episodiosRotulos = PACIFICO.episodios.map(e => e.rotulo);
  // O TÍTULO NÃO LISTA OS EPISÓDIOS, e a lista vai para a nota. O handover pediu a lista no
  // título; a regra de componente vence, e por duas razões que o próprio dado impõe. A primeira é
  // medida: numa coluna da grade de dois, "RONI nos episódios de El Niño de 2015–16, 2018–19 e
  // 2023–24 e em 2026" ocupava CINCO linhas contra duas da figura ao lado, e o cartão de mapa
  // reserva duas — as duas figuras desalinhavam em 70 px no subtítulo e na mídia, e o portão de
  // consistência visual reprovava, com razão. A segunda é de trajetória: com a série desde 1950 a
  // lista passa de três episódios para dezenas, e um título que cresce com o dado não é título.
  // A nota é onde a lista cabe, e a legenda do gráfico nomeia cada linha de qualquer modo.
  põeCat('episodiosTitulo',
    IP + (episodiosRotulos.length ? 'episodios.molde_titulo' : 'episodios.molde_titulo_sem_episodio'),
    {ano: String(PACIFICO.emCurso ? PACIFICO.emCurso.ano : ultimo.ano),
     n: episodiosRotulos.length,
     inicio: String(PACIFICO.episodios.length ? PACIFICO.episodios[0].ano : primeiro.ano)});
  // A lista dos episódios NÃO entra na nota: ela cresce com o dado, e nota que cresce desalinha a
  // dupla do mesmo jeito que o título desalinhava. Quem os nomeia é a legenda do gráfico, item a
  // item, e a frase de leitura logo abaixo, com o valor de cada um.
  põeCat('episodiosNota', IP + 'episodios.molde_nota', anos);

  desenharNaLargura('wrapEpisodios', 20,
    txtCat(IP + 'episodios.rotulo_acessivel', null, 'Linhas do RONI por episódio'),
    function (g, geo) {
      const {L, T, pw, ph, y, estreito} = geo;
      const xs = k => L + k * (pw / 17);
      const passo = estreito ? 3 : 2;
      for (let k = 0; k <= 17; k += passo) {
        g.appendChild(svgEl('text', {x: xs(k).toFixed(1), y: T + ph + 18, class: 'tk',
                                     'text-anchor': 'middle'}, PAC.MES[k % 12]));
      }
      g.appendChild(svgEl('line', {x1: xs(11.5).toFixed(1), x2: xs(11.5).toFixed(1),
                                   y1: T, y2: T + ph + 30, class: 'div'}));
      g.appendChild(svgEl('text', {x: xs(5.5).toFixed(1), y: T + ph + 34, class: 'tk2',
        'text-anchor': 'middle'}, txtCat(IP + 'episodios.eixo_ano_inicio', null, '')));
      g.appendChild(svgEl('text', {x: xs(14.5).toFixed(1), y: T + ph + 34, class: 'tk2',
        'text-anchor': 'middle'}, txtCat(IP + 'episodios.eixo_ano_seguinte', null, '')));
      // Rótulo da linha vertical: o mês que ela marca. Ele entra na lista de ocupados antes dos
      // rótulos dos episódios, para que nenhum caia em cima dele.
      const txtDiv = txtCat(IP + 'episodios.rotulo_divisoria', null, 'janeiro do ano seguinte');
      // Na coluna estreita o rótulo não cabe à direita da linha: vai para a esquerda dela.
      g.appendChild(svgEl('text', {x: (xs(11.5) + (estreito ? -4 : 4)).toFixed(1), y: (T + 10).toFixed(1),
        class: 'tk2', 'text-anchor': estreito ? 'end' : 'start'}, txtDiv));
      // Rótulos diretos: posição pedida no pico; colisão resolvida aqui, com deslocamento vertical
      // mínimo. Nunca dois rótulos sobrepostos: o que não acha lugar fica sem rótulo direto (ele
      // continua no mouse, no toque, no teclado e na lista).
      const largDiv = 4 + txtDiv.length * 7.2;
      const ocupados = [estreito ? {x0: xs(11.5) - largDiv, x1: xs(11.5), y0: T - 2, y1: T + 14}
                                 : {x0: xs(11.5), x1: xs(11.5) + largDiv, y0: T - 2, y1: T + 14}];
      const caixa = (x, yy, txt) => ({x0: x - txt.length * 3.6, x1: x + txt.length * 3.6, y0: yy - 12, y1: yy + 3});
      const colide = c => ocupados.some(o => !(c.x1 < o.x0 || c.x0 > o.x1 || c.y1 < o.y0 || c.y0 > o.y1));
      const rotuloDireto = (linha) => {
        const deveRotular = linha.agora ? !estreito
          : (estreito ? tresMaiores.includes(linha) : fortes.includes(linha));
        if (!deveRotular) return null;
        const onde = linha.agora ? PAC.janela(serie, linha.ano).slice(-1)[0] : linha.pico;
        if (!onde) return null;
        const x = Math.min(Math.max(xs(onde.k), L + 20), L + pw - 20);
        const base = linha.agora ? y(onde.p.anomalia) + 20 : y(onde.p.anomalia) - 6;
        for (const dx of [0, -34, 34]) {
          for (const d of [0, 14, -14, 28, -28, 42, 56, 70]) {
            const xx = Math.min(Math.max(x + dx, L + 20), L + pw - 20);
            const c = caixa(xx, base + d, linha.rotulo);
            if (c.y0 < T - 4 || c.y1 > T + ph) continue;
            if (!colide(c)) { ocupados.push(c); return {x: xx, y: base + d}; }
          }
        }
        return null;
      };
      // Posições calculadas ANTES de desenhar, na ordem de prioridade: o ciclo em curso, depois
      // os picos maiores — é o que garante que o deslocamento recai sobre os menores.
      const posicoes = new Map();
      linhas.filter(l => l.pico).slice()
        .sort((a, b) => (b.agora - a.agora) || (b.pico.p.anomalia - a.pico.p.anomalia))
        .forEach(l => posicoes.set(l, rotuloDireto(l)));
      // O ciclo em curso é desenhado POR ÚLTIMO, para ficar por cima.
      const grupos = [];
      linhas.slice().reverse().forEach(linha => {
        const pts = PAC.janela(serie, linha.ano);
        if (!pts.length) return;
        const grupo = svgEl('g', {class: 'ep' + (linha.agora ? ' ep-agora' : ''), tabindex: '0',
                                  role: 'img', 'aria-label': linha.agora ? linha.rotulo : descreveEpisodio(linha)});
        grupo.appendChild(svgEl('polyline', {class: linha.classe,
          points: pts.map(x => xs(x.k).toFixed(1) + ',' + y(x.p.anomalia).toFixed(1)).join(' ')}));
        // Faixa larga e invisível sobre a linha: é o alvo do mouse e do toque para a linha inteira.
        grupo.appendChild(svgEl('polyline', {class: 'hit-linha',
          points: pts.map(x => xs(x.k).toFixed(1) + ',' + y(x.p.anomalia).toFixed(1)).join(' ')}));
        pts.forEach(x => {
          const alvo = svgEl('circle', {cx: xs(x.k).toFixed(1), cy: y(x.p.anomalia).toFixed(1),
                                        r: 7, class: 'hit', tabindex: '-1'});
          grupo.appendChild(comValor(alvo, linha.rotulo + ' · ' + PAC.periodoCurto(x.p)
                                       + ': ' + PAC.num(x.p.anomalia) + ' °C'));
        });
        const acende = evt => { g.classList.add('foco'); grupo.classList.add('acesa');
          if (!linha.agora && evt && evt.type !== 'mouseover') MonitorMapas.showTip(esc(descreveEpisodio(linha)), evt); };
        const apaga = () => { g.classList.remove('foco'); grupo.classList.remove('acesa'); MonitorMapas.hideTip(); };
        grupo.addEventListener('mouseover', acende);
        grupo.addEventListener('mouseout', apaga);
        grupo.addEventListener('focus', acende);
        grupo.addEventListener('blur', apaga);
        grupo.addEventListener('touchstart', acende, {passive: true});
        g.appendChild(grupo);
        grupos.push([grupo, linha]);
        const pos = posicoes.get(linha);
        if (pos && !linha.agora) g.appendChild(svgEl('text', {x: pos.x.toFixed(1), y: pos.y.toFixed(1),
          class: 'ann ann-ep', 'text-anchor': 'middle'}, linha.rotulo));
        if (pos && linha.agora) g.appendChild(svgEl('text', {x: pos.x.toFixed(1), y: pos.y.toFixed(1),
          class: 'ann ann-agora', 'text-anchor': 'middle'}, linha.rotulo));
        const fimDaLinha = pts[pts.length - 1];
        if (linha.agora) g.appendChild(svgEl('circle', {cx: xs(fimDaLinha.k).toFixed(1),
          cy: y(fimDaLinha.p.anomalia).toFixed(1), r: 4, class: 'agora'}));
      });
    });

  // A legenda mostra o traço de cada linha: cor nunca é o único portador da informação.
  // A legenda tem DOIS itens, não 23: o ciclo em curso e a família de contexto, com a contagem
  // e o intervalo de anos. Quem quer saber qual linha é qual toca nela.
  (function legendaEpisodios(){
    const alvo = document.getElementById('legEpisodios'); if (!alvo) return;
    const itens = [];
    if (PACIFICO.emCurso) itens.push(['t-agora', txtCat(IP + 'episodios.legenda_atual',
      {ano: String(PACIFICO.emCurso.ano)}, String(PACIFICO.emCurso.ano))]);
    if (PACIFICO.episodios.length) itens.push(['t-contexto', txtCat(IP + 'episodios.legenda_contexto',
      {n: PACIFICO.episodios.length,
       inicio: String(PACIFICO.episodios[0].ano),
       fim: String(PACIFICO.episodios[PACIFICO.episodios.length - 1].ano)}, null)]);
    alvo.innerHTML = itens.filter(i => i[1])
      .map(i => '<span><i class="' + i[0] + '"></i>' + esc(i[1]) + '</span>').join('');
    // 09/10/2026 (ajuste 4): a alternativa acessível — os episódios em lista, na ordem do
    // calendário (ano, pico e trimestre do pico), recolhida no mesmo link discreto dos mapas.
    if (linhas.some(l => !l.agora)) {
      const lin = linhas.filter(l => !l.agora && l.pico).slice().sort((a, b) => a.ano - b.ano)
        .map(l => '<tr><td>' + esc(l.rotulo) + '</td><td>' + esc(PAC.num(l.pico.p.anomalia)) + ' °C</td><td>'
          + esc(PAC.periodoCurto(l.pico.p)) + '</td></tr>').join('');
      alvo.insertAdjacentHTML('beforeend', '<details class="cartao-mapa-dados lista-episodios"><summary>'
        + esc(txtCat(IP + 'episodios.ver_em_lista', null, 'Ver em lista')) + '</summary>'
        + '<div class="tbl-wrap" tabindex="0" role="region" aria-label="Tabela rolável horizontalmente">'
        + '<table class="mun-table"><thead><tr><th>Episódio</th><th>Pico do RONI</th><th>Trimestre do pico</th></tr></thead><tbody>'
        + lin + '</tbody></table></div></details>');
    }
  })();

  // A leitura sob o gráfico: o MESMO trimestre em cada linha, na ordem do calendário. Não há
  // ordenação por valor aqui — ranking é comparação nossa, e a página mostra as etapas.
  (function leituraEpisodios(){
    const alvoK = (ultimo.ano - (PACIFICO.emCurso ? PACIFICO.emCurso.ano : ultimo.ano)) * 12 + PAC.centro(ultimo);
    // A leitura dá o valor do ciclo em curso e a FAIXA dos demais no mesmo ponto do calendário —
    // mínimo e máximo. Listar 22 valores não se lê, e ordená-los seria ranking. A faixa descreve
    // a nuvem sem ordenar nada, e é o leitor quem conclui onde o ciclo em curso cai dentro dela.
    const noAlvo = PACIFICO.episodios
      .map(e => (PAC.janela(serie, e.ano).find(x => x.k === alvoK) || {}).p)
      .filter(Boolean).map(p => p.anomalia);
    let texto = noAlvo.length ? txtCat(IP + 'episodios.molde_leitura', {
      trimestre: PAC.periodoCurto(ultimo),
      atual: PAC.num(ultimo.anomalia),
      ano: String(PACIFICO.emCurso ? PACIFICO.emCurso.ano : ultimo.ano),
      n: noAlvo.length,
      minimo: PAC.num(Math.min.apply(null, noAlvo)),
      maximo: PAC.num(Math.max.apply(null, noAlvo))}, null) : null;
    // A contagem do ciclo em curso só é dita enquanto o critério NÃO se completou: depois das
    // cinco, a frase "se completa na quinta" deixa de ser verdadeira.
    if (PACIFICO.emCurso && PACIFICO.emCurso.pontos.length < 5) {
      const c = txtCat(IP + 'episodios.molde_contagem', {ano: String(PACIFICO.emCurso.ano),
        n: PACIFICO.emCurso.pontos.length, trimestre: PAC.periodoCurto(ultimo)}, null);
      if (c) texto = (texto ? texto + ' ' : '') + c;
    }
    const el = document.getElementById('episodiosLeitura');
    if (el && texto) { el.textContent = texto; el.setAttribute('data-conteudo-fixado', '1'); }
  })();
} else {
  lacuna('wrapRoni', txtCat(IP + 'roni.lacuna', null, 'Sem coleta até o corte.'));
  lacuna('wrapEpisodios', txtCat(IP + 'episodios.lacuna', null, 'Sem coleta até o corte.'));
}
creditoPacifico('boxRoni');
creditoPacifico('boxEpisodios');

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
// "Ver estados" e descrição acessível de cada mapa (09/10/2026, ajuste 5), depois de todos desenhados.
[['mapaRiscoPrevisto', 'estadosRiscoPrevisto'], ['mapaSecas', 'estadosSecas'], ['mapaFogo', 'estadosFogo'],
 ['mapaAr', 'estadosAr'], ['mapaTemperatura', 'estadosTemperatura'], ['mapaAvisos', 'estadosAvisos']]
  .forEach(([svg, alvo]) => { try { if (ROTULOS_DOS_MAPAS[svg]) escreverEstados(alvo, ROTULOS_DOS_MAPAS[svg]); } catch (e) {} });
}
__load();

// ===== monitor-de-riscos.html · bloco 2 (extraído em 06/09/2026, CSP sem unsafe-inline) =====
window.addEventListener('load', function(){ if (window.VLibras && window.VLibras.Widget) { try { new window.VLibras.Widget('https://vlibras.gov.br/app'); } catch (e) {} } });

