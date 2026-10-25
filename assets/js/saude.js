/* A7-17 (12/10/2026): erro de bloco que não renderiza não é engolido em silêncio — vai ao
   console com o lugar, onde o portão de runtime e quem abre o DevTools o veem. */
function _erroSaude(onde) { return function (e) { try { console.error("[MARÉ] falha em " + onde + ":", e); } catch (_) {} }; }
/* A7-14 (12/10/2026): número de cartão pela régua de `layout/regras.json` (numeros) — zero medido
   se escreve por extenso, e ausência de dado nunca vira zero. */
function _qtdCartao(v) {
  if (v === null || v === undefined || v === '') return 'sem dado';
  const x = Number(v);
  if (!Number.isFinite(x)) return 'sem dado';
  return x === 0 ? 'zero' : decBR(x);
}
// ===== saude.html · bloco 1 (extraído em 06/09/2026, CSP sem unsafe-inline) =====
let BR_GEOJSON, SUF, SSIN, SINAIS, MARE, MSAUDE;
// Lote 6, §2: a frase do dado nasce oculta e só aparece com texto — nunca "—" nem linha vazia.
const mostrarFrase = (alvo, texto) => { alvo.textContent = texto; alvo.hidden = !texto; };
/* Número em texto público com vírgula decimal (A4-16); não-número passa como veio ("—", nulo).
   21/10/2026: uma casa decimal, SALVO quando ela zeraria um valor medido — 0,037 internação por
   100 mil saía "0", e dizer zero onde houve 75 internações é afirmar o que não se mediu. Abaixo de
   0,05 vale um dígito significativo ("0,04", "0,009"), que é curto e não mente. */
const decBR = v => (v == null || v === '' || isNaN(Number(v))) ? v
  : MonitorMapas.numBR(v, Number.isInteger(Number(v)) ? 0 : 1);

/* QUAIS COMPONENTES FORMAM A NOTA — 22/10/2026, decisão da editoria (v0.6).
 *
 * A cobertura municipal saiu da nota e passou a ser camada publicada ao lado dela. A página não
 * traz a lista de componentes escrita aqui: ela lê o PESO que o arquivo declara. Componente de
 * peso zero aparece com rótulo próprio e sem pontos, porque enumerá-lo entre os outros diria ao
 * leitor que ele conta. É a mesma razão de o parágrafo de abertura não testar a versão: no dia em
 * que o motor troca os pesos, a página já está certa, sem rodada.
 */
const pesoSaude = (o, c) => Number(((((o || {}).metodo || {}).pesos) || {})[c] || 0);
const pesaSaude = c => pesoSaude(MSAUDE, c) > 0;
const pesosIguaisSaude = () => { const v = Object.values((((MSAUDE || {}).metodo || {}).pesos) || {}).map(Number).filter(x => x > 0);
  return v.length > 1 && v.every(x => Math.abs(x - v[0]) < 1e-9); };
/* A camada, nas palavras da sua classe, pela régua de número do projeto (`_qtdCartao`): sem plano
 * municipal localizado o percentual é ZERO POR CONSTRUÇÃO, e escrever "0 % da população" diria que
 * se mediu cobertura nula onde não se leu documento nenhum — hoje seriam 15 das 27. Nenhuma classe
 * é zero: percentual medido · localizado e não lido · não localizado até o corte. */
const camadaMunicipalSaude = c => {
  const lidos = Number(c.planos_lidos || 0), sem = Number(c.planos_sem_leitura || 0);
  if (c.cobertura_pct == null) return 'sem leitura até o corte';
  if (!lidos) return sem ? 'nenhum plano municipal lido até o corte · ' + sem + (sem === 1 ? ' localizado' : ' localizados')
                         : 'nenhum plano municipal localizado até o corte';
  /* Percentual abaixo da resolução do campo publicado também não é zero: no RS, 3.022 pessoas
   * moram em município cujo plano trata a saúde e `cobertura_pct` traz 0,0. */
  const pct = Number(c.cobertura_pct) === 0 && Number(c.pop_coberta || 0) > 0
    ? 'menos de 0,1' : _qtdCartao(c.cobertura_pct);
  return pct + ' % da população em município cujo plano trata a saúde ('
    + lidos + (lidos === 1 ? ' plano municipal lido' : ' planos municipais lidos')
    + (sem ? ' · ' + sem + ' sem leitura' : '') + ')';
};

/* A SEMANA VIRA DATA — item 0 do handover de 07/10/2026, regra da editoria para o site inteiro.
 *
 * O dado do SINAN e do InfoDengue é por semana epidemiológica, e continua sendo: isso é da fonte.
 * O que não chega ao leitor é a palavra. Ele lê "na semana de 16 a 22 de agosto de 2026", que é
 * como se pensa uma data; "semana epidemiológica 33" exige saber o que é e contar no calendário.
 *
 * A conversão mora em `assets/semana.js`, com a regra do Ministério da Saúde e um autoteste
 * conferido contra o calendário publicado em quatro anos de virada diferente. Aqui ficam só os
 * três ajudantes que traduzem a chave "2026-33" que os arquivos de série usam.
 *
 * Sem o utilitário carregado, as funções devolvem vazio em vez de a chave crua: a página perde a
 * data, e não ganha um "2026-33" na cara do leitor. */
function semanaEmDatas(ano, chave, curta) {
  if (!window.MonitorSemana || !chave) return '';
  // A chave vem "2026-33" nas séries e "202633" no sinal do InfoDengue: a leitura cobre as duas.
  const parte = String(chave).includes('-') ? String(chave).split('-') : [String(chave).slice(0, 4), String(chave).slice(4)];
  const n = Number(parte[1]);
  const a = Number(ano || parte[0]);
  if (!a || !n) return '';
  // COM a preposição: quem chama escreve "na semana " e a função completa "de 16 a 22 de
  // agosto de 2026". Sem ela saía "na semana 16 a 22", que tropeça na leitura.
  return (curta ? MonitorSemana.curta(a, n) : MonitorSemana.porExtenso(a, n, true)) || '';
}
/* O rótulo do eixo: o nome do mês na PRIMEIRA semana dele, vazio nas outras. */
function rotulosDeMes(ano, chaves) {
  let ultimo = null;
  return (chaves || []).map(k => {
    const mes = window.MonitorSemana
      ? MonitorSemana.mesDaSemana(Number(ano), Number(String(k).split('-')[1])) : null;
    if (!mes || mes === ultimo) return '';
    ultimo = mes;
    return mes;
  });
}
/* O eixo de um gráfico semanal: rótulo de mês na primeira semana de cada mês, e o título do
 * tooltip com o intervalo de datas da semana. Recebe os números de semana ("01", "02", …) que os
 * três gráficos de série já montam, e devolve as duas listas na mesma ordem. */
function eixoDeMeses(ano, semanas) {
  const labels = rotulosDeMes(ano, (semanas || []).map(w => ano + '-' + w));
  const titulos = (semanas || []).map(w => semanaEmDatas(ano, ano + '-' + w, true));
  return {labels: labels, titulos: titulos};
}
/* As opções de eixo e tooltip que acompanham `eixoDeMeses`, para os três não divergirem. */
function opcoesDeEixoSemanal(titulos, extra) {
  const base = {ticks: {autoSkip: false, maxRotation: 0}};
  return {x: Object.assign(base, extra || {}),
          tooltipTitulo: itens => (itens && itens[0] ? (titulos[itens[0].dataIndex] || '') : '')};
}

/* O começo do período coberto, por extenso, da primeira semana que tem valor. */
function primeiraSemanaComValor(ano, comValor) {
  if (!window.MonitorSemana || !comValor || !comValor.length) return null;
  const r = MonitorSemana.semanaParaDatas(Number(ano), Number(comValor[0].split('-')[1]));
  if (!r) return null;
  return r.inicio.getUTCDate() + ' de ' + MonitorSemana.MESES[r.inicio.getUTCMonth()]
         + ' de ' + r.inicio.getUTCFullYear();
}
// 14/09/2026: chikungunya — mesmos quatro arquivos do painel, com prefixo chik_ (coletar_desfechos_saude.py --doenca chikungunya).
// Nulos enquanto o coletor não rodar: o comparador e o mapa declaram lacuna, nunca preenchem.
const UFS = ["AC","AL","AM","AP","BA","CE","DF","ES","GO","MA","MG","MS","MT","PA","PB","PE","PI","PR","RJ","RN","RO","RR","RS","SC","SE","SP","TO"];
const NOME_UF = {AC:'Acre',AL:'Alagoas',AM:'Amazonas',AP:'Amapá',BA:'Bahia',CE:'Ceará',DF:'Distrito Federal',ES:'Espírito Santo',GO:'Goiás',MA:'Maranhão',MG:'Minas Gerais',MS:'Mato Grosso do Sul',MT:'Mato Grosso',PA:'Pará',PB:'Paraíba',PE:'Pernambuco',PI:'Piauí',PR:'Paraná',RJ:'Rio de Janeiro',RN:'Rio Grande do Norte',RO:'Rondônia',RR:'Roraima',RS:'Rio Grande do Sul',SC:'Santa Catarina',SE:'Sergipe',SP:'São Paulo',TO:'Tocantins'};
const NEUTRA = MonitorMapas.cor('sem-dado');
const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const { showTip, hideTip } = MonitorMapas;

