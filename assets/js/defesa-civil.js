/* ===== defesa-civil.html · alertas e emergências =========================================
 *
 * A página foi refeita em 01/10/2026 por decisão da editoria: ela é só sobre **alertas** e
 * **emergências**. O que saiu e para onde foi:
 *
 *   - os dois mapas de PREPARAÇÃO (verificação municipal com seletor de 12 categorias; cobertura
 *     e natureza dos atos por UF) — o plano mora no MARÉ Legal, na página inicial, e mostrá-lo
 *     aqui era a mesma pergunta respondida duas vezes, com duas réguas;
 *   - todo o material de AUDITORIA (log de verificação e cobertura, log por estado/canal/nível,
 *     a parede de fontes e registros, a tabela dos municípios verificados um a um, o painel
 *     amostral) — vai para `dados-abertos/` e para a METODOLOGIA, que é onde pesquisador procura.
 *     Nada foi apagado do repositório: deixou de ter página própria.
 *
 * Duas decisões de dado que mudam o que o leitor vê, e por quê:
 *
 *   (1) **O mapa principal de alerta é o do CEMADEN.** O aviso do INMET é emitido por ÁREA, não
 *       por município: 3.479 municípios sob aviso contra 17 sob alerta, na consulta de 30/09.
 *       Desenhados juntos, o Cemaden desaparece sob o Inmet e o mapa do país fica uniforme — um
 *       mapa que não distingue nada. O Inmet continua no contador do topo e no gráfico por tipo,
 *       onde a informação é a CONTAGEM e a geografia não acrescenta.
 *   (2) **O cadastro é o da Casa Civil, nominal.** O mapa usava `municipios_prioritarios.json`,
 *       que era uma APROXIMAÇÃO POPULACIONAL — para cada UF, os N municípios mais populosos, com
 *       N vindo da contagem pública. Agora usa `cadastro_prioritarios_federal.json`, a lista nome
 *       a nome dos 2.095 do cadastro federal de municípios suscetíveis a enxurradas e inundações
 *       (SEPAC/Casa Civil, Decreto 12.444/2025). O nome "Cadastro Nacional" sai da página: aquele
 *       é outro cadastro, o do art. 3º-A da Lei 12.340, de inscrição voluntária, que inclui
 *       deslizamento e não tem fonte pública — confundir os dois era afirmar dever que esta lista
 *       não cria.
 *
 * Todo cartão de mapa traz "Ver em lista" com busca por município: o mapa responde "onde", a
 * lista responde "e a minha cidade?", que é a pergunta que traz a pessoa aqui.
 */
let BR_GEOJSON, MAP_POINTS, RESP, DECRETADOS, ALERTAS, SINAIS, CADASTRO,
    MUN_COD = {}, LATLON_POR_CODIGO = {};

async function __load(){
  try {
    const m = (await fetch('data/meta.json').then(r => r.ok ? r.json() : null)) || {};
    window.__metaCorte = m.corte; window.__metaAtualizado = m.atualizado_em || m.corte;
  } catch (e) {}
  let ref;
  [BR_GEOJSON, MAP_POINTS, ref] = await Promise.all(
    ['geo_uf', 'pontos_mapa', 'municipios_ibge_referencia']
      .map(f => fetch('data/' + f + '.json').then(r => {
        if (!r.ok) throw new Error('Falha ao carregar data/' + f + '.json');
        return r.json();
      }))
  );
  /* Os quatro opcionais não derrubam a página: cada seção que depende deles DECLARA a lacuna.
     Zero município sob alerta e arquivo ausente são coisas diferentes, e a página não pode fazer
     uma passar pela outra (regra editorial da ausência declarada). */
  [RESP, DECRETADOS, ALERTAS, SINAIS, CADASTRO] = await Promise.all(
    ['data/resposta/por_uf.json', 'data/resposta/municipios_decretados.json',
     'data/alertas/vigentes.json', 'data/sinais_risco.json',
     'data/cadastro_prioritarios_federal.json']
      .map(f => fetch(f).then(r => r.ok ? r.json() : null).catch(() => null))
  );
  /* Coordenada e nome pelo CÓDIGO IBGE, nunca pelo nome: o arquivo de alertas é indexado por
     código, e as fontes escrevem o nome de formas diferentes (o Cemaden sempre em caixa alta, o
     Inmet às vezes). Casar por nome já deixou os municípios do Cemaden fora do mapa em silêncio. */
  ref.forEach(m => {
    const c = String(m.codigo_ibge).padStart(7, '0');
    MUN_COD[m.uf + '|' + m.nome] = c;
    LATLON_POR_CODIGO[c] = [m.lon, m.lat];
  });
  __init();
}

