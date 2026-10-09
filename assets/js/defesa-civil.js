/* ===== defesa-civil.html · a cadeia do aviso ao recurso ==================================
 *
 * Refeita em 02/10/2026 pelo handover "a cadeia do aviso ao recurso". A página conta UMA cadeia:
 * aviso (Inmet) → alerta (Cemaden) → decreto do município → reconhecimento federal → recurso
 * autorizado. O que mudou em relação à versão de 01/10, e por quê:
 *
 *   (1) **Saíram os três mapas de PONTOS das emergências.** Ponto por município satura o país e
 *       não responde a pergunta que traz a pessoa aqui ("e a minha cidade?"). No lugar: um mapa
 *       POR ESTADO, com a lista municipal embutida e busca, e cada município numa linha com as
 *       três marcas da cadeia — decretou · reconhecido · alerta agora. Clicar no estado filtra.
 *   (2) **Entrou a cadeia no tempo**: três linhas acumuladas semana a semana desde 29/06 —
 *       decretaram, reconhecidos, com recursos autorizados. Sem razão entre as linhas e sem
 *       rótulo de diferença: a página mostra as três etapas, não constrói comparação.
 *   (3) **Entrou o tipo de evento declarado no ato.** Ele não está no arquivo consolidado dos
 *       decretos; está em `atos_resposta.json`, por município. O conjunto de quem decretou
 *       continua vindo do consolidado — este arquivo entra só como ATRIBUTO (tipo e datas),
 *       casado por código IBGE. Recontar o conjunto aqui abriria uma segunda definição de
 *       "município que decretou", defeito que esta página já pagou uma vez.
 *   (4) **As três listas federais de risco ficam juntas**: enxurradas e inundações (Casa Civil),
 *       Semiárido (Sudene) e prioritários do controle do desmatamento e do fogo (Ministério do
 *       Meio Ambiente). São a mesma pergunta — onde o risco já é reconhecido pelo governo federal.
 *
 * REGRA DE SEGURANÇA DOS ALERTAS (handover, item 6.3). Aviso e alerta são informação de AGORA, que
 * a população pode usar para se proteger. Um retrato de dias atrás mostrado como "em vigor" seria
 * enganoso, e aqui enganoso é perigoso. Se a coleta tiver mais de 24 horas, a seção não desenha
 * alerta nenhum: ela declara "sem atualização desde {data e hora}". Zero alerta em vigor e coleta
 * parada são coisas diferentes, e a página não pode fazer uma passar pela outra.
 *
 * O layout desta página é contrato: `layout/contratos/defesa-civil.json`, verificado pelo portão
 * `scripts/verificar_layout.py`. Cartão, grade, ordem de seção e texto proibido vivem lá.
 */
let BR_GEOJSON, MAP_POINTS, RESP, DECRETADOS, ALERTAS, SINAIS, CADASTRO, ENQ, ATOS, RECURSOS, TOPO,
    MUN_COD = {}, LATLON_POR_CODIGO = {}, NOME_POR_CODIGO = {}, UF_POR_CODIGO = {};

const INICIO_CICLO = '2026-06-29';
const LIMITE_ALERTA_HORAS = 24;

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
  /* Os opcionais não derrubam a página: cada seção que depende deles DECLARA a lacuna. Arquivo
     ausente e zero medido são coisas diferentes (regra editorial da ausência declarada). */
  [RESP, DECRETADOS, ALERTAS, SINAIS, CADASTRO, ENQ, ATOS, RECURSOS, TOPO] = await Promise.all(
    ['data/resposta/por_uf.json', 'data/resposta/municipios_decretados.json',
     'data/alertas/vigentes.json', 'data/sinais_risco.json',
     'data/cadastro_prioritarios_federal.json', 'data/enquadramento_card.json',
     'data/atos_resposta.json', 'data/resposta/recursos_liberados.json',
     'data/resposta/topo_defesa_civil.json']
      .map(f => fetch(f).then(r => r.ok ? r.json() : null).catch(() => null))
  );
  /* Coordenada, nome e UF pelo CÓDIGO IBGE, nunca pelo nome: as fontes escrevem o nome de formas
     diferentes (o Cemaden sempre em caixa alta, o Inmet às vezes). Casar por nome já deixou os
     municípios do Cemaden fora do mapa em silêncio. */
  ref.forEach(m => {
    const c = String(m.codigo_ibge).padStart(7, '0');
    MUN_COD[m.uf + '|' + m.nome] = c;
    LATLON_POR_CODIGO[c] = [m.lon, m.lat];
    NOME_POR_CODIGO[c] = m.nome;
    UF_POR_CODIGO[c] = m.uf;
  });
  __init();
}

// =========================================================
// Lista buscável — o mesmo componente em todos os cartões
// =========================================================
/* Uma função e não nove blocos de HTML: os cartões fazem a mesma promessa ao leitor ("digite a sua
   cidade"), e nove cópias divergem na primeira correção. O campo tem rótulo VISÍVEL (quem vê a
   lista precisa saber o que o campo faz) e a contagem do resultado é anunciada por leitor de tela,
   porque filtrar sem anunciar deixa quem não vê a tabela sem saber que algo mudou.

   Devolve `filtrar(texto)`: é o que faz o clique no estado valer para a lista — o mapa responde
   "onde", e o clique leva a lista até lá, em vez de obrigar a digitar. */
