/* ===== defesa-civil.html · do aviso ao reconhecimento, por município ======================
 *
 * Reforma de 17/10/2026 (robo-registro/notas/HANDOVER_DEFESA_CIVIL_16-10-2026.md). A ordem é a do
 * contrato `layout/contratos/defesa-civil.json`: números do topo, consulta do município, mapa
 * municipal das emergências (figura principal) e o caminho do decreto ao reconhecimento.
 *
 * UMA fonte para o conjunto dos municípios com decreto: `data/resposta/municipios_decretados.json`,
 * o consolidado de `gerar_resposta.py`. O evento declarado no ato (`evento_declarado`), as datas e a
 * pendência (`dias_sem_reconhecimento`) vêm dele; a página
 * não casa ato por conta própria (antes casava `atos_resposta.json` aqui, uma segunda definição do
 * mesmo conjunto). Campo que o gerador ainda não escreve aparece como lacuna da sua classe.
 *
 * Valor em reais não entra nesta página: o dinheiro autorizado depois do reconhecimento está em
 * `financiamento.html#defesaCivil`. As três listas federais de risco estão no Monitor de riscos.
 *
 * REGRA DE SEGURANÇA DOS ALERTAS. Aviso e alerta são informação de AGORA. Se a coleta tiver mais de
 * 24 horas, a página não diz que há alerta em vigor: declara "sem atualização desde {data e hora}".
 */
let BR_GEOJSON, RESP, DECRETADOS, ALERTAS, TOPO,
    MUN_COD = {}, LATLON_POR_CODIGO = {}, NOMES_POR_UF = {};

const INICIO_CICLO = '2026-06-29';
const LIMITE_ALERTA_HORAS = 24;
const DIAS_PENDENCIA = 30;
/* Preposição de cada estado, para a linha do estado ("No Ceará", "Na Bahia", "Em Pernambuco"). */
const PREPOSICAO = {AC: 'No', AL: 'Em', AM: 'No', AP: 'No', BA: 'Na', CE: 'No', DF: 'No', ES: 'No',
  GO: 'Em', MA: 'No', MG: 'Em', MS: 'No', MT: 'No', PA: 'No', PB: 'Na', PE: 'Em', PI: 'No', PR: 'No',
  RJ: 'No', RN: 'No', RO: 'Em', RR: 'Em', RS: 'No', SC: 'Em', SE: 'Em', SP: 'Em', TO: 'No'};

async function __load(){
  if (window.MonitorCatalogo && window.MonitorCatalogo.pronto) {
    try { await window.MonitorCatalogo.pronto; } catch (e) {}
  }
  try {
    const m = (await fetch('data/meta.json').then(r => r.ok ? r.json() : null)) || {};
    window.__metaAtualizado = m.atualizado_em || m.corte;
  } catch (e) {}
  let ref;
  [BR_GEOJSON, ref] = await Promise.all(['geo_uf', 'municipios_ibge_referencia']
    .map(f => fetch('data/' + f + '.json').then(r => {
      if (!r.ok) throw new Error('Falha ao carregar data/' + f + '.json');
      return r.json();
    })));
  /* Os opcionais não derrubam a página: cada bloco que depende deles declara a lacuna. */
  [RESP, DECRETADOS, ALERTAS, TOPO] = await Promise.all(
    ['data/resposta/por_uf.json', 'data/resposta/municipios_decretados.json',
     'data/alertas/vigentes.json', 'data/resposta/topo_defesa_civil.json']
      .map(f => fetch(f).then(r => r.ok ? r.json() : null).catch(() => null)));
  /* Coordenada e nome pelo CÓDIGO IBGE, nunca pelo nome (as fontes escrevem o nome de formas diferentes). */
  ref.forEach(m => {
    const c = String(m.codigo_ibge).padStart(7, '0');
    MUN_COD[m.uf + '|' + m.nome] = c;
    LATLON_POR_CODIGO[c] = [m.lon, m.lat];
    (NOMES_POR_UF[m.uf] = NOMES_POR_UF[m.uf] || []).push(m.nome);
  });
  __init(ref.length);
}

