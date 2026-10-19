/* A7-17 (12/10/2026): erro de bloco que não renderiza não é engolido em silêncio — vai ao
   console com o lugar, onde o portão de runtime e quem abre o DevTools o veem. */
function _erroSaude(onde) { return function (e) { try { console.error("[MARÉ] falha em " + onde + ":", e); } catch (_) {} }; }
/* A7-14 (12/10/2026): número de cartão pela régua de `layout/regras.json` (numeros) — zero medido
   se escreve por extenso, e ausência de dado nunca vira zero. */
function _qtdCartao(v) {
  if (v === null || v === undefined || v === '') return 'sem dado';
  const x = Number(v);
  if (!Number.isFinite(x)) return 'sem dado';
  return x === 0 ? 'zero' : x.toLocaleString('pt-BR');
}
// ===== saude.html · bloco 1 (extraído em 06/09/2026, CSP sem unsafe-inline) =====
let BR_GEOJSON, SUF, SSIN, SINAIS, MARE, MSAUDE, DESF, DESF_CANAL, DESF_COMP, PAINEL_LISTA;
// Lote 6, §2: a frase do dado nasce oculta e só aparece com texto — nunca "—" nem linha vazia.
const mostrarFrase = (alvo, texto) => { alvo.textContent = texto; alvo.hidden = !texto; };
/* Número em texto público com vírgula decimal (A4-16); não-número passa como veio ("—", nulo). */
const decBR = v => (v == null || v === '' || isNaN(Number(v))) ? v : Number(v).toLocaleString('pt-BR', {maximumFractionDigits: 1});

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
  const n = Number(String(chave).split('-')[1]);
  const a = Number(ano || String(chave).split('-')[0]);
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
let DESF_CHIK = null, DESF_CANAL_CHIK = null;
const DOENCAS_DESF = {
  dengue:      {rotulo: 'dengue',      dados: () => ({serie: DESF,      canal: DESF_CANAL}),      capitais: true},
  chikungunya: {rotulo: 'chikungunya', dados: () => ({serie: DESF_CHIK, canal: DESF_CANAL_CHIK}), capitais: false}   // sem série por capitais ainda (coletar_saude.py é só dengue)
};
let desenharComparadorSemanal = null;   // 13/09/2026 (auditoria de visualizações, consolidação): fechamento com o desenho do comparador "semanal por capitais", preenchido em __init(), chamado pelo seletor em renderDesfechos()
const UFS = ["AC","AL","AM","AP","BA","CE","DF","ES","GO","MA","MG","MS","MT","PA","PB","PE","PI","PR","RJ","RN","RO","RR","RS","SC","SE","SP","TO"];
const NOME_UF = {AC:'Acre',AL:'Alagoas',AM:'Amazonas',AP:'Amapá',BA:'Bahia',CE:'Ceará',DF:'Distrito Federal',ES:'Espírito Santo',GO:'Goiás',MA:'Maranhão',MG:'Minas Gerais',MS:'Mato Grosso do Sul',MT:'Mato Grosso',PA:'Pará',PB:'Paraíba',PE:'Pernambuco',PI:'Piauí',PR:'Paraná',RJ:'Rio de Janeiro',RN:'Rio Grande do Norte',RO:'Rondônia',RR:'Roraima',RS:'Rio Grande do Sul',SC:'Santa Catarina',SE:'Sergipe',SP:'São Paulo',TO:'Tocantins'};
const NEUTRA = MonitorMapas.cor('sem-dado');
const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const { showTip, hideTip } = MonitorMapas;

async function __load(){
  [BR_GEOJSON, SUF, SSIN, SINAIS, MARE, MSAUDE] = await Promise.all(
    ['geo_uf','saude_uf','saude_sinais','sinais_risco','indice','monitor_saude'].map(f => fetch('data/' + f + '.json').then(r => {
      if(!r.ok) throw new Error('Falha ao carregar data/' + f + '.json'); return r.json(); })));
  try { [DESF, DESF_CANAL, DESF_COMP, PAINEL_LISTA] = await Promise.all(['data/saude_desfechos/serie_painel.json','data/saude_desfechos/canal_endemico.json','data/saude_desfechos/completude.json','data/municipios_ibge_referencia.json'].map(f => fetch(f).then(r => r.ok ? r.json() : null))); } catch(e) { DESF = DESF_CANAL = DESF_COMP = PAINEL_LISTA = null; }
  try { [DESF_CHIK, DESF_CANAL_CHIK] = await Promise.all(['data/saude_desfechos/chik_serie_painel.json','data/saude_desfechos/chik_canal_endemico.json'].map(f => fetch(f).then(r => r.ok ? r.json() : null))); } catch(e) { DESF_CHIK = DESF_CANAL_CHIK = null; }
  // 19/10/2026 (HANDOVER_SAUDE_DESFECHOS_BLOCO): as séries dos desfechos deixam de ser carregadas
  // aqui. Quem as lê é a seção "O que os órgãos de saúde registram", ao fim deste arquivo, e cada
  // uma só é buscada quando o cartão dela é desenhado.
  __init();
  secaoDosDesfechos();   // 19/10/2026: a seção dos desfechos, com a malha e a lista já em mão
  // 02/10/2026 (bloco A.3): a amostra de 313 municípios saiu do mapa e a série duplicada saiu da
  // página. Dengue e chikungunya são contadas pelo SINAN, na seção dos desfechos ao fim do arquivo.
  try { titulosFatoSaude(); } catch (e) {}   // 15/09/2026 (§2.10): depois de tudo carregado

    /* Contadores do topo (bloco C.1 do handover de 01/10/2026).
     *
     * Cada um conta DOCUMENTO LIDO, não categoria: "plano localizado" é a UF cujo instrumento tem
     * documento no banco, e "coordenação" é a UF cujo degrau de coordenação tem documento. A
     * diferença importa porque categoria muda de régua (foi o que a v0.4 fez) e documento lido não.
     * Enquanto as 27 não estiverem verificadas, a linha de fonte diz quantas faltam — em vez de
     * deixar o leitor ler 21 como se fosse o país inteiro. */
  (function contadoresDoTopo(){
      const el = id => document.getElementById(id);
      const n = v => Number(v || 0).toLocaleString('pt-BR');
      const ufs = (MSAUDE && MSAUDE.ufs) || {};
      const comPlano = Object.values(ufs).filter(u => u && u.instrumento && u.instrumento.doc).length;
      const verificadas = (MSAUDE && MSAUDE.resumo && MSAUDE.resumo.verificadas) || 0;
      const faltam = 27 - verificadas;
      if (el('nPlanoSaude')) {
        el('nPlanoSaude').textContent = n(comPlano) + ' de 27';
        el('fontePlanoSaude').textContent = 'Documento oficial lido em cada estado · '
          + (faltam > 0 ? faltam + (faltam === 1 ? ' estado ainda não verificado' : ' estados ainda não verificados') : 'as 27 verificadas');
      }
      if (el('nCoordSaude')) {
        /* A coordenação vive no arquivo da v0.4, que é quem a mede. Sem ele, o cartão diz que não
         * há coleta — nunca zero. */
        fetch('data/monitor_saude_v04.json').then(r => r.ok ? r.json() : null).then(V => {
          const u = (V && V.uf) || null;
          if (!u) { el('nCoordSaude').textContent = '—';
                    el('fonteCoordSaude').textContent = 'Sem coleta até o corte.'; return; }
          const comCoord = Object.values(u).filter(x => x && x.coordenacao && x.coordenacao.doc).length;
          el('nCoordSaude').textContent = n(comCoord) + ' de 27';
          el('fonteCoordSaude').textContent = 'Ato de criação ou de ativação lido em cada estado · '
            + 'sala de situação ou centro de operações de emergência';
        }).catch(_erroSaude("saude:125"));
      }
      // O cartão "Resposta" saiu dos números em 19/10/2026 (HANDOVER_SAUDE_PAGINA §1.3 e §7): a
      // emergência em saúde pública tem medidor próprio no topo, e zero não vira cartão.
    })();

}

const fonteFigura = MonitorMapas.credito;