async function __load(){
  [BR_GEOJSON, SUF, SSIN, SINAIS, MARE, MSAUDE] = await Promise.all(
    ['geo_uf','saude_uf','saude_sinais','sinais_risco','indice','monitor_saude'].map(f => fetch('data/' + f + '.json').then(r => {
      if(!r.ok) throw new Error('Falha ao carregar data/' + f + '.json'); return r.json(); })));
  __init();
  // 02/10/2026 (bloco A.3): a amostra de 313 municípios saiu do mapa e a série duplicada
  // saiu da página. Dengue e chikungunya passam a ser contadas pelo SINAN, no bloco
  // `arbovirosesPelaPrimaria`, ao fim deste arquivo.

  montarDesfechos().catch(_erroSaude("saude:desfechos"));
}

const fonteFigura = MonitorMapas.credito;

function __init(){
  const ctx = MonitorMapas.contexto(BR_GEOJSON, 480, 460); const projection = ctx.projection;
  const desenharMapa = (svgId, legendaId, corDe, rotuloDe, itens) => MonitorMapas.desenharMapa(ctx, svgId, legendaId, corDe, rotuloDe, itens);

  // 0 · MARÉ · Saúde (v0.6, Metodologia §31): prontidão = média dos componentes que o arquivo declara
  // com peso (hoje instrumento e antecipação, ½ cada); não verificada = cinza, sem número
  (function(){
    const M = (MSAUDE && MSAUDE.ufs) || {};
    const FX = {'estágio inicial': MonitorMapas.PALETA.faixas.inicial, 'em construção': MonitorMapas.PALETA.faixas.construcao, 'consolidado': MonitorMapas.PALETA.faixas.consolidado, 'avançado': MonitorMapas.PALETA.faixas.avancado, 'não verificado': MonitorMapas.PALETA.faixas.nao_verificado};
    const ST_H = {NOVO:'novo, do ciclo', READ:'readaptado', VIG:'vigente-recorrente', ELAB:'em elaboração', LAC:'não localizado', NAO_VERIFICADO:'ainda não verificado'};
    desenharMapa('mapaMonitor', 'legMonitor', uf => FX[(M[uf] || {}).faixa] || FX['não verificado'],
      uf => { const m = M[uf] || {}; if (!m.verificado) return '<em>ainda não verificado</em> — sem número'; const i = m.instrumento || {}, a = m.antecipacao || {};
        const c = m.cobertura || {};
        return '<em>' + esc(m.faixa) + ' · ' + esc(decBR(m.prontidao)) + '</em><br>instrumento ' + esc(decBR(i.pontos)) + ' (' + esc(ST_H[i.status] || i.status) + ')' + (i.data ? ' · ' + esc(i.data) : '') + '<br>' + (pesaSaude('cobertura')
          ? 'cobertura sanitária ' + esc(decBR(c.pontos) ?? '—') + ' (' + esc(c.planos_lidos ?? 0) + (Number(c.planos_lidos ?? 0) === 1 ? ' plano lido · ' : ' planos lidos · ') + esc(c.planos_sem_leitura ?? 0) + ' sem leitura)'
          : esc(camadaMunicipalSaude(c))) + '<br>quando o ato saiu em relação ao primeiro boletim ' + esc(decBR(a.pontos)) + (i.temporada ? ' (edição ' + esc(i.temporada) + ')' : ''); },
      []);
    const R = (MSAUDE && MSAUDE.resumo) || {}; const pf = R.por_faixa || {};
    const lim = ((MSAUDE && MSAUDE.metodo) || {}).faixas || {};
    MonitorMapas.legenda('legMonitor', [
      ...['avançado', 'consolidado', 'em construção', 'estágio inicial'].map(f => ({cor: FX[f], rotulo: f + (lim[f] ? ' (' + lim[f] + ')' : '') + ' · ' + (pf[f] || 0) + ' UF' + ((pf[f] || 0) === 1 ? '' : 's')})),
      {cor: FX['não verificado'], rotulo: 'ainda não verificado · ' + (R.nao_verificadas ?? '—') + ' UFs (sem número)'}]);
    fonteFigura('boxMonitor', {fontes: ['MARÉ Saúde'], data: (MSAUDE || {}).gerado_em});
    // tabela alternativa
    const tb = document.querySelector('#tblMonitor tbody');
    // Lote 6, §2 (16/10/2026): a tabela diz o que o mapa mostra — nota, faixa, plano, coordenação e
    // ligação com o governo; componentes internos ("cobertura 0.1 · 1 lido(s)") saem.
    const coord = o => (o && o.doc) ? esc(ST_COORD[o.status] || o.status || '') + (o.data ? ' · ' + esc(o.data) : '') : 'ainda não verificada';
    if (tb) tb.innerHTML = UFS.map(uf => { const m = M[uf] || {}, i = m.instrumento || {}, co = ((SUF && SUF.uf && SUF.uf[uf]) || {}).coordenacao || {};
      return '<tr><td><strong>' + uf + '</strong></td><td>' + (m.verificado ? esc(decBR(m.prontidao)) : 'sem número') + '</td><td>' + esc(m.faixa || 'ainda não verificado') + '</td><td>' + esc(ST_H[i.status] || 'ainda não verificado') + (i.data ? ' · ' + esc(i.data) : '') + '</td><td>' + coord(co.f1 || (co.status ? co : null)) + '</td><td>' + coord(co.f2) + '</td></tr>'; }).join('');
    // 13/09/2026 (auditoria de visualizações, consolidação): #monitorBarras retirado do HTML —
    // duplicava a tabela alternativa de boxMonitor. Bloco guardado por ausência do elemento.
    // 02/10/2026 (bloco A.5): o medidor do MARÉ Saúde saiu do topo da página — o número de
    // cada estado passou para a grade e para a ficha. O bloco do medidor sai inteiro: ele
    // já estava sem a linha que declarava o elemento, e o ReferenceError derrubava TODO o
    // carregamento da página, levando o mapa de calor, a grade e os títulos-fato com ele.
    // Deletar linha por id é perigoso assim: o que resta pode continuar compilando.
    // 13/09/2026: #monitorBarras já não existe no HTML (bloco morto, nunca executava — se existisse,
    // seria uma lista de UFs ordenada por nota, ranking exatamente do tipo que a editoria veta em
    // 16/09/2026). Removido por inteiro, não só guardado.
    // Resposta sanitária (E17): ESPIN federal, decretos estaduais por arboviroses, créditos por portaria — contador, hoje zero de verdade
    (function respostaSanitaria(){
      const RS = (MSAUDE && MSAUDE.resposta) || {emergencias: 0, indice: 0, pop_sob_emergencia: 0, fontes: ['DOU (ESPIN)', 'diários oficiais estaduais']};
      const ir = +(RS.indice || 0);
    })();
    // 17/09/2026 (paridade com a home, handover de identidade §4.5): contador de tempo, semana desde
    // o primeiro boletim (29/06/2026) — mesmo cálculo, mesma variante Leve da home.
  })();

  // 13/09/2026 (proposta de enxugamento, Manus AI): 'O que a União publicou' (8 cartões federais)
  // migrou para pesquisadores.html — documentos de referência, não narrativa principal da página.
  // 2 · estadual
  const ST = {NOVO:['Novo, específico para o ciclo',MonitorMapas.PALETA.status.NOVO], READ:['Recorrente readaptado',MonitorMapas.PALETA.status.READ], VIG:['Vigente, sem menção ao ciclo',MonitorMapas.PALETA.status.VIG],
              ELAB:['Em elaboração',MonitorMapas.PALETA.status.ELAB], LAC:['Não localizado (bateria datada)',MonitorMapas.PALETA.status.LAC], NAO_VERIFICADO:['Ainda não verificado',MonitorMapas.PALETA.status.NAO_VERIFICADO]};
  const st = uf => (SUF.uf[uf] || {}).status || 'NAO_VERIFICADO';
  // 02/10/2026 (bloco A.2): um mapa só por estado. O mapa de status saiu, e com ele o seu
  // desenho — `desenharMapa` sobre elemento ausente levanta no d3 (null.getAttribute) e
  // derrubava TODO o carregamento da página: calor, grade e títulos-fato incluídos.
  const nv = UFS.filter(u => st(u) === 'NAO_VERIFICADO').length;
  const FAM = {seca:['Seca / calor / fogo',MonitorMapas.PALETA.risco.seca], chuvas:['Chuvas extremas',MonitorMapas.PALETA.risco.chuvas], multi:['Mais de uma família',MonitorMapas.PALETA.risco.multi]};
  const fam = uf => { const r = ((SUF.uf[uf]||{}).risco_sanitario_projetado||[]).join(' ').toLowerCase(); const s = /calor|queimad|arbovir|estiagem/.test(r), c = /leptospir|diarre|hepatite/.test(r); return s&&c?'multi':s?'seca':c?'chuvas':null; };
  // O mapa de risco sanitário projetado saiu pela mesma decisão; o risco previsto de cada
  // estado continua na FICHA, onde o leitor o lê junto do plano e da coordenação.
  // A tabela das 27 UFs vivia no mapa de status, que saiu em 02/10/2026 (um mapa só por
  // estado). A grade de estados e a ficha de cada um passaram a ser a leitura por UF.
  { const _tb = document.querySelector('#tblUF tbody');
    if (_tb) _tb.innerHTML = UFS.map(uf => { const u = SUF.uf[uf]||{}; return '<tr><td><strong>'+uf+'</strong></td><td>'+esc(ST[st(uf)][0])+'</td><td>'+esc(u.doc||'—')+'</td><td>'+esc((u.risco_sanitario_projetado||[]).join('; '))+'</td><td>'+esc(u.data_verificacao||'—')+'</td></tr>'; }).join(''); }

}
// 15/09/2026 (MARÉ Saúde espelha o MARÉ Legal): "Como ler" em ficha popup; um cartão por estado (mesma anatomia da inicial:
// micro-barra do índice no degradê único, segunda barra de resposta, face com plano · data · dengue na capital); clique abre o detalhe.
const REG = {}, NOMES = {};
// A ficha do estado: era aninhada em `cartoesEstadosSaude`, e o item 7 reescreveu aquela
// função para usar o componente compartilhado. Ela passa a ser função irmã — o clique do
// cartão a chama pelo nome, e o componente não precisa saber o que ela faz.
// O vocabulário do degrau do instrumento, em linguagem de leitor, no nível do módulo: a ficha e o
// cartão leem a mesma tabela.
const ST_H = {NOVO: 'plano do ciclo', READ: 'readaptado', VIG_REVISADO: 'plano revisado em 2026',
              VIG: 'plano de todo ano', ELAB: 'em elaboração', LAC: 'não localizado',
              NAO_VERIFICADO: 'ainda não verificado'};