// =========================================================
// Lista buscável — o mesmo componente em todos os cartões
// =========================================================
/* Uma função e não cinco blocos de HTML: os cinco cartões fazem a mesma promessa ao leitor
   ("digite a sua cidade"), e cinco cópias divergem na primeira correção. O campo tem rótulo
   VISÍVEL (não `sr-only`: quem vê a lista precisa saber o que o campo faz) e a contagem do
   resultado é anunciada por leitor de tela, porque filtrar sem anunciar deixa quem não vê a
   tabela sem saber que algo mudou. */
let __seqBusca = 0;
function listaBuscavel(figuraId, opts){
  const alvo = document.querySelector('#' + figuraId + ' [data-busca]');
  if (!alvo) return;
  const esc = MonitorMapas.esc;
  const id = 'busca' + (++__seqBusca);
  const linhas = opts.linhas || [];
  const cols = opts.colunas;

  alvo.insertAdjacentHTML('afterbegin',
    '<details class="cartao-mapa-dados"><summary>Ver em lista</summary>'
    + '<div class="busca-mun">'
    + '<label for="' + id + '">' + esc(opts.rotulo || 'Buscar município') + '</label>'
    + '<input id="' + id + '" type="search" autocomplete="off" spellcheck="false" '
    + 'placeholder="Digite o nome da cidade ou a sigla do estado">'
    + '<p class="busca-mun-conta" role="status" aria-live="polite"></p>'
    + '</div>'
    + '<div class="tbl-wrap" tabindex="0" role="region" aria-label="Tabela rolável horizontalmente">'
    + '<table class="mun-table"><thead><tr>'
    + cols.map(c => '<th>' + esc(c) + '</th>').join('')
    + '</tr></thead><tbody></tbody></table></div></details>');

  const corpo = alvo.querySelector('tbody');
  const campo = alvo.querySelector('#' + id);
  const conta = alvo.querySelector('.busca-mun-conta');
  /* O teto existe porque o cadastro tem 2.095 linhas e os decretos 902: montar tudo de uma vez
     custa segundos no celular. Quem digita vê a sua cidade; quem não digita vê o começo da lista
     e a contagem diz quantas existem — teto silencioso seria dizer que a lista é menor. */
  const TETO = 200;

  function pinta(){
    const q = (campo.value || '').trim().toLowerCase();
    const achadas = q ? linhas.filter(l => (l.busca || '').toLowerCase().indexOf(q) >= 0) : linhas;
    corpo.innerHTML = achadas.slice(0, TETO).map(l =>
      '<tr>' + l.celulas.map(c => '<td>' + c + '</td>').join('') + '</tr>').join('')
      || '<tr><td colspan="' + cols.length + '">nenhum município encontrado com esse texto</td></tr>';
    const unidade = opts.unidade || 'município';
    conta.textContent = achadas.length === 1
      ? '1 ' + unidade + (q ? ' encontrado' : '')
      : achadas.length.toLocaleString('pt-BR') + ' ' + unidade + 's'
        + (q ? ' encontrados' : '')
        + (achadas.length > TETO ? ' · mostrando os ' + TETO + ' primeiros; refine a busca' : '');
  }
  campo.addEventListener('input', pinta);
  pinta();
}

