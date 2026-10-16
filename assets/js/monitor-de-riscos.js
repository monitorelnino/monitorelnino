// ===== monitor-de-riscos.html · bloco 1 (extraído em 06/09/2026, CSP sem unsafe-inline) =====
/* Sinais oficiais de risco — camada de apresentação.
   Regra desta página: nenhum valor é calculado aqui. Tudo vem de
   data/sinais_risco.json, escrito por coletar_sinais_risco.py, com fonte,
   documento e data. Fonte não coletada vira lacuna declarada na tela. */
let BR_GEOJSON, SINAIS, MARE, AVISOS, FOCOS, NORMAIS, FOGO_REF, SECAS_MANCHAS, AR;   // NORMAIS: normais do Inmet, para o DESVIO do mapa de calor
const UFS = ["AC","AL","AM","AP","BA","CE","DF","ES","GO","MA","MG","MS","MT","PA","PB","PE","PI","PR","RJ","RN","RO","RR","RS","SC","SE","SP","TO"];
const NEUTRA = MonitorMapas.cor('sem-dado');           // estado sem dado coletado

async function __load(){
  [BR_GEOJSON, SINAIS, MARE] = await Promise.all(
    ['geo_uf','sinais_risco','indice'].map(f => fetch('data/' + f + '.json').then(r => {
      if(!r.ok) throw new Error('Falha ao carregar data/' + f + '.json');
      return r.json();
    }))
  );
  /* 29/09/2026: focos do INPE agregados em grade, em arquivo próprio — são milhares de células
     e não cabem no arquivo de sinais, que toda página da seção carrega inteiro. Ausente, o mapa
     diz que não houve coleta; nunca desenha zero. */
  /* Índice de avisos por município (o resumo traz os municípios por UF e grau). Ausente = lacuna. */
  AVISOS = await fetch('data/alertas/vigentes.json').then(r => r.ok ? r.json() : null).catch(() => null);
  NORMAIS = await fetch('data/normais_capitais.json').then(r => r.ok ? r.json() : null).catch(() => null);
  FOCOS = await fetch('data/focos_pontos.json').then(r => r.ok ? r.json() : null).catch(() => null);
  /* 16/10/2026: contagens do satélite de referência (dia, série, mês, UF, bioma). Ausente = lacuna. */
  FOGO_REF = await fetch('data/focos_referencia.json').then(r => r.ok ? r.json() : null).catch(() => null);
  SECAS_MANCHAS = await fetch('data/secas_manchas.json').then(r => r.ok ? r.json() : null).catch(() => null);
  AR = await fetch('data/ar_medido.json').then(r => r.ok ? r.json() : null).catch(() => null);
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
const projection = __ctx().projection;
const pathGen = __ctx().path;
const fonteDe = id => (SINAIS.fontes || {})[id] || {};
const coletada = id => fonteDe(id).status === 'coletado';

/* Crédito de UMA linha ao pé do cartão (04/09/2026): "Fonte: nome · data" ou "· sem coleta até o corte". */
function credito(caixaId, fonteId, apoioId){
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
  /* 09/10/2026 (ajuste 6): a medição da estação entra no texto do mouse e na tabela, não no mapa;
     a fonte dela vai no mesmo crédito, como segunda parte — só quando há medição coletada para mostrar. */
  if (apoioId && coletada(apoioId)) partes.push('medição: ' + (fonteDe(apoioId).orgao || fonteDe(apoioId).nome));
  MonitorMapas.credito(caixaId, {fontes: partes.join(' · '), url: f.url_publica,
                                 data: coletada(fonteId) ? f.consultado_em : null});
  const d = document.querySelector('#' + caixaId + ' .fonte-figura'); if (d) d.dataset.credito = fonteId;
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
  const f = fonteDe('inmet_previsao_capitais');
  return MonitorMapas.dica({titulo: capitalUF(uf, (temp(uf) || {}).capital),
    linhas: ['Sem dado de ' + (f.orgao || 'a fonte') + ' para a capital na consulta'
             + (f.consultado_em ? ' de ' + f.consultado_em : '')]});
}
function __ctx(){ if (!window.__ctxCache) window.__ctxCache = MonitorMapas.contexto(BR_GEOJSON, 480, 460); return window.__ctxCache; }

// ---- Risco previsto pelo boletim (Painel El Niño): famílias por estado ----
const riscoDe = uf => (SINAIS.uf[uf] || {}).risco_projetado || null;
const componentesDe = uf => {
  const r = riscoDe(uf); if (!r) return [];
  const c = (r.componentes && r.componentes.length ? r.componentes : [r.tipo]).filter(Boolean);
  return c.filter(x => x !== 'sem_sinal');
};
// 16/10/2026 (editoria, HANDOVER_MONITOR_DE_RISCOS §2): o risco previsto é uma FAIXA de etiquetas por
// família, na ordem pedida; cada sigla abre a ficha do estado na inicial. Previsão, não observação.
const FAMILIAS_PREVISTAS = [
  ['Seca', c => c.length === 1 && c[0] === 'estiagem'],
  ['Seca e fogo', c => c.includes('estiagem') && c.includes('incendios')],
  ['Chuva forte', c => c.length === 1 && c[0] === 'chuvas'],
  ['Chuva forte e fogo', c => c.includes('chuvas') && c.includes('incendios')],
  ['Fogo', c => c.length === 1 && c[0] === 'incendios'],
  ['Sem sinal elevado', c => !c.length],
];
const siglasLigadas = ufs => ufs.map(uf => '<a class="chip-risco" href="index.html#' + esc(uf) + '">'
  + esc(uf) + '</a>').join('');
const ufsCom = teste => UFS.filter(uf => SINAIS.uf[uf] && teste(componentesDe(uf)));
(function faixaRiscoPrevisto(){
  const dl = document.getElementById('faixaRiscoPrevisto'); if (!dl) return;
  const pe = fonteDe('painel_el_nino');
  if (pe.status !== 'coletado') { lacuna('faixaRiscoPrevisto', 'Sem coleta até o corte.'); return; }
  const usados = new Set();
  dl.innerHTML = FAMILIAS_PREVISTAS.map(([rotulo, teste]) => {
    const ufs = ufsCom(teste).filter(uf => !usados.has(uf)); ufs.forEach(uf => usados.add(uf));
    return ufs.length ? '<div><dt>' + esc(rotulo) + '</dt><dd class="chips">' + siglasLigadas(ufs) + '</dd></div>' : '';
  }).join('');
  const doc = pe.documento ? String(pe.documento).replace(/^.*?(Boletim)/, '$1') : 'Boletim do Painel El Niño';
  const sub = document.getElementById('riscoPrevistoSub');
  if (sub) sub.textContent = doc + ' · até março de 2027 · previsão, não observação';
  credito('boxRiscoPrevisto', 'painel_el_nino');
  // "Boletim prevê para", ao lado do título de cada bloco de família.
  const preve = (id, teste) => { const el = document.getElementById(id); if (!el) return;
    const ufs = ufsCom(teste);
    el.innerHTML = ufs.length ? '<span>Boletim prevê para:</span> <span class="chips">' + siglasLigadas(ufs) + '</span>' : ''; };
  preve('preveSeca', c => c.includes('estiagem') || c.includes('incendios') || c.includes('calor'));
  preve('preveChuva', c => c.includes('chuvas'));
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



  const fTemp = fonte('inmet_previsao_capitais');
  const diaPrev = (SINAIS.uf.SP && SINAIS.uf.SP.temperatura && SINAIS.uf.SP.temperatura.data) || fTemp.consultado_em;
  if (diaPrev) põe('tituloTemperatura', 'Temperatura máxima prevista nas capitais, ' + String(diaPrev).slice(0, 10));
  põe('temperaturaSub', (diaPrev ? 'Para ' + diaMes(diaPrev) + ' · ' : '') + 'diferença para a normal 1991–2020 do mês · uma capital por estado');

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
const seca = uf => (SINAIS.uf[uf] || {}).secas;
// 16/10/2026 (HANDOVER_MONITOR_DE_RISCOS §3.8): as MANCHAS do mapa mensal do Monitor de Secas,
// como a fonte publica, no lugar do estado pintado pela mediana. Estados em branco por baixo (o
// texto do mouse continua dando a distribuição por estado); contorno dos 27 por cima, sempre, e
// hachura onde o boletim prevê seca.
const MANCHAS = ((SECAS_MANCHAS || {}).features || []).filter(f => SECA_COR[(f.properties || {}).categoria]);
desenharMapa('mapaSecas', 'legSecas', () => MANCHAS.length ? ATM.seca.uf : NEUTRA,
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
  MANCHAS.length
    ? [{cor:ATM.seca.uf, rotulo:'Sem seca'}, {cor:SECA_COR.S0, rotulo:'Fraca'},
       {cor:SECA_COR.S1, rotulo:'Moderada'}, {cor:SECA_COR.S2, rotulo:'Grave'},
       {cor:SECA_COR.S3, rotulo:'Extrema'}, {cor:SECA_COR.S4, rotulo:'Excepcional'},
       {cor:ATM.seca.contorno, rotulo:'Seca prevista pelo boletim', hachura:true}]
    : [{cor:NEUTRA, rotulo:'Sem coleta até o corte'}], 'seca');
(function manchasDeSeca(){
  if (!MANCHAS.length) return;
  const ctx = __ctx(), svg = d3.select('#mapaSecas');
  const ordem = ['S0', 'S1', 'S2', 'S3', 'S4'];
  svg.insert('g', 'g.siglas').attr('class', 'manchas').style('pointer-events', 'none')
    .selectAll('path').data(MANCHAS.slice().sort((a, b) => ordem.indexOf(a.properties.categoria) - ordem.indexOf(b.properties.categoria)))
    .join('path').attr('d', ctx.path).attr('fill', f => SECA_COR[f.properties.categoria]).attr('stroke', 'none');
  const HACHURA = MonitorMapas.hachura('mapaSecas', 'transparent', ATM.seca.contorno);
  svg.insert('g', 'g.siglas').attr('class', 'contornos').style('pointer-events', 'none')
    .selectAll('path').data(ctx.geo.features).join('path').attr('d', ctx.path)
    .attr('fill', d => componentesDe(d.properties.sigla).includes('estiagem') ? HACHURA : 'none')
    .attr('fill-opacity', .45).attr('stroke', ATM.seca.contorno).attr('stroke-width', .8);
  const mes = /^(\d{4})-(\d{2})$/.exec(SECAS_MANCHAS.mes || '');
  const MESES = ['janeiro','fevereiro','março','abril','maio','junho','julho','agosto','setembro','outubro','novembro','dezembro'];
  const nomeMes = mes ? MESES[Number(mes[2]) - 1] + ' de ' + mes[1] : '';
  const t = document.getElementById('tituloSecas'); if (t) t.textContent = 'Seca observada' + (nomeMes ? ', ' + nomeMes : '');
  const sub = document.getElementById('secasSub');
  if (sub) sub.textContent = (nomeMes ? nomeMes.charAt(0).toUpperCase() + nomeMes.slice(1) + ' · ' : '')
    + 'manchas do Monitor de Secas · hachura: estados com seca prevista pelo boletim';
  MonitorMapas.credito('boxSecas', {fontes: [SECAS_MANCHAS.fonte || 'Monitor de Secas — ANA', nomeMes ? 'mapa de ' + nomeMes : ''].filter(Boolean),
    url: SECAS_MANCHAS.url_publica, data: SECAS_MANCHAS.consultado_em});
  const d = document.querySelector('#boxSecas .fonte-figura'); if (d) d.dataset.credito = 'monitor_secas';
})();
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
credito('boxTemperatura', 'inmet_previsao_capitais', 'inmet_estacoes');

// ---- Qualidade do ar MEDIDA (16/10/2026, HANDOVER_MONITORAR §5) ----
/* Três fontes, uma unidade: IQAr só onde é oficial (MMA/MonitorAr, calculado pelo órgão, nunca aqui);
   PM2,5 do OpenAQ só para a mesma estação; sensores IPAM/RedeAr como losango vazado, sem índice.
   Círculo = estações oficiais agregadas por cidade; cor = pior faixa da cidade; tamanho = nº de estações. */
const IQAR_FAIXAS = ['Boa', 'Moderada', 'Ruim', 'Muito Ruim', 'Péssima'];
const IQAR_COR = MonitorMapas.PALETA.iqar;
const faixaIqar = e => IQAR_FAIXAS.indexOf(((e.iqar || {}).classificacao || ''));
const hora = v => { const m = /(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/.exec(String(v || ''));
  return m ? m[3] + '/' + m[2] + ' ' + m[4] + ':' + m[5] : ''; };
const cidadesAr = (() => {
  const por = {};
  ((AR || {}).estacoes || []).filter(e => faixaIqar(e) >= 0 && e.lat != null).forEach(e => {
    const k = e.municipio + '|' + e.uf; (por[k] = por[k] || []).push(e); });
  return Object.values(por).map(es => {
    const pior = es.reduce((a, b) => faixaIqar(b) > faixaIqar(a) ? b : a, es[0]);
    return {es, pior, lat: es.reduce((s, e) => s + e.lat, 0) / es.length, lon: es.reduce((s, e) => s + e.lon, 0) / es.length};
  });
})();
const fontesAr = (AR || {}).fontes || {};
const fichaCidade = c => { const e = c.pior, i = e.iqar;
  const pm = c.es.find(x => x.pm25_openaq && x.pm25_openaq.valor != null);
  return MonitorMapas.dica({titulo: e.municipio + ' · ' + e.uf + ' — ' + c.es.length + (c.es.length === 1 ? ' estação' : ' estações'),
    linhas: ['IQAr ' + i.classificacao + ' · ' + n1(Math.round(i.valor)) + (i.poluente ? ' · ' + i.poluente : '') + (hora(i.medido_em) ? ' · ' + hora(i.medido_em) : ''),
      pm ? 'PM2,5: ' + n1(pm.pm25_openaq.valor) + ' µg/m³ · via OpenAQ' : 'PM2,5: não disponível na fonte de concentrações',
      'Rede: ' + e.rede + ' · MMA/MonitorAr']}); };
const fichaSensor = s => MonitorMapas.dica({titulo: s.municipio + ' — ' + s.nome,
  linhas: ['PM2,5: ' + n1(s.pm25.valor) + ' µg/m³' + (s.pm25.pm10 != null ? ' · PM10: ' + n1(s.pm25.pm10) : '') + (hora(s.pm25.lido_em) ? ' · ' + hora(s.pm25.lido_em) : ''),
    'IPAM/RedeAr · sensor ótico, não é estação regulatória e não gera IQAr']});
desenharMapa('mapaAr', 'legAr', () => ATM.ar.uf, uf => MonitorMapas.dica({semTitulo: true,
  linhas: [cidadesAr.filter(c => c.pior.uf === uf).length + ' cidade(s) com estação oficial com IQAr na consulta']}),
  AR ? IQAR_FAIXAS.map((f, k) => ({cor: IQAR_COR[k], rotulo: f})) : [{cor: NEUTRA, rotulo: 'Sem coleta até o corte'}], 'ar');
if (AR) {
  const maxN = Math.max(1, ...cidadesAr.map(c => c.es.length));
  MonitorMapas.pontos(__ctx(), 'mapaAr', cidadesAr.slice().sort((a, b) => faixaIqar(a.pior) - faixaIqar(b.pior)), {
    r: c => 3 + 4 * Math.sqrt(c.es.length / maxN), cor: c => IQAR_COR[faixaIqar(c.pior)], opacidade: .9,
    rotulo: fichaCidade, classe: 'pontosAr'});
  const ctx = __ctx();
  d3.select('#mapaAr').append('g').attr('class', 'sensoresAr').selectAll('path')
    .data((AR.sensores || []).filter(s => s.pm25 && s.pm25.valor != null && s.lat != null)).join('path')
    .attr('d', s => { const [x, y] = ctx.projection([s.lon, s.lat]); return 'M' + x + ' ' + (y - 3.5) + 'l3.5 3.5l-3.5 3.5l-3.5 -3.5z'; })
    .attr('fill', 'none').attr('stroke', ATM.ar.contorno).attr('stroke-width', 1.2)
    .on('mouseenter', (evt, s) => MonitorMapas.showTip(fichaSensor(s), evt)).on('mousemove', (evt, s) => MonitorMapas.showTip(fichaSensor(s), evt))
    .on('mouseleave', MonitorMapas.hideTip);
  const leg = document.getElementById('legAr');
  if (leg) leg.insertAdjacentHTML('beforeend', '<span><i class="leg-losango" style="background:transparent"></i>Sensor de baixo custo (IPAM/RedeAr) · PM2,5 em µg/m³, média de 24 h</span>');
  const sub = document.getElementById('arSub');
  if (sub) sub.textContent = 'IQAr das estações oficiais por cidade (cor: faixa mais alta da cidade; tamanho: nº de estações) · sensores de PM2,5, µg/m³';
}
(function creditoAr(){
  const fm = fontesAr.monitorar || {};
  MonitorMapas.credito('boxAr', {fontes: ['MMA · MonitorAr (IQAr das redes estaduais)', 'concentrações das estações oficiais: OpenAQ',
    'sensores: IPAM/RedeAr'], url: fm.url_publica, data: AR ? (fm.consultado_em || AR.gerado_em) : null});
  const d = document.querySelector('#boxAr .fonte-figura'); if (d) d.dataset.credito = 'monitorar';
})();


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
  // Hachura = estado com fogo previsto pelo boletim (único significado da hachura no site).
  const previstoFogo = uf => componentesDe(uf).includes('incendios');
  const HACHURA_FOGO = MonitorMapas.hachura('mapaFogo', ATM.fogo.uf, ATM.fogo.contorno);
  desenharMapa('mapaFogo', 'legFogo', uf => previstoFogo(uf) ? HACHURA_FOGO : ATM.fogo.uf,
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
    {cor: ATM.fogo.contorno, fundo: ATM.fogo.uf, rotulo: 'Fogo previsto pelo boletim', hachura: true},
  ]);
})();
/* 16/10/2026 (HANDOVER_MONITOR_DE_RISCOS §3.6): ao lado do mapa, os números do satélite de
   referência — dia, mesma data do ano anterior, mês, estados — a série de 30 dias e as tabelas por
   estado e por bioma. Tudo como o INPE publica; nada calculado além de diferença, soma e média. */
(function painelFogo(){
  const R = FOGO_REF && FOGO_REF.resumo;
  const dl = document.getElementById('fogoNumeros');
  if (!R || !R.dia || !dl) { const l = document.getElementById('fogoLado');
    if (l) { l.innerHTML = ''; lacuna('fogoLado', 'Contagens do satélite de referência: sem coleta até o corte.'); } return; }
  const fmt = n => Number(n).toLocaleString('pt-BR');
  const sinal = n => (n > 0 ? '+' : n < 0 ? '−' : '') + fmt(Math.abs(n));
  const dia = R.ultimo_dia, serie = FOGO_REF.serie || {};
  const dias = Object.keys(serie).sort(), iDia = dias.indexOf(dia);
  const ontem = iDia > 0 ? serie[dias[iDia - 1]] : null;
  const ontemOk = ontem && dias[iDia - 1] === new Date(Date.parse(dia + 'T12:00:00Z') - 864e5).toISOString().slice(0, 10);
  const dBR = MonitorMapas.dataBR;
  const nUfs = Object.keys(R.dia.uf || {}).filter(uf => R.dia.uf[uf] > 0).length;
  const ano = R.mesmo_dia_ano_anterior;
  const itens = [
    ['Focos em ' + dBR(dia), fmt(R.dia.total),
     ontemOk ? sinal(R.dia.total - ontem.total) + ' em relação ao dia anterior' : 'dia anterior sem arquivo'],
    ['Mesma data em ' + (ano ? ano.dia.slice(0, 4) : 'ano anterior'), ano ? fmt(ano.total) : 'sem arquivo',
     ano && ano.total ? sinal(Math.round((R.dia.total - ano.total) / ano.total * 100)) + '% em relação a ' + ano.dia.slice(0, 4) : ''],
    ['Acumulado do mês', R.mes ? fmt(R.mes.total) : 'sem arquivo',
     R.mes && R.mes.dias_com_dado ? 'média de ' + fmt(Math.round(R.mes.total / R.mes.dias_com_dado)) + ' por dia em '
       + R.mes.dias_com_dado + ' dias' : ''],
    ['Estados com foco', fmt(nUfs), (27 - nUfs) + ' sem foco no dia'],
  ];
  dl.innerHTML = itens.map(([k, v, a]) => '<div><dt>' + esc(k) + '</dt><dd>' + esc(v) + '</dd>'
    + (a ? '<dd class="lado-var">' + esc(a) + '</dd>' : '') + '</div>').join('');

  // Série de 30 dias: linha simples, sem eixo Y numerado, datas nas pontas.
  const pd = (R.ultimos_30_dias || {}).por_dia || [];
  const alvo = document.getElementById('fogoSerie');
  if (alvo && pd.length > 1) {
    const W = 480, H = 72, max = Math.max(...pd.map(p => p[1])) || 1;
    const x = i => 4 + i * (W - 8) / (pd.length - 1), y = v => H - 18 - v / max * (H - 26);
    const pts = pd.map((p, i) => x(i).toFixed(1) + ',' + y(p[1]).toFixed(1)).join(' ');
    alvo.innerHTML = '<svg viewBox="0 0 ' + W + ' ' + H + '" role="img" aria-label="Focos por dia de '
      + esc(dBR(pd[0][0])) + ' a ' + esc(dBR(pd[pd.length - 1][0])) + '"><polyline class="serie-linha" points="' + pts + '"/>'
      + pd.map((p, i) => '<circle class="serie-alvo" r="5" cx="' + x(i).toFixed(1) + '" cy="' + y(p[1]).toFixed(1)
        + '"><title>' + esc(dBR(p[0]) + ': ' + fmt(p[1]) + ' focos') + '</title></circle>').join('')
      + '<text class="tk" x="4" y="' + (H - 2) + '">' + esc(dBR(pd[0][0]).slice(0, 5)) + '</text>'
      + '<text class="tk" x="' + (W - 4) + '" y="' + (H - 2) + '" text-anchor="end">' + esc(dBR(pd[pd.length - 1][0]).slice(0, 5)) + '</text></svg>';
  }

  // Por estado: os seis com mais focos no dia (fato do dia), com dia anterior, mês e previsão.
  const mesDe = uf => dias.filter(d => d.slice(0, 7) === dia.slice(0, 7))
    .reduce((s, d) => s + (((serie[d] || {}).uf || {})[uf] || 0), 0);
  const corpo = document.querySelector('#tblFogo tbody');
  if (corpo) corpo.innerHTML = Object.entries(R.dia.uf || {}).sort((a, b) => b[1] - a[1]).slice(0, 6)
    .map(([uf, n]) => '<tr><td>' + esc(uf) + '</td> <td>' + esc(fmt(n)) + '</td> <td>'
      + esc(ontemOk ? fmt(((ontem.uf || {})[uf]) || 0) : '—') + '</td> <td>' + esc(fmt(mesDe(uf)))
      + '</td> <td>' + (componentesDe(uf).includes('incendios') ? 'sim' : 'não') + '</td></tr>').join('');
  const bio = document.querySelector('#tblFogoBioma tbody');
  if (bio) bio.innerHTML = Object.entries(R.dia.bioma || {}).sort((a, b) => b[1] - a[1])
    .map(([b, n]) => '<tr><td>' + esc(b) + '</td> <td>' + esc(fmt(n)) + '</td> <td>'
      + esc(R.dia.total ? (n / R.dia.total * 100).toLocaleString('pt-BR', {maximumFractionDigits: 1}) : '—') + '</td></tr>').join('');

  const sub = document.getElementById('fogoSub');
  if (sub) sub.textContent = 'Números: ' + dBR(dia) + ', satélite de referência (Aqua, tarde)'
    + (FOCOS && FOCOS.arquivo_de_origem ? ' · pontos: todos os satélites' : '') + ' · hachura: fogo previsto pelo boletim';
})();
(function creditoFogo(){
  const f = FOGO_REF || fonteDe('inpe_fogo');
  MonitorMapas.credito('boxFogo', {fontes: ['INPE · Programa Queimadas' + (FOGO_REF ? ' (BDQueimadas, Aqua M-T)' : '')],
    url: f.url_publica, data: f.consultado_em});
  const d = document.querySelector('#boxFogo .fonte-figura'); if (d) d.dataset.credito = 'inpe_fogo';
})();

// ---- Chuva forte (16/10/2026, HANDOVER_MONITOR_DE_RISCOS §4): duas tabelas, sem mapa por estado ----
/* Avisos do INMET por grau, com os MUNICÍPIOS cobertos (do índice por município do coletor) e os
   alertas do CEMADEN por nível, com os municípios nomeados. Grau e nível no vocabulário do órgão.
   Fonte que não respondeu = lacuna; resposta válida sem aviso tem texto próprio. */
(function chuvaForte(){
  const GRAUS = ['Grande Perigo', 'Perigo', 'Perigo Potencial'];
  const fmt = n => Number(n).toLocaleString('pt-BR');
  const muns = Object.values((AVISOS || {}).municipios || {});
  const lacunaEm = (tbl, midia, txt) => { const c = document.querySelector('#' + tbl);
    if (c) c.closest('.tbl-wrap').remove(); lacuna(midia, txt); };
  const creditoDe = (caixa, chave) => { const f = fonteDe(chave);
    MonitorMapas.credito(caixa, {fontes: [f.orgao, f.nome].filter(Boolean).join(' · '), url: f.url_publica,
      data: AVISOS ? AVISOS.gerado_em : f.consultado_em});
    const d = document.querySelector('#' + caixa + ' .fonte-figura'); if (d) d.dataset.credito = chave; };
  if (!AVISOS || !coletada('inmet_avisos')) {
    lacunaEm('tblAvisos', 'midiaAvisos', 'A fonte não respondeu nesta consulta — não quer dizer que não haja aviso em vigor.');
  } else {
    const linhas = GRAUS.map(g => {
      const com = muns.filter(m => (m.inmet || []).some(x => x.severidade === g));
      const ufs = [...new Set(com.map(m => m.uf))].sort();
      const fen = [...new Set(com.flatMap(m => m.inmet.filter(x => x.severidade === g).map(x => x.tipo)))].sort();
      return [g, com.length, ufs, fen];
    });
    const comAviso = muns.filter(m => (m.inmet || []).length).length, total = (window.__refMunicipios || []).length;
    document.querySelector('#tblAvisos tbody').innerHTML = linhas.map(([g, n, ufs, fen]) => '<tr><td>' + esc(g) + '</td> <td>'
        + esc(fmt(n)) + '</td> <td>' + esc(ufs.join(', ') || '—') + '</td> <td>' + esc(fen.join(', ') || '—') + '</td></tr>').join('')
      + (total ? '<tr><td>Sem aviso</td><td>' + esc(fmt(total - comAviso)) + '</td><td>—</td><td>—</td></tr>' : '');
    const previstos = UFS.filter(uf => componentesDe(uf).includes('chuvas'));
    const ufsComAviso = new Set(muns.filter(m => (m.inmet || []).length).map(m => m.uf));
    const nAvisos = new Set(muns.flatMap(m => (m.inmet || []).map(x => x.id))).size;
    document.getElementById('avisosRodape').textContent = plural(nAvisos, 'aviso', 'avisos') + ' · '
      + plural(comAviso, 'município', 'municípios') + ' · nos estados com chuva forte prevista: '
      + (previstos.filter(uf => ufsComAviso.has(uf)).join(', ') || 'nenhum com aviso');
  }
  creditoDe('boxAvisos', 'inmet_avisos');
  if (!AVISOS || !coletada('cemaden_alertas')) {
    lacunaEm('tblCemaden', 'midiaCemaden', 'A fonte não respondeu nesta consulta — não quer dizer que não haja alerta vigente.');
  } else {
    const grupos = {};
    muns.forEach(m => (m.cemaden || []).forEach(x => { const k = x.nivel + '|' + m.uf;
      (grupos[k] = grupos[k] || new Set()).add(m.nome); }));
    const chaves = Object.keys(grupos).sort();
    document.querySelector('#tblCemaden tbody').innerHTML = chaves.length
      ? chaves.map(k => { const [nv, uf] = k.split('|'); return '<tr><td>' + esc(nv) + '</td> <td>' + esc(uf) + '</td> <td>'
          + esc([...grupos[k]].sort().join(', ')) + '</td></tr>'; }).join('')
      : '<tr><td colspan="3">Nenhum alerta vigente nesta consulta</td></tr>';
    const r = AVISOS.resumo || {};
    document.getElementById('cemadenRodape').textContent = plural(r.alertas_cemaden_em_vigor || 0, 'alerta', 'alertas')
      + ' · ' + plural(r.municipios_cemaden || 0, 'município', 'municípios') + ' · '
      + plural(new Set(chaves.map(k => k.split('|')[1])).size, 'estado', 'estados');
  }
  creditoDe('boxCemaden', 'cemaden_alertas');
  const t = document.getElementById('tituloAvisos'); if (t && AVISOS) t.textContent = 'Avisos de tempo severo em vigor, ' + AVISOS.gerado_em;
})();

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
    MonitorMapas.credito('stRoniFonte', {fontes: [f.orgao], data: f.consultado_em});
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
    MonitorMapas.credito('stDuracaoFonte', {fontes: [f.orgao], data: f.consultado_em});
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

  // 5 a 8 — os números de agora no Brasil (16/10/2026, lote 2 da editoria), do mesmo dado dos
  // mapas abaixo. Só descrição: valor, data e órgão. Variação só com leitura anterior gravada —
  // fogo, seca, calor e avisos ainda não a gravam, e o cartão não a inventa.
  const credito = (id, k) => { const f = fonte(k); MonitorMapas.credito(id, {fontes: [f.orgao], data: f.consultado_em}); };
  const porUf = campo => UFS.map(uf => [uf, (SINAIS.uf[uf] || {})[campo]]).filter(([, v]) => v);

  const fogos = porUf('fogo').filter(([, v]) => typeof v.focos_24h === 'number');
  if (fogos.length) {
    const total = fogos.reduce((a, [, v]) => a + v.focos_24h, 0);
    const [ufMax, vMax] = fogos.reduce((a, b) => b[1].focos_24h > a[1].focos_24h ? b : a);
    põeCat('stFogoValor', I + 'fogo.molde_valor', {n: total});
    if (vMax.focos_24h > 0) põeCat('stFogoApoio', I + 'fogo.molde_apoio', {uf: ufMax, n: vMax.focos_24h});
    credito('stFogoFonte', 'inpe_fogo');
  }

  const secas = porUf('secas').filter(([, v]) => v.categoria_mediana);
  if (secas.length) {
    const graves = secas.filter(([, v]) => ['S2', 'S3', 'S4'].includes(v.categoria_mediana)).length;
    const mapa = secas.map(([, v]) => v.mapa).find(Boolean);
    if (mapa) põeCat('stSecaRotulo', I + 'seca.molde_rotulo', {mapa: String(mapa).toLowerCase()});
    põeCat('stSecaValor', I + 'seca.molde_valor', {n: graves});
    credito('stSecaFonte', 'monitor_secas');
  }

  const desvios = UFS.map(uf => [uf, desvioDe(uf)]).filter(([, v]) => v != null);
  if (desvios.length) {
    const [uf, dv] = desvios.reduce((a, b) => b[1] > a[1] ? b : a);
    const t = temp(uf) || {};
    põeCat('stCalorRotulo', I + 'calor.molde_rotulo', {data: diaMes(t.data)});
    põeCat('stCalorValor', I + 'calor.molde_valor', {valor: (dv > 0 ? '+' : '') + n1(dv)});
    põeCat('stCalorApoio', I + 'calor.molde_apoio', {capital: t.capital || uf, tmax: n1(t.tmax), normal: n1(normalDe(uf))});
    credito('stCalorFonte', 'inmet_previsao_capitais');
  }

  if ((fonte('inmet_avisos').status || '') === 'coletado') {
    const avisos = porUf('avisos_inmet');
    const comAviso = avisos.filter(([, a]) => Number(a.total || 0) > 0);
    const perigo = comAviso.filter(([, a]) => Object.keys(a.graus || {}).some(g => /perigo/i.test(g) && !/potencial/i.test(g)));
    põeCat('stAvisosValor', I + 'avisos.molde_valor', {n: comAviso.length});
    põeCat('stAvisosApoio', I + 'avisos.molde_apoio', {m: perigo.length});
    credito('stAvisosFonte', 'inmet_avisos');
  }

  // Cartão "Ar" (HANDOVER_TEXTOS_B §10.3.6): só existe quando há cidade com IQAr Ruim ou pior no MMA.
  const ruins = cidadesAr.filter(c => faixaIqar(c.pior) >= 2);
  const grade = document.getElementById('situacaoGrade');
  if (ruins.length && grade) {
    const ult = ruins.map(c => c.pior.iqar.medido_em).sort().pop();
    grade.insertAdjacentHTML('beforeend', '<div class="cartao-numero cartao-numero--risco_agora" data-cartao="ar_iqar_ruim">'
      + '<p class="cartao-numero-rotulo">Cidades com IQAr Ruim, Muito Ruim ou Péssima' + (hora(ult) ? ', ' + esc(hora(ult)) : '') + '</p>'
      + '<p class="cartao-numero-valor">' + esc(String(ruins.length)) + '</p>'
      + '<p class="cartao-numero-variacao">primeira leitura</p><p class="cartao-numero-fonte" id="stArFonte"></p></div>');
    MonitorMapas.credito('stArFonte', {fontes: ['MMA/MonitorAr'], data: (fontesAr.monitorar || {}).consultado_em});
  }
})();