/* Os degraus das duas funções da coordenação, em linguagem de leitor (METODOLOGIA §91.3). A tabela
 * saiu daqui quando a ficha virou função irmã; sem ela a ficha lançava ReferenceError (A4-02). */
const ST_COORD = {
  CRIADO_CICLO: 'criada para o ciclo',
  REATIVADO_CICLO: 'reativada para o ciclo',
  PERMANENTE: 'estrutura permanente',
  ANUNCIADO: 'anunciada, sem ato publicado',
  NOMEADA_COM_ATRIBUICAO: 'secretaria de saúde nomeada, com atribuição',
  LISTADA_SEM_ATRIBUICAO: 'secretaria de saúde listada, sem atribuição',
  LAC: 'não localizada até o corte',
};


function abrirDetalheSaude(uf){
  /* A ficha busca o que precisa: ela deixou de viver dentro da função que montava a grade, e por
   * isso não herda mais o escopo daquela função. */
  const M = (MSAUDE && MSAUDE.ufs) || {};
  const RS = (MSAUDE && MSAUDE.resposta) || {ufs: []};
  const m = M[uf] || {}; const i = m.instrumento || {}; const c = m.cobertura || {}; const a = m.antecipacao || {}; const dc = m.risco_atual || {}; const semanaDengue = semanaEmDatas(null, dc.dengue_se); const u = (SUF.uf || {})[uf] || {};
  const linha = (k, v) => '<div class="field"><div class="k">' + k + '</div><div class="v">' + v + '</div></div>';
  document.getElementById('detailSaudeConteudo').innerHTML = '<div class="uf-name">' + esc(NOMES[uf] || uf) + ' <span class="sub">(' + uf + ')</span></div>'
    + (m.verificado ? '<div class="gauge-mini gauge-zone"><div class="gauge-head"><span class="gnum">' + String(m.prontidao).replace('.', ',') + '</span><span class="gden">/ 100 · ' + esc(m.faixa) + '</span></div><div class="gauge-track"><div class="gauge-fill" style="--galvo:' + Math.max(m.prontidao, 0.1) + '; width:' + m.prontidao + '%"></div></div></div>' : '<p class="placeholder">Ainda não verificado nesta camada: a bateria de busca de saúde não foi executada para o estado — não é ausência de documento.</p>')
    + '<div class="uf-region">' + esc(REG[uf] || '') + '</div>'
    + linha('Instrumento estadual de saúde', '<span class="pill-nivel">' + esc(ST_H[i.status] || i.status || 'ainda não verificado') + '</span>' + (i.doc || u.doc ? ' ' + esc(i.doc || u.doc) : '') + (i.data ? ' (' + esc(i.data) + ')' : '') + (i.orgao || u.orgao ? ' · ' + esc(i.orgao || u.orgao) : '') + (i.url ? ' · <a href="' + esc(i.url) + '" target="_blank" rel="noopener">fonte oficial →</a>' : ''))
    /* Bloco B.3 do handover de 02/10/2026: a coordenação aparece em DUAS linhas, em linguagem
     * de leitor. O leitor não precisa saber que internamente são F1 e F2; precisa saber que
     * são duas coisas diferentes, e qual documento sustenta cada uma. Função não procurada
     * aparece como não verificada, nunca como ausência de estrutura. */
    + (() => {
        const co = u.coordenacao || {};
        const descreve = (o, rotulo_vazio) => {
          if (!o || !o.doc) return rotulo_vazio;
          return '<span class="pill-nivel">' + esc(ST_COORD[o.status] || o.status || '—') + '</span> '
            + esc(o.doc) + (o.data ? ' (' + esc(o.data) + ')' : '')
            + (o.url ? ' · <a href="' + esc(o.url) + '" target="_blank" rel="noopener">fonte oficial →</a>' : '');
        };
        const f1 = co.f1 || (co.status ? co : null);
        return linha('Coordenação na saúde', descreve(f1, 'ainda não verificada'))
          + linha('Ligação com o governo do estado', descreve(co.f2, 'ainda não verificada'));
      })()
    /* O handover de 02/10/2026 tirou a palavra "antecipação" da ficha: ela é nome interno de
     * componente, e o que o número mede é quando o ato saiu em relação ao primeiro boletim. */
    + (m.verificado ? linha('Como o número é formado', [
        'documento estadual ' + esc(decBR(i.pontos)),
        ...(pesaSaude('cobertura') ? ['cobertura sanitária ' + esc(decBR(c.pontos) ?? '—') + ' (' + esc(c.planos_lidos ?? 0)
          + (Number(c.planos_lidos ?? 0) === 1 ? ' plano municipal lido, ' : ' planos municipais lidos, ') + esc(c.planos_sem_leitura ?? 0) + ' sem leitura)'] : []),
        'quando o ato saiu em relação ao primeiro boletim ' + esc(decBR(a.pontos)),
      ].join(' · ') + ' → média ' + String(m.prontidao).replace('.', ',')
        + (pesosIguaisSaude() ? ' (pesos iguais)' : '')) : '')
    /* A camada de peso zero tem linha própria, rotulada, como o plano decenal já tinha: o leitor vê
     * o que foi medido e que aquilo não entra na nota. */
    + (m.verificado && !pesaSaude('cobertura')
        ? linha('Saúde no plano municipal de defesa civil', esc(camadaMunicipalSaude(c)) + '; publicada ao lado da nota, não pontua') : '')
    + (m.camada === 'adaptacao' ? linha('Plano decenal de adaptação', 'registrado como estrutura; não pontua') : '')
    + linha('Resposta sanitária', ((RS || {}).ufs || []).includes(uf) ? 'emergência sanitária declarada no ciclo' : 'nenhuma emergência sanitária declarada localizada desde 29/06/2026')
    + linha('Risco sanitário projetado', (m.risco_projetado || []).length ? (m.risco_projetado || []).map(esc).join('; ') : 'sem registro')
    + linha('Dengue na capital', dc.dengue_capital_nivel != null ? 'nível ' + esc(dc.dengue_capital_nivel) + ' (InfoDengue), ' + esc(dc.dengue_capital || '') + (semanaDengue ? ', na semana ' + semanaDengue : '') : 'sem coleta');
  const dlg = document.getElementById('detailSaude');
  if (!dlg) return;
  dlg.setAttribute('aria-label', 'Detalhe do estado');
  if (!dlg.open) { if (typeof dlg.showModal === 'function') dlg.showModal(); else dlg.open = true; }
}