function __init(){
  const ctx = MonitorMapas.contexto(BR_GEOJSON, 480, 460); const projection = ctx.projection;
  const desenharMapa = (svgId, legendaId, corDe, rotuloDe, itens) => MonitorMapas.desenharMapa(ctx, svgId, legendaId, corDe, rotuloDe, itens);

  // 13/09/2026 (proposta de enxugamento, Manus AI): 'Escolha um estado' logo após o título — perfil
  // resumido usando dados já carregados (MSAUDE.ufs), sem fetch novo. Não substitui as tabelas e
  // mapas nacionais abaixo (que seguem servindo a comparação entre estados); é um atalho para quem
  // já sabe qual estado quer ver primeiro.
  (function(){
    const sel = document.getElementById('selEstadoSaude');
    if (!sel) return;
    UFS.slice().sort((a, b) => (NOME_UF[a] || a).localeCompare(NOME_UF[b] || b)).forEach(uf => {
      const o = document.createElement('option'); o.value = uf; o.textContent = (NOME_UF[uf] || uf) + ' (' + uf + ')'; sel.appendChild(o);
    });
    sel.addEventListener('change', () => renderPerfilEstado(sel.value));   // (seletor retirado do HTML em 15/09/2026; cartões por estado no lugar)
  })();
  function renderPerfilEstado(uf){
    const alvo = document.getElementById('perfilEstadoSaude');
    if (!alvo) return;
    if (!uf) { alvo.hidden = true; alvo.innerHTML = ''; return; }
    const m = (MSAUDE && MSAUDE.ufs && MSAUDE.ufs[uf]) || {};
    const riscos = (m.risco_projetado || []);
    const dc = m.risco_atual || {};
    const cartaoCondicoes = '<div class="cartao"><h3 class="figura-titulo">Condições de risco projetadas</h3>'
      + (riscos.length ? '<p class="card-body">' + riscos.map(esc).join(', ') + '</p>' : '<p class="card-body u-muted">Ainda não verificado.</p>') + '</div>';
    const cartaoSinal = '<div class="cartao"><h3 class="figura-titulo">Sinal mais recente: dengue na capital</h3>'
      + (dc.dengue_capital_nivel != null ? '<p class="card-body">Nível ' + dc.dengue_capital_nivel + ' (InfoDengue), ' + esc(dc.dengue_capital || '') + ', SE ' + esc(String(dc.dengue_se || '—')) + '.</p>' : '<p class="card-body u-muted">Ainda não coletado.</p>') + '</div>';
    const cartaoCobertura = '<div class="cartao"><h3 class="figura-titulo">Cobertura do dado</h3>'
      + '<p class="card-body">Sinal de dengue: só a capital, não o estado inteiro. Documento estadual: ' + (m.verificado ? 'verificado' : 'ainda não verificado') + '.</p></div>';
    const cartaoInstitucional = '<div class="cartao"><h3 class="figura-titulo">MARÉ Saúde do estado</h3>'
      + (m.prontidao != null ? '<p class="card-body">' + decBR(m.prontidao) + '/100 · ' + esc(m.faixa || '—') + ' — mede documento e quando o ato saiu, não o estado de saúde da população.</p>' : '<p class="card-body u-muted">Ainda não verificado.</p>') + '</div>';
    alvo.innerHTML = '<h3 class="figura-titulo u-largura-total">' + esc(NOME_UF[uf] || uf) + '</h3>' + cartaoCondicoes + cartaoSinal + cartaoCobertura + cartaoInstitucional;
    alvo.hidden = false;
  }

  // 0 · MARÉ · Saúde (v0.3, Metodologia §31): prontidão = média (instrumento, cobertura populacional sanitária, antecipação); não verificada = cinza, sem número
  (function(){
    const M = (MSAUDE && MSAUDE.ufs) || {};
    const FX = {'estágio inicial': MonitorMapas.PALETA.faixas.inicial, 'em construção': MonitorMapas.PALETA.faixas.construcao, 'consolidado': MonitorMapas.PALETA.faixas.consolidado, 'avançado': MonitorMapas.PALETA.faixas.avancado, 'não verificado': MonitorMapas.PALETA.faixas.nao_verificado};
    const ST_H = {NOVO:'novo, do ciclo', READ:'readaptado', VIG:'vigente-recorrente', ELAB:'em elaboração', LAC:'não localizado', NAO_VERIFICADO:'ainda não verificado'};
    desenharMapa('mapaMonitor', 'legMonitor', uf => FX[(M[uf] || {}).faixa] || FX['não verificado'],
      uf => { const m = M[uf] || {}; if (!m.verificado) return '<em>ainda não verificado</em> — sem número'; const i = m.instrumento || {}, a = m.antecipacao || {};
        const c = m.cobertura || {};
        return '<em>' + esc(m.faixa) + ' · ' + esc(decBR(m.prontidao)) + '</em><br>instrumento ' + esc(decBR(i.pontos)) + ' (' + esc(ST_H[i.status] || i.status) + ')' + (i.data ? ' · ' + esc(i.data) : '') + '<br>cobertura sanitária ' + esc(decBR(c.pontos) ?? '—') + ' (' + esc(c.planos_lidos ?? 0) + (Number(c.planos_lidos ?? 0) === 1 ? ' plano lido · ' : ' planos lidos · ') + esc(c.planos_sem_leitura ?? 0) + ' sem leitura)' + '<br>quando o ato saiu em relação ao primeiro boletim ' + esc(decBR(a.pontos)) + (i.temporada ? ' (edição ' + esc(i.temporada) + ')' : ''); },
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

  // 3 · observado
  const NIV_DENGUE = {1:['Nível 1 (baixa atividade)',MonitorMapas.PALETA.ordinal4[0]], 2:['Nível 2 (atenção)',MonitorMapas.PALETA.ordinal4[1]], 3:['Nível 3 (alerta)',MonitorMapas.PALETA.ordinal4[2]], 4:['Nível 4 (emergência)',MonitorMapas.PALETA.ordinal4[3]]};
  // 02/10/2026 (bloco A.3): o mapa das capitais e os pontos da amostra saíram da página — a
  // contagem passou a ser do SINAN, por estado. O bloco inteiro sai: ele desenhava num
  // elemento que não existe mais, e o erro ficava ENGOLIDO pelo try/catch em volta,
  // levando consigo o mapa de calor, que vem depois e não tem nada a ver.
  const fD = SSIN.fontes.infodengue;

  /* CALOR — o mapa de excesso de calor, a tabela por classe e o resumo saíram da página em
     19/10/2026 (HANDOVER_SAUDE_DESFECHOS_BLOCO): calor é EXPOSIÇÃO, não desfecho, e exposição vive
     nas páginas de risco; o painel por município continua no Monitor de riscos, e a contagem de
     municípios em classe severa ou extrema continua no cartão do topo desta página. O código
     desenhava em `mapaCalor`, `tblCalor` e `calorResumo`, que não existem mais — e deixá-lo aqui
     derrubava `__load` inteiro (d3 em elemento nulo), levando consigo a grade dos 27. */

  // 13/09/2026 (proposta de enxugamento, Manus AI): quadrante 'Defesa civil × saúde' retirado —
  // "mistura prontidão documental com risco projetado e não mede efeito na população".
  // 13/09/2026 (auditoria de visualizações, consolidação): mapa/lista de emergências só aparece
  // quando há ocorrência — o contador nacional (boxRespostaSanitaria, acima) já é a leitura
  // completa enquanto for zero; duplicar como mapa sempre cinza era redundante.
  // 15/09/2026: mapa/lista de emergências (boxEmerg) retirado — a resposta sanitária é o segundo medidor do topo (MSAUDE.resposta).
  // Série semanal 2026 × 2025 × 2024 (05/09/2026): soma das 27 capitais no InfoDengue — não é o total nacional.
  // 13/09/2026 (consolidação): não desenha mais direto — vira a opção "semanal" do comparador único
  // em #cDesfAcum (ver renderDesfechos). Guarda o crédito e o closure de desenho.
  const SER = SSIN.serie_capitais;
  if (SER && SER.anos && Object.keys(SER.anos).length && typeof Chart !== 'undefined') {
    desenharComparadorSemanal = function(){
      MonitorMapas.padraoGraficos(window.Chart);
      const semanas = Array.from({length: 52}, (_, i) => String(i + 1).padStart(2, '0'));
      const cores = MonitorMapas.PALETA.anos;
      const ds = Object.keys(SER.anos).sort().reverse().map(ano => ({label: ano, data: semanas.map(w => SER.anos[ano][w] ?? null),
        borderColor: cores[ano] || MonitorMapas.PALETA.serie[1], backgroundColor: 'transparent', borderWidth: ano === '2026' ? 2.5 : 1.5, pointRadius: 0, tension: .25, spanGaps: false}));
      // Item 0: o eixo era "SE 01 … SE 52". Passa a ser de meses, e o tooltip diz as datas.
      // O ano aqui é o corrente, porque é a série dele que ancora o calendário; as outras linhas
      // são anos anteriores sobrepostos na mesma posição de semana, que é o que o gráfico compara.
      const eixoAcum = eixoDeMeses(String(new Date().getUTCFullYear()), semanas);
      const opAcum = opcoesDeEixoSemanal(eixoAcum.titulos);
      const chart = new Chart(document.getElementById('cDesfAcum'), {type: 'line', data: {labels: eixoAcum.labels, datasets: ds},
        options: {animation: false, responsive: true, maintainAspectRatio: false,
                  plugins: {legend: {display: false}, tooltip: {callbacks: {title: opAcum.tooltipTitulo}}},
                  scales: {x: opAcum.x, y: {title: {display: true, text: 'casos estimados · 27 capitais'}}}}});
      MonitorMapas.legenda('legDesfAcum', Object.keys(cores).map(a => ({cor: cores[a], rotulo: a})));
      fonteFigura('boxDesfAcum', {fontes: ['InfoDengue (Fiocruz/FGV)', 'soma das 27 capitais'], data: SER.coletado_em});
      return chart;
    };
  }
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
  const m = M[uf] || {}; const i = m.instrumento || {}; const c = m.cobertura || {}; const a = m.antecipacao || {}; const dc = m.risco_atual || {}; const u = (SUF.uf || {})[uf] || {};
  const linha = (k, v) => '<div class="field"><div class="k">' + k + '</div><div class="v">' + v + '</div></div>';
  document.getElementById('detailSaudeConteudo').innerHTML = '<div class="uf-name">' + esc(NOMES[uf] || uf) + ' <span class="sub">(' + uf + ')</span></div>'
    + (m.verificado ? '<div class="gauge-mini gauge-zone"><div class="gauge-head"><span class="gnum">' + String(m.prontidao).replace('.', ',') + '</span><span class="gden">/ 100 · ' + esc(m.faixa) + '</span></div><div class="gauge-track"><div class="gauge-fill" style="--galvo:' + Math.max(m.prontidao, 0.1) + '; width:' + m.prontidao + '%"></div></div></div>' : '<p class="placeholder">Ainda não verificado nesta camada: a bateria de busca de saúde não foi executada para o estado — não é ausência de documento.</p>')
    + '<div class="uf-region">' + esc(REG[uf] || '') + '</div>'
    + linha('Instrumento estadual de saúde', '<span class="pill-nivel">' + esc(ST_H[i.status] || i.status || 'ainda não verificado') + '</span> ' + esc(i.doc || u.doc || '—') + (i.data ? ' (' + esc(i.data) + ')' : '') + (i.orgao || u.orgao ? ' · ' + esc(i.orgao || u.orgao) : '') + (i.url ? ' · <a href="' + esc(i.url) + '" target="_blank" rel="noopener">fonte oficial →</a>' : ''))
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
    + (m.verificado ? linha('Como o número é formado', 'documento estadual ' + esc(decBR(i.pontos))
        + ' · cobertura sanitária ' + esc(decBR(c.pontos) ?? '—') + ' (' + esc(c.planos_lidos ?? 0)
        + (Number(c.planos_lidos ?? 0) === 1 ? ' plano municipal lido, ' : ' planos municipais lidos, ') + esc(c.planos_sem_leitura ?? 0) + ' sem leitura)'
        + ' · quando o ato saiu em relação ao primeiro boletim ' + esc(decBR(a.pontos))
        + ' → média ' + String(m.prontidao).replace('.', ',') + ' (pesos iguais)') : '')
    + (m.camada === 'adaptacao' ? linha('Plano decenal de adaptação', 'registrado como estrutura; não pontua') : '')
    + linha('Resposta sanitária', ((RS || {}).ufs || []).includes(uf) ? 'emergência sanitária declarada no ciclo' : 'nenhuma emergência sanitária declarada localizada desde 29/06/2026')
    + linha('Risco sanitário projetado', (m.risco_projetado || []).length ? (m.risco_projetado || []).map(esc).join('; ') : 'sem registro')
    + linha('Dengue na capital', dc.dengue_capital_nivel != null ? 'nível ' + esc(dc.dengue_capital_nivel) + ' (InfoDengue), ' + esc(dc.dengue_capital || '') + ', SE ' + esc(String(dc.dengue_se || '—')) : 'sem coleta');
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


// ===== 3 · O que aconteceu — desfechos em saúde (§8, 07/09/2026). Peso zero. O Monitor não atribui casos ao El Niño. =====
// 14/09/2026: parametrizada por doença (pedido de Patricia). Um só código para dengue e chikungunya —
// o conjunto de dados muda, a lógica (canal endêmico, vazamento, acumulado, mapa por nível) é a mesma.
// 15/09/2026: cada doença tem a própria seção (pedido da editoria: nenhum desfecho escondido, nenhum seletor de doença);
// os ids de canvas/mapa/legenda/crédito entram por parâmetro e um só código desenha as duas.
const __comparadorCharts = {};
// crédito das figuras de cada doença (ids literais: o portão verificar_saude.py confere um fonteFigura por figura)
function creditoDesfecho(doenca, c){
  if (doenca === 'chikungunya') { fonteFigura('boxChikMapa', c); fonteFigura('boxChikSerie', c); }
  else { fonteFigura('boxDesfMapa', c); fonteFigura('boxDesfAcum', c); }
}
function renderDesfechos(doenca, ids){
  ids = ids || IDS_DENGUE;
  doenca = (doenca && DOENCAS_DESF[doenca]) ? doenca : 'dengue';
  const cfg = DOENCAS_DESF[doenca]; const {serie: S, canal: C} = cfg.dados();
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const selComparador = document.getElementById(ids.sel);
  // opção 'semanal por capitais' só existe para dengue (coletar_saude.py); para chikungunya some, e o valor cai para o painel
  if (selComparador) { const op = selComparador.querySelector('option[value="semanal"]'); if (op) op.hidden = !cfg.capitais;
    if (!cfg.capitais && selComparador.value === 'semanal') selComparador.value = 'semanal_painel'; }
  if (__comparadorCharts[ids.canvas]) { if (typeof __comparadorCharts[ids.canvas].destroy === 'function') __comparadorCharts[ids.canvas].destroy(); __comparadorCharts[ids.canvas] = null; }
  const svgMapa = document.getElementById(ids.mapa); if (svgMapa) while (svgMapa.firstChild) svgMapa.removeChild(svgMapa.firstChild);
  const M = S && S.municipios; const semColeta = {fontes: ['InfoDengue (Fiocruz/FGV), ' + cfg.rotulo, 'painel amostral'], data: null};
  if (!M || !Object.keys(M).length) {
    // lacuna declarada para ESTA doença: gráfico e mapa vazios, legenda e crédito dizem que não há coleta
    const cv = document.getElementById(ids.canvas); if (cv && cv.getContext) { const g = cv.getContext('2d'); g && g.clearRect && g.clearRect(0, 0, cv.width, cv.height); }
    MonitorMapas.legenda(ids.legSerie, [{cor: MonitorMapas.NEUTRA, rotulo: 'série de ' + cfg.rotulo + ' ainda não coletada — lacuna declarada'}]);
    MonitorMapas.legenda(ids.legMapa, [{cor: MonitorMapas.NEUTRA, rotulo: 'sem coleta de ' + cfg.rotulo + ' até o corte'}]);
    MonitorMapas.ufs(MonitorMapas.contexto(BR_GEOJSON, 480, 460), ids.mapa, () => MonitorMapas.NEUTRA, uf => uf);
    creditoDesfecho(doenca, semColeta); return;
  }
  const credito = {fontes: ['modelo InfoDengue (Fiocruz/FGV), ' + cfg.rotulo, 'Sinan', 'painel amostral'], data: S.gerado_em};
  creditoDesfecho(doenca, credito);
  MonitorMapas.padraoGraficos(window.Chart);
  // 13/09/2026 (proposta de enxugamento, Manus AI): 'Casos notificados por semana' (boxDesfSemanal,
  // painel × canal endêmico) deixou de ser figura própria — vira a 3ª opção do comparador único em
  // #cDesfAcum ('Semanal · painel × canal endêmico'), ao lado de 'Acumulado' e 'Semanal por capitais'.
  function desenharComparadorPainel(){
    const semanas = Array.from({length: 53}, (_, i) => String(i + 1).padStart(2, '0'));
    const soma = {casos: {}, med: {}, p75: {}, p90: {}, nmin: {}, nmax: {}};
    Object.entries(M).forEach(([cod, m]) => { const c = (C && C.municipios && C.municipios[cod]) || {};
      semanas.forEach(ss => { const k = '2026-' + ss; const v = (m.semanas_2026 || {})[k];
        if (v && v.casos != null) soma.casos[ss] = (soma.casos[ss] || 0) + v.casos;
        if (c[ss]) { soma.med[ss] = (soma.med[ss] || 0) + c[ss].mediana; soma.p75[ss] = (soma.p75[ss] || 0) + c[ss].p75; soma.p90[ss] = (soma.p90[ss] || 0) + c[ss].p90; }
        const n = (m.nowcasting || {})[k]; if (n && n.est_min != null) { soma.nmin[ss] = (soma.nmin[ss] || 0) + n.est_min; soma.nmax[ss] = (soma.nmax[ss] || 0) + n.est_max; } }); });
    const ate = Math.max(...Object.keys(soma.casos).concat(Object.keys(soma.nmax)).map(Number)); const labels = semanas.slice(0, ate);
    const eixoInfo = eixoDeMeses(String(new Date().getUTCFullYear()), labels);
    const opInfo = opcoesDeEixoSemanal(eixoInfo.titulos);
    const chart = new Chart(document.getElementById(ids.canvas), {type: 'bar', data: {labels: eixoInfo.labels, datasets: [
        {type: 'bar', label: '2026 (consolidado)', data: labels.map(w => soma.casos[w] ?? null), backgroundColor: MonitorMapas.PALETA.anos['2026'], order: 3},
        {type: 'line', label: 'nowcasting (máx.)', data: labels.map(w => soma.nmax[w] ?? null), borderColor: MonitorMapas.PALETA.anos['2026'], borderDash: [4, 3], borderWidth: 1, pointRadius: 0, order: 2, spanGaps: false},
        {type: 'line', label: 'nowcasting (mín.)', data: labels.map(w => soma.nmin[w] ?? null), borderColor: MonitorMapas.PALETA.anos['2026'], borderDash: [4, 3], borderWidth: 1, pointRadius: 0, order: 2, spanGaps: false},
        {type: 'line', label: 'mediana 2019–2025', data: labels.map(w => soma.med[w] ?? null), borderColor: MonitorMapas.PALETA.anos.canal, borderWidth: 2, pointRadius: 0, order: 1},
        {type: 'line', label: 'p75', data: labels.map(w => soma.p75[w] ?? null), borderColor: MonitorMapas.PALETA.anos.p75, borderWidth: 1.5, pointRadius: 0, order: 1},
        {type: 'line', label: 'p90', data: labels.map(w => soma.p90[w] ?? null), borderColor: MonitorMapas.PALETA.anos.p90, borderWidth: 1.5, pointRadius: 0, order: 1}]},
      options: {animation: false, responsive: true, maintainAspectRatio: false,
        plugins: {legend: {display: false}, tooltip: {callbacks: {title: opInfo.tooltipTitulo}}},
        scales: {x: opInfo.x, y: {beginAtZero: true, title: {display: true, text: 'casos notificados de ' + cfg.rotulo + ' · painel'}}}}});
    MonitorMapas.legenda(ids.legSerie, [{cor: MonitorMapas.PALETA.anos['2026'], rotulo: '2026 consolidado (últimas 4 semanas excluídas)'}, {cor: MonitorMapas.PALETA.anos['2026'], opacidade: .5, rotulo: 'faixa de nowcasting (tracejado)'}, {cor: MonitorMapas.PALETA.anos.canal, rotulo: 'mediana 2019–2025 (2024 à parte)'}, {cor: MonitorMapas.PALETA.anos.p75, rotulo: 'p75'}, {cor: MonitorMapas.PALETA.anos.p90, rotulo: 'p90'}]);
    fonteFigura(ids.boxSerie, credito);
    return chart;
  }
  // escada do acumulado — opção "acum" do comparador único em #cDesfAcum
  const acum = a => Object.values(M).reduce((s, m) => s + ((m.acumulado || {})[a] || 0), 0);
  function desenharComparadorAcum(){
    const chart = new Chart(document.getElementById(ids.canvas), {type: 'bar', data: {labels: ['2024', '2025', '2026 (até a última SE consolidada)'], datasets: [{data: [acum('2024'), acum('2025'), acum('2026')], backgroundColor: [MonitorMapas.PALETA.anos['2024'], MonitorMapas.PALETA.anos['2025'], MonitorMapas.PALETA.anos['2026']]}]},
      options: {animation: false, responsive: true, maintainAspectRatio: false, plugins: {legend: {display: false}}, scales: {y: {beginAtZero: true, title: {display: true, text: 'casos notificados de ' + cfg.rotulo + ' · painel'}}}}});
    MonitorMapas.legenda(ids.legSerie, [{cor: MonitorMapas.PALETA.anos['2024'], rotulo: '2024 (ano epidêmico, fora do canal)'}, {cor: MonitorMapas.PALETA.anos['2025'], rotulo: '2025'}, {cor: MonitorMapas.PALETA.anos['2026'], rotulo: '2026 parcial'}]);
    fonteFigura(ids.boxSerie, credito);
    return chart;
  }
  // 13/09/2026 (auditoria de visualizações, consolidação): comparador único — "acumulado" (painel
  // amostral), "semanal por capitais" (27 capitais, ex-boxSerie) e "semanal · painel × canal endêmico"
  // (ex-boxDesfSemanal) alternam no mesmo #cDesfAcum em vez de figuras fixas. Escopos diferentes
  // (painel × capitais); por isso permanecem como opções explícitas, nunca combinadas num só número.
  function mostrarComparador(modo){
    if (__comparadorCharts[ids.canvas]) { if (typeof __comparadorCharts[ids.canvas].destroy === 'function') __comparadorCharts[ids.canvas].destroy(); __comparadorCharts[ids.canvas] = null; }
    __comparadorCharts[ids.canvas] = modo === 'semanal' && cfg.capitais && desenharComparadorSemanal ? desenharComparadorSemanal()
      : modo === 'semanal_painel' ? desenharComparadorPainel()
      : desenharComparadorAcum();
  }
  if (selComparador && !selComparador.__ligado) { selComparador.__ligado = true; selComparador.addEventListener('change', () => mostrarComparador(selComparador.value)); }
  mostrarComparador(selComparador ? selComparador.value : 'semanal_painel');
  // mapa: pontos do painel coloridos pelo nível da última SE consolidada
  const ctx = MonitorMapas.contexto(BR_GEOJSON, 480, 460);
  const NIV = {1: MonitorMapas.PALETA.ordinal4[0], 2: MonitorMapas.PALETA.ordinal4[1], 3: MonitorMapas.PALETA.ordinal4[2], 4: MonitorMapas.PALETA.ordinal4[3]};   // mesmo ordinal do mapa de dengue por UF (Figura acima)
  const ref = Array.isArray(PAINEL_LISTA) ? PAINEL_LISTA : Object.values(PAINEL_LISTA || {}); const coord = {}; ref.forEach(r => { coord[String(r.codigo_ibge).padStart(7, '0')] = r; });
  const pontos = Object.entries(M).filter(([cod]) => coord[cod] && coord[cod].lat != null).map(([cod, d]) => ({lat: coord[cod].lat, lon: coord[cod].lon, nivel: d.nivel_ultima_se, nome: d.nome, uf: d.uf, ultima: d.ultima_se}));
  MonitorMapas.ufs(ctx, ids.mapa, () => MonitorMapas.NEUTRA, uf => uf);
  if (pontos.length) MonitorMapas.pontos(ctx, ids.mapa, pontos, {r: () => 4, cor: d => NIV[d.nivel] || MonitorMapas.NEUTRA, rotulo: d => esc(d.nome) + '/' + esc(d.uf) + ' · nível ' + esc(d.nivel ?? '—') + ' · ' + esc(d.ultima || '')});
  MonitorMapas.legenda(ids.legMapa, [{cor: NIV[1], rotulo: 'nível 1 (baixa atividade)'}, {cor: NIV[2], rotulo: 'nível 2 (atenção)'}, {cor: NIV[3], rotulo: 'nível 3 (alerta)'}, {cor: NIV[4], rotulo: 'nível 4 (emergência)'}, {cor: MonitorMapas.NEUTRA, rotulo: (pontos.length ? pontos.length + ' municípios do painel' : 'painel sem coordenadas')}]);
  fonteFigura(ids.boxMapa, credito);
}
// seletor de doença (14/09/2026): redesenha comparador e mapa com o conjunto escolhido


// 13/09/2026 (proposta de enxugamento, Manus AI): renderEstrutura() (catálogo de 20 desfechos e
// tabela de gatilhos, §36) migrou por completo para pesquisadores.js.


// 15/09/2026 (auditoria editorial §2.10): títulos-fato calculados dos dados já carregados — nunca digitados.
function titulosFatoSaude(){
  const titulo = (box, txt) => { const h = document.querySelector('#' + box + ' .figura-titulo'); if (h && txt) h.textContent = txt; };
  const n = v => Number(v || 0).toLocaleString('pt-BR');
  try {   // MARÉ · Saúde: estados por categoria do plano de saúde
    const UFS = Object.keys(SUF.uf || {}); const st = uf => (SUF.uf[uf] || {}).status || 'NAO_VERIFICADO';
    const c = k => UFS.filter(u => k.includes(st(u))).length;
    // 23/09/2026 (governança editorial §12, §32.8): este mapa pinta PRONTIDÃO SANITÁRIA — média de
    // instrumento, cobertura populacional e antecipação (Metodologia §31). O título-fato anterior
    // contava estados por STATUS DE INSTRUMENTO, que é o objeto da figura seguinte (boxStatus), e
    // saía quase idêntico ao dela. Título herdado da figura vizinha é o defeito que o §32.8 procura.
    // O fato agora é sobre o próprio objeto, e traz à tona a cobertura da verificação.
    // A contagem vem do agregado do próprio dado (MSAUDE.resumo), não de um recálculo aqui: o campo
    // `verificado` não existe em SUF.uf, e uma primeira tentativa de derivá-lo dali imprimiu
    // "0 de 27 estados verificados" numa página pública. Fato de título sai da fonte, nunca de palpite.
    const Rsa = (typeof MSAUDE !== 'undefined' && MSAUDE && MSAUDE.resumo) || {};
    titulo('boxStatus', `Plano de saúde por estado: ${c(['NOVO'])} para o ciclo, ${c(['VIG','READ'])} de todo ano, ${c(['NAO_VERIFICADO'])} não verificados`);
  } catch (e) {}
  // dengue: municípios em alerta laranja/vermelho na última semana consolidada (nível 3 = laranja, 4 = vermelho no InfoDengue)
  const tituloDoenca = (doenca, box) => { try {
    const S = DOENCAS_DESF[doenca].dados().serie; const M = (S && S.municipios) || {};
    if (!Object.keys(M).length) return; const se = Object.values(M).map(m => m.ultima_se).filter(Boolean).sort().pop();
    const alto = Object.values(M).filter(m => m.ultima_se === se && (m.nivel_ultima_se === 3 || m.nivel_ultima_se === 4)).length;
    const rot = doenca === 'chikungunya' ? 'Chikungunya' : 'Dengue';
    const mun = alto === 1 ? 'município' : 'municípios';
    titulo(box, `${rot}: ${n(alto)} ${mun} em alerta laranja ou vermelho na semana ${semanaEmDatas(String(se || '').split('-')[0], se)} (painel amostral)`);
  } catch (e) {} };
  tituloDoenca('dengue', 'boxDesfMapa'); tituloDoenca('chikungunya', 'boxChikMapa');
}

// ===== tabela COBRADE (§258, 27/09/2026) =====
// Migrada de assets/js/pesquisadores.js, que foi arquivado com a página. A tabela é// verificar_consistencia.py leu AREAS de pesquisadores.js desde 14/09 (§1.4 da auditoria
// editorial); passa a ler daqui, e o portão foi atualizado no mesmo commit.
(function(){
  const tb = document.getElementById('tblAreas'); if (!tb) return;
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const AREAS = [
  {label:'Grupo Seca (COBRADE 1.4.1): estiagem, seca e segurança hídrica', cor:MonitorMapas.PALETA.risco.seca, ufs:['AC','AL','AM','AP','BA','CE','DF','GO','PA','PE','PI','SE']},
  {label:'Grupo Seca · frente de incêndio florestal (1.4.1.3)', cor:MonitorMapas.PALETA.risco.fogo, ufs:['BA','GO','MA','MS','MT','RO','RR','TO']},
  {label:'Família das chuvas (1.2-1.3): chuvas intensas e enchentes', cor:MonitorMapas.PALETA.risco.chuvas, ufs:['ES','MG','PR','RJ','RS','SP']},
  {label:'Multirrisco integrado', cor:MonitorMapas.PALETA.risco.multi, ufs:['SC']},
];
  tb.querySelector('tbody').innerHTML = AREAS.map(a => `<tr><td>${esc(a.label)}</td><td>${a.ufs.length}</td><td>${esc(a.ufs.join(', '))}</td></tr>`).join('');
  MonitorMapas.credito('boxAreas', {fontes: ['MARÉ', 'classificação COBRADE'], data: (typeof META !== 'undefined' && META && (META.atualizado_em || META.corte)) || null});
})();



/* ===== Cartões do topo (bloco A.1 do handover de 02/10/2026) =====
 * Cinco indicadores que mudam a cada coleta. Os dois primeiros vêm da FONTE PRIMÁRIA (SINAN e
 * SIVEP-Gripe) e trazem, no próprio cartão, a ressalva de parcialidade e a frase que a editoria
 * fixou: estes números não indicam relação com o El Niño.
 *
 * "Última semana epidemiológica fechada" é a última com valor na série — não a última do
 * calendário. A diferença importa: as semanas recentes existem no arquivo com valor nulo, e tratar
 * nulo como zero publicaria uma queda que é só atraso de notificação.
 */
(function cartoesDoTopoSaude(){
  const el = id => document.getElementById(id);
  const n = v => Number(v || 0).toLocaleString('pt-BR');
  const ultimaFechada = serie => {
    const ses = Object.keys(serie || {}).filter(k => serie[k] != null).sort();
    return ses.length ? {se: ses[ses.length - 1], valor: serie[ses[ses.length - 1]]} : null;
  };

  /* Dengue e chikungunya: o mesmo cartão, cada um do seu arquivo do SINAN. */
  const cartaoSinan = (arquivo, doenca, idValor, idRotulo, idFonte) =>
    fetch('data/saude_desfechos/' + arquivo).then(r => r.ok ? r.json() : null).then(D => {
      const br = ((D || {}).serie || {}).BR;
      const u = br ? ultimaFechada(Object.fromEntries(Object.entries(br).filter(([k]) => k.startsWith(String(D.ano_corrente))))) : null;
      if (!u) { if (el(idValor)) el(idValor).textContent = 'sem coleta'; return; }
      if (el(idValor)) el(idValor).textContent = n(u.valor);
      if (el(idRotulo)) el(idRotulo).textContent = 'notificações de ' + doenca + ' na semana ' + semanaEmDatas(u.se.split('-')[0], u.se);
      MonitorMapas.credito(idFonte, {fontes: ['SINAN (Ministério da Saúde)', D.conta === 'notificacoes' ? 'notificações, não casos confirmados' : ''].filter(Boolean), data: D.gerado_em});
    }).catch(_erroSaude("saude:777"));
  cartaoSinan('dengue_sinan_serie.json', 'dengue', 'nDengueSE', 'rotuloDengueSE', 'fonteDengueSE');
  cartaoSinan('chik_sinan_serie.json', 'chikungunya', 'nChikSE', 'rotuloChikSE', 'fonteChikSE');

  fetch('data/saude_desfechos/srag_serie.json').then(r => r.ok ? r.json() : null).then(S => {
    const serie = (S || {}).serie;
    if (!serie) { if (el('nSragSE')) el('nSragSE').textContent = 'sem coleta'; return; }
    /* O arquivo é {UF: {SE: n}} — e traz a linha `BR` JUNTO das 27 UFs.
       02/10/2026, defeito medido: somar `serie.values()` somava o país duas vezes, porque a linha
       do país entrava na soma das UFs. O cartão publicava 8.534 internações onde a fonte diz 4.267.
       Quando existe a linha `BR`, ela É o país; só na falta dela o país é a soma das UFs. A mesma
       regra está em `scripts/gerar_topo_das_paginas.py`, que é quem a Imprensa lê. */
    const ano = String(S.ano_corrente || new Date().getFullYear());
    const total = {};
    const somar = porSE => {
      if (!porSE || typeof porSE !== 'object') return;
      Object.entries(porSE).forEach(([se, v]) => {
        if (se.startsWith(ano) && typeof v === 'number') total[se] = (total[se] || 0) + v;
      });
    };
    if (serie.BR && typeof serie.BR === 'object') somar(serie.BR);
    else Object.entries(serie).forEach(([uf, porSE]) => { if (uf !== 'BR') somar(porSE); });
    const u = ultimaFechada(total);
    if (!u) { if (el('nSragSE')) el('nSragSE').textContent = 'sem coleta'; return; }
    if (el('nSragSE')) el('nSragSE').textContent = n(u.valor);
    if (el('rotuloSragSE')) {
      el('rotuloSragSE').textContent = 'internações por síndrome respiratória grave na semana '
        + semanaEmDatas(u.se.split('-')[0], u.se);
    }
    MonitorMapas.credito('fonteSragSE', {fontes: ['SIVEP-Gripe (Ministério da Saúde)'], data: S.gerado_em});
    // 11/10/2026 (HANDOVER_SAUDE item 2): a frase do dado de Respiratórias ficava em "—".
    if (el('fraseResp')) {
      mostrarFrase(el('fraseResp'), n(u.valor) + ' internações por síndrome respiratória grave na semana '
        + semanaEmDatas(u.se.split('-')[0], u.se) + ', a última com dado no SIVEP-Gripe. As semanas '
        + 'seguintes ainda recebem notificações e aparecem sem valor.');
    }
  }).catch(_erroSaude("saude:811"));

  /* Estados com dengue em nível de alerta: a régua é do InfoDengue (níveis 3 e 4) e a agregação por
   * estado é nossa — a nota diz qual é, porque o InfoDengue não publica um nível por estado. */
  fetch('data/saude_desfechos/serie_painel.json').then(r => r.ok ? r.json() : null).then(P => {
    const M = (P || {}).municipios || {};
    if (!Object.keys(M).length) { if (el('nUFsAlerta')) el('nUFsAlerta').textContent = 'sem coleta'; return; }
    const ufs = new Set();
    Object.values(M).forEach(m => { if ((m.nivel_ultima_se || 0) >= 3 && m.uf) ufs.add(m.uf); });
    if (el('nUFsAlerta')) el('nUFsAlerta').textContent = ufs.size + ' de 27';
    MonitorMapas.credito('fonteUFsAlerta', {fontes: ['InfoDengue (Fiocruz/FGV)', 'o estado entra quando ao menos um município acompanhado está em nível 3 ou 4'], data: P.gerado_em});
  }).catch(_erroSaude("saude:825"));

  /* O calor vem de `calor_excesso`, que é onde o coletor o escreve: `resumo` com as quatro classes
   * do vocabulário do Ministério da Saúde e `municipios_lidos`. A primeira versão deste cartão
   * procurou o dado em `uf[*].calor_ms`, caminho que o arquivo nunca teve — e dizia "sem coleta"
   * com o dado em disco, que é o pior jeito de errar numa figura de risco. */
  fetch('data/saude_sinais.json').then(r => r.ok ? r.json() : null).then(SS => {
    const C = (SS || {}).calor_excesso || null;
    const r = (C || {}).resumo || null;
    if (!r) {
      /* 11/10/2026: retrato com mais de 9 dias sai do ar (coletar_saude.vencer_calor); o cartão e a
         fonte dizem desde quando não há leitura, em vez de mostrar o retrato velho como o mais recente. */
      const ult = (((SS || {}).fontes || {}).painel_calor_ms || {}).ultima_coleta_ok;
      if (el('nCalorMun')) el('nCalorMun').textContent = ult
        ? 'sem leitura desde ' + String(MonitorMapas.dataBR(ult) || ult).slice(0, 5) : 'sem coleta';
      MonitorMapas.credito('fonteCalorMun', {fontes: ['Painel Nacional de Excesso de Calor (Ministério da Saúde)', ult ? 'nenhum município lido desde então' : 'nenhum município lido até o corte'], data: ult});
      return;
    }
    const acima = Number(r.severo || 0) + Number(r.extremo || 0);
    if (el('nCalorMun')) el('nCalorMun').textContent = n(acima);
    const lidos = C.municipios_lidos || Object.keys(C.municipios || {}).length;
    MonitorMapas.credito('fonteCalorMun', {fontes: ['Painel Nacional de Excesso de Calor (Ministério da Saúde)', n(lidos) + (Number(lidos) === 1 ? ' município lido' : ' municípios lidos')], data: C.data});
  }).catch(_erroSaude("saude:851"));

})();

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

  /* 1 · O topo (HANDOVER_SAUDE_PAGINA §1.2): os dois medidores da inicial. À esquerda, a média das
   * UFs verificadas, nunca dita como nacional enquanto houver estado sem número (METODOLOGIA §1048);
   * à direita, a parcela da população sob emergência em saúde pública. Índice nulo é lacuna
   * declarada, nunca zero. A barra e o número sobem pelo mesmo `animarGauges` da inicial. */
  fetch('data/monitor_saude.json').then(r => r.ok ? r.json() : null).then(MS => {
    const res = ((MS || {}).resumo) || {}, rp = ((MS || {}).resposta) || {};
    const fixa = (id, v) => { const f = el(id); f.dataset.alvo = String(v); f.style.setProperty('--galvo', String(Math.max(v, 0.1)));
      f.closest('.gauge-track').setAttribute('aria-label', 'Barra de progresso: ' + (id === 'gaugeFillSaude' ? 'MARÉ Saúde' : 'emergências em saúde pública') + ' em ' + umaCasa(v) + ' de 100'); };
    const media = res.media_das_verificadas;
    if (media == null) { el('nIndiceSaude').textContent = '—'; el('linhaPreparoSaude').textContent = 'sem coleta até o corte'; }
    else {
      el('nIndiceSaude').textContent = umaCasa(media); el('nIndiceSaude').dataset.contar = media;
      el('faixaSaude').replaceChildren(MonitorMapas.pilulaDaFaixa(media));
      fixa('gaugeFillSaude', media);
      el('linhaPreparoSaude').textContent = 'média de ' + n(res.verificadas) + ' estados verificados · '
        + n(27 - (res.verificadas || 0)) + ' ainda sem número · ' + ((MS || {}).corte || '');
    }
    // A frase do que se procura muda com a versão do método (v0.4: coordenação em vez de antecedência).
    if (/^0\.4/.test(String((MS || {}).versao)) && window.MonitorCatalogo)
      MonitorCatalogo.pronto.then(() => MonitorCatalogo.escrever('saudeLeiIndice', 'saude.abertura.lei_e_indice_v04'));
    const quando = (MS || {}).gerado_em || (MS || {}).corte || '';
    if (rp.indice == null) {
      el('respNumSaude').textContent = '—';
      el('respBadgeSaude').innerHTML = '<span class="gfaixa-pill">sem coleta até o corte</span>';
    } else {
      el('respNumSaude').textContent = umaCasa(rp.indice); el('respNumSaude').dataset.contar = rp.indice;
      fixa('respFillSaude', rp.indice);
      el('respBadgeSaude').innerHTML = '<span class="gfaixa-pill">' + esc(rp.emergencias
        ? n(rp.emergencias) + (rp.emergencias === 1 ? ' emergência' : ' emergências') + ' · ' + umaCasa(100 * (rp.pop_sob_emergencia || 0) / (rp.pop_total || 1)) + ' % da população'
        : 'nenhuma emergência declarada') + '</span>';
    }
    el('linhaRespostaSaude').textContent = 'Parcela da população em estados ou municípios sob emergência em saúde pública declarada desde '
      + (rp.desde || '29/06/2026') + ' · ' + (rp.indice == null ? 'sem coleta até o corte' : rp.emergencias ? 'até ' + quando : 'nenhuma localizada até ' + quando)
      + ' · DOU e diários oficiais estaduais';
    MonitorMapas.animarGauges(el('topoSaude'));
  }).catch(_erroSaude("saude:1066"));

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
    if (el('linhaRiscoSan')) el('linhaRiscoSan').textContent = 'boletins do Painel El Niño';
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

/* ===== "O que os órgãos de saúde registram": uma seção, um cartão por desfecho =====
 *
 * HANDOVER_SAUDE_DESFECHOS_BLOCO (editoria, 16/10/2026, mockup aprovado). Substitui os quatro
 * blocos por agravo — dengue, chikungunya, respiratórias e calor, cada um com duas ou três
 * figuras — por UMA seção: um seletor de estado, um cartão por desfecho e UM detalhe por vez.
 *
 * O que é cartão: DESFECHO EM PESSOAS (casos, internações, óbitos). Exposição não é cartão —
 * calor, fumaça, chuva e seca vivem nas páginas de risco, e por isso o mapa de excesso de calor
 * saiu desta página com a reforma. Desfecho sem arquivo não ganha cartão (§36): é nomeado na
 * linha de lacuna, com o nome que o catálogo lhe dá.
 *
 * A faixa habitual é o canal endêmico que os próprios arquivos trazem (mediana e p90 das semanas
 * equivalentes de 2019 a 2025, da mesma UF), nunca um cálculo novo aqui; série sem canal — os
 * óbitos registrados, que têm 18 meses — diz "sem faixa habitual", em vez de inventar uma.
 * Nenhuma frase relaciona caso a El Niño, e nenhuma semana aparece como número: data por extenso,
 * por `assets/semana.js`, e eixo em meses.
 */
function secaoDosDesfechos(){
  const grade = document.getElementById('gradeDesfechos'); if (!grade) return;
  const el = id => document.getElementById(id);
  const n = v => Number(v || 0).toLocaleString('pt-BR');
  const umaCasa = v => Number(v || 0).toLocaleString('pt-BR', {minimumFractionDigits: 1, maximumFractionDigits: 1});
  const C = () => window.MonitorCatalogo;
  const txt = (id, valores) => (C() && C().texto(id, valores)) || '';

  /* A tabela dos desfechos EM EVIDÊNCIA do handover (§2). `arquivo` é o que a página lê, que é a
   * fonte primária decidida em 02/10 (SINAN para as arboviroses, não o painel amostral). A
   * cadência é a da fonte, e é ela que decide se a série é por semana ou por mês. */
  const DESFECHOS = [
    {id: 'dengue', rotulo: 'Dengue', unidade: 'notificações', conta: 'notificações', cadencia: 'semana',
     arquivo: 'data/saude_desfechos/dengue_sinan_serie.json', fonte: ['SINAN (Ministério da Saúde)'], mapa: 'acumulado'},
    {id: 'chik', rotulo: 'Chikungunya', unidade: 'notificações', conta: 'notificações', cadencia: 'semana',
     arquivo: 'data/saude_desfechos/chik_sinan_serie.json', fonte: ['SINAN (Ministério da Saúde)'], mapa: 'acumulado'},
    {id: 'srag', rotulo: 'Síndrome respiratória grave', unidade: 'internações', conta: 'internações', cadencia: 'semana',
     arquivo: 'data/saude_desfechos/srag_serie.json', fonte: ['SIVEP-Gripe (Ministério da Saúde)'], mapa: 'acumulado'},
    {id: 'obitos', rotulo: 'Óbitos registrados', unidade: 'registros de óbito', conta: 'registros', cadencia: 'mês',
     arquivo: 'data/saude_desfechos/obitos_registro_civil.json',
     fonte: ['Portal da Transparência do Registro Civil (ARPEN/CNJ)'], mapa: 'ultimo',
     ressalva: 'registro, não ocorrência; sem causa'},
  ];
  const UFS_SEL = ('AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO').split(' ');
  const NOMES = {AC:'Acre',AL:'Alagoas',AM:'Amazonas',AP:'Amapá',BA:'Bahia',CE:'Ceará',DF:'Distrito Federal',ES:'Espírito Santo',GO:'Goiás',MA:'Maranhão',MG:'Minas Gerais',MS:'Mato Grosso do Sul',MT:'Mato Grosso',PA:'Pará',PB:'Paraíba',PE:'Pernambuco',PI:'Piauí',PR:'Paraná',RJ:'Rio de Janeiro',RN:'Rio Grande do Norte',RO:'Rondônia',RR:'Roraima',RS:'Rio Grande do Sul',SC:'Santa Catarina',SE:'Sergipe',SP:'São Paulo',TO:'Tocantins'};

  let POP_UF = {}, CATALOGO = null, grafico = null;
  let uf = 'BR', escolhido = null;
  const dados = {};   // id → arquivo lido (ou null quando a fonte não respondeu)

  /* ---- leitura da série de um desfecho, na forma comum que os dois formatos já têm ---- */
  // Períodos com valor da UF escolhida, em ordem; chave "2026-33" (semana) ou "2026-09" (mês).
  const periodos = (D, u) => {
    const s = (D && D.serie && D.serie[u]) || null;
    return s ? Object.keys(s).filter(k => s[k] != null).sort() : [];
  };
  const valor = (D, u, k) => ((D.serie[u] || {})[k]);
  /* O QUE É PERÍODO FECHADO. A fonte continua recebendo notificação atrasada: as séries semanais
   * declaram `se_incompletas` (quatro semanas, nas três) e a mensal declara qual é o mês corrente
   * incompleto. Valor e faixa do cartão saem do último período FECHADO, com a data dele na linha
   * de fonte — comparar período incompleto com a faixa habitual daria "abaixo do habitual" para o
   * que é só notificação que ainda não chegou. Os períodos incompletos não entram nem no gráfico
   * nem no mapa, pela mesma razão. */
  const fechados = (D, d, ks) => d.cadencia === 'semana'
    ? ks.slice(0, Math.max(0, ks.length - (D.se_incompletas || 0)))
    : ks.filter(k => k !== D.mes_corrente_incompleto);
  // A faixa habitual vem do canal endêmico do arquivo: {mediana, p90} por semana da UF.
  const faixa = (D, u, k) => {
    const canal = (D.canal_endemico || {})[u];
    if (!canal) return null;
    const c = canal[String(k).split('-')[1]];
    return (c && c.mediana != null && c.p90 != null) ? {de: c.mediana, ate: c.p90} : null;
  };
  // O período por extenso: a semana vira intervalo de datas; o mês, nome e ano.
  const periodoEmTexto = (d, k) => {
    if (!k) return '';
    const [ano, nn] = String(k).split('-');
    if (d.cadencia === 'semana') return semanaEmDatas(ano, k) || '';
    return (window.MonitorSemana ? MonitorSemana.MESES[Number(nn) - 1] + ' de ' + ano : '');
  };
  /* O intervalo coberto pela série desenhada: do começo do primeiro período ao fim do último. Para
   * semanas usa as datas das pontas (não "de <semana> a <semana>", que repetiria a preposição). */
  const intervaloEmTexto = (d, ks) => {
    if (!ks.length) return '';
    const fim = ks[ks.length - 1], [af, nf] = String(fim).split('-');
    if (d.cadencia === 'semana') {
      const ini = primeiraSemanaComValor(String(ks[0]).split('-')[0], [ks[0]]);
      const ate = window.MonitorSemana ? MonitorSemana.fimPorExtenso(Number(af), Number(nf)) : '';
      return (ini && ate) ? 'de ' + ini + ' a ' + ate : '';
    }
    return 'de ' + periodoEmTexto(d, ks[0]) + ' a ' + periodoEmTexto(d, fim);
  };

  /* ---- a linha das semanas (ou meses) recentes, dentro do cartão ----
   * SVG inline, sem biblioteca: faixa habitual como polígono, a série como linha, o último ponto
   * marcado. Escala própria do cartão (o eixo não é legível neste tamanho), e é por isso que o
   * valor e a faixa aparecem em número logo acima. */
  const QUANTOS = {semana: 52, mes: 24};
  function linhaDoCartao(d, D, chaves) {
    const ks = chaves.slice(-QUANTOS[d.cadencia]);
    if (ks.length < 2) return '';
    const vs = ks.map(k => Number(valor(D, uf, k)) || 0);
    const fs = ks.map(k => faixa(D, uf, k));
    const topo = Math.max(1, ...vs, ...fs.filter(Boolean).map(f => f.ate));
    const x = i => (i / (ks.length - 1) * 100).toFixed(2);
    const y = v => (100 - v / topo * 100).toFixed(2);
    const linha = vs.map((v, i) => x(i) + ',' + y(v)).join(' ');
    let faixaPoli = '';
    if (fs.every(Boolean)) {
      const cima = fs.map((f, i) => x(i) + ',' + y(f.ate));
      const baixo = fs.map((f, i) => x(i) + ',' + y(f.de)).reverse();
      faixaPoli = '<polygon class="faixa" points="' + cima.concat(baixo).join(' ') + '"></polygon>';
    }
    return '<svg class="cartao-numero-serie" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">'
      + faixaPoli + '<polyline class="linha" points="' + linha + '"></polyline>'
      + '<circle class="ponto" cx="' + x(vs.length - 1) + '" cy="' + y(vs[vs.length - 1]) + '" r="2.5"></circle></svg>';
  }

  /* ---- os cartões ---- */
  function desenharCartoes() {
    const esc = MonitorMapas.esc;
    grade.innerHTML = DESFECHOS.map(d => {
      const D = dados[d.id]; const ks = D ? fechados(D, d, periodos(D, uf)) : [];
      const ultimo = ks[ks.length - 1];
      const v = ultimo ? valor(D, uf, ultimo) : null;
      const f = ultimo ? faixa(D, uf, ultimo) : null;
      const posicao = !f ? txt('saude.observado.cartao.faixa_sem')
        : txt(v > f.ate ? 'saude.observado.cartao.faixa_acima'
              : (v < f.de ? 'saude.observado.cartao.faixa_abaixo' : 'saude.observado.cartao.faixa_dentro'),
              {de: f.de, ate: f.ate});
      return '<button type="button" class="cartao-numero cartao-numero--saude" data-desfecho="' + d.id + '"'
        + ' aria-pressed="' + (d.id === escolhido ? 'true' : 'false') + '">'
        + '<p class="cartao-numero-rotulo"><strong>' + esc(d.rotulo) + '</strong> · '
        + esc(txt('saude.observado.cartao.unidade',
                  {unidade: d.unidade, cadencia: d.cadencia, periodo: periodoEmTexto(d, ultimo)})) + '</p>'
        + '<p class="cartao-numero-valor" id="vDesf' + d.id + '">' + esc(_qtdCartao(v)) + '</p>'
        + '<p class="cartao-numero-variacao">' + esc(posicao) + '</p>'
        + (D ? linhaDoCartao(d, D, ks) : '')
        + '<p class="cartao-numero-fonte" id="fDesf' + d.id + '"></p>'
        + '</button>';
    }).join('');
    // A linha de fonte é a MESMA da figura, escrita pelo mesmo lugar (`MonitorMapas.credito`):
    // "Fonte: … · Atualização: dd/mm/aaaa". Cartão sem arquivo diz "sem coleta até o corte".
    DESFECHOS.forEach(d => MonitorMapas.credito('fDesf' + d.id,
      {fontes: d.fonte.concat(d.ressalva ? [d.ressalva] : []), data: (dados[d.id] || {}).gerado_em || null}));
    grade.querySelectorAll('[data-desfecho]').forEach(b =>
      b.addEventListener('click', () => { escolhido = b.dataset.desfecho; desenharCartoes(); desenharDetalhe(); }));
    MonitorMapas.legenda('legDesfechos', [
      {cor: MonitorMapas.PALETA.anos['2026'], rotulo: txt('saude.observado.legenda.observado')},
      {cor: MonitorMapas.PALETA.anos.canal, rotulo: txt('saude.observado.legenda.faixa')}]);
  }

  /* ---- o detalhe: a série inteira sobre a faixa, e o mapa por estado ---- */
  function desenharDetalhe() {
    const d = DESFECHOS.find(x => x.id === escolhido); if (!d) return;
    const D = dados[d.id]; if (!D) return;
    const todos = fechados(D, d, periodos(D, uf));
    /* O gráfico cobre o ano do ciclo nas séries semanais — é o que o eixo em meses sabe rotular, e
     * é o recorte que a página já publicava — e os 24 meses mais recentes na mensal. */
    const anoCiclo = String(todos[todos.length - 1] || '').split('-')[0];
    const ks = d.cadencia === 'semana' ? todos.filter(k => k.startsWith(anoCiclo)) : todos.slice(-QUANTOS.mes);
    const ultimo = ks[ks.length - 1];
    const anos = (D.anos_canal || []).map(String);
    const faixaAnos = anos.length ? anos[0] + ' a ' + anos[anos.length - 1] : '';
    const territorio = uf === 'BR' ? 'Brasil' : (NOMES[uf] || uf);
    const parciais = d.cadencia === 'semana'
      ? txt('saude.observado.detalhe.parciais_semana', {n: D.se_incompletas || 0})
      : txt('saude.observado.detalhe.parciais_mes');

    _poe('tituloSerieDesfecho', 'saude.observado.detalhe.titulo',
         {desfecho: d.rotulo, unidade: d.unidade, cadencia: d.cadencia, territorio: territorio});
    _poe('subSerieDesfecho', 'saude.observado.detalhe.legenda',
         {medida: d.conta, cadencia: d.cadencia, anos: faixaAnos, parciais: parciais});
    _poe('linhaSerieDesfecho', 'saude.observado.detalhe.periodo', {periodo: intervaloEmTexto(d, ks)});
    MonitorMapas.credito('boxSerieDesfecho', {fontes: d.fonte, url: D.fonte, data: D.gerado_em});

    const cv = el('cDesfecho');
    if (cv && typeof Chart !== 'undefined') {
      if (grafico && typeof grafico.destroy === 'function') grafico.destroy();
      MonitorMapas.padraoGraficos(window.Chart);
      const rotulos = d.cadencia === 'semana'
        ? rotulosDeMes(String(ks[ks.length - 1] || '').split('-')[0], ks)
        : ks.map(k => periodoEmTexto(d, k));
      const titulos = ks.map(k => periodoEmTexto(d, k));
      const fs = ks.map(k => faixa(D, uf, k));
      grafico = new Chart(cv, {data: {labels: rotulos, datasets: [
        {type: 'bar', label: d.conta, data: ks.map(k => valor(D, uf, k)), backgroundColor: MonitorMapas.PALETA.anos['2026']},
        {type: 'line', label: 'menor valor esperado', data: fs.map(f => f ? f.de : null), borderColor: MonitorMapas.PALETA.anos.canal, borderWidth: 2, pointRadius: 0, fill: false},
        {type: 'line', label: 'maior valor esperado', data: fs.map(f => f ? f.ate : null), borderColor: MonitorMapas.PALETA.anos.p90, borderWidth: 1.5, pointRadius: 0, fill: false}]},
        options: {animation: false, responsive: true, maintainAspectRatio: false,
          plugins: {legend: {display: false},
            tooltip: {callbacks: {title: itens => (itens && itens[0] ? (titulos[itens[0].dataIndex] || '') : '')}}},
          scales: {y: {beginAtZero: true, title: {display: true, text: d.unidade}},
                   x: {ticks: {autoSkip: false, maxRotation: 0}}}}});
    }
    MonitorMapas.legenda('legSerieDesfecho', [
      {cor: MonitorMapas.PALETA.anos['2026'], rotulo: d.conta},
      {cor: MonitorMapas.PALETA.anos.canal, rotulo: txt('saude.observado.legenda.menor', {anos: faixaAnos})},
      {cor: MonitorMapas.PALETA.anos.p90, rotulo: txt('saude.observado.legenda.maior', {anos: faixaAnos})}]);

    /* O mapa é sempre por estado — é o que ele é —, e não muda com o seletor: o que muda é o
     * desfecho. Acumulado do ano para as séries semanais; último período fechado para as mensais,
     * que é o que o handover pede e o que a fonte mensal sustenta. */
    const fechadosBR = fechados(D, d, periodos(D, 'BR'));
    const ultimoBR = fechadosBR[fechadosBR.length - 1] || '';
    const ano = String(ultimoBR).split('-')[0];
    const bruto = {}, taxa = {};
    UFS_SEL.forEach(u => {
      const s = (D.serie || {})[u]; if (!s) return;
      const kFechados = fechados(D, d, Object.keys(s).filter(k => s[k] != null).sort());
      bruto[u] = d.mapa === 'acumulado'
        ? kFechados.filter(k => k.startsWith(ano)).reduce((a, k) => a + Number(s[k]), 0)
        : (kFechados.indexOf(ultimoBR) >= 0 ? Number(s[ultimoBR]) : null);
      if (bruto[u] == null) { delete bruto[u]; return; }
      if (POP_UF[u]) taxa[u] = bruto[u] / POP_UF[u] * 1e5;
    });
    _poe('tituloMapaDesfecho', 'saude.observado.mapa.titulo', {desfecho: d.rotulo});
    _poe('subMapaDesfecho', d.mapa === 'acumulado' ? 'saude.observado.mapa.legenda_acumulado' : 'saude.observado.mapa.legenda_ultimo',
         {ano: ano, ate: periodoEmTexto(d, ultimoBR), medida: d.conta});
    _poe('linhaMapaDesfecho', 'saude.observado.mapa.periodo', {periodo: periodoEmTexto(d, ultimoBR)});
    if (el('mapaDesfechoUF') && BR_GEOJSON) {
      const ctx = MonitorMapas.contexto(BR_GEOJSON, 480, 460);
      const rampa = MonitorMapas.PALETA.atmosfera.chuva_claro.rampa;
      const max = Math.max(1, ...Object.values(taxa));
      MonitorMapas.fundo && MonitorMapas.fundo('mapaDesfechoUF', 'chuva_claro');
      MonitorMapas.ufs(ctx, 'mapaDesfechoUF',
        u => taxa[u] == null ? MonitorMapas.NEUTRA : rampa[Math.min(rampa.length - 1, Math.floor(taxa[u] / max * rampa.length))],
        u => taxa[u] == null ? u + ': sem coleta'
          : u + ': ' + umaCasa(taxa[u]) + ' por 100 mil habitantes (' + n(bruto[u]) + ' ' + d.conta + ')');
      MonitorMapas.legenda('legMapaDesfecho', [
        ...rampa.map((c, i) => ({cor: c, rotulo: i === 0 ? 'menor' : (i === rampa.length - 1 ? 'maior' : '·')})),
        {cor: MonitorMapas.NEUTRA, rotulo: 'sem coleta'}]);
      MonitorMapas.credito('boxMapaDesfecho', {fontes: d.fonte.concat(['Censo 2022 (IBGE)']), data: D.gerado_em});
    }
    if (el('dlDesfechoUF')) {
      const esc = MonitorMapas.esc;
      el('dlDesfechoUF').innerHTML = Object.keys(taxa).sort((a, b) => taxa[b] - taxa[a]).map(u =>
        '<dt>' + esc(u) + '</dt><dd>' + umaCasa(taxa[u]) + ' por 100 mil habitantes · ' + n(bruto[u]) + ' ' + esc(d.conta) + '</dd>').join('');
    }
  }
  function _poe(id, catalogoId, valores) { const e = el(id); if (e) e.textContent = txt(catalogoId, valores); }

  /* ---- a lacuna da classe: desfecho em evidência sem arquivo, nomeado pelo catálogo ---- */
  function declararLacuna() {
    const p = el('desfechosLacuna'); if (!p || !CATALOGO) return;
    const semArquivo = (CATALOGO.desfechos || []).filter(x => ['dda', 'lepto'].indexOf(x.id) >= 0 && x.status_coleta !== 'coletado');
    const nomes = semArquivo.map(x => String(x.nome).replace(/\s*\(.*\)$/, ''))
      .map((s, i) => i === 0 ? s : s.charAt(0).toLowerCase() + s.slice(1));
    const texto = nomes.length ? txt('saude.observado.lacuna', {faltam: nomes.join(' e ')}) : '';
    p.textContent = texto; p.hidden = !texto;
  }

  /* ---- arranque: a malha e a lista de municípios são as que `__load` já buscou (é por isso que
   * esta seção é chamada no fim dele, e não um bloco solto: duas buscas do mesmo arquivo atrasavam
   * o desenho da grade dos 27). Daqui saem só a população, o catálogo e os quatro arquivos. ---- */
  Promise.all([
    (window.MonitorCatalogo && window.MonitorCatalogo.pronto) || Promise.resolve(),
    fetch('data/populacao_censo2022.json').then(r => r.ok ? r.json() : null).catch(() => null),
    fetch('data/saude_desfechos/catalogo.json').then(r => r.ok ? r.json() : null).catch(() => null),
  ].concat(DESFECHOS.map(d => fetch(d.arquivo).then(r => r.ok ? r.json() : null).catch(() => null))))
  .then(resultado => {
    const [, pop, cat] = resultado;
    CATALOGO = cat;
    const ref = PAINEL_LISTA;
    if (pop && ref) (Array.isArray(ref) ? ref : Object.values(ref)).forEach(m => {
      POP_UF[m.uf] = (POP_UF[m.uf] || 0) + Number(pop[String(m.codigo_ibge).padStart(7, '0')] || 0);
    });
    DESFECHOS.forEach((d, i) => { dados[d.id] = resultado[3 + i]; });
    // O primeiro cartão com arquivo abre o detalhe (o handover pede dengue aberto por padrão; se a
    // série de dengue faltar, abre o primeiro que tiver arquivo, nunca uma figura vazia).
    escolhido = (DESFECHOS.find(d => dados[d.id]) || {}).id || null;
    const sel = el('desfechosUF');
    if (sel) {
      UFS_SEL.slice().sort((a, b) => (NOMES[a] || a).localeCompare(NOMES[b] || b)).forEach(u => {
        const o = document.createElement('option'); o.value = u; o.textContent = (NOMES[u] || u) + ' (' + u + ')'; sel.appendChild(o);
      });
      sel.addEventListener('change', () => { uf = sel.value || 'BR'; desenharCartoes(); desenharDetalhe(); });
    }
    desenharCartoes(); desenharDetalhe(); declararLacuna();
  }).catch(_erroSaude("saude:secaoDosDesfechos"));
}