/* Lista buscável, o mesmo componente em todos os cartões. Devolve `filtrar(texto)`. */
let __seqBusca = 0;
function listaBuscavel(figuraId, opts){
  const alvo = document.querySelector('#' + figuraId + ' [data-busca]');
  if (!alvo) return null;
  const esc = MonitorMapas.esc, id = 'busca' + (++__seqBusca), linhas = opts.linhas || [], cols = opts.colunas;
  alvo.insertAdjacentHTML('afterbegin',
    '<details class="cartao-mapa-dados"><summary>Ver em tabela</summary>'
    + '<div class="busca-mun"><label for="' + id + '">' + esc(opts.rotulo || 'Buscar município') + '</label>'
    + '<input id="' + id + '" type="search" autocomplete="off" spellcheck="false" placeholder="Digite o nome da cidade ou a sigla do estado">'
    + '<p class="busca-mun-conta" role="status" aria-live="polite"></p></div>'
    + '<div class="tbl-wrap" tabindex="0" role="region" aria-label="Tabela rolável horizontalmente">'
    + '<table class="mun-table"><thead><tr>' + cols.map(c => '<th>' + esc(c) + '</th>').join('')
    + '</tr></thead><tbody></tbody></table></div></details>');
  const bloco = alvo.querySelector('details'), corpo = alvo.querySelector('tbody');
  const campo = alvo.querySelector('#' + id), conta = alvo.querySelector('.busca-mun-conta');
  /* Teto de linhas montadas: quem digita vê a sua cidade; a contagem diz quantas existem. */
  const TETO = 200, unidade = opts.unidade || 'município';
  function pinta(){
    const q = (campo.value || '').trim().toLowerCase();
    const achadas = q ? linhas.filter(l => (l.busca || '').toLowerCase().indexOf(q) >= 0) : linhas;
    corpo.innerHTML = achadas.slice(0, TETO).map(l => '<tr>' + l.celulas.map(c => '<td>' + c + '</td>').join('') + '</tr>').join('')
      || '<tr><td colspan="' + cols.length + '">nenhum município encontrado com esse texto</td></tr>';
    conta.textContent = achadas.length === 1 ? '1 ' + unidade + (q ? ' encontrado' : '')
      : achadas.length.toLocaleString('pt-BR') + ' ' + unidade + 's' + (q ? ' encontrados' : '')
        + (achadas.length > TETO ? ' · mostrando os ' + TETO + ' primeiros; refine a busca' : '');
  }
  campo.addEventListener('input', pinta);
  pinta();
  return function filtrar(texto){ campo.value = texto || ''; if (bloco) bloco.open = true; pinta(); };
}

/* Família de cor do evento declarado (tokens de `assets/mapas.js`): seca, chuva, fogo, outro. Aceita
   o nome do ato ("Estiagem - 1.4.1.1.0") e a família já classificada ("seca", "vendaval"). */
const FAMILIAS = [
  {chave: 'seca', cor: 'seca', rotulo: 'seca e estiagem', re: /^seca|estiag/i},
  {chave: 'chuva', cor: 'chuva', rotulo: 'chuva, vendaval, granizo', re: /chuva|vendaval|granizo|inunda|enxurr|alaga|tornad|desliza|eros/i},
  {chave: 'fogo', cor: 'fogo', rotulo: 'fogo', re: /fogo|incênd|incend/i},
  {chave: 'outro', cor: 'cinza-quente', rotulo: 'outro evento ou tipo não declarado', re: /./},
];
const EM_CLASSIFICACAO = 'em_classificacao';
const NOME_DO_CODIGO = {seca: 'Seca ou estiagem', chuva: 'Chuva', vendaval: 'Vendaval', fogo: 'Fogo',
  outro_declarado: 'Outros tipos declarados', sem_tipo_informado: 'Tipo não declarado no ato'};