function cartoesEstadosSaude(){
  /* Item 7 do handover de 02/10/2026: os 27 estados no MESMO componente da inicial — o mapa de
   * cartões, cada estado na sua posição geográfica, com sigla, nome, número e uma barra (a resposta tem medidor próprio no topo). Antes
   * eram colunas por região, com outro desenho: dois componentes para a mesma coisa divergem na
   * primeira correção. A disposição, o teclado e o estilo vivem em assets/js/grade-estados.js.
   */
  const wrap = document.getElementById('regionsSaude'), dlg = document.getElementById('detailSaude');
  if (!wrap || !dlg || !window.GradeEstados) return;
  const M = (MSAUDE && MSAUDE.ufs) || {};
  fetch('data/estados.json').then(r => r.ok ? r.json() : null).then(E => {
    const lista = ((E && E.ufs) || []).map(u => ({uf: u.uf, nome: u.nome, status: u.status}));
    (E && E.ufs || []).forEach(u => { NOMES[u.uf] = u.nome; REG[u.uf] = u.regiao; });
    GradeEstados.montar({
      alvo: wrap, ufs: lista, rotulo: 'MARÉ Saúde',
      indice: uf => { const m = M[uf] || {}; return m.verificado ? m.prontidao : null; },
      aoClicar: uf => abrirDetalheSaude(uf),
    });
    if (window.MonitorMapas && MonitorMapas.animarGauges) MonitorMapas.animarGauges(wrap);
  }).catch(_erroSaude("saude:440"));
}
__load().then(cartoesEstadosSaude).catch(err => { const m = document.getElementById('subSaude'); if (m) m.insertAdjacentHTML('afterend', '<p class="note u-rust">Erro ao carregar os dados: '+esc(err.message)+'</p>'); });

window.addEventListener('load', function(){ if (window.VLibras && window.VLibras.Widget) { try { new window.VLibras.Widget('https://vlibras.gov.br/app'); } catch (e) {} } });




// 13/09/2026 (proposta de enxugamento, Manus AI): renderEstrutura() (catálogo de 20 desfechos e
// tabela de gatilhos, §36) migrou por completo para pesquisadores.js.



/* ===== Cartões e figuras criados pelo contrato de layout (02/10/2026) =====
 * Um só lugar para o que o contrato acrescentou: o número do índice no topo, a lista do que foi
 * localizado em cada estado, o mapa do risco previsto, o mapa de síndrome respiratória grave por
 * estado, a distribuição do calor por classe e as três buscas por município.
 */