let __seqBusca = 0;
function listaBuscavel(figuraId, opts){
  const alvo = document.querySelector('#' + figuraId + ' [data-busca]');
  if (!alvo) return null;
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

  const bloco = alvo.querySelector('details');
  const corpo = alvo.querySelector('tbody');
  const campo = alvo.querySelector('#' + id);
  const conta = alvo.querySelector('.busca-mun-conta');
  /* O teto existe porque o cadastro tem 2.095 linhas e os decretos 736: montar tudo de uma vez
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
  return function filtrar(texto){
    campo.value = texto || '';
    if (bloco) bloco.open = true;
    pinta();
  };
}

function __init(){
  MonitorMapas.padraoGraficos(window.Chart);
  const esc = MonitorMapas.esc;
  const n = v => Number(v || 0).toLocaleString('pt-BR');
  const ctx = MonitorMapas.contexto(BR_GEOJSON, 480, 460);
  const ATM = MonitorMapas.PALETA.atmosfera;
  const CINZA = MonitorMapas.cor('zebra');
  const texto = (id, v) => { const e = document.getElementById(id); if (e) e.textContent = v; };
  const desenharMapa = (svgId, legId, corDe, rotuloDe, itens, familia) =>
    MonitorMapas.desenharMapa(ctx, svgId, legId, corDe, rotuloDe, itens, familia);

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

  // ---------------------------------------------------------
  // Mapa por estado: uma função, cinco figuras
  // ---------------------------------------------------------
  /* Cinco mapas de contagem por estado, e uma só régua. As faixas são do NÚMERO de municípios, e
     a última é aberta: faixa fechada no topo esconde a diferença entre 200 e 800. A primeira
     categoria é "nenhum" e é nomeada — zero medido não é a mesma coisa que ausência de dado, e a
     legenda tem de dizer qual dos dois é. */
  function mapaDeContagem(svgId, legId, porUF, familia, unidade, extraRotulo){
    const valores = Object.values(porUF).filter(v => v > 0);
    const maior = valores.length ? Math.max.apply(null, valores) : 0;
    /* Família sem rampa cai no cinza de categoria da paleta, e não numa cor semântica escolhida
       aqui: cor de família só vem da atmosfera (portão de estrutura). */
    const rampa = (ATM[familia] || {}).rampa || [CINZA];
    /* Quatro faixas sobre o maior valor observado, arredondadas para número legível. A régua é do
       dado desta edição, e a legenda diz os limites — régua fixa inventaria faixa vazia. */
    const passo = Math.max(1, Math.ceil(maior / 4));
    const faixas = [1, passo, passo * 2, passo * 3].map((x, i) => ({
      de: i === 0 ? 1 : (passo * i) + 1,
      ate: i === 3 ? null : passo * (i + 1),
      cor: rampa[Math.min(i, rampa.length - 1)],
    }));
    const faixaDe = v => {
      if (!v) return null;
      for (let i = faixas.length - 1; i >= 0; i--) if (v >= faixas[i].de) return faixas[i];
      return faixas[0];
    };
    const corDe = uf => { const f = faixaDe(porUF[uf] || 0); return f ? f.cor : CINZA; };
    const rotuloDe = uf => {
      const v = porUF[uf] || 0;
      return (v ? n(v) + ' ' + unidade + (v === 1 ? '' : 's') : 'nenhum ' + unidade)
        + (extraRotulo ? extraRotulo(uf) : '');
    };
    const itens = faixas.map(f => ({
      cor: f.cor,
      rotulo: f.ate ? n(f.de) + ' a ' + n(f.ate) : n(f.de) + ' ou mais',
    })).concat([{cor: CINZA, rotulo: 'nenhum'}]);
    const svg = desenharMapa(svgId, legId, corDe, rotuloDe, itens, familia);
    return svg;
  }

  /* O clique no estado leva a lista municipal até ele. Teclado também: o `path` da UF já recebe
     `tabindex` do componente de mapa, e sem Enter quem navega por teclado não alcança o filtro. */
  function cliqueDeUF(svgId, filtrar){
    if (!filtrar) return;
    d3.select('#' + svgId).selectAll('path.uf-path')
      .on('click', (evt, d) => filtrar(d.properties.sigla))
      .on('keydown', (evt, d) => {
        if (evt.key === 'Enter' || evt.key === ' ') { evt.preventDefault(); filtrar(d.properties.sigla); }
      });
  }

  const UFS = BR_GEOJSON.features.map(f => f.properties.sigla);
  const contarPorUF = () => { const o = {}; UFS.forEach(u => o[u] = 0); return o; };

  // =========================================================
  // 1. Alertas agora
  // =========================================================
  const muns = (ALERTAS && ALERTAS.municipios) || null;
  const rAl = (ALERTAS && ALERTAS.resumo) || {};
  const carimbo = ALERTAS && ALERTAS.gerado_em;

  /* A regra das 24 horas, medida e não suposta: `gerado_em` vem como "dd/mm/aaaa hh:mm". Sem hora
     legível, trata-se como dia — e dia anterior já passa das 24 horas. */
  function horasDesde(marca){
    if (!marca) return null;
    const m = String(marca).match(/(\d{2})\/(\d{2})\/(\d{4})(?:[ T](\d{2}):(\d{2}))?/);
    if (!m) return null;
    /* 08/10/2026: o carimbo e escrito pelo coletor no FUSO DA REDACAO (America/Sao_Paulo, -03:00)
       -- `coletar_sinais_risco.agora()`. Construir a data com componentes LOCAIS fazia a idade do
       dado depender de onde a pagina renderiza: no navegador no Brasil, tres horas mais nova; no
       runner, que roda em UTC, tres horas mais velha. Era o bastante para a pagina declarar a
       parada das 24 horas enquanto a Imprensa, lendo o mesmo arquivo, publicava a contagem. O
       fuso passa a ser explicito. */
    const d = new Date(Date.UTC(Number(m[3]), Number(m[2]) - 1, Number(m[1]),
                                (m[4] ? Number(m[4]) : 23) + 3, m[5] ? Number(m[5]) : 59));
    return (Date.now() - d.getTime()) / 36e5;
  }
  const horas = horasDesde(carimbo);
  const alertasVelhos = !muns || horas === null || horas > LIMITE_ALERTA_HORAS;
  const semAtualizacao = 'Sem atualização desde ' + (carimbo || 'a última coleta registrada');

  const lista = muns ? Object.entries(muns).map(([cod, v]) => ({
    cod: cod, nome: v.nome, uf: v.uf, inmet: v.inmet || [], cemaden: v.cemaden || [],
  })) : [];
  const comCemaden = lista.filter(m => m.cemaden.length);
  const codsAlerta = new Set(alertasVelhos ? [] : lista.map(m => m.cod));

  if (alertasVelhos){
    /* Nada de mapa e nada de contagem: a seção declara a parada. Desenhar o retrato de ontem como
       "em vigor" é o único erro desta página que pode machucar alguém. */
    ['linhaAlertas', 'linhaCemaden', 'linhaAlertasTipo'].forEach(id => texto(id, semAtualizacao));
    texto('subAlertas', semAtualizacao + ' · a coleta de avisos e alertas roda a cada publicação');
    texto('subCemaden', semAtualizacao + ' · a coleta de avisos e alertas roda a cada publicação');
    ['legAlertas', 'legCemaden', 'legAlertasTipo'].forEach(id =>
      MonitorMapas.legenda(id, [{cor: MonitorMapas.cor('sem-dado'), rotulo: 'sem atualização'}]));
    ['boxAlertas', 'boxCemaden', 'boxAlertasTipo'].forEach(id =>
      creditoSinal(id, ['cemaden_alertas', 'inmet_avisos'], carimbo || null));
  } else {
    texto('linhaAlertas', 'Consulta de ' + carimbo);
    texto('linhaCemaden', 'Consulta de ' + carimbo);
    texto('linhaAlertasTipo', 'Consulta de ' + carimbo);

    // ---- 1a. aviso ou alerta em vigor, por estado ----
    const porUFAviso = contarPorUF();
    const porUFCemaden = contarPorUF();
    lista.forEach(m => {
      if (porUFAviso[m.uf] === undefined) return;
      porUFAviso[m.uf] += 1;
      if (m.cemaden.length) porUFCemaden[m.uf] += 1;
    });
    const detalheAviso = uf => {
      const c = porUFCemaden[uf] || 0;
      return c ? '<br>' + n(c) + ' sob alerta do Cemaden' : '';
    };
    mapaDeContagem('mapAlertas', 'legAlertas', porUFAviso, 'chuva_claro', 'município', detalheAviso);
    creditoSinal('boxAlertas', ['inmet_avisos', 'cemaden_alertas'], carimbo);
    const filtrarAviso = listaBuscavel('boxAlertas', {
      colunas: ['Município', 'UF', 'Órgão', 'Tipo', 'Grau ou nível', 'Desde'],
      rotulo: 'Buscar município sob aviso ou alerta',
      linhas: lista.slice().sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR')).reduce((ac, m) => {
        m.cemaden.forEach(a => ac.push({busca: m.nome + ' ' + m.uf + ' cemaden',
          celulas: ['<strong>' + esc(m.nome) + '</strong>', esc(m.uf), 'Cemaden',
                    esc(a.tipo || 'tipo não declarado'), esc(a.nivel || '—'),
                    esc(MonitorMapas.dataBR(a.inicio) || a.desde || '—')]}));
        m.inmet.forEach(a => ac.push({busca: m.nome + ' ' + m.uf + ' inmet',
          celulas: ['<strong>' + esc(m.nome) + '</strong>', esc(m.uf), 'Inmet',
                    esc(a.tipo || 'tipo não declarado'), esc(a.severidade || '—'),
                    esc(MonitorMapas.dataBR(a.inicio) || '—')]}));
        return ac;
      }, []),
      unidade: 'aviso ou alerta',
    });
    cliqueDeUF('mapAlertas', filtrarAviso);

    // ---- 1b. alertas do Cemaden ----
    mapaDeContagem('mapCemaden', 'legCemaden', porUFCemaden, 'chuva_claro', 'município');
    creditoSinal('boxCemaden', ['cemaden_alertas'], carimbo);
    const filtrarCemaden = listaBuscavel('boxCemaden', {
      colunas: ['Município', 'UF', 'Tipo', 'Nível', 'Desde'],
      rotulo: 'Buscar município sob alerta do Cemaden',
      linhas: comCemaden.slice().sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR')).map(m => ({
        busca: m.nome + ' ' + m.uf,
        celulas: ['<strong>' + esc(m.nome) + '</strong>', esc(m.uf),
          m.cemaden.map(a => esc(a.tipo || 'tipo não declarado')).join('<br>'),
          m.cemaden.map(a => esc(a.nivel || '—')).join('<br>'),
          m.cemaden.map(a => esc(MonitorMapas.dataBR(a.inicio) || '—')).join('<br>')],
      })),
    });
    cliqueDeUF('mapCemaden', filtrarCemaden);

    // ---- 1c. tipos em vigor ----
    /* Rótulo INTEIRO, com o órgão por extenso e o tipo como o órgão o nomeia. A versão anterior
       cortava o rótulo no meio ("et · Acumulado de Chuva"): o eixo de categoria do Chart aparava o
       texto na largura que sobrava. A correção é reservar a largura do eixo (`afterFit`) e proibir
       o salto de rótulo (`autoSkip: false`) — rótulo cortado é rótulo que mente. */
    const porTipo = {};
    lista.forEach(m => {
      new Set(m.inmet.map(a => 'Inmet · ' + String(a.tipo || 'tipo não declarado').toLowerCase()))
        .forEach(t => porTipo[t] = (porTipo[t] || 0) + 1);
      new Set(m.cemaden.map(a => 'Cemaden · ' + String(a.tipo || 'tipo não declarado').toLowerCase()))
        .forEach(t => porTipo[t] = (porTipo[t] || 0) + 1);
    });
    const tipos = Object.entries(porTipo).sort((a, b) => b[1] - a[1]);
    const cv = document.getElementById('cAlertasTipo');
    if (cv && window.Chart && tipos.length){
      new Chart(cv, {type: 'bar',
        data: {labels: tipos.map(t => t[0]),
               datasets: [{data: tipos.map(t => t[1]), backgroundColor: MonitorMapas.PALETA.faixas.construcao}]},
        options: {indexAxis: 'y', responsive: true, maintainAspectRatio: false,
                  plugins: {legend: {display: false}},
                  scales: {x: {beginAtZero: true},
                           y: {ticks: {autoSkip: false, crossAlign: 'far'},
                               afterFit: function(escala){ escala.width = Math.max(escala.width, 150); }}}}});
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
  /* UMA fonte para o conjunto: `data/resposta/municipios_decretados.json`, o consolidado que
     `gerar_resposta.py` escreve e de onde sai o número publicado em `resposta/por_uf.json`. A
     primeira versão desta página montava o conjunto aqui, unindo registros por NOME, e dava 770
     municípios enquanto o topo dizia 734 — dois números para a mesma pergunta na mesma página.
     `atos_resposta.json` entra apenas como ATRIBUTO (tipo de evento e datas), casado por código. */
  const atosPorCodigo = {};
  ((ATOS && ATOS.eventos) || []).forEach(e => {
    const c = e.ibge && String(e.ibge).padStart(7, '0');
    if (!c) return;
    const a = atosPorCodigo[c] || (atosPorCodigo[c] = {});
    if (e.desastre && !a.evento) a.evento = e.desastre;
    if (e.data_decreto_municipal && !a.decreto) a.decreto = e.data_decreto_municipal;
    if (e.data_reconhecimento && !a.reconhecimento) a.reconhecimento = e.data_reconhecimento;
    if (e.portaria && !a.portaria) a.portaria = e.portaria;
    if (e.url && !a.url) a.url = e.url;
  });

  const decretados = DECRETADOS && DECRETADOS.municipios
    ? Object.values(DECRETADOS.municipios).filter(m => m.decreto).map(m => {
        const f = (m.fontes || [])[0] || {};
        const a = atosPorCodigo[m.ibge] || {};
        return {cod: m.ibge, nome: m.nome, uf: m.uf,
                data: a.decreto || m.primeiro_decreto, dataReconhecimento: a.reconhecimento || null,
                evento: a.evento || null, reconhecida: !!m.reconhecido,
                documento: a.portaria || f.decreto || null, url: a.url || f.url || null};
      })
    : [];
  const reconhecidos = decretados.filter(m => m.reconhecida);
  const carimboCiclo = (DECRETADOS && DECRETADOS.gerado_em) || window.__metaAtualizado || null;
  const FONTE_DECRETO = 'Defesa Civil nacional, no Diário Oficial da União';
  const FONTE_DIARIOS = 'diários oficiais dos estados e dos municípios';

  // ---- 2a. mapa por estado + lista com as três marcas da cadeia ----
  texto('linhaDecretosUF', carimboCiclo ? 'Registro de ' + carimboCiclo : 'Sem registro até o corte');
  const porUFDecreto = contarPorUF();
  decretados.forEach(m => { if (porUFDecreto[m.uf] !== undefined) porUFDecreto[m.uf] += 1; });
  const totalUF = {};
  Object.entries((RESP && RESP.uf) || {}).forEach(([uf, v]) => totalUF[uf] = v.total_municipios || 0);
  const parcelaDe = uf => {
    const t = totalUF[uf] || 0, d = porUFDecreto[uf] || 0;
    return t ? d / t : null;
  };
  /* A cor é a PARCELA dos municípios do estado, não a contagem: estado grande apareceria sempre
     mais escuro só por ser grande. As faixas são quartos da parcela, e a primeira categoria é
     "nenhum" — zero medido, nomeado. */
  const RAMPA_RESP = (ATM.resposta || {}).rampa || [MonitorMapas.PALETA.resposta];
  const FAIXAS_PARCELA = [
    {de: 0.5, cor: RAMPA_RESP[Math.min(3, RAMPA_RESP.length - 1)], rotulo: 'metade ou mais'},
    {de: 0.25, cor: RAMPA_RESP[Math.min(2, RAMPA_RESP.length - 1)], rotulo: 'de um quarto a metade'},
    {de: 0.1, cor: RAMPA_RESP[Math.min(1, RAMPA_RESP.length - 1)], rotulo: 'de 10% a um quarto'},
    {de: 0.0001, cor: RAMPA_RESP[0], rotulo: 'menos de 10%'},
  ];
  const corParcela = uf => {
    const p = parcelaDe(uf);
    if (p === null) return MonitorMapas.cor('sem-dado');
    const f = FAIXAS_PARCELA.find(x => p >= x.de);
    return f ? f.cor : CINZA;
  };
  const rotuloParcela = uf => {
    const d = porUFDecreto[uf] || 0, t = totalUF[uf] || 0;
    if (!t) return 'sem contagem de municípios até o corte';
    return n(d) + ' de ' + n(t) + ' município' + (t === 1 ? '' : 's') + ' com decreto no ciclo'
      + '<br>' + (Math.round((d / t) * 1000) / 10).toLocaleString('pt-BR') + '% do estado';
  };
  desenharMapa('mapDecretosUF', 'legDecretosUF', corParcela, rotuloParcela,
    FAIXAS_PARCELA.map(f => ({cor: f.cor, rotulo: f.rotulo}))
      .concat([{cor: CINZA, rotulo: 'nenhum'}]), 'resposta');
  MonitorMapas.credito('boxDecretosUF', {fontes: [FONTE_DECRETO, FONTE_DIARIOS], data: window.__metaAtualizado});
  /* As três marcas da cadeia lado a lado, na mesma linha do município: é a leitura que o mapa não
     dá — onde o município está na cadeia. Marca presente é "sim"; ausente é "—", e a ausência do
     reconhecimento NÃO é pedido negado (a ficha semântica da figura declara essa fronteira). */
  const marca = v => v ? 'sim' : '—';
  const filtrarDecretos = listaBuscavel('boxDecretosUF', {
    colunas: ['Município', 'UF', 'Decretou', 'Reconhecido', 'Alerta agora', 'Data do decreto',
              'Tipo de evento', 'Documento'],
    rotulo: 'Buscar município que decretou emergência',
    linhas: decretados.slice().sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR')).map(m => ({
      busca: m.nome + ' ' + m.uf,
      celulas: ['<strong>' + esc(m.nome) + '</strong>', esc(m.uf), 'sim', marca(m.reconhecida),
        marca(codsAlerta.has(m.cod)), esc(m.data || '—'), esc(m.evento || 'não declarado no ato'),
        m.url ? '<a href="' + esc(m.url) + '" target="_blank" rel="noopener">' + esc(m.documento || 'documento') + '</a>'
              : esc(m.documento || '—')],
    })),
  });
  cliqueDeUF('mapDecretosUF', filtrarDecretos);

  // ---- 2b. do decreto ao recurso, semana a semana ----
  /* Três linhas acumuladas na mesma escala, por semana, desde 29/06. Cada linha é uma etapa, com a
     data do ato que a define: decreto do município, portaria de reconhecimento, portaria que
     autoriza recurso. Nenhuma razão entre linhas e nenhum rótulo de diferença — a página mostra as
     três etapas; quem compara é o leitor. */
  function paraISO(v){
    if (!v) return null;
    const s = String(v);
    let m = s.match(/(\d{2})\/(\d{2})\/(\d{4})/);
    if (m) return m[3] + '-' + m[2] + '-' + m[1];
    m = s.match(/(\d{4})-(\d{2})-(\d{2})/);
    return m ? m[0] : null;
  }
  function semanaDe(iso){
    if (!iso || iso < INICIO_CICLO) return INICIO_CICLO;
    const d = new Date(iso + 'T12:00:00');
    const base = new Date(INICIO_CICLO + 'T12:00:00');
    const semanas = Math.floor((d - base) / (7 * 864e5));
    const s = new Date(base.getTime() + semanas * 7 * 864e5);
    return s.toISOString().slice(0, 10);
  }
  const primeiraData = {decretaram: {}, reconhecidos: {}, recursos: {}};
  decretados.forEach(m => {
    const iso = paraISO(m.data);
    if (iso) primeiraData.decretaram[m.cod] = iso;
    const r = paraISO(m.dataReconhecimento);
    if (m.reconhecida && r) primeiraData.reconhecidos[m.cod] = r;
  });
  Object.entries((RECURSOS && RECURSOS.municipios) || {}).forEach(([cod, v]) => {
    const datas = (v.atos || []).map(a => paraISO(a.data)).filter(Boolean).sort();
    if (datas.length) primeiraData.recursos[cod] = datas[0];
  });
  const semanas = [];
  {
    const base = new Date(INICIO_CICLO + 'T12:00:00');
    for (let d = new Date(base); d <= new Date(); d = new Date(d.getTime() + 7 * 864e5)){
      semanas.push(d.toISOString().slice(0, 10));
    }
  }
  const acumulado = (mapa) => {
    const porSemana = {};
    Object.values(mapa).forEach(iso => {
      const s = semanaDe(iso);
      porSemana[s] = (porSemana[s] || 0) + 1;
    });
    let soma = 0;
    return semanas.map(s => { soma += porSemana[s] || 0; return soma; });
  };
  const SERIES = [
    {chave: 'decretaram', rotulo: 'decretaram', cor: RAMPA_RESP[0]},
    {chave: 'reconhecidos', rotulo: 'reconhecidos pelo governo federal', cor: RAMPA_RESP[Math.min(2, RAMPA_RESP.length - 1)]},
    {chave: 'recursos', rotulo: 'com recursos de resposta autorizados', cor: MonitorMapas.PALETA.faixas.consolidado},
  ];
  texto('linhaEtapas', carimboCiclo ? 'Registro de ' + carimboCiclo : 'Sem registro até o corte');
  const cvE = document.getElementById('cEtapas');
  if (cvE && window.Chart && semanas.length){
    new Chart(cvE, {type: 'line',
      data: {labels: semanas.map(s => s.slice(8) + '/' + s.slice(5, 7)),
             datasets: SERIES.map(s => ({label: s.rotulo, data: acumulado(primeiraData[s.chave]),
               borderColor: s.cor, backgroundColor: s.cor, tension: 0.2, pointRadius: 2}))},
      options: {responsive: true, maintainAspectRatio: false,
                plugins: {legend: {display: false}},
                scales: {y: {beginAtZero: true}}}});
  }
  MonitorMapas.legenda('legEtapas', SERIES.map(s => ({cor: s.cor, rotulo: s.rotulo})));
  MonitorMapas.credito('boxEtapas', {fontes: [FONTE_DECRETO, FONTE_DIARIOS], data: window.__metaAtualizado});
  listaBuscavel('boxEtapas', {
    colunas: ['Semana', 'Decretaram', 'Reconhecidos', 'Com recursos autorizados'],
    rotulo: 'Buscar semana', unidade: 'semana',
    linhas: (function(){
      const cols = SERIES.map(s => acumulado(primeiraData[s.chave]));
      return semanas.map((s, i) => ({busca: s.slice(8) + '/' + s.slice(5, 7) + ' ' + s,
        celulas: [s.slice(8) + '/' + s.slice(5, 7) + '/' + s.slice(0, 4),
                  n(cols[0][i]), n(cols[1][i]), n(cols[2][i])]}));
    })(),
  });

  // ---- 2c. decretos por tipo de evento ----
  /* O tipo é o DECLARADO NO ATO, no vocabulário do próprio ato (o código da classificação sai do
     rótulo, porque código não é informação para quem lê). Tipo com menos de dez municípios entra
     em "outros tipos declarados", para a barra não virar uma lista de casos únicos; a lista
     embutida mostra todos. Município sem tipo declarado é nomeado, não somado a outro tipo. */
  const nomeDoEvento = v => String(v || '').split(' - ')[0].trim();
  const porEvento = {};
  decretados.forEach(m => {
    const t = m.evento ? nomeDoEvento(m.evento) : 'Tipo não declarado no ato';
    porEvento[t] = (porEvento[t] || 0) + 1;
  });
  const MINIMO_BARRA = 10;
  const eventosTodos = Object.entries(porEvento).sort((a, b) => b[1] - a[1]);
  const grandes = eventosTodos.filter(e => e[1] >= MINIMO_BARRA);
  const pequenos = eventosTodos.filter(e => e[1] < MINIMO_BARRA);
  const somaPequenos = pequenos.reduce((s, e) => s + e[1], 0);
  const barras = grandes.concat(somaPequenos ? [['Outros tipos declarados', somaPequenos]] : []);
  texto('linhaDecretosTipo', carimboCiclo ? 'Registro de ' + carimboCiclo : 'Sem registro até o corte');
  const cvT = document.getElementById('cDecretosTipo');
  if (cvT && window.Chart && barras.length){
    new Chart(cvT, {type: 'bar',
      data: {labels: barras.map(b => b[0]),
             datasets: [{data: barras.map(b => b[1]), backgroundColor: RAMPA_RESP[Math.min(1, RAMPA_RESP.length - 1)]}]},
      options: {indexAxis: 'y', responsive: true, maintainAspectRatio: false,
                plugins: {legend: {display: false}},
                scales: {x: {beginAtZero: true},
                         y: {ticks: {autoSkip: false, crossAlign: 'far'},
                             afterFit: function(escala){ escala.width = Math.max(escala.width, 150); }}}}});
  }
  MonitorMapas.legenda('legDecretosTipo', [
    {cor: RAMPA_RESP[Math.min(1, RAMPA_RESP.length - 1)], rotulo: 'municípios com o tipo declarado'}]);
  MonitorMapas.credito('boxDecretosTipo', {fontes: [FONTE_DECRETO, FONTE_DIARIOS], data: window.__metaAtualizado});
  listaBuscavel('boxDecretosTipo', {
    colunas: ['Tipo de evento declarado', 'Municípios'], rotulo: 'Buscar tipo de evento', unidade: 'tipo',
    linhas: eventosTodos.map(e => ({busca: e[0], celulas: [esc(e[0]), n(e[1])]})),
  });

  // =========================================================
  // 3. Onde os riscos são conhecidos oficialmente
  // =========================================================
  /* "Com plano localizado" é o rótulo aprovado, e o conjunto tem de ser o que o rótulo diz: PLANO
     localizado. Ficam fora `plano_elaboracao` (plano que ainda não existe), `estrutura` (comitê ou
     gabinete, não plano) e `coberto_estadual` (cobertura do estado, não plano do município). */
  const CAT_COM_PLANO = new Set(['plano', 'plano_novo', 'plano_readaptado', 'plano_recorrente',
                                 'plano_antigo']);
  const comPlano = new Set(MAP_POINTS.filter(p => CAT_COM_PLANO.has(p.categoria))
    .map(p => MUN_COD[p.uf + '|' + p.nome]).filter(Boolean));

  /* Uma função para as três listas federais. Cada uma tem a sua fonte e o seu recorte, e o mapa é
     o mesmo: quantos municípios do estado constam da lista. A parcela com plano localizado é
     verificação do MARÉ, não da fonte federal, e por isso aparece no crédito como fonte própria. */
  function listaFederal(conf){
    const porUF = contarPorUF();
    const itens = conf.itens;
    itens.forEach(m => { if (porUF[m.uf] !== undefined) porUF[m.uf] += 1; });
    const comPlanoPorUF = contarPorUF();
    itens.forEach(m => { if (m.plano && comPlanoPorUF[m.uf] !== undefined) comPlanoPorUF[m.uf] += 1; });
    texto(conf.linha, itens.length
      ? (conf.rotuloLinha || 'Lista de ') + conf.data + ' · ' + n(itens.length) + ' municípios'
      : 'Sem coleta da lista até o corte');
    if (!itens.length){
      MonitorMapas.legenda(conf.legenda, [{cor: MonitorMapas.cor('sem-dado'), rotulo: 'sem coleta até o corte'}]);
      MonitorMapas.credito(conf.caixa, {fontes: [conf.fonte], url: conf.url, data: null});
      return;
    }
    mapaDeContagem(conf.mapa, conf.legenda, porUF, conf.familia, 'município',
      uf => (comPlanoPorUF[uf] ? '<br>' + n(comPlanoPorUF[uf]) + ' com plano localizado' : ''));
    MonitorMapas.credito(conf.caixa, {
      fontes: [conf.fonte, 'MARÉ (verificação própria)'], url: conf.url, data: conf.data});
    const filtrar = listaBuscavel(conf.caixa, {
      colunas: conf.colunas || ['Município', 'UF', 'Plano localizado'],
      rotulo: conf.rotuloBusca,
      linhas: itens.slice().sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR')).map(m => ({
        busca: m.nome + ' ' + m.uf,
        celulas: conf.celulas
          ? conf.celulas(m)
          : ['<strong>' + esc(m.nome) + '</strong>', esc(m.uf),
             m.plano ? 'sim' : 'não localizado até o corte'],
      })),
    });
    cliqueDeUF(conf.mapa, filtrar);
  }

  const fontesEnq = (ENQ && ENQ.fontes) || {};
  const dataBR = v => MonitorMapas.dataBR(v) || null;

  // ---- 3a. enxurradas e inundações (Casa Civil) ----
  const cad = CADASTRO && CADASTRO.municipios
    ? Object.entries(CADASTRO.municipios).map(([cod, v]) => ({
        cod: cod, nome: v.municipio, uf: v.uf, tipos: v.tipos_de_risco || [],
        plano: comPlano.has(cod)}))
    : [];
  listaFederal({
    itens: cad, caixa: 'boxRiscoEnchente', mapa: 'mapRiscoEnchente', legenda: 'legRiscoEnchente',
    linha: 'linhaRiscoEnchente', familia: 'chuva_claro',
    rotuloLinha: 'Cadastro de ', data: dataBR(CADASTRO && CADASTRO.coletado_em),
    fonte: 'Casa Civil, Nota Técnica nº 2/2025', url: CADASTRO && CADASTRO.fonte,
    rotuloBusca: 'Buscar município do cadastro de enxurradas e inundações',
    colunas: ['Município', 'UF', 'Risco no cadastro', 'Plano localizado'],
    celulas: m => ['<strong>' + esc(m.nome) + '</strong>', esc(m.uf),
                   esc(m.tipos.join(', ') || '—'), m.plano ? 'sim' : 'não localizado até o corte'],
  });

  // ---- 3b. Semiárido (Sudene) e 3c. fogo (Ministério do Meio Ambiente) ----
  /* As duas saem de `enquadramento_card.json`, o derivado que marca cada município com as listas
     de que ele consta (`sa` = Semiárido, `mma` = prioritário do controle do desmatamento). Nome e
     UF vêm da referência do IBGE por código: o derivado guarda só as marcas, de propósito. */
  const porMarca = marcaChave => Object.entries((ENQ && ENQ.municipios) || {})
    .filter(([, v]) => v[marcaChave])
    .map(([cod]) => ({cod: cod, nome: NOME_POR_CODIGO[cod] || cod, uf: UF_POR_CODIGO[cod] || '—',
                      plano: comPlano.has(cod)}))
    .filter(m => m.uf !== '—');
  listaFederal({
    itens: porMarca('sa'), caixa: 'boxRiscoSemiarido', mapa: 'mapRiscoSemiarido',
    legenda: 'legRiscoSemiarido', linha: 'linhaRiscoSemiarido', familia: 'seca',
    rotuloLinha: 'Delimitação de ', data: dataBR((fontesEnq.seca || {}).consultado_em),
    fonte: 'Sudene, Resolução Condel nº 176/2024', url: (fontesEnq.seca || {}).url,
    rotuloBusca: 'Buscar município do Semiárido',
  });
  listaFederal({
    itens: porMarca('mma'), caixa: 'boxRiscoFogo', mapa: 'mapRiscoFogo', legenda: 'legRiscoFogo',
    linha: 'linhaRiscoFogo', familia: 'fogo_claro',
    rotuloLinha: 'Lista de ', data: dataBR((fontesEnq.fogo || {}).consultado_em),
    fonte: 'Ministério do Meio Ambiente, portaria vigente', url: (fontesEnq.fogo || {}).url,
    rotuloBusca: 'Buscar município prioritário para o controle do fogo',
  });

  // =========================================================
  // 4. Números do topo — os mesmos que os mapas, nunca uma segunda conta
  // =========================================================
  /* Cada contador lê o MESMO objeto que alimentou o mapa logo abaixo. Recontar aqui abriria a porta
     a dois números diferentes para a mesma pergunta na mesma página.

     A VARIAÇÃO é só dos cartões do ciclo, e vem da data do próprio ato: quantos municípios entraram
     na etapa nos últimos sete dias. Os cartões de AGORA não têm variação porque a página não guarda
     retrato do que estava em vigor há sete dias — comparar com o que não foi medido seria inventar. */
  const N = (RESP && RESP.nacional) || {};
  const fonteAgora = alertasVelhos ? semAtualizacao : 'Consulta de ' + carimbo;
  /* A VARIAÇÃO DA SEMANA vem do instantâneo `resposta/topo_defesa_civil.json`, escrito por
     `scripts/gerar_topo_das_paginas.py`. Ela não é recalculada aqui, e a razão é medida: a página
     contava pela data do ato em `atos_resposta.json` (22 na semana) e o instantâneo conta pela data
     do primeiro decreto no consolidado (69). Dois números para a mesma frase — um na página, outro
     no release da Imprensa, que lê o instantâneo. Uma definição só, no gerador; a página lê.

     Sem o instantâneo, o cartão fica sem variação: estimar aqui recriaria a segunda definição. */
  const topoCartao = id => ((TOPO && TOPO.cartoes) || []).find(c => c.id === id) || {};
  const variacaoDoInstantaneo = id => {
    const v = topoCartao(id).variacao;
    return v === undefined ? null : v;
  };
  function variacao(id, valor, unidade){
    const e = document.getElementById(id);
    if (!e) return;
    if (valor === null || valor === undefined) { e.textContent = ''; return; }
    const seta = valor > 0 ? '↑' : (valor < 0 ? '↓' : '=');
    e.innerHTML = seta + ' ' + Math.abs(valor).toLocaleString('pt-BR')
      + (unidade ? ' ' + esc(unidade) : '')
      + '<span class="sr-only"> em relação à semana anterior</span>';
  }

  texto('topoCemaden', alertasVelhos ? semAtualizacao : n(rAl.municipios_cemaden));
  texto('topoCemadenFonte', 'Cemaden · ' + fonteAgora);
  texto('topoInmet', alertasVelhos ? semAtualizacao : n(rAl.municipios_inmet));
  texto('topoInmetFonte', 'Inmet · ' + fonteAgora);
  const cruzados = decretados.filter(m => codsAlerta.has(m.cod));
  texto('topoCruzamento', alertasVelhos ? semAtualizacao : n(cruzados.length));
  texto('topoCruzamentoFonte', 'MARÉ · ' + fonteAgora);

  const inicio = (RESP && RESP.inicio_ciclo) || '29/06/2026';
  texto('topoDecretaram', decretados.length ? n(decretados.length) : (N.n_municipios != null ? n(N.n_municipios) : '—'));
  texto('topoDecretaramFonte', FONTE_DECRETO + ' · desde ' + inicio);
  variacao('topoDecretaramVariacao', variacaoDoInstantaneo('municipios_decretaram'), 'na semana');

  /* A população que entrou na semana também vem do instantâneo, pela mesma razão. */
  variacao('topoPopulacaoVariacao', variacaoDoInstantaneo('populacao_sob_decreto'), 'na semana');
  const pop = N.pop_sob_decreto;
  /* População arredondada em milhões, com uma casa: o número inteiro dá precisão que o recorte não
     tem, e a editoria pediu o arredondado. */
  texto('topoPopulacao', pop != null
    ? (pop >= 1e6 ? (Math.round(pop / 1e5) / 10).toLocaleString('pt-BR') + ' milhões' : n(pop))
    : '—');
  texto('topoPopulacaoFonte', 'Censo 2022, do IBGE · municípios com decreto no ciclo');

  texto('topoReconhecidos', decretados.length ? n(reconhecidos.length) : (N.reconhecidos != null ? n(N.reconhecidos) : '—'));
  texto('topoReconhecidosFonte', FONTE_DECRETO + ' · desde ' + inicio);
  variacao('topoReconhecidosVariacao', variacaoDoInstantaneo('reconhecidos_pelo_governo_federal'), 'na semana');
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