// 13/09/2026: cartoesCiclo/cartaoCiclo1-4 removidos — três dos quatro cartões duplicavam valores já
// no painel Situação Atual (ONI, Probabilidade, Prognóstico/Boletim nº 3); só 'Boletim mais recente
// do ciclo' trazia informação nova (o nome do documento), agora em stDocumento acima, com a citação
// combinada das três fontes substituindo os quatro créditos individuais.

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
const RONI_MIN = -2.0, RONI_MAX = 2.5;
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
  // 16/10/2026 (editoria): na largura inteira, metade da altura de antes; no celular, a de antes.
  const H = (estreito ? 260 : 200) + (baixo || 0);
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
  // O título traz os anos DO DADO: quando a série passar a começar em 1950, ele diz 1950 sozinho.
  // ANO É RÓTULO, NÃO QUANTIDADE: o catálogo formata número em pt-BR, e `2026` chegaria à tela
  // como "2.026". Tudo o que é ano entra no molde já como texto.
  const anos = {inicio: String(primeiro.ano), fim: String(ultimo.ano)};
  // ---- O gráfico: o ciclo em curso e os episódios que o dado define ----
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
        .map(l => '<tr><td>' + esc(l.rotulo) + '</td> <td>' + esc(PAC.num(l.pico.p.anomalia)) + ' °C</td><td>'
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
  lacuna('wrapEpisodios', txtCat(IP + 'episodios.lacuna', null, 'Sem coleta até o corte.'));
}
creditoPacifico('boxEpisodios');

// O gráfico de estados por tipo de risco (#cTipos) saiu da página em 27/09/2026 com o risco projetado;
// a montagem que sobrou aqui mirava um canvas inexistente e foi retirada (A4-21, 10/10/2026).
// 15/09/2026: a contagem por família mora na figura dupla boxTipoRisco (mapa + gráfico, uma legenda) — o crédito é o da figura.
// 17/09/2026: o cruzamento "tipo de risco × estágio" (que morava na home, #cCruz) saiu do site — pedido da editoria.

}
__load();

// ===== monitor-de-riscos.html · bloco 2 (extraído em 06/09/2026, CSP sem unsafe-inline) =====
window.addEventListener('load', function(){ if (window.VLibras && window.VLibras.Widget) { try { new window.VLibras.Widget('https://vlibras.gov.br/app'); } catch (e) {} } });