(function cartoesDoContrato(){
  const el = id => document.getElementById(id);
  const n = v => Number(v || 0).toLocaleString('pt-BR');
  const umaCasa = v => Number(v || 0).toLocaleString('pt-BR', {minimumFractionDigits: 1, maximumFractionDigits: 1});
  const esc = v => String(v == null ? '' : v).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const UFS = ('AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO').split(' ');

  /* 1 · O topo (HANDOVER_SAUDE_PAGINA §1.2): os dois medidores da inicial. À esquerda, o MARÉ Saúde
   * NACIONAL, sobre as 27 UFs, ponderado pela população (v0.7, METODOLOGIA §123); à direita, a
   * parcela da população sob decreto de emergência em saúde, no vocabulário do medidor da inicial.
   * Sem dado, o número e o "/ 100" ficam vazios e a linha diz UMA vez "sem coleta até o corte". */
  const T = (id, v) => (window.MonitorCatalogo && MonitorCatalogo.texto(id, v)) || '';
  const escreve = (id, chave, v) => window.MonitorCatalogo && MonitorCatalogo.escrever(id, chave, v);
  fetch('data/monitor_saude.json').then(r => r.ok ? r.json() : null).then(MS => {
    const res = ((MS || {}).resumo) || {}, rp = ((MS || {}).resposta) || {};
    const fixa = (id, v, nome) => { const f = el(id); f.dataset.alvo = String(v); f.style.setProperty('--galvo', String(Math.max(v, 0.1)));
      f.closest('.gauge-track').setAttribute('aria-label', 'Barra de progresso: ' + nome + ' em ' + umaCasa(v) + ' de 100'); };
    const media = res.indice_nacional;
    /* Ausência se escreve em palavras, inclusive no número grande (layout/regras.json, numeros):
       um travessão no lugar do índice deixaria o leitor sem saber se é zero ou se não houve coleta. */
    if (media == null) { el('nIndiceSaude').textContent = 'sem coleta'; el('linhaPreparoSaude').textContent = 'sem coleta até o corte'; }
    else {
      el('nIndiceSaude').textContent = umaCasa(media); el('nIndiceSaude').dataset.contar = media;
      el('faixaSaude').replaceChildren(MonitorMapas.pilulaDaFaixa(media));
      fixa('gaugeFillSaude', media, 'MARÉ Saúde');
      /* A linha ao lado conta o ESTATUTO, nas palavras da classe: estado sem plano localizado e
         estado ainda não verificado são coisas distintas, e integrar o nacional não apaga a lacuna. */
      if (window.MonitorCatalogo) MonitorCatalogo.pronto.then(() =>
        escreve('linhaPreparoSaude', 'saude.topo.preparacao.linha', {
          com_plano: n(res.ufs_com_plano_localizado), denominador: n(res.denominador || 27),
          sem_numero: res.nao_verificadas, corte: (MS || {}).corte || ''}));
    }
    if (rp.indice != null) {
      el('respNumSaude').textContent = umaCasa(rp.indice); el('respNumSaude').dataset.contar = rp.indice;
      el('respDenSaude').textContent = '/ 100';
      fixa('respFillSaude', rp.indice, 'decretos de emergência em saúde');
    }
    if (window.MonitorCatalogo) MonitorCatalogo.pronto.then(() => {
      if (rp.indice == null) return;   // a reserva do HTML ("sem coleta até o corte") já é a linha
      el('respBadgeSaude').innerHTML = '<span class="gfaixa-pill">' + esc(T('saude.topo.resposta.pilula', {
        n: rp.emergencias || 0, pct: umaCasa(100 * (rp.pop_sob_emergencia || 0) / (rp.pop_total || 1))})) + '</span>';
      escreve('linhaRespostaSaude', 'saude.topo.resposta.linha', {quando: (MS || {}).gerado_em || (MS || {}).corte || ''});
    });
    MonitorMapas.animarGauges(el('topoSaude'));
  }).catch(_erroSaude("saude:topo"));

  /* 2 · Os cartões do topo (editoria, 24/10/2026): dengue, chikungunya e internações respiratórias
   * graves vêm de `topo_saude.json`, que traz a semana consolidada, o valor do país e QUANTOS
   * estados estão acima da faixa habitual pela MESMA função que o detalhe usa. Nada é recalculado
   * aqui. País sem semana fechada em comum às 27 UFs é lacuna declarada, nunca soma de semanas
   * diferentes. O calor não é desfecho: é exposição, e vira a linha de contexto abaixo da fileira. */
  Promise.all([MonitorCatalogo.pronto, fetch('data/saude_desfechos/topo_saude.json').then(r => r.ok ? r.json() : null),
               fetch('data/saude_sinais.json').then(r => r.ok ? r.json() : null)]).then(([, TS, SS]) => {
    const D = (TS || {}).desfechos || {}, cartao = id => ((TS || {}).cartoes || []).find(c => c.id === id) || {};
    const fonte = (idf, chave, dia) => escreve(idf, 'saude.numerosSaude.fonte.molde',
      {fonte: T(chave), data: MonitorMapas.dataBR(dia) || dia || ''});
    [['dengue', 'nDengueSE', 'estadosDengueSE', 'semanaDengueSE', 'fonteDengueSE', 'n_dengue_se'],
     ['chikungunya', 'nChikSE', 'estadosChikSE', 'semanaChikSE', 'fonteChikSE', 'n_chik_se'],
     ['srag', 'nSragSE', 'estadosSragSE', 'semanaSragSE', 'fonteSragSE', 'n_srag_se']].forEach(([d, nid, eid, sid, fid, chave]) => {
      const x = D[d];
      if (!x) return;
      el(nid).textContent = x.valor_br == null ? T('saude.numerosSaude.valor.lacuna') : _qtdCartao(x.valor_br);
      escreve(eid, 'saude.numerosSaude.estados_acima.molde', {k: x.ufs_acima_faixa, total: x.ufs_comparadas});
      if (x.periodo) escreve(sid, 'saude.numerosSaude.semana.molde', {datas: semanaEmDatas(null, x.periodo)});
      else escreve(sid, 'saude.numerosSaude.semana.lacuna');
      fonte(fid, 'saude.numerosSaude.' + chave + '.fonte', x.consultado_em);
    });
    const al = cartao('uf_dengue_alerta');
    if (al.valor != null) {
      el('nUFsAlerta').textContent = _qtdCartao(al.valor) + ' de ' + n((D.dengue || {}).ufs_comparadas || 27);
      fonte('fonteUFsAlerta', 'saude.numerosSaude.n_u_fs_alerta.fonte', (TS || {}).gerado_em);
    }
    const C = ((SS || {}).calor_excesso) || {}, r = C.resumo;
    if (r) escreve('linhaCalorSaude', 'saude.numerosSaude.calor_contexto.molde', {
      n: Number(r.severo || 0) + Number(r.extremo || 0), total: C.municipios_lidos || Object.keys(C.municipios || {}).length,
      fonte: T('saude.numerosSaude.calor_contexto.fonte'), data: MonitorMapas.dataBR(C.data) || C.data || ''});
    else escreve('linhaCalorSaude', 'saude.numerosSaude.calor_contexto.lacuna');
  }).catch(_erroSaude("saude:cartoes-do-topo"));

  /* A figura "O que foi localizado em cada estado" (lista dos 27) saiu da página em
   * 19/10/2026 (HANDOVER_SAUDE_PAGINA §2.6 e §7): o documento, o órgão e a data de cada
   * estado abrem na ficha do estado, pelo mapa e pela grade. */

  /* 3 · Risco previsto por estado (HANDOVER_SAUDE_PAGINA §2.5): as famílias dos boletins do Painel
   * El Niño em etiquetas de sigla, o mesmo componente do Monitor de riscos. */
  fetch('data/saude_uf.json').then(r => r.ok ? r.json() : null).then(SUFd => {
    const dl = el('faixaRiscoSan');
    if (!dl || !SUFd || !window.MonitorMapas) return;
    const fam = uf => {
      const r = (((SUFd.uf || {})[uf] || {}).risco_sanitario_projetado || []).join(' ').toLowerCase();
      const s = /calor|queimad|arbovir|estiagem|seca/.test(r), c = /leptospir|diarre|hepatite|chuva/.test(r);
      return s && c ? 'multi' : s ? 'seca' : c ? 'chuvas' : 'nenhum';
    };
    MonitorMapas.faixaPrevista(dl, [['Seca, calor e fogo', 'seca'], ['Chuvas extremas', 'chuvas'],
      ['As duas famílias', 'multi'], ['Sem risco previsto registrado', 'nenhum']]
      .map(([rotulo, f]) => [rotulo, UFS.filter(uf => fam(uf) === f)]));
    // O dado não traz a numeração dos boletins lidos: a frase não a fixa (nº 1 a 3 envelhecia).
    MonitorMapas.credito('boxRiscoSan', {fontes: ['Painel El Niño 2026-2027 (CEMADEN/INPE)'], data: SUFd.corte});
  }).catch(_erroSaude("saude:1136"));

  /* 6 · Consulta do município (HANDOVER_SAUDE_PAGINA §4): uma só, no componente comum. Dengue,
   * chikungunya, calor e plano vêm de `data/saude_municipio/<UF>.json`, por código IBGE; município
   * sem bloco não foi lido pela fonte, e é dito assim, nunca zero. Respiratória grave e o MARÉ Saúde
   * são do estado, e a linha diz que são. */
  const NIVEL = {1: 'nível 1 (baixa atividade)', 2: 'nível 2 (atenção)', 3: 'nível 3 (alerta)', 4: 'nível 4 (emergência)'};
  const semana = v => { const m = /(\d{4})-(\d{1,2})/.exec(String(v || '')); return (m && MonitorSemana.porExtenso(+m[1], +m[2], true)) || ''; };
  const porUF = {}, extra = Promise.all(['data/monitor_saude.json', 'data/saude_desfechos/srag_serie.json']
    .map(f => fetch(f).then(r => r.ok ? r.json() : null).catch(() => null)));
  const linha = (rotulo, valor, fonte) => '<tr><th scope="row">' + esc(rotulo) + '</th> <td>' + valor + '</td> <td class="dica-fonte">' + esc(fonte) + '</td></tr>';
  fetch('data/geo_uf.json').then(r => r.json()).then(GEO => ConsultaMunicipio.montar({uf: 'consultaSaudeUF', municipio: 'consultaSaudeMun', lista: 'consultaSaudeLista', cartao: 'consultaSaudeCard',
    estados: Object.fromEntries(GEO.features.map(f => [f.properties.sigla, f.properties.name])), semLista: 'Consulta do estado: sem coleta até o corte.',
    municipios: uf => (porUF[uf] = porUF[uf] || Promise.all([fetch('data/saude_municipio/' + uf + '.json').then(r => r.ok ? r.json() : null).catch(() => null), extra]))
      .then(([D, [MS, S]]) => { porUF[uf].dados = {D, MS, S}; return D && Object.values(D.municipios).map(x => x.nome); }),
    mostrar: (uf, nome, card) => {
      const {D, MS, S} = porUF[uf].dados, o = D.origens || {}, m = Object.values(D.municipios).find(x => x.nome === nome);
      const arbo = (x, fonte) => x ? esc(NIVEL[x.nivel] || 'nível ' + x.nivel) + (semana(x.semana) ? ', semana ' + esc(semana(x.semana)) : '')
          + (x.notificacoes ? ' · ' + n(x.notificacoes.casos) + (x.notificacoes.casos === 1 ? ' notificação' : ' notificações') + (semana(x.notificacoes.semana) ? ' na semana ' + esc(semana(x.notificacoes.semana)) : '') : '')
        : 'município não lido pelo ' + esc(fonte) + ' na semana';
      const ano = String((S && S.ano_corrente) || ''), su = S && S.serie && S.serie[uf];
      const srag = su ? Object.entries(su).filter(([k, v]) => k.startsWith(ano) && typeof v === 'number').reduce((t, [, v]) => t + v, 0) : null;
      const e = ((MS || {}).ufs || {})[uf] || {}, pl = m.saude_no_plano;
      card.innerHTML = '<h4>' + esc(nome) + ' · ' + esc(uf) + '</h4><div class="tbl-wrap"><table class="mun-table"><tbody>'
        + linha('Dengue', arbo(m.dengue, 'InfoDengue'), (o.dengue || {}).fonte + ' · ' + ((o.dengue || {}).gerado_em || ''))
        + linha('Chikungunya', arbo(m.chikungunya, 'InfoDengue'), (o.chikungunya || {}).fonte + ' · ' + ((o.chikungunya || {}).gerado_em || ''))
        + linha('Excesso de calor', m.calor ? 'classe ' + esc(m.calor) : 'município não lido na consulta mais recente', (o.calor || {}).fonte + ' · ' + (MonitorMapas.dataBR((o.calor || {}).data) || ''))
        + linha('Síndrome respiratória grave (estado)', srag == null ? 'sem coleta até o corte' : n(srag) + ' internações no estado em ' + esc(ano), 'SIVEP-Gripe (Ministério da Saúde)' + (S && S.gerado_em ? ' · ' + S.gerado_em : ''))
        + linha('MARÉ Saúde (estado)', (e.verificado ? umaCasa(e.prontidao) + ' de 100 · ' + esc(e.faixa || '') : 'estado ainda não verificado') + ' · <a href="#regionsSaude">ver a ficha do estado</a>', 'MARÉ' + (MS && MS.corte ? ' · ' + MS.corte : ''))
        + linha('Plano de contingência do município', (pl ? 'trata a saúde (leitura automática' + (pl.pagina_citada ? ', p. ' + esc(pl.pagina_citada) : '') + ')' + (pl.url ? ' · <a href="' + esc(pl.url) + '" target="_blank" rel="noopener">abrir o plano</a>' : '') : 'sem leitura da saúde no plano até o corte')
          + ' · <a href="index.html#' + esc(uf) + '">ver a ficha na página inicial</a>', (o.saude_no_plano || {}).fonte || 'MARÉ Legal')
        + '</tbody></table></div>';
    }})).catch(_erroSaude("saude:consulta"));

  /* 7 · A lista do governo federal, sem cartão (o contrato pede lista simples). */
  fetch('data/saude_federal.json').then(r => r.ok ? r.json() : null).then(F => {
    const alvo = el('listaFederalSaude');
    if (!alvo) return;
    // 11/10/2026 (HANDOVER_SAUDE item 2): o arquivo guarda a lista em `cartoes`; a página procurava
    // `itens`/`documentos` e dizia "nenhum documento localizado" com oito no arquivo.
    const itens = (F && (F.cartoes || F.itens || F.documentos)) || [];
    if (!itens.length) {
      alvo.innerHTML = '<li>Nenhum documento federal localizado até o corte.</li>';
      return;
    }
    alvo.innerHTML = itens.map(x => {
      // Travessão como pontuação reprova no portão 19; no título do documento vira dois-pontos.
      const nome = esc(String(x.nome || x.titulo || x.documento || 'documento').replace(/\s+—\s+/g, ': '));
      const meta = [x.orgao, x.data].filter(v => v && v !== '—').map(esc).join(' · ');
      const alvoTxt = x.url ? '<a href="' + esc(x.url) + '" target="_blank" rel="noopener">' + nome + '</a>' : nome;
      const nl = x.status === 'anunciado_nao_localizado'
        ? '. Anunciado; documento não localizado até ' + esc(F.corte || 'o corte') + '.' : '';
      return '<li>' + alvoTxt + (meta ? ' <span class="u-muted">(' + meta + ')</span>' : '') + nl + '</li>';
    }).join('');
  }).catch(_erroSaude("saude:1338"));
})();