function __init(){
  MonitorMapas.padraoGraficos(window.Chart);
  const esc = MonitorMapas.esc;
  const showTip = MonitorMapas.showTip, hideTip = MonitorMapas.hideTip;
  const n = v => Number(v || 0).toLocaleString('pt-BR');
  const projection = d3.geoMercator().fitSize([480, 460], BR_GEOJSON);
  const pathGen = d3.geoPath().projection(projection);
  const CINZA = MonitorMapas.cor('zebra');
  const addSiglas = svg => MonitorMapas.siglas(MonitorMapas.contexto(BR_GEOJSON, 480, 460), svg);
  const texto = (id, v) => { const e = document.getElementById(id); if (e) e.textContent = v; };

  /* Crédito de figura de SINAL: nome, endereço e data saem do catálogo de `sinais_risco.json`,
     não de texto escrito aqui — é o que mantém a proveniência igual em todas as páginas, e o que
     `verificar_sinais.py` confere. */
  function creditoSinal(caixaId, chaves, data){
    const fontes = (SINAIS && SINAIS.fontes) || {};
    MonitorMapas.credito(caixaId, {
      fontes: chaves.map(k => (fontes[k] || {}).nome || k),
      url: (fontes[chaves[0]] || {}).url_publica, data: data,
    });
    const d = document.querySelector('#' + caixaId + ' .fonte-figura');
    if (d) d.dataset.credito = chaves.join(' ');
  }
  function fundo(svg){
    svg.append('g').selectAll('path').data(BR_GEOJSON.features).join('path')
      .attr('d', pathGen).attr('fill', CINZA).attr('class', 'uf-path')
      .on('mouseenter', (evt, d) => showTip('<strong>' + esc(d.properties.name) + '</strong>', evt))
      .on('mousemove', (evt) => showTip(tooltip.innerHTML, evt))
      .on('mouseleave', hideTip);
    return svg;
  }

  // =========================================================
  // 1. Alertas e avisos em vigor
  // =========================================================
  const muns = (ALERTAS && ALERTAS.municipios) || null;
  const rAl = (ALERTAS && ALERTAS.resumo) || {};
  const carimbo = ALERTAS && ALERTAS.gerado_em;
  const GRAU = MonitorMapas.PALETA.grauAviso;
  const COR_CEMADEN = GRAU.cemaden;
  const corDoGrau = g => GRAU[g] || GRAU.outro;

  const lista = muns ? Object.entries(muns).map(([cod, v]) => ({
    cod: cod, nome: v.nome, uf: v.uf, inmet: v.inmet || [], cemaden: v.cemaden || [],
    ll: LATLON_POR_CODIGO[cod],
  })) : [];
  const comCemaden = lista.filter(m => m.cemaden.length);

  texto('linhaAlertas', carimbo ? 'Consulta de ' + carimbo : 'Sem consulta até o corte');
  texto('linhaAlertasTipo', carimbo ? 'Consulta de ' + carimbo : 'Sem consulta até o corte');

  if (!muns){
    texto('alertasResumo', 'Alertas do Cemaden e avisos do Inmet: sem coleta até o corte.');
    ['legAlertas', 'legAlertasTipo'].forEach(id =>
      MonitorMapas.legenda(id, [{cor: MonitorMapas.cor('sem-dado'), rotulo: 'sem coleta até o corte'}]));
    ['boxAlertas', 'boxAlertasTipo'].forEach(id => creditoSinal(id, ['cemaden_alertas', 'inmet_avisos'], null));
  } else {
    const svgA = fundo(d3.select('#mapAlertas'));
    const semCoord = comCemaden.filter(m => !m.ll).length;
    svgA.append('g').selectAll('circle').data(comCemaden.filter(m => m.ll)).join('circle')
      .attr('cx', m => projection(m.ll)[0]).attr('cy', m => projection(m.ll)[1])
      .attr('r', 5).attr('fill', COR_CEMADEN)
      .attr('stroke', MonitorMapas.cor('branco')).attr('stroke-width', 1.4)
      .on('mouseenter', (evt, m) => showTip(
        '<strong>' + esc(m.nome) + ' (' + esc(m.uf) + ')</strong>'
        + m.cemaden.map(a => '<br>Cemaden · ' + esc(a.tipo || 'tipo não declarado') + ' · ' + esc(a.nivel)
            + (a.desde ? ' · desde ' + esc(a.desde) : '')).join(''), evt))
      .on('mousemove', (evt) => showTip(tooltip.innerHTML, evt))
      .on('mouseleave', hideTip);
    addSiglas(svgA);

    const niveis = [...new Set(comCemaden.reduce((ac, m) => ac.concat(m.cemaden.map(a => a.nivel)), []))].filter(Boolean);
    MonitorMapas.legenda('legAlertas',
      (niveis.length ? niveis.map(x => ({cor: COR_CEMADEN, rotulo: 'Cemaden · ' + x}))
                     : [{cor: COR_CEMADEN, rotulo: 'Cemaden · alerta em vigor'}])
      .concat([{cor: CINZA, rotulo: 'sem alerta do Cemaden em vigor'}])
      .concat(semCoord ? [{cor: MonitorMapas.cor('sem-dado'), rotulo: 'sem coordenada (' + semCoord + ')'}] : []));
    creditoSinal('boxAlertas', ['cemaden_alertas'], carimbo);

    texto('alertasResumo',
      n(rAl.municipios_cemaden) + ' município(s) sob alerta do Cemaden e ' + n(rAl.municipios_inmet)
      + ' sob aviso do Inmet, na consulta de ' + (carimbo || '—') + '. O aviso do Inmet é emitido por '
      + 'área, não por município; o mapa mostra o alerta do Cemaden.');

    listaBuscavel('boxAlertas', {
      colunas: ['Município', 'UF', 'Alerta do Cemaden', 'Aviso do Inmet'],
      rotulo: 'Buscar município sob alerta ou aviso',
      linhas: lista.sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR')).map(m => ({
        busca: m.nome + ' ' + m.uf,
        celulas: ['<strong>' + esc(m.nome) + '</strong>', esc(m.uf),
          m.cemaden.map(a => esc((a.tipo || 'tipo não declarado') + ' · ' + a.nivel)).join('<br>') || '—',
          m.inmet.map(a => esc(a.tipo + ' · ' + a.severidade)).join('<br>') || '—'],
      })),
    });

    // ---- gráfico por tipo (um município sob dois tipos conta nos dois) ----
    const porTipo = {};
    lista.forEach(m => {
      new Set(m.inmet.map(a => 'Inmet · ' + a.tipo)).forEach(t => porTipo[t] = (porTipo[t] || 0) + 1);
      new Set(m.cemaden.map(a => 'Cemaden · ' + (a.tipo || 'tipo não declarado'))).forEach(t => porTipo[t] = (porTipo[t] || 0) + 1);
    });
    const tipos = Object.entries(porTipo).sort((a, b) => b[1] - a[1]);
    const cv = document.getElementById('cAlertasTipo');
    if (cv && window.Chart && tipos.length){
      new Chart(cv, {type: 'bar',
        data: {labels: tipos.map(t => t[0]),
               datasets: [{data: tipos.map(t => t[1]), backgroundColor: MonitorMapas.PALETA.faixas.construcao}]},
        options: {indexAxis: 'y', plugins: {legend: {display: false}}, scales: {x: {beginAtZero: true}}}});
    }
    MonitorMapas.legenda('legAlertasTipo', [{cor: MonitorMapas.PALETA.faixas.construcao, rotulo: 'municípios sob o tipo'}]);
    creditoSinal('boxAlertasTipo', ['inmet_avisos', 'cemaden_alertas'], carimbo);
    listaBuscavel('boxAlertasTipo', {
      colunas: ['Tipo em vigor', 'Municípios'], rotulo: 'Buscar tipo de aviso ou alerta', unidade: 'tipo',
      linhas: tipos.map(t => ({busca: t[0], celulas: [esc(t[0]), n(t[1])]})),
    });
  }

  // =========================================================
  // 2. Emergências no ciclo
  // =========================================================
  /* UMA fonte para os três mapas e para os três contadores: `data/resposta/municipios_decretados.json`,
     que é o arquivo que `gerar_resposta.py` consolida e do qual sai o número publicado em
     `resposta/por_uf.json`.

     Isto foi defeito medido, não precaução. A primeira versão desta página montava o conjunto aqui,
     unindo os registros `decreto` de `municipios.json` aos eventos de `atos_resposta.json` e casando
     por NOME: dava 770 municípios, enquanto o contador do topo, lendo o arquivo consolidado, dizia
     734. Dois números para a mesma pergunta na mesma página — exatamente o que a regra 0 da página de
     imprensa existe para barrar. O consolidado casa por CÓDIGO IBGE e é quem decide; recontar aqui
     seria manter uma segunda definição de "município que decretou". */
  const decretados = DECRETADOS && DECRETADOS.municipios
    ? Object.values(DECRETADOS.municipios).filter(m => m.decreto).map(m => {
        const ll = LATLON_POR_CODIGO[m.ibge];
        const f = (m.fontes || [])[0] || {};
        return {cod: m.ibge, nome: m.nome, uf: m.uf, ll: ll,
                data: m.primeiro_decreto, tipos: m.tipos || [], eventos: m.n_eventos || 1,
                reconhecida: !!m.reconhecido, documento: f.decreto || null, url: f.url || null};
      })
    : [];
  const reconhecidos = decretados.filter(m => m.reconhecida);
  const semReconhecimento = decretados.length - reconhecidos.length;
  const semCoordDec = decretados.filter(m => !m.ll).length;
  const carimboCiclo = (DECRETADOS && DECRETADOS.gerado_em) || window.__metaAtualizado || null;
  /* Tipo no vocabulário do arquivo, traduzido para o do leitor sem acrescentar juízo: o arquivo
     distingue o decreto do município do reconhecimento federal, e são coisas diferentes. */
  const TIPO_ROTULO = {decreto_municipal: 'decreto do município',
                       decreto_estadual: 'decreto estadual',
                       reconhecimento_federal: 'reconhecimento federal',
                       em_classificacao: 'em classificação'};
  const tipoTexto = m => (m.tipos.map(t => TIPO_ROTULO[t] || t).join(', ') || '—');

  function pontos(svgSel, dados, raio, aoEntrar){
    const svg = fundo(d3.select(svgSel));
    svg.append('g').selectAll('circle').data(dados.filter(m => m.ll)).join('circle')
      .attr('cx', m => projection(m.ll)[0]).attr('cy', m => projection(m.ll)[1])
      .attr('r', raio).attr('fill', MonitorMapas.PALETA.resposta)
      .attr('stroke', MonitorMapas.cor('branco')).attr('stroke-width', 1.4)
      .on('mouseenter', (evt, m) => showTip(aoEntrar(m), evt))
      .on('mousemove', (evt) => showTip(tooltip.innerHTML, evt))
      .on('mouseleave', hideTip);
    addSiglas(svg);
    return svg;
  }
  const semCoordItem = q => q ? [{cor: MonitorMapas.cor('sem-dado'), rotulo: 'sem coordenada (' + q + ')'}] : [];

  // ---- 2a. quem decretou ----
  texto('linhaAtos', carimboCiclo ? 'Registro de ' + carimboCiclo : 'Sem registro até o corte');
  pontos('#mapAtosResposta', decretados, 4, m =>
    '<strong>' + esc(m.nome) + ' (' + esc(m.uf) + ')</strong><br>'
    + (m.eventos > 1 ? m.eventos + ' atos no ciclo' : 'Decreto de emergência')
    + (m.data ? ' · primeiro em ' + esc(m.data) : '')
    + '<br>' + esc(tipoTexto(m)));
  MonitorMapas.legenda('legAtosResposta', [
    {cor: MonitorMapas.PALETA.resposta, rotulo: 'decreto de emergência no ciclo'},
    {cor: CINZA, rotulo: 'demais municípios'}].concat(semCoordItem(semCoordDec)));
  MonitorMapas.credito('boxAtosResposta', {fontes: ['DOU/SEDEC (S2iD)', 'diários oficiais'], data: window.__metaAtualizado});
  listaBuscavel('boxAtosResposta', {
    colunas: ['Município', 'UF', 'Primeiro decreto', 'Tipo', 'Documento'],
    rotulo: 'Buscar município que decretou emergência',
    linhas: decretados.slice().sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR')).map(m => ({
      busca: m.nome + ' ' + m.uf,
      celulas: ['<strong>' + esc(m.nome) + '</strong>', esc(m.uf), esc(m.data || '—'), esc(tipoTexto(m)),
        m.url ? '<a href="' + esc(m.url) + '" target="_blank" rel="noopener">' + esc(m.documento || 'documento') + '</a>'
              : esc(m.documento || '—')],
    })),
  });

  // ---- 2b. decreto no ciclo × alerta agora ----
  texto('linhaCruzamento', carimbo ? 'Consulta de ' + carimbo : 'Sem consulta até o corte');
  const codsAlerta = new Set(muns ? Object.keys(muns) : []);
  const cruzados = decretados.filter(m => codsAlerta.has(m.cod));
  pontos('#mapAlertaDecreto', cruzados, 4.5, m => {
    const v = (muns && muns[m.cod]) || {inmet: [], cemaden: []};
    return '<strong>' + esc(m.nome) + ' (' + esc(m.uf) + ')</strong><br>'
      + (m.eventos > 1 ? m.eventos + ' atos no ciclo' : 'Decreto de emergência')
      + (m.data ? ' · primeiro em ' + esc(m.data) : '')
      + (v.cemaden || []).map(a => '<br>Cemaden · ' + esc(a.tipo || 'tipo não declarado') + ' · ' + esc(a.nivel)).join('')
      + (v.inmet || []).map(a => '<br>Inmet · ' + esc(a.tipo) + ' · ' + esc(a.severidade)).join('');
  });
  MonitorMapas.legenda('legAlertaDecreto', [
    // Rótulo de legenda é nome de categoria, não frase: até 40 caracteres (portão de
    // harmonização). A contagem vive no cartão do topo e no texto do mouse.
    {cor: MonitorMapas.PALETA.resposta, rotulo: 'decreto no ciclo e alerta agora'},
    {cor: CINZA, rotulo: 'demais municípios'}]
    .concat(semCoordItem(cruzados.filter(m => !m.ll).length)));
  creditoSinal('boxAlertaDecreto', ['cemaden_alertas', 'inmet_avisos'], carimbo);
  listaBuscavel('boxAlertaDecreto', {
    colunas: ['Município', 'UF', 'Primeiro decreto', 'Em vigor agora'],
    rotulo: 'Buscar município com decreto e alerta',
    linhas: cruzados.slice().sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR')).map(m => {
      const v = (muns && muns[m.cod]) || {inmet: [], cemaden: []};
      return {busca: m.nome + ' ' + m.uf,
        celulas: ['<strong>' + esc(m.nome) + '</strong>', esc(m.uf), esc(m.data || '—'),
          (v.cemaden || []).map(a => esc('Cemaden · ' + (a.tipo || 'tipo não declarado') + ' · ' + a.nivel))
            .concat((v.inmet || []).map(a => esc('Inmet · ' + a.tipo + ' · ' + a.severidade))).join('<br>') || '—'],
      };
    }),
  });

  // ---- 2c. reconhecidos pelo governo federal ----
  texto('linhaReconhecidos', carimboCiclo ? 'Registro de ' + carimboCiclo : 'Sem registro até o corte');
  pontos('#mapReconhecidos', reconhecidos, 4, m =>
    '<strong>' + esc(m.nome) + ' (' + esc(m.uf) + ')</strong><br>Emergência reconhecida pelo governo federal'
    + (m.documento ? '<br>' + esc(m.documento) : ''));
  /* A diferença entre decretar e ser reconhecido é o que este mapa distingue, e por isso está na
     legenda. Ausência de portaria até o corte NÃO é pedido negado — a ficha semântica da figura
     declara essa fronteira, e o rótulo aqui diz "sem reconhecimento", não "negado". */
  MonitorMapas.legenda('legReconhecidos', [
    {cor: MonitorMapas.PALETA.resposta, rotulo: 'emergência reconhecida'},
    {cor: CINZA, rotulo: 'sem reconhecimento (' + semReconhecimento + ')'}]
    .concat(semCoordItem(reconhecidos.filter(m => !m.ll).length)));
  MonitorMapas.credito('boxReconhecidos', {fontes: ['Portarias SEDEC/MIDR (DOU)'], data: window.__metaAtualizado});
  listaBuscavel('boxReconhecidos', {
    colunas: ['Município', 'UF', 'Primeiro decreto', 'Documento do reconhecimento'],
    rotulo: 'Buscar município com emergência reconhecida',
    linhas: reconhecidos.slice().sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR')).map(m => ({
      busca: m.nome + ' ' + m.uf,
      celulas: ['<strong>' + esc(m.nome) + '</strong>', esc(m.uf), esc(m.data || '—'),
        m.url ? '<a href="' + esc(m.url) + '" target="_blank" rel="noopener">' + esc(m.documento || 'documento') + '</a>'
              : esc(m.documento || '—')],
    })),
  });

  // =========================================================
  // 3. Cadastro federal de suscetíveis a enxurradas e inundações (Casa Civil)
  // =========================================================
  const svgPrior = fundo(d3.select('#mapPrioritarios'));
  /* As duas cores saem da paleta semântica de categorias: "com instrumento" é a mesma cor de
     `plano` e "sem instrumento" a mesma de `nao_localizado`, nas outras páginas. Hexadecimal ou
     token de cor escolhido aqui criaria uma segunda convenção para a mesma distinção. */
  const COR_COM_PLANO = MonitorMapas.PALETA.categorias.plano;
  const COR_SEM_PLANO = MonitorMapas.PALETA.categorias.nao_localizado;
  const CAT_COM_PLANO = new Set(['plano', 'plano_novo', 'plano_readaptado', 'plano_recorrente',
                                 'plano_antigo', 'plano_elaboracao', 'estrutura', 'coberto_estadual']);
  const comPlano = new Set(MAP_POINTS.filter(p => CAT_COM_PLANO.has(p.categoria))
    .map(p => MUN_COD[p.uf + '|' + p.nome]).filter(Boolean));

  if (!CADASTRO || !CADASTRO.municipios){
    texto('linhaPrioritarios', 'Sem coleta do cadastro até o corte');
    MonitorMapas.legenda('legPrioritarios', [{cor: MonitorMapas.cor('sem-dado'), rotulo: 'sem coleta até o corte'}]);
    MonitorMapas.credito('boxPrioritarios', {fontes: ['SEPAC/Casa Civil'], data: null});
  } else {
    const cad = Object.entries(CADASTRO.municipios).map(([cod, v]) => ({
      cod: cod, nome: v.municipio, uf: v.uf, tipos: v.tipos_de_risco || [],
      ll: LATLON_POR_CODIGO[cod], plano: comPlano.has(cod),
    }));
    const semCoordCad = cad.filter(m => !m.ll).length;
    texto('linhaPrioritarios', 'Cadastro de ' + (CADASTRO.coletado_em || '—').split('-').reverse().join('/')
      + ' · ' + n(cad.length) + ' municípios');
    svgPrior.append('g').selectAll('circle').data(cad.filter(m => m.ll)).join('circle')
      .attr('cx', m => projection(m.ll)[0]).attr('cy', m => projection(m.ll)[1])
      .attr('r', 2.6)
      .attr('fill', m => m.plano ? COR_COM_PLANO : COR_SEM_PLANO)
      .attr('fill-opacity', 0.85)
      .on('mouseenter', (evt, m) => showTip(
        '<strong>' + esc(m.nome) + ' (' + esc(m.uf) + ')</strong><br>'
        + (m.plano ? 'Instrumento localizado pelo MARÉ' : 'Nenhum instrumento localizado até o corte')
        + (m.tipos.length ? '<br>Risco no cadastro: ' + esc(m.tipos.join(', ')) : ''), evt))
      .on('mousemove', (evt) => showTip(tooltip.innerHTML, evt))
      .on('mouseleave', hideTip);
    addSiglas(svgPrior);
    MonitorMapas.legenda('legPrioritarios', [
      {cor: COR_COM_PLANO, rotulo: 'com instrumento localizado (' + n(cad.filter(m => m.plano).length) + ')'},
      {cor: COR_SEM_PLANO, rotulo: 'sem instrumento localizado (' + n(cad.filter(m => !m.plano).length) + ')'}]
      .concat(semCoordCad ? [{cor: MonitorMapas.cor('sem-dado'), rotulo: 'sem coordenada (' + semCoordCad + ')'}] : []));
    MonitorMapas.credito('boxPrioritarios', {
      fontes: ['Cadastro federal de municípios suscetíveis a enxurradas e inundações (SEPAC/Casa Civil)',
               'MARÉ (verificação própria)'],
      url: CADASTRO.fonte, data: (CADASTRO.coletado_em || '').split('-').reverse().join('/') || null});
    listaBuscavel('boxPrioritarios', {
      colunas: ['Município', 'UF', 'Risco no cadastro', 'Instrumento localizado'],
      rotulo: 'Buscar município do cadastro',
      linhas: cad.slice().sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR')).map(m => ({
        busca: m.nome + ' ' + m.uf,
        celulas: ['<strong>' + esc(m.nome) + '</strong>', esc(m.uf), esc(m.tipos.join(', ') || '—'),
          m.plano ? 'sim' : 'não localizado até o corte'],
      })),
    });
  }

  // =========================================================
  // 4. Números do topo — os mesmos que os mapas, nunca uma segunda conta
  // =========================================================
  /* Cada contador lê o MESMO objeto que alimentou o mapa logo abaixo. Recontar aqui seria abrir a
     porta a dois números diferentes para a mesma pergunta na mesma página — defeito que a página
     de imprensa já pagou e que o portão da regra 0 existe para barrar. */
  const N = (RESP && RESP.nacional) || {};
  const fonteAgora = carimbo ? 'Consulta de ' + carimbo : 'sem consulta até o corte';
  texto('topoCemaden', muns ? n(rAl.municipios_cemaden) : '—');
  texto('topoCemadenFonte', 'Cemaden · ' + fonteAgora);
  texto('topoInmet', muns ? n(rAl.municipios_inmet) : '—');
  texto('topoInmetFonte', 'Inmet · ' + fonteAgora);
  texto('topoCruzamento', muns ? n(cruzados.length) : '—');
  texto('topoCruzamentoFonte', 'MARÉ · ' + fonteAgora);
  texto('topoDecretaram', decretados.length ? n(decretados.length) : (N.n_municipios != null ? n(N.n_municipios) : '—'));
  texto('topoDecretaramFonte', 'DOU/SEDEC e diários oficiais · desde ' + (RESP ? RESP.inicio_ciclo : '29/06/2026'));
  texto('topoPopulacao', N.pop_sob_decreto != null ? n(N.pop_sob_decreto) : '—');
  texto('topoPopulacaoFonte', 'Censo 2022/IBGE · municípios sob decreto no ciclo');
  texto('topoReconhecidos', decretados.length ? n(reconhecidos.length) : (N.reconhecidos != null ? n(N.reconhecidos) : '—'));
  texto('topoReconhecidosFonte', 'Portarias SEDEC/MIDR (DOU) · desde ' + (RESP ? RESP.inicio_ciclo : '29/06/2026'));
}

__load().catch(err => {
  document.body.insertAdjacentHTML('afterbegin',
    '<div id="errBanner" class="erro-carga">'
    + 'Erro ao carregar os dados: ' + err.message
    + '. Sirva a pasta via HTTP (ex.: <code>npx serve</code>) — abrir o arquivo diretamente bloqueia o fetch.</div>');
});

window.addEventListener('load', function(){
  if (window.VLibras && window.VLibras.Widget){
    try { new window.VLibras.Widget('https://vlibras.gov.br/app'); } catch (e) {}
  }
});