const nomeDoEvento = v => NOME_DO_CODIGO[v] || (/não declarado|^$/i.test(String(v || '').trim()) ? 'Tipo não declarado no ato' : String(v).split(' - ')[0].trim());
const familiaDe = ev => ev ? FAMILIAS.find(f => f.re.test(ev)) : FAMILIAS[3];

function __init(totalMunicipios){
  MonitorMapas.padraoGraficos(window.Chart);
  const esc = MonitorMapas.esc, cor = MonitorMapas.cor, C = window.MonitorCatalogo;
  const n = v => Number(v || 0).toLocaleString('pt-BR');
  const texto = (id, v) => { const e = document.getElementById(id); if (e) e.textContent = v; };
  const molde = (id, chave, valores) => C && C.escrever(id, chave, valores);
  const lacunaDe = corte => (C && C.texto('defesa-civil.municipio.lacuna.molde', {corte: corte || 'sem registro'}))
    || 'Não localizado até o corte (' + (corte || 'sem registro') + ')';
  const UFS = BR_GEOJSON.features.map(f => f.properties.sigla);
  const NOME_UF = Object.fromEntries(BR_GEOJSON.features.map(f => [f.properties.sigla, f.properties.name]));

  // ---------------------------------------------------------
  // Alertas: a regra das 24 horas, medida (carimbo "dd/mm/aaaa hh:mm", fuso -03:00)
  // ---------------------------------------------------------
  const carimbo = ALERTAS && ALERTAS.gerado_em;
  function horasDesde(marca){
    const m = String(marca || '').match(/(\d{2})\/(\d{2})\/(\d{4})(?:[ T](\d{2}):(\d{2}))?/);
    if (!m) return null;
    const d = new Date(Date.UTC(+m[3], +m[2] - 1, +m[1], (m[4] ? +m[4] : 23) + 3, m[5] ? +m[5] : 59));
    return (Date.now() - d.getTime()) / 36e5;
  }
  const horas = horasDesde(carimbo);
  const alertasVelhos = !(ALERTAS && ALERTAS.municipios) || horas === null || horas > LIMITE_ALERTA_HORAS;
  const semAtualizacao = 'Sem atualização desde ' + (carimbo || 'a última coleta registrada');
  const alertasDe = cod => (!alertasVelhos && ALERTAS.municipios[cod]) || {inmet: [], cemaden: []};

  // ---------------------------------------------------------
  // O conjunto: municípios com decreto no consolidado
  // ---------------------------------------------------------
  const corteDecretos = (DECRETADOS && DECRETADOS.gerado_em) || window.__metaAtualizado || null;
  const decretados = DECRETADOS && DECRETADOS.municipios
    ? Object.values(DECRETADOS.municipios).filter(m => m.decreto).map(m => {
        const ev = m.evento_declarado;
        const eventos = Array.isArray(ev) ? ev.map(nomeDoEvento) : [];
        const fontes = m.fontes || [];
        return {cod: m.ibge, nome: m.nome, uf: m.uf, eventos: eventos, classificado: Array.isArray(ev),
                familia: familiaDe(eventos[0]), decreto: m.primeiro_decreto || null, reconhecimento: m.primeiro_reconhecimento || null,
                reconhecida: !!m.reconhecido, tipos: m.tipos || [], dias: m.dias_sem_reconhecimento,
                atoMunicipal: fontes.find(f => f.canal !== 'DOU') || null, portaria: fontes.find(f => f.canal === 'DOU') || null};
      })
    : [];
  const POR_COD = Object.fromEntries(decretados.map(m => [m.cod, m]));
  const reconhecidos = decretados.filter(m => m.reconhecida);
  const FONTE_DECRETO = 'Defesa Civil nacional, no Diário Oficial da União';
  const FONTE_DIARIOS = 'diários oficiais dos estados e dos municípios';
  const docLink = f => f ? (f.url ? '<a href="' + esc(f.url) + '" target="_blank" rel="noopener">' + esc(f.decreto || 'documento') + '</a>' : esc(f.decreto || '')) : '';
  const eventoTexto = m => m.classificado ? (m.eventos.join(', ') || 'tipo não declarado no ato') : 'evento em classificação até o corte';

  // =========================================================
  // 1. Números do topo
  // =========================================================
  /* A variação da semana vem do instantâneo `resposta/topo_defesa_civil.json` (uma definição só, no
     gerador; a Imprensa lê o mesmo). Sem instantâneo, o cartão fica sem variação. */
  const variacaoDe = id => { const c = ((TOPO && TOPO.cartoes) || []).find(x => x.id === id) || {}; return c.variacao === undefined ? null : c.variacao; };
  function variacao(id, valor){
    const e = document.getElementById(id);
    if (!e || valor === null || valor === undefined) return;
    e.innerHTML = (valor > 0 ? '↑' : (valor < 0 ? '↓' : '=')) + ' ' + Math.abs(valor).toLocaleString('pt-BR')
      + ' na semana<span class="sr-only"> em relação à semana anterior</span>';
  }
  const cred = (id, fontes, data) => MonitorMapas.credito(id, {fontes: fontes, data: data});
  const rAl = (ALERTAS && ALERTAS.resumo) || {};
  if (alertasVelhos) {
    texto('topoInmet', semAtualizacao); texto('topoCemaden', semAtualizacao);
  } else {
    texto('topoInmet', n(rAl.municipios_inmet));
    texto('topoCemaden', n(rAl.municipios_cemaden));
    const lista = Object.values(ALERTAS.municipios);
    const conta = {};
    lista.forEach(m => new Set((m.inmet || []).map(a => a.tipo)).forEach(t => t && (conta[t] = (conta[t] || 0) + 1)));
    const principal = Object.entries(conta).sort((a, b) => b[1] - a[1])[0];
    molde('topoInmetApoio', 'defesa-civil.dc-topo.topo_inmet.apoio.molde',
      {n: rAl.avisos_inmet || 0, tipo: principal ? principal[0].toLowerCase() : 'tipo não declarado'});
    const ORDEM_NIVEL = ['moderado', 'alto', 'muito alto'];
    const cem = lista.filter(m => (m.cemaden || []).length);
    if (cem.length) {
      const grau = a => ORDEM_NIVEL.indexOf(String(a.nivel || '').toLowerCase());
      const todos = cem.flatMap(m => m.cemaden.map(a => Object.assign({uf: m.uf}, a)));
      const topo = Math.max.apply(null, todos.map(grau));
      const doTopo = todos.filter(a => grau(a) === topo);
      molde('topoCemadenApoio', 'defesa-civil.dc-topo.topo_cemaden.apoio.molde',
        {nivel: String(doTopo[0].nivel || 'nível não declarado').toLowerCase(), ufs: [...new Set(doTopo.map(a => a.uf))].sort().join(', ')});
    }
  }
  cred('topoInmetFonte', ['Inmet'], carimbo);
  cred('topoCemadenFonte', ['Cemaden'], carimbo);
  const N = (RESP && RESP.nacional) || {};
  if (decretados.length) {
    texto('topoDecretaram', n(decretados.length));
    texto('topoReconhecidos', n(reconhecidos.length));
  }
  variacao('topoDecretaramVariacao', variacaoDe('municipios_decretaram'));
  variacao('topoReconhecidosVariacao', variacaoDe('reconhecidos_pelo_governo_federal'));
  variacao('topoPopulacaoVariacao', variacaoDe('populacao_sob_decreto'));
  cred('topoDecretaramFonte', [FONTE_DECRETO], corteDecretos);
  cred('topoReconhecidosFonte', [FONTE_DECRETO], corteDecretos);
  /* População em milhões com uma casa (regra de número do site). */
  const pop = N.pop_sob_decreto;
  if (pop != null) texto('topoPopulacao', pop >= 1e6
    ? (Math.round(pop / 1e5) / 10).toLocaleString('pt-BR', {minimumFractionDigits: 1, maximumFractionDigits: 1}) + ' milhões' : n(pop));
  cred('topoPopulacaoFonte', ['Censo 2022, do IBGE'], RESP && RESP.gerado_em);

  // =========================================================
  // 2. Como está o seu município
  // =========================================================
  molde('municipioAbertura', 'defesa-civil.municipio.abertura.molde', {n_municipios: totalMunicipios});
  const cartao = (classe, tituloId, corpo) => '<div class="cartao ' + classe + '"><p class="cartao-k">'
    + esc((C && C.texto(tituloId)) || '') + '</p>' + corpo + '</div>';
  const linhaT = (t, s) => '<b class="cartao-t">' + t + '</b>' + (s ? '<span class="cartao-s">' + s + '</span>' : '');
  const horaBR = v => { const m = /(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})/.exec(String(v || '')); return m ? m[3] + '/' + m[2] + ', ' + m[4] + ':' + m[5] : ''; };
  const NATUREZA = {SE: 'Situação de emergência', ECP: 'Estado de calamidade pública'};
  function mostrar(uf, nome, card){
    const cod = MUN_COD[uf + '|' + nome], a = alertasDe(cod), m = POR_COD[cod];
    const avisos = (a.cemaden || []).map(x => linhaT('Alerta do Cemaden · ' + esc(x.tipo || 'tipo não declarado') + ' · ' + esc(String(x.nivel || 'nível não declarado').toLowerCase()), x.inicio ? 'Emitido em ' + esc(horaBR(x.inicio)) : ''))
      .concat((a.inmet || []).map(x => linhaT('Aviso do Inmet · ' + esc(x.tipo || 'tipo não declarado') + ' · ' + esc(String(x.severidade || '').toLowerCase()), x.fim ? 'Válido até ' + esc(horaBR(x.fim)) : '')));
    const corpoAviso = alertasVelhos ? linhaT(esc(semAtualizacao)) : (avisos.join('') || linhaT(esc(lacunaDe(carimbo))));
    let corpoDecreto, corpoRec;
    if (m) {
      const nat = m.tipos.map(t => NATUREZA[t]).filter(Boolean)[0];
      corpoDecreto = linhaT(esc((nat ? nat + ' · ' : '') + eventoTexto(m)),
        (m.atoMunicipal ? docLink(m.atoMunicipal) + ', de ' + esc(m.atoMunicipal.data || m.decreto || '') : 'Decreto de ' + esc(m.decreto || '') + ' · ato municipal: ' + esc(lacunaDe(corteDecretos))));
      corpoRec = m.reconhecida
        ? linhaT('Reconhecido em ' + esc(m.reconhecimento || (m.portaria || {}).data || ''), m.portaria ? docLink(m.portaria) : '')
        : linhaT(esc(lacunaDe(corteDecretos)));
    } else {
      corpoDecreto = linhaT(esc(lacunaDe(corteDecretos)));
      corpoRec = linhaT(esc(lacunaDe(corteDecretos)));
    }
    const e = (RESP && RESP.uf && RESP.uf[uf]) || null;
    const estado = e ? (C && C.texto('defesa-civil.municipio.estado.molde', {
      no_estado: (PREPOSICAO[uf] || 'Em') + ' ' + (NOME_UF[uf] || uf), n_dec: e.n_municipios || 0, n_mun: e.total_municipios || 0,
      pct: (Math.round((e.fracao_municipios || 0) * 1000) / 10).toLocaleString('pt-BR'),
      n_rec: (e.tons || {}).reconhecido || 0,
      evento: e.evento_mais_declarado === undefined ? 'em classificação até o corte'
        : e.evento_mais_declarado ? [].concat(e.evento_mais_declarado).map(x => nomeDoEvento(x).toLowerCase()).join(' e ') : 'tipo não declarado nos atos'})) : null;
    card.innerHTML = '<h4>' + esc(nome) + ' · ' + esc(uf) + '</h4><div class="grade-cartoes">'
      + cartao('cartao--acento-neutro', 'defesa-civil.municipio.aviso.titulo', corpoAviso)
      + cartao('cartao--acento-argila', 'defesa-civil.municipio.decreto.titulo', corpoDecreto)
      + cartao('cartao--acento-musgo', 'defesa-civil.municipio.reconhecimento.titulo', corpoRec)
      + '</div><p class="hint">' + ((C && C.texto('defesa-civil.municipio.recurso.linha')) || '') + '</p>'
      + (estado ? '<p class="hint">' + estado + '</p>' : '');
    const ver = card.querySelector('a[href="#boxEmergencias"]');
    if (ver) ver.addEventListener('click', ev => { ev.preventDefault(); if (filtrarEmergencias) filtrarEmergencias(uf);
      document.getElementById('boxEmergencias').scrollIntoView({behavior: 'smooth', block: 'start'}); });
  }
  ConsultaMunicipio.montar({uf: 'consultaUF', municipio: 'consultaMun', lista: 'consultaLista', cartao: 'consultaCard',
    estados: NOME_UF, mostrar, semLista: 'Lista de municípios do estado: sem coleta até o corte.',
    municipios: uf => (NOMES_POR_UF[uf] || []).slice().sort((x, y) => x.localeCompare(y, 'pt-BR'))});

  // =========================================================
  // 3. Onde estão as emergências: mapa municipal (figura principal)
  // =========================================================
  const ctx = MonitorMapas.contexto(BR_GEOJSON, 480, 460);
  const porUF = (RESP && RESP.uf) || {};
  MonitorMapas.desenharMapa(ctx, 'mapEmergencias', null, () => cor('branco'),
    uf => { const e = porUF[uf]; return e ? n(e.n_municipios) + ' de ' + n(e.total_municipios) + ' municípios com decreto' : 'sem contagem até o corte'; },
    [], 'contagem');
  const pontosMapa = decretados.filter(m => LATLON_POR_CODIGO[m.cod]).map(m =>
    Object.assign({lon: LATLON_POR_CODIGO[m.cod][0], lat: LATLON_POR_CODIGO[m.cod][1]}, m));
  const corFam = m => cor(m.classificado ? m.familia.cor : 'cinza-quente');
  MonitorMapas.pontos(ctx, 'mapEmergencias', pontosMapa, {
    r: () => 2.6, cor: corFam, opacidade: 0.9, classe: 'pontos-decretos',
    rotulo: m => '<strong>' + esc(m.nome) + ' · ' + esc(m.uf) + '</strong><br>' + esc(eventoTexto(m))
      + '<br>Decreto: ' + esc(m.decreto || 'data não localizada')
      + '<br>Reconhecimento: ' + esc(m.reconhecida ? (m.reconhecimento || '') + (m.portaria ? ' · ' + (m.portaria.decreto || '') : '') : 'não localizado até o corte'),
  }).selectAll('circle')
    .attr('fill', m => m.reconhecida ? corFam(m) : cor('branco'))
    .attr('stroke', m => m.reconhecida ? cor('branco') : corFam(m))
    .attr('stroke-width', m => m.reconhecida ? 0.6 : 1.2);
  /* Legenda: contagem por família; sem evento classificado no consolidado, a classe é nomeada. */
  const porFamilia = {};
  decretados.forEach(m => { const k = m.classificado ? m.familia.chave : EM_CLASSIFICACAO; porFamilia[k] = (porFamilia[k] || 0) + 1; });
  MonitorMapas.legenda('legEmergencias', FAMILIAS.filter(f => porFamilia[f.chave])
    .map(f => ({cor: cor(f.cor), rotulo: f.rotulo + ' · ' + n(porFamilia[f.chave])}))
    .concat(porFamilia[EM_CLASSIFICACAO] ? [{cor: cor('cinza-quente'), rotulo: 'em classificação até o corte · ' + n(porFamilia[EM_CLASSIFICACAO])}] : []));
  molde('subEmergencias', 'defesa-civil.emergencias.mapa.legenda', {n: decretados.length, data: corteDecretos || 'sem registro'});
  MonitorMapas.credito('boxEmergencias', {fontes: [FONTE_DECRETO, FONTE_DIARIOS], data: corteDecretos});

  /* Barras por tipo de evento declarado: valor na ponta; "Tipo não declarado no ato" e "Outros tipos
     declarados" por último; tipo com menos de dez municípios entra em "outros" (a tabela traz todos). */
  const porEvento = {};
  decretados.filter(m => m.classificado).forEach(m =>
    new Set(m.eventos.length ? m.eventos : ['Tipo não declarado no ato']).forEach(t => porEvento[t] = (porEvento[t] || 0) + 1));
  const ND = 'Tipo não declarado no ato', OUTROS = 'Outros tipos declarados', MINIMO_BARRA = 10;
  const ev = Object.entries(porEvento).sort((a, b) => b[1] - a[1]);
  const somaPequenos = ev.filter(e => e[1] < MINIMO_BARRA && e[0] !== ND && e[0] !== OUTROS).reduce((s, e) => s + e[1], 0)
    + (porEvento[OUTROS] || 0);
  const barras = ev.filter(e => e[1] >= MINIMO_BARRA && e[0] !== ND && e[0] !== OUTROS)
    .concat(porEvento[ND] ? [[ND, porEvento[ND]]] : []).concat(somaPequenos ? [[OUTROS, somaPequenos]] : []);
  const alvoBarras = document.getElementById('wrapDecretosTipo');
  if (alvoBarras) {
    const max = Math.max.apply(null, barras.map(b => b[1]).concat([1]));
    alvoBarras.innerHTML = barras.length ? '<div class="barras-painel">' + barras.map(b => '<div class="barra-linha"><span class="barra-rotulo">' + esc(b[0])
      + '</span><span class="barra-trilho"><span class="barra" style="width:calc((100% - 4em) * ' + Math.max(0.01, b[1] / max).toFixed(4)
      + ');background:' + MonitorMapas.PALETA.atmosfera.contagem.rampa[2] + '"></span><span class="barra-valor">' + n(b[1]) + '</span></span></div>').join('') + '</div>'
      : '<div class="lacuna">Evento declarado em classificação até o corte (' + esc(corteDecretos || 'sem registro') + ').</div>';
  }
  const filtrarEmergencias = listaBuscavel('boxEmergencias', {
    colunas: ['Município', 'UF', 'Evento declarado', 'Decreto', 'Reconhecimento', 'Documento'],
    rotulo: 'Buscar município com decreto',
    linhas: decretados.slice().sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR')).map(m => ({
      busca: m.nome + ' ' + m.uf,
      celulas: ['<strong>' + esc(m.nome) + '</strong>', esc(m.uf), esc(eventoTexto(m)), esc(m.decreto || 'não localizado até o corte'),
        esc(m.reconhecida ? m.reconhecimento || '' : 'não localizado até o corte'),
        [docLink(m.atoMunicipal), docLink(m.portaria)].filter(Boolean).join('<br>') || 'não localizado até o corte'],
    })),
  });

  // =========================================================
  // 4. Do decreto ao reconhecimento, semana a semana + onde a cadeia parou
  // =========================================================
  const paraISO = v => { const m = String(v || '').match(/(\d{2})\/(\d{2})\/(\d{4})/); return m ? m[3] + '-' + m[2] + '-' + m[1] : null; };
  const semanas = [];
  for (let d = new Date(INICIO_CICLO + 'T12:00:00'); d <= new Date(); d = new Date(d.getTime() + 7 * 864e5)) semanas.push(d.toISOString().slice(0, 10));
  const semanaDe = iso => { if (!iso || iso < INICIO_CICLO) return INICIO_CICLO;
    const base = new Date(INICIO_CICLO + 'T12:00:00');
    return new Date(base.getTime() + Math.floor((new Date(iso + 'T12:00:00') - base) / (7 * 864e5)) * 7 * 864e5).toISOString().slice(0, 10); };
  const acumulado = datas => { const por = {}; datas.filter(Boolean).forEach(iso => { const s = semanaDe(iso); por[s] = (por[s] || 0) + 1; });
    let soma = 0; return semanas.map(s => (soma += por[s] || 0)); };
  const RAMPA = MonitorMapas.PALETA.atmosfera.resposta.rampa;
  const SERIES = [
    {rotulo: 'decretaram', cor: RAMPA[1], dados: acumulado(decretados.map(m => paraISO(m.decreto)))},
    {rotulo: 'reconhecidos pela União', cor: RAMPA[RAMPA.length - 1], dados: acumulado(reconhecidos.map(m => paraISO(m.reconhecimento)))},
  ];
  const cvE = document.getElementById('cEtapas');
  if (cvE && window.Chart && semanas.length) new Chart(cvE, {type: 'line',
    data: {labels: semanas.map(s => s.slice(8) + '/' + s.slice(5, 7)),
           datasets: SERIES.map(s => ({label: s.rotulo, data: s.dados, borderColor: s.cor, backgroundColor: s.cor, tension: 0.2, pointRadius: 2}))},
    options: {responsive: true, maintainAspectRatio: false, plugins: {legend: {display: false}}, scales: {y: {beginAtZero: true}}}});
  MonitorMapas.legenda('legEtapas', SERIES.map(s => ({cor: s.cor, rotulo: s.rotulo})));
  MonitorMapas.credito('boxEtapas', {fontes: [FONTE_DECRETO, FONTE_DIARIOS], data: corteDecretos});
  listaBuscavel('boxEtapas', {colunas: ['Semana', 'Decretaram', 'Reconhecidos'], rotulo: 'Buscar semana', unidade: 'semana',
    linhas: semanas.map((s, i) => ({busca: s.slice(8) + '/' + s.slice(5, 7) + ' ' + s,
      celulas: [s.slice(8) + '/' + s.slice(5, 7) + '/' + s.slice(0, 4), n(SERIES[0].dados[i]), n(SERIES[1].dados[i])]}))});

  /* A pendência é campo do gerador (`dias_sem_reconhecimento`); sem ele, a classe é "não calculado". */
  const calculado = decretados.some(m => m.dias !== undefined);
  const pendentes = decretados.filter(m => !m.reconhecida && m.dias > DIAS_PENDENCIA).sort((a, b) => b.dias - a.dias);
  texto('topoPendencia', calculado ? (pendentes.length ? n(pendentes.length) : 'nenhum') : 'não calculado até o corte');
  molde('subPendencia', 'defesa-civil.reconhecimento.pendencia.legenda', {data: corteDecretos || 'sem registro'});
  cred('topoPendenciaFonte', [FONTE_DECRETO], corteDecretos);
  MonitorMapas.credito('boxPendencia', {fontes: [FONTE_DECRETO, FONTE_DIARIOS], data: corteDecretos});
  listaBuscavel('boxPendencia', {colunas: ['Município', 'UF', 'Decreto', 'Dias sem reconhecimento'], rotulo: 'Buscar município sem reconhecimento',
    linhas: pendentes.map(m => ({busca: m.nome + ' ' + m.uf,
      celulas: ['<strong>' + esc(m.nome) + '</strong>', esc(m.uf), esc(m.decreto || ''), n(m.dias)]}))});
}

__load().catch(err => {
  document.body.insertAdjacentHTML('afterbegin', '<div id="errBanner" class="erro-carga">Erro ao carregar os dados: '
    + err.message + '. Sirva a pasta via HTTP (ex.: <code>npx serve</code>) — abrir o arquivo diretamente bloqueia o fetch.</div>');
});

window.addEventListener('load', function(){
  if (window.VLibras && window.VLibras.Widget) { try { new window.VLibras.Widget('https://vlibras.gov.br/app'); } catch (e) {} }
});