/* ===== Seção única de desfechos ============================================================
 * HANDOVER_SAUDE_DESFECHOS_BLOCO (editoria, 16/10/2026) e prioridade da editoria de 19/10.
 *
 * Um cartão por desfecho, todos lidos da MESMA forma: `data/saude_desfechos/<id>.json`, como
 * `desfechos_sus.py` a escreve (série por UF, por 100 mil, faixa habitual da época, último
 * período e o último já fechado). A página não sabe de onde veio cada número: o arquivo diz o
 * rótulo, a unidade, a cadência, a fonte e a data.
 *
 * Desfecho sem arquivo na forma comum não vira cartão vazio nem zero — ele ainda não tem cartão.
 * Território sem série no arquivo declara a lacuna da sua classe, com as palavras da classe.
 * Peso zero no índice (METODOLOGIA §8): o Monitor não atribui casos ao El Niño em nenhuma
 * superfície de desfecho — nem no cartão, nem no detalhe, nem na lista por estado.
 */
/* Os seis desfechos em evidência: o nome do arquivo na forma comum e o id do mesmo desfecho no
   catálogo, que é de onde sai o NOME quando ainda não há arquivo para dar o rótulo. */
const DESFECHOS_DA_SECAO = ['dengue', 'chikungunya', 'srag', 'obitos', 'diarreias', 'leptospirose'];
/* A segunda camada (HANDOVER_SAUDE_DESFECHOS_BLOCO §2): cartão igual, nas linhas seguintes, SEM mapa
   e sem detalhe, na ordem em que o dado nasceu. Os demais do catálogo (pele e olhos, saúde mental,
   ICSAP, tuberculose, desnutrição, malária) ficam no catálogo até a editoria pedir cartão. */
const SEGUNDA_CAMADA = ['internacoes_respiratorias', 'internacoes_cardio', 'internacoes_renal',
                        'internacoes_desidratacao', 'hepatite_a', 'internacoes_fumaca', 'internacoes_calor'];
const NO_CATALOGO = {dengue: 'dengue', chikungunya: 'chik', srag: 'srag', obitos: 'obitos',
                     diarreias: 'dda', leptospirose: 'lepto', internacoes_respiratorias: 'ira',
                     internacoes_cardio: 'cardio', internacoes_renal: 'renal',
                     internacoes_desidratacao: 'desidratacao', hepatite_a: 'hepatite_a',
                     internacoes_fumaca: 'intox_fumaca', internacoes_calor: 'calor_agravo'};
const EM_EVIDENCIA = d => DESFECHOS_DA_SECAO.indexOf(d.desfecho) >= 0;
const FAIXA_COR = {acima: MonitorMapas.PALETA.serie_habitual.acima, dentro: MonitorMapas.cor('vazio')};
let DESFECHOS_LIDOS = [], DESFECHO_ESCOLHIDO = null, DESF_CATALOGO = null;
const __graficoDesfecho = {};

/* "2026-08" → "agosto de 2026"; "2026-33" → a semana em datas (a palavra não chega ao leitor). */
function periodoEmPalavras(chave, cadencia) {
  const [ano, parte] = String(chave || '').split('-');
  if (cadencia === 'semana') return semanaEmDatas(Number(ano), chave, false) || '';
  const meses = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto',
                 'setembro', 'outubro', 'novembro', 'dezembro'];
  return (meses[Number(parte) - 1] || '') + ' de ' + ano;
}

/* O mesmo período, curto o bastante para caber numa legenda de 140 caracteres. */
function periodoCompacto(chave, cadencia) {
  if (!chave) return 'sem período fechado';
  if (cadencia !== 'semana') return periodoEmPalavras(chave, cadencia);
  const [ano] = String(chave).split('-');
  const curta = semanaEmDatas(Number(ano), chave, true);
  return curta ? curta + ' de ' + ano : chave;
}

/* A linha dos períodos recentes sobre a faixa habitual, em SVG: polígono da faixa em mineral,
   linha em tinta, último ponto em argila. Sem eixo e sem número: quem mede é o cartão. */
function serieEmSvg(valores, faixas, rotulo, estado) {
  const L = 240, A = 48, n = valores.length;
  if (n < 2) return '';
  const tetos = faixas.map(f => (f && f.p90) || 0);
  const alto = Math.max(1, Math.max.apply(null, valores.concat(tetos).filter(v => v != null)));
  const x = i => (i * L) / (n - 1), y = v => A - (Math.max(0, v || 0) / alto) * (A - 2);
  const faixaCima = faixas.map((f, i) => x(i) + ',' + y(f && f.p90)).join(' ');
  const faixaBaixo = faixas.map((f, i) => x(i) + ',' + y(f && f.mediana)).reverse().join(' ');
  const temFaixa = faixas.some(f => f && f.p90 != null);
  const linha = valores.map((v, i) => (v == null ? null : x(i) + ',' + y(v)))
    .filter(Boolean).join(' ');
  const ultimo = valores[n - 1];
  return '<svg class="cartao-numero-serie" viewBox="0 0 ' + L + ' ' + A + '" preserveAspectRatio="none"'
    + ' role="img" aria-label="' + esc(rotulo) + '">'
    + (temFaixa ? '<polygon points="' + faixaCima + ' ' + faixaBaixo + '" fill="' + MonitorMapas.PALETA.serie_habitual.faixa + '" fill-opacity="0.28"></polygon>' : '')
    + '<polyline points="' + linha + '" fill="none" stroke="' + MonitorMapas.cor('vazio') + '" stroke-width="1.5"></polyline>'
    /* O último período fechado é marcado por um traço vertical, não por um ponto: a caixa é
       esticada (`preserveAspectRatio="none"`) e um círculo sairia deformado. */
    + (ultimo == null ? '' : '<line x1="' + (L - 1) + '" x2="' + (L - 1) + '" y1="' + (y(ultimo) - 4)
       + '" y2="' + (y(ultimo) + 4) + '" stroke="' + (estado === 'acima' ? FAIXA_COR.acima : FAIXA_COR.dentro)
       + '" stroke-width="2"></line>')
    + '</svg>';
}

/* Os períodos recentes do território, na ordem do calendário: 52 semanas ou 24 meses, SEM os
   períodos que o arquivo declara parciais. Eles ainda recebem registro, e desenhá-los faria a
   linha do cartão cair no fim — ao lado de um valor que é o do último período fechado. */
function recorteRecente(d, uf) {
  const parciais = new Set(d.parcial || []);
  const serie = (d.por_100mil || {})[uf] || {};
  const chaves = Object.keys(serie).sort().filter(ch => !parciais.has(ch));
  const quantos = d.periodo === 'semana' ? 52 : 24;
  return chaves.slice(-quantos);
}

function cartaoDesfecho(d, uf) {
  const u = (d.ultimo || {})[uf];
  const fonte = d.fonte || {};
  const cadencia = d.periodo === 'semana' ? ' · por semana · ' : ' · por mês · ';
  const rodape = 'Fonte: ' + esc((fonte.sistema || '').split(',')[0]) + ' · Atualização: ' + esc(MonitorMapas.dataBR(d.coletado_em) || d.coletado_em);
  if (!u || !u.consolidado) {
    return '<div class="cartao-numero cartao-numero--saude">'
      + '<p class="cartao-numero-familia">' + esc(d.rotulo) + '</p>'
      + '<p class="cartao-numero-valor">sem coleta</p>'
      + '<p class="cartao-numero-rotulo">' + esc(d.unidade) + ' por 100 mil' + cadencia
      + 'sem série para este território até o corte</p>'
      + '<p class="cartao-numero-fonte">' + rodape + '</p></div>';
  }
  const c = u.consolidado, chaves = recorteRecente(d, uf);
  const serie = (d.por_100mil || {})[uf] || {}, faixas = (d.faixa_habitual || {})[uf] || {};
  const doAno = ch => faixas[String(ch).split('-')[1]] || null;
  const f = doAno(c.periodo);
  /* Três posições, cada uma dita como é: acima do maior valor esperado, dentro da faixa, ou
     abaixo do menor. Dizer "dentro" de um valor que está abaixo da faixa seria descrever errado
     o que o leitor vê no gráfico. */
  /* A comparação é feita nos MESMOS números que o leitor lê (uma casa decimal): comparar no valor
     cheio escreve "abaixo da faixa habitual (0,2 a 0,2)" para um cartão que mostra 0,2. */
  /* Comparar NO NÚMERO EXIBIDO, lendo de volta o que `decBR` escreveu: a precisão do rótulo varia
     com o tamanho do valor, e repetir aqui a régua do decBR seria copiar a mesma decisão em dois
     lugares — o jeito de os dois nunca divergirem é só um deles decidir. */
  const uma = x => Number(String(decBR(x)).replace(/\./g, '').replace(',', '.'));
  const dentro = !f || f.p90 == null ? null
    : (uma(c.por_100mil) > uma(f.p90) ? 'acima' : (uma(c.por_100mil) < uma(f.mediana) ? 'abaixo' : 'dentro'));
  const texto = !dentro ? 'sem faixa habitual para a época'
    : dentro + ' da faixa habitual (' + decBR(f.mediana) + ' a ' + decBR(f.p90) + ')';
  /* Só o desfecho em evidência abre detalhe (§2): o cartão da segunda camada não é botão, não entra
     na ordem de tabulação e não promete um mapa que a seção não desenha para ele. */
  return '<div class="cartao-numero cartao-numero--saude"'
    + (EM_EVIDENCIA(d) ? ' role="button" tabindex="0" data-desfecho="' + esc(d.desfecho)
        + '" aria-pressed="' + (d.desfecho === DESFECHO_ESCOLHIDO) + '"' : '') + '>'
    + '<p class="cartao-numero-familia">' + esc(d.rotulo) + '</p>'
    + '<p class="cartao-numero-valor">' + esc(_qtdCartao(c.por_100mil)) + '</p>'
    + '<p class="cartao-numero-rotulo">' + esc(d.unidade) + ' por 100 mil' + cadencia
    + esc(periodoEmPalavras(c.periodo, d.periodo)) + '</p>'
    + '<p class="cartao-numero-variacao"' + (dentro === 'acima' ? ' style="color:' + FAIXA_COR.acima + '"' : '')
    + '>' + esc(texto) + '</p>'
    + serieEmSvg(chaves.map(ch => serie[ch]), chaves.map(doAno),
        d.rotulo + ', ' + (d.periodo === 'semana' ? 'últimas 52 semanas' : 'últimos 24 meses')
        + ', sobre a faixa habitual para a época', dentro)
    + '<p class="cartao-numero-fonte">' + rodape + '</p></div>';
}

/* O mapa do detalhe: o último período FECHADO de cada estado, pintado pelos cortes que o próprio
   arquivo traz — os quintis de 2019 a 2025, congelados na primeira gravação (METODOLOGIA §108).
   Cortes congelados são o que permite comparar o mapa de hoje com o de outro dia; recalculá-los a
   cada rodada mudaria a cor sem mudar o dado. Estado sem período fechado fica em sem-dado e a
   legenda nomeia a classe — nunca zero. */
function pintarMapaDoDesfecho(d) {
  const svgId = 'mapaDesfecho';
  if (!document.getElementById(svgId) || !BR_GEOJSON) return;
  const cortes = ((d.cortes_mapa || {}).cortes || []).slice();
  const rampa = MonitorMapas.PALETA.atmosfera.chuva_claro.rampa;
  const faixaDe = v => cortes.reduce((i, corte) => (v > corte ? i + 1 : i), 0);
  const valor = {};
  Object.keys(d.ultimo || {}).forEach(u => {
    const c = (d.ultimo[u] || {}).consolidado;
    if (u !== 'BR' && c && c.por_100mil != null) valor[u] = c.por_100mil;
  });
  const ctx = MonitorMapas.contexto(BR_GEOJSON, 480, 460);
  MonitorMapas.ufs(ctx, svgId,
    u => valor[u] == null ? MonitorMapas.NEUTRA : rampa[Math.min(rampa.length - 1, faixaDe(valor[u]))],
    u => valor[u] == null ? 'sem período fechado até o corte'
      : decBR(valor[u]) + ' ' + d.unidade + ' por 100 mil habitantes');
  const rotuloDaFaixa = i => (i === 0 ? 'até ' + decBR(cortes[0])
    : i === cortes.length ? decBR(cortes[cortes.length - 1]) + ' ou mais'
    : decBR(cortes[i - 1]) + ' a ' + decBR(cortes[i]));
  MonitorMapas.legenda('legMapaDesfecho', rampa.map((cor, i) => ({cor: cor, rotulo: rotuloDaFaixa(i)}))
    .concat([{cor: MonitorMapas.NEUTRA, rotulo: 'sem período fechado'}]));
  const lista = document.getElementById('dlDesfechoUF');
  if (lista) lista.innerHTML = Object.keys(valor).sort((a, b) => valor[b] - valor[a]).map(u =>
    '<dt>' + esc(NOME_UF[u] || u) + '</dt><dd>' + esc(decBR(valor[u])) + ' ' + esc(d.unidade)
    + ' por 100 mil habitantes</dd>').join('');
}

function pintarDesfechos() {
  const grade = document.getElementById('gradeDesfechos');
  const seletor = document.getElementById('ufDesfechos');
  if (!grade || !DESFECHOS_LIDOS.length) return;
  const uf = (seletor && seletor.value) || 'BR';
  const comDetalhe = DESFECHOS_LIDOS.filter(EM_EVIDENCIA);
  if (!comDetalhe.some(d => d.desfecho === DESFECHO_ESCOLHIDO)) DESFECHO_ESCOLHIDO = (comDetalhe[0] || {}).desfecho || null;
  grade.innerHTML = DESFECHOS_LIDOS.map(d => cartaoDesfecho(d, uf)).join('');
  pintarDetalhe(comDetalhe.find(d => d.desfecho === DESFECHO_ESCOLHIDO), uf);
}

/* Um ouvinte na grade, não um por cartão: a grade se repinta inteira a cada troca de território. */
function escolherDesfecho(ev) {
  const alvo = ev.target.closest('[data-desfecho]');
  if (!alvo || (ev.type === 'keydown' && ev.key !== 'Enter' && ev.key !== ' ')) return;
  if (ev.type === 'keydown') ev.preventDefault();
  DESFECHO_ESCOLHIDO = alvo.getAttribute('data-desfecho');
  pintarDesfechos();
}

/* O detalhe do cartão escolhido: a série inteira do território sobre a faixa habitual da época.
   Um detalhe por vez — escolher outro cartão troca o conteúdo, e a página não cresce. */
function pintarDetalhe(d, uf) {
  const fig = document.getElementById('boxDesfecho'), cv = document.getElementById('cDesfecho');
  if (!fig || !cv || !window.Chart) return;
  /* Sem desfecho escolhido não há o que detalhar: a figura recolhe, e declara a lacuna na própria
     linha de fonte — sem nomear sistema que não foi lido. Moldura vazia e muda é o pior desfecho. */
  if (!d) {
    fig.hidden = true;
    fonteFigura('boxDesfecho', {fontes: ['os sistemas de registro declarados em cada desfecho'], data: null});
    return;
  }
  fig.hidden = false;
  /* Só período FECHADO, na linha e no mapa: período parcial ainda recebe registro e, comparado
     com a faixa habitual, desenha queda onde há notificação a caminho. */
  const parciais = new Set(d.parcial || []);
  const chaves = Object.keys((d.por_100mil || {})[uf] || {}).sort().filter(ch => !parciais.has(ch));
  const serie = (d.por_100mil || {})[uf] || {}, faixas = (d.faixa_habitual || {})[uf] || {};
  const doAno = ch => faixas[String(ch).split('-')[1]] || {};
  /* Eixo em meses, como manda a régua do site; o período inteiro, por extenso, fica no texto do
     mouse — a série pode ter oito anos de semanas, e o rótulo por extenso não cabe no eixo. */
  const MES3 = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez'];
  const noEixo = ch => {
    if (d.periodo !== 'semana') return MES3[Number(ch.split('-')[1]) - 1] + '/' + ch.split('-')[0];
    const por = periodoEmPalavras(ch, 'semana').match(/de (\w+) de (\d{4})$/);
    return por ? por[1].slice(0, 3) + '/' + por[2] : ch;
  };
  const rotulos = chaves.map(noEixo);
  const C = window.MonitorCatalogo;
  const campo = (id, texto) => { const el = document.getElementById(id); if (el) el.textContent = texto; };
  const molde = (chave, vals) => (C && C.texto('saude.observado.registram.detalhe.' + chave, vals)) || '';
  const anos = chaves.length ? (chaves[0].split('-')[0] + ' a ' + chaves[chaves.length - 1].split('-')[0]) : 'sem série';
  campo('tituloDesfecho', molde('titulo', {desfecho: d.rotulo,
    territorio: uf === 'BR' ? 'Brasil' : NOME_UF[uf], periodo: anos}));
  const ultimoBR = ((d.ultimo || {}).BR || {}).consolidado || {};
  campo('legendaDesfecho', molde('legenda', {
    periodo: periodoCompacto(ultimoBR.periodo, d.periodo),
    parciais: (d.parcial || []).length
      ? 'os ' + (d.parcial || []).length + ' períodos ainda em registro ficam fora'
      : 'série fechada até o último período'}));
  MonitorMapas.padraoGraficos(window.Chart);
  if (__graficoDesfecho.g && typeof __graficoDesfecho.g.destroy === 'function') __graficoDesfecho.g.destroy();
  __graficoDesfecho.g = new Chart(cv, {data: {labels: rotulos, datasets: [
      {type: 'line', label: 'valor observado', data: chaves.map(ch => serie[ch] ?? null),
       borderColor: MonitorMapas.cor('vazio'), borderWidth: 1.5, pointRadius: 0, order: 1},
      /* A faixa é uma FAIXA, não duas linhas: o traço de cima preenche até o de baixo, como a
         legenda aprovada diz ("faixa cinza") e como a linha dentro do cartão já desenha. */
      {type: 'line', label: 'faixa habitual para a época', fill: '+1',
       data: chaves.map(ch => doAno(ch).p90 ?? null), borderColor: MonitorMapas.PALETA.serie_habitual.faixa,
       backgroundColor: MonitorMapas.PALETA.serie_habitual.faixa_fundo, borderWidth: 1, pointRadius: 0, order: 2},
      {type: 'line', label: 'faixa habitual para a época',
       data: chaves.map(ch => doAno(ch).mediana ?? null), borderColor: MonitorMapas.PALETA.serie_habitual.faixa,
       borderWidth: 1, pointRadius: 0, order: 2}]},
    options: {animation: false, responsive: true, maintainAspectRatio: false,
      plugins: {legend: {display: false},
        tooltip: {callbacks: {title: it => periodoEmPalavras(chaves[it[0].dataIndex], d.periodo)}}},
      scales: {x: {ticks: {maxTicksLimit: 8, autoSkip: true}},
               y: {beginAtZero: true, title: {display: true, text: d.unidade + ' por 100 mil'}}}}});
  MonitorMapas.legenda('legDesfecho', [
    {cor: MonitorMapas.cor('vazio'), rotulo: 'valor observado'},
    {cor: MonitorMapas.PALETA.serie_habitual.faixa, rotulo: 'faixa habitual para a época (2019–2025)'}]);
  pintarMapaDoDesfecho(d);
  /* O gráfico nasce antes de o mapa ocupar a segunda coluna da figura dupla: sem este ajuste, a
     tela do Chart.js guarda a largura da figura inteira e passa por cima do mapa. */
  if (__graficoDesfecho.g && typeof __graficoDesfecho.g.resize === 'function') __graficoDesfecho.g.resize();
  fonteFigura('boxDesfecho', {fontes: [(d.fonte || {}).sistema], data: d.coletado_em, url: (d.fonte || {}).url});
}

/* Desfecho em evidência que ainda não tem arquivo na forma comum não vira cartão vazio: a seção
   declara a lacuna da CLASSE numa linha, e o nome vem do catálogo dos desfechos — não daqui.
   Enquanto nenhum faltar, a linha não existe. */
function declararDesfechoSemArquivo(lidos) {
  const linha = document.getElementById('desfechosLacuna'), C = window.MonitorCatalogo;
  if (!linha || !C) return;
  const temArquivo = new Set((lidos || []).filter(Boolean).map(d => d.desfecho));
  const faltam = DESFECHOS_DA_SECAO.filter(id => !temArquivo.has(id)).map(id => NO_CATALOGO[id]);
  if (!faltam.length || !DESF_CATALOGO) { mostrarFrase(linha, ''); return; }
  const nomes = (DESF_CATALOGO.desfechos || [])
    .filter(x => faltam.indexOf(x.id) >= 0)
    .map(x => String(x.nome || '').replace(/\s*\(.*\)\s*$/, ''))
    .map((nome, i) => (i === 0 ? nome : nome.charAt(0).toLowerCase() + nome.slice(1)));
  const lista = nomes.length > 1 ? nomes.slice(0, -1).join(', ') + ' e ' + nomes[nomes.length - 1] : nomes[0];
  mostrarFrase(linha, nomes.length ? C.texto('saude.observado.registram.lacuna', {faltam: lista}) : '');
}

async function montarDesfechos() {
  const grade = document.getElementById('gradeDesfechos');
  if (!grade) return;
  if (window.MonitorCatalogo && window.MonitorCatalogo.pronto) { try { await window.MonitorCatalogo.pronto; } catch (e) {} }
  const lidos = await Promise.all(DESFECHOS_DA_SECAO.concat(SEGUNDA_CAMADA).map(id =>
    fetch('data/saude_desfechos/' + id + '.json').then(r => (r.ok ? r.json() : null)).catch(() => null)));
  DESF_CATALOGO = await fetch('data/saude_desfechos/catalogo.json')
    .then(r => (r.ok ? r.json() : null)).catch(() => null);
  DESFECHOS_LIDOS = lidos.filter(d => d && d.esquema === 1 && d.ultimo && d.por_100mil);
  const bloco = document.getElementById('desfechos');
  if (!DESFECHOS_LIDOS.length) { if (bloco) bloco.hidden = true; pintarDetalhe(null); return; }   // bloco inteiro recolhido: a lacuna não aparece sozinha numa seção sem grade
  if (bloco) bloco.hidden = false;
  declararDesfechoSemArquivo(lidos);
  const seletor = document.getElementById('ufDesfechos');
  if (seletor && !seletor.options.length) {
    seletor.innerHTML = '<option value="BR">Brasil</option>'
      + UFS.map(u => '<option value="' + u + '">' + esc(NOME_UF[u]) + '</option>').join('');
    seletor.addEventListener('change', pintarDesfechos);
  }
  grade.addEventListener('click', escolherDesfecho);
  grade.addEventListener('keydown', escolherDesfecho);
  pintarDesfechos();
}
