// ===== saude.html · bloco 1 (extraído em 06/09/2026, CSP sem unsafe-inline) =====
let BR_GEOJSON, SUF, SSIN, SINAIS, MARE, MSAUDE, DESF, DESF_CANAL, DESF_COMP, PAINEL_LISTA, SRAG;

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
let SG = null;   // 14/09/2026: síndrome gripal (sg_serie.json, mesmo coletor do SRAG); nulo = lacuna declarada
let DDA = null;  // 14/09/2026: doenças diarreicas agudas (dda_serie.json, Sivep-DDA via LAI/Zenodo); nulo = lacuna declarada
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
  // 13/09/2026 (proposta de enxugamento, Manus AI): catálogo de 20 desfechos e tabela de gatilhos
  // migraram para pesquisadores.html — "é backlog metodológico; pertence a Pesquisadores". SRAG
  // continua aqui: alimenta o gráfico 'SRAG por semana', mantido na página principal.
  try { SRAG = await fetch('data/saude_desfechos/srag_serie.json').then(r => r.ok ? r.json() : null); } catch(e) { SRAG = null; }
  try { SG = await fetch('data/saude_desfechos/sg_serie.json').then(r => r.ok ? r.json() : null); } catch(e) { SG = null; }
  try { DDA = await fetch('data/saude_desfechos/dda_serie.json').then(r => r.ok ? r.json() : null); } catch(e) { DDA = null; }
  __init();
  // 02/10/2026 (bloco A.3): a amostra de 313 municípios saiu do mapa e a série duplicada
  // saiu da página. Dengue e chikungunya passam a ser contadas pelo SINAN, no bloco
  // `arbovirosesPelaPrimaria`, ao fim deste arquivo.
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
          + (faltam > 0 ? faltam + ' estado(s) ainda não verificado(s)' : 'as 27 verificadas');
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
        }).catch(() => {});
      }
      if (el('nEmergSaude')) {
        const r = (MSAUDE && MSAUDE.resposta) || {};
        el('nEmergSaude').textContent = n(r.emergencias);
        el('fonteEmergSaude').textContent = 'Desde ' + (r.desde || '—')
          + ' · emergência em saúde pública de importância nacional e decretos estaduais';
      }
    })();

  renderSRAG('srag');
  renderSG();
  renderDDA();
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
    const cartaoInstitucional = '<div class="cartao"><h3 class="figura-titulo">Contexto secundário: prontidão institucional</h3>'
      + (m.prontidao != null ? '<p class="card-body">' + m.prontidao + '/100 · ' + esc(m.faixa || '—') + ' — mede documento e antecipação, não o estado de saúde da população.</p>' : '<p class="card-body u-muted">Ainda não verificado.</p>') + '</div>';
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
        return '<em>' + esc(m.faixa) + ' · ' + esc(m.prontidao) + '</em><br>instrumento ' + esc(i.pontos) + ' (' + esc(ST_H[i.status] || i.status) + ')' + (i.data ? ' · ' + esc(i.data) : '') + '<br>cobertura sanitária ' + esc(c.pontos ?? '—') + ' (' + esc(c.planos_lidos ?? 0) + ' plano(s) lido(s) · ' + esc(c.planos_sem_leitura ?? 0) + ' sem leitura)' + '<br>antecipação ' + esc(a.pontos) + (i.temporada ? ' (edição ' + esc(i.temporada) + ')' : ''); },
      []);
    const R = (MSAUDE && MSAUDE.resumo) || {}; const pf = R.por_faixa || {};
    MonitorMapas.legenda('legMonitor', [
      ...['avançado', 'consolidado', 'em construção', 'estágio inicial'].map(f => ({cor: FX[f], rotulo: f + ' · ' + (pf[f] || 0) + ' UF' + ((pf[f] || 0) === 1 ? '' : 's')})),
      {cor: FX['não verificado'], rotulo: 'ainda não verificado · ' + (R.nao_verificadas ?? '—') + ' UFs (sem número)'}]);
    fonteFigura('boxMonitor', {fontes: ['MARÉ', 'MARÉ Saúde v0.3'], data: (MSAUDE || {}).gerado_em});
    // tabela alternativa
    const tb = document.querySelector('#tblMonitor tbody');
    if (tb) tb.innerHTML = UFS.map(uf => { const m = M[uf] || {}, i = m.instrumento || {}, a = m.antecipacao || {}, r = m.risco_atual || {};
      return '<tr><td><strong>' + uf + '</strong></td><td>' + (m.verificado ? esc(m.prontidao) : '—') + '</td><td>' + esc(m.faixa || '') + '</td><td>' + esc(ST_H[i.status] || '') + (i.data ? ' · ' + esc(i.data) : '') + '</td><td>' + ((m.cobertura || {}).pontos ?? '—') + ' · ' + esc((m.cobertura || {}).planos_lidos ?? 0) + ' lido(s) / ' + esc((m.cobertura || {}).planos_sem_leitura ?? 0) + ' sem leitura</td><td>' + (a.pontos ?? '—') + (i.temporada ? ' · ' + esc(i.temporada) : '') + '</td><td>' + (r.dengue_capital_nivel ? 'nível ' + esc(r.dengue_capital_nivel) + ' (' + esc(r.dengue_capital) + ')' : '—') + '</td><td>' + esc((m.risco_projetado || []).join('; ')) + '</td></tr>'; }).join('');
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

  /* CALOR (24/09/2026) — classe de excesso de calor do Ministério da Saúde, por município, agregada
     por UF. Substitui a contagem de avisos do INMET que estava aqui: aviso é ALERTA e mora na
     Defesa civil. E aquela contagem estava quebrada desde que foi escrita — lia `a.lista`/`a.avisos`
     em `avisos_inmet`, campos que o agregado nunca teve, então pintava ZERO nos 27 estados sempre,
     em qualquer dia, inclusive com aviso de calor em vigor. Zero silencioso é o pior defeito
     possível numa figura de risco: parece informação.
     O vocabulário (Normal, Baixo, Severo, Extremo) é o do MS; o projeto não reescala nada. */
  const CALOR = SSIN.calor_excesso || null;
  const fCalor = (SSIN.fontes || {}).painel_calor_ms || {};
  const CAL = [MonitorMapas.PALETA.zero, MonitorMapas.PALETA.ordinal4[1], MonitorMapas.PALETA.ordinal4[2], MonitorMapas.PALETA.ordinal4[3]];
  const calorUf = uf => (CALOR && CALOR.por_uf && CALOR.por_uf[uf]) || null;
  const nAcima = uf => { const c = calorUf(uf); return c ? (c.severo || 0) + (c.extremo || 0) : null; };
  desenharMapa('mapaCalor', 'legCalor',
    uf => { const n = nAcima(uf); return n == null ? NEUTRA : CAL[Math.min(3, n)]; },
    uf => { const c = calorUf(uf);
      if(!c) return 'Sem coleta até o corte';
      return 'Severo: ' + (c.severo || 0) + ' · Extremo: ' + (c.extremo || 0)
           + '<br>Baixo: ' + (c.baixo || 0) + ' · Normal: ' + (c.normal || 0)
           + '<br>' + (c.total || 0) + ' município(s) lido(s)'; },
    [{cor:CAL[0], rotulo:'nenhum município em severo ou extremo'}, {cor:CAL[1], rotulo:'1'},
     {cor:CAL[2], rotulo:'2'}, {cor:CAL[3], rotulo:'3 ou mais'}, {cor:NEUTRA, rotulo:'sem coleta até o corte'}]);
  fonteFigura('boxCalor', {fontes: fCalor.nome || 'Painel Nacional de Excesso de Calor',
                           url: fCalor.url_publica, data: CALOR ? CALOR.coletado_em : null});
  (function listaCalor(){
    const corpo = document.querySelector('#tblCalor tbody');
    if(!corpo) return;
    corpo.innerHTML = UFS.map(function(uf){
      const c = calorUf(uf);
      if(!c) return '<tr><td><strong>' + esc(uf) + '</strong></td><td colspan="5">sem coleta até o corte</td></tr>';
      return '<tr><td><strong>' + esc(uf) + '</strong></td><td>' + (c.normal || 0) + '</td><td>' + (c.baixo || 0)
           + '</td><td>' + (c.severo || 0) + '</td><td>' + (c.extremo || 0) + '</td><td>' + (c.total || 0) + '</td></tr>';
    }).join('');
  })();
  (function resumoCalor(){
    const el = document.getElementById('calorResumo');
    if(!el) return;
    if(CALOR && CALOR.resumo){
      const r = CALOR.resumo;
      el.textContent = (r.severo || 0) + ' município(s) em classe severa e ' + (r.extremo || 0)
        + ' em extrema, de ' + (CALOR.municipios_lidos || Object.keys(CALOR.municipios || {}).length)
        + ' lidos no dia ' + (CALOR.data || '') + ', segundo o Ministério da Saúde.';
      return;
    }
    /* Sem coleta, a seção diz POR QUE não há número. O painel do MS não publica API: o endereço é
       função interna do aplicativo e, medido em 24/09/2026, responde HTTP 200 com corpo vazio
       quando recusa. Recusa servida com 200 é recusa, nunca "nenhum município em excesso de calor". */
    el.textContent = 'Classe de excesso de calor por município: sem coleta até o corte.'
      + (fCalor.ultima_tentativa_falhou ? ' Última tentativa em ' + fCalor.ultima_tentativa_falhou + '.' : '');
  })();
  /* 01/10/2026 (bloco D): sigla traduzida no texto visível. O rótulo vem do arquivo de sinais, que
   * é escrito pelo coletor no vocabulário interno; traduzir na LEITURA, e não no dado, mantém o
   * banco do jeito que o coletor o escreveu e o leitor sem sigla para decodificar. */
  const PUBLICO = [[/\bESPIN\b/g, 'emergência em saúde pública de importância nacional'],
                   [/\bCIEVS\b/g, 'centro de vigilância'],
                   [/\bCOES?\b/g, 'centro de operações de emergência'],
                   [/\bSRAG\b/g, 'síndrome respiratória grave'],
                   [/\bMDDA\b/g, 'vigilância das diarreicas']];
  const semSigla = t => PUBLICO.reduce((x, [re, por]) => String(x).replace(re, por), t || '');
  (function(){ const f = SSIN.fontes || {}; const c = Object.entries(f).map(([k, v]) => semSigla(v.nome || k) + ': ' + (v.consultado_em ? 'consultado em ' + v.consultado_em : (v.status === 'reuso' ? 'reuso da página de sinais' : 'ainda não consultado')));
    const el = document.getElementById('carimboSaude'); if (el) el.textContent = 'Estado das fontes: ' + c.join(' · ') + '.'; })();

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
    + (m.verificado ? linha('Como o número é formado', 'documento estadual ' + esc(i.pontos)
        + ' · cobertura sanitária ' + esc(c.pontos ?? '—') + ' (' + esc(c.planos_lidos ?? 0)
        + ' plano(s) municipal(is) lido(s), ' + esc(c.planos_sem_leitura ?? 0) + ' sem leitura)'
        + ' · quando o ato saiu em relação ao primeiro boletim ' + esc(a.pontos)
        + ' → média ' + String(m.prontidao).replace('.', ',') + ' (pesos iguais)') : '')
    + (m.camada === 'adaptacao' ? linha('Plano decenal de adaptação', 'registrado como estrutura; não pontua') : '')
    + linha('Resposta sanitária', ((RS || {}).ufs || []).includes(uf) ? 'emergência sanitária declarada no ciclo' : 'nenhuma emergência sanitária declarada localizada desde 29/06/2026')
    + linha('Risco sanitário projetado', (m.risco_projetado || []).length ? (m.risco_projetado || []).map(esc).join('; ') : 'sem registro')
    + linha('Dengue na capital', dc.dengue_capital_nivel != null ? 'nível ' + esc(dc.dengue_capital_nivel) + ' (InfoDengue), ' + esc(dc.dengue_capital || '') + ', SE ' + esc(String(dc.dengue_se || '—')) : 'sem coleta')
    + (u.data_verificacao ? '<p class="note">Bateria estadual executada em ' + esc(u.data_verificacao) + '.</p>' : '');
  const dlg = document.getElementById('detailSaude');
  if (!dlg) return;
  dlg.setAttribute('aria-label', 'Detalhe do estado');
  if (!dlg.open) { if (typeof dlg.showModal === 'function') dlg.showModal(); else dlg.open = true; }
}

function cartoesEstadosSaude(){
  /* Item 7 do handover de 02/10/2026: os 27 estados no MESMO componente da inicial — o mapa de
   * cartões, cada estado na sua posição geográfica, com sigla, nome, número e as duas barras. Antes
   * eram colunas por região, com outro desenho: dois componentes para a mesma coisa divergem na
   * primeira correção. A disposição, o teclado e o estilo vivem em assets/js/grade-estados.js.
   */
  const wrap = document.getElementById('regionsSaude'), dlg = document.getElementById('detailSaude');
  if (!wrap || !dlg || !window.GradeEstados) return;
  const M = (MSAUDE && MSAUDE.ufs) || {};
  const RS = (MSAUDE && MSAUDE.resposta) || {ufs: []};
  const ST_H = {NOVO: 'plano do ciclo', READ: 'readaptado', VIG_REVISADO: 'plano revisado em 2026',
                VIG: 'plano de todo ano', ELAB: 'em elaboração', LAC: 'não localizado',
                NAO_VERIFICADO: 'ainda não verificado'};
  fetch('data/estados.json').then(r => r.ok ? r.json() : null).then(E => {
    const lista = ((E && E.ufs) || []).map(u => ({uf: u.uf, nome: u.nome, status: u.status}));
    (E && E.ufs || []).forEach(u => { NOMES[u.uf] = u.nome; REG[u.uf] = u.regiao; });
    GradeEstados.montar({
      alvo: wrap, ufs: lista, rotulo: 'MARÉ Saúde',
      indice: uf => { const m = M[uf] || {}; return m.verificado ? m.prontidao : null; },
      /* A barra de baixo é a mesma da inicial: resposta 0–100. Em saúde, a resposta registrada é a
       * emergência em saúde pública declarada no ciclo — e onde não houve declaração o valor é
       * ZERO medido, não ausência. */
      resposta: uf => ((RS.ufs || []).includes(uf) ? 100 : 0),
      extra: uf => {
        const m = M[uf] || {}; const i = m.instrumento || {}; const dc = m.risco_atual || {};
        return '<div class="tile-face"><span>'
          + esc(ST_H[i.status] || i.status || 'ainda não verificado')
          + (i.data ? ' · ' + esc(i.data) : '') + '</span><span>'
          + (m.camada === 'adaptacao' ? 'plano decenal: estrutura'
             : 'cobertura sanitária ' + esc((m.cobertura || {}).pontos ?? '—'))
          + '</span></div>';
      },
      aoClicar: uf => abrirDetalheSaude(uf),
    });
    GradeEstados.legendaDasBarras('legendaRegionsSaude', 'MARÉ Saúde');
    if (window.MonitorMapas && MonitorMapas.animarGauges) MonitorMapas.animarGauges(wrap);
  }).catch(() => {});
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


// ===== SRAG por semana, Brasil (§36; InfoGripe). Peso zero. O Monitor não atribui casos ao El Niño. =====
// 14/09/2026: parametrizada por indicador (SRAG | SG) — mesmo CSV do InfoGripe, mesmo desenho; sem arquivo = lacuna declarada
const __serieCharts = {};
const INDICADORES_RESP = {
  // 01/10/2026: rótulo, eixo e fonte no vocabulário público — sigla traduzida (bloco D) e a fonte
  // é a PRIMÁRIA. O InfoGripe deixou de ser a origem da série em 29/09 (§ do coletor): as duas URLs
  // dele exigem login desde setembro, e quem entrega a série é o SIVEP-Gripe, do Ministério da
  // Saúde, sem estimativa de dados recentes — por isso também sai o "nowcasting".
  srag: {rotulo: 'síndrome respiratória grave', eixo: 'casos · Brasil',
         fonte: ['SIVEP-Gripe (Ministério da Saúde)'], dados: () => SRAG,
         motivo: 'A série do SIVEP-Gripe ainda não foi coletada até o corte.',
         // A fonte primária NÃO publica nowcasting: as últimas semanas são parciais (valor
         // bruto, atraso de notificação), e é isso que a segunda barra diz — mesmo tratamento
         // da série de diarreicas, pela mesma razão.
         segunda: 'parciais (últimas semanas — sem estimativa)', chaveSegunda: 'parcial'},
  // 01/10/2026: a fonte da síndrome gripal passa a ser a PRIMÁRIA (e-SUS Notifica). O motivo
  // da lacuna diz o que foi medido em 01/10: as duas rotas que o portal publica recusam
  // acesso automatizado, e o conjunto por ano vai de 2020 a 2024 — sem o ano do ciclo.
  sg:   {rotulo: 'síndrome gripal', eixo: 'casos · Brasil',
         fonte: ['e-SUS Notifica (Ministério da Saúde)'], dados: () => SG,
         motivo: 'A fonte recusa acesso automatizado e não publica o ano do ciclo: lacuna declarada.'},
};
// 14/09/2026: DDA usa o MESMO componente e o mesmo renderizador da figura respiratória (série nacional sobre o canal
// endêmico); só mudam os textos e a segunda barra — a fonte não publica nowcasting, então as últimas 4 semanas são
// mostradas como 'parciais' (valor bruto, atraso de digitação), nunca como estimativa.
const INDICADOR_DDA = {rotulo: 'diarreicas agudas',
  eixo: 'atendimentos em unidades sentinela · Brasil', fonte: ['Sivep-DDA (Ministério da Saúde) via LAI, depósito Zenodo (Saldanha/Fiocruz)'], dados: () => DDA,
  motivo: 'A série da vigilância das diarreicas não pôde ser lida nas últimas tentativas de coleta.', segunda: 'parciais (últimas 4 semanas — sem estimativa)', chaveSegunda: 'parcial'};
function renderSerieNacional(cfg, ids){
  const D = cfg.dados();
  const cv = document.getElementById(ids.canvas), svg = document.getElementById(ids.svg);
  if (__serieCharts[ids.canvas]) { if (typeof __serieCharts[ids.canvas].destroy === 'function') __serieCharts[ids.canvas].destroy(); __serieCharts[ids.canvas] = null; }
  const br = D && D.serie && D.serie.BR;
  if (!br) {
    // 11/09/2026: sem arquivo a figura ficava como moldura vazia, sem dizer nada a quem lê — o pior desfecho possível.
    // Ausência é DECLARADA na própria mídia (o portão de figuras só admite título, legenda e crédito no cartão): canvas some, SVG de lacuna aparece.
    if (cv) cv.hidden = true;
    if (svg) { svg.hidden = false; svg.setAttribute('aria-label', 'Série de ' + cfg.rotulo + ' ainda não coletada — lacuna declarada; ' + cfg.motivo);
      const t1 = document.getElementById(ids.txt1), t2 = document.getElementById(ids.txt2);
      if (t1) { t1.textContent = 'Série de ' + cfg.rotulo + ' ainda não coletada — lacuna declarada'; t1.setAttribute('fill', MonitorMapas.cor('muted')); }
      if (t2) { t2.textContent = cfg.motivo; t2.setAttribute('fill', MonitorMapas.cor('muted')); } }
    MonitorMapas.legenda(ids.leg, [{cor: MonitorMapas.NEUTRA, rotulo: 'sem coleta de ' + cfg.rotulo + ' até o corte'}]);
    ids.credito({fontes: cfg.fonte, data: null});
    return;
  }
  if (svg) svg.hidden = true; if (cv) cv.hidden = false;
  const canal = (D.canal_endemico || {}).BR || {}; const seg = (D[cfg.chaveSegunda] || {}).BR || {};
  const ano = D.ano_corrente; const semanas = Array.from({length: 53}, (_, i) => String(i + 1).padStart(2, '0'));
  const ate = Math.max(...Object.keys(br).concat(Object.keys(seg)).filter(k => k.startsWith(String(ano))).map(k => +k.split('-')[1]));
  const labels = semanas.slice(0, ate);
  MonitorMapas.padraoGraficos(window.Chart);
  const eixoSerie = eixoDeMeses(String(ano), labels);
  const opSerie = opcoesDeEixoSemanal(eixoSerie.titulos);
  __serieCharts[ids.canvas] = new Chart(cv, {data: {labels: eixoSerie.labels, datasets: [
      {type: 'bar', label: 'consolidado', data: labels.map(w => (br[ano + '-' + w] ?? null)), backgroundColor: MonitorMapas.PALETA.anos['2026'] || MonitorMapas.PALETA.anos.canal, order: 2},
      {type: 'bar', label: cfg.segunda, data: labels.map(w => (seg[ano + '-' + w] ?? null)), backgroundColor: MonitorMapas.PALETA.anos['2024'], order: 2},
      {type: 'line', label: 'mediana 2019–2025', data: labels.map(w => (canal[w] || {}).mediana ?? null), borderColor: MonitorMapas.PALETA.anos.canal, borderWidth: 2, pointRadius: 0, order: 1},
      {type: 'line', label: 'p90', data: labels.map(w => (canal[w] || {}).p90 ?? null), borderColor: MonitorMapas.PALETA.anos.p90, borderWidth: 1.5, pointRadius: 0, order: 1}]},
    options: {animation: false, responsive: true, maintainAspectRatio: false,
      plugins: {legend: {display: false}, tooltip: {callbacks: {title: opSerie.tooltipTitulo}}},
      scales: {x: opSerie.x, y: {beginAtZero: true, title: {display: true, text: cfg.eixo}}}}});
  // Entrada de legenda sem rótulo é quadradinho de cor sem nome: a legenda deixa de explicar e
  // passa a decorar. Indicador sem segunda barra simplesmente não a declara.
  // Item 8: "mediana" e "p90" saem da legenda — são o nome do cálculo, não o do que se vê.
  MonitorMapas.legenda(ids.leg, [
    {cor: MonitorMapas.PALETA.anos['2026'] || MonitorMapas.PALETA.anos.canal, rotulo: 'consolidado'},
    ...(cfg.segunda ? [{cor: MonitorMapas.PALETA.anos['2024'], rotulo: cfg.segunda}] : []),
    {cor: MonitorMapas.PALETA.anos.canal, rotulo: 'faixa habitual para a época: menor valor esperado'},
    {cor: MonitorMapas.PALETA.anos.p90, rotulo: 'faixa habitual para a época: maior valor esperado'}]);
  ids.credito({fontes: cfg.fonte, data: D.gerado_em, url: D.fonte});
}
function renderSRAG(ind){
  ind = INDICADORES_RESP[ind] ? ind : 'srag';
  renderSerieNacional(INDICADORES_RESP[ind], {credito: p => fonteFigura('boxSRAG', p), canvas: 'cSRAG', svg: 'svgSRAGLacuna', txt1: 'txtSRAGLacuna1', txt2: 'txtSRAGLacuna2', leg: 'legSRAG'});
}
function renderSG(){
  if (!document.getElementById('boxSG')) return;
  renderSerieNacional(INDICADORES_RESP.sg, {credito: p => fonteFigura('boxSG', p), canvas: 'cSG', svg: 'svgSGLacuna', txt1: 'txtSGLacuna1', txt2: 'txtSGLacuna2', leg: 'legSG'});
}
function renderDDA(){
  if (!document.getElementById('boxDDA')) return;
  renderSerieNacional(INDICADOR_DDA, {credito: p => fonteFigura('boxDDA', p), canvas: 'cDDA', svg: 'svgDDALacuna', txt1: 'txtDDALacuna1', txt2: 'txtDDALacuna2', leg: 'legDDA'});
}
(function(){ const sel = document.getElementById('selIndicadorSRAG'); if (sel) sel.addEventListener('change', () => renderSRAG(sel.value)); })();

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
    if (Rsa.verificadas != null) titulo('boxMonitor', `Prontidão sanitária por estado: ${Rsa.verificadas} de ${UFS.length} estados verificados`);
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


/* Busca por município no nível de alerta (bloco C.3 do handover de 01/10/2026).
 *
 * Três travas, e as três existem porque a alternativa de cada uma seria afirmar o que não se sabe:
 *   - cidade FORA dos municípios acompanhados não aparece como nível 1 nem como zero: aparece como
 *     não acompanhada, que é ausência de observação e não ausência de casos;
 *   - cidade sem semana consolidada aparece sem nível, com a semana declarada;
 *   - a lista de cidades é a do IBGE inteira, de propósito: só assim a busca pode DIZER que a
 *     cidade existe e não é acompanhada. Listar apenas as acompanhadas esconderia a lacuna.
 */
(async function buscaMunicipalSaude(){
  const el = id => document.getElementById(id);
  const sel = el('munUFSaude'), entrada = el('munNomeSaude'), lista = el('munListaSaude'),
        conta = el('munContaSaude'), saida = el('munResultadoSaude');
  if (!sel || !entrada || !lista || !saida) return;
  const esc = v => String(v == null ? '' : v).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const NIVEL = {1: 'nível 1 (baixa atividade)', 2: 'nível 2 (atenção)',
                 3: 'nível 3 (alerta)', 4: 'nível 4 (emergência)'};
  let REF, DEN, CHI;
  try {
    [REF, DEN, CHI] = await Promise.all([
      fetch('data/municipios_ibge_referencia.json').then(r => r.ok ? r.json() : null),
      fetch('data/saude_desfechos/serie_painel.json').then(r => r.ok ? r.json() : null),
      fetch('data/saude_desfechos/chik_serie_painel.json').then(r => r.ok ? r.json() : null),
    ]);
  } catch (e) { REF = DEN = CHI = null; }
  if (!REF) { conta.textContent = 'Lista de municípios sem coleta até o corte.'; return; }
  const ref = Array.isArray(REF) ? REF : Object.values(REF);
  const porUF = {}, codigo = {};
  ref.forEach(m => {
    const c = String(m.codigo_ibge).padStart(7, '0');
    (porUF[m.uf] = porUF[m.uf] || []).push(m.nome);
    codigo[m.uf + '|' + m.nome.toLowerCase()] = c;
  });
  Object.keys(porUF).sort().forEach(uf => sel.insertAdjacentHTML('beforeend', `<option value="${uf}">${uf}</option>`));
  const acompanhados = new Set([...Object.keys((DEN && DEN.municipios) || {}),
                                ...Object.keys((CHI && CHI.municipios) || {})]);
  conta.textContent = `${acompanhados.size.toLocaleString('pt-BR')} municípios acompanhados de `
    + `${ref.length.toLocaleString('pt-BR')} no país`;

  sel.addEventListener('change', () => {
    const nomes = porUF[sel.value] || [];
    lista.innerHTML = nomes.slice().sort((a, b) => a.localeCompare(b, 'pt-BR'))
      .map(x => `<option value="${esc(x)}"></option>`).join('');
    entrada.disabled = !sel.value;
    entrada.value = '';
    saida.hidden = true;
  });

  function linha(rotulo, base, cod){
    const m = base && base.municipios && base.municipios[cod];
    if (!m) return `<li>${rotulo}: município não acompanhado nesta série</li>`;
    const nv = m.nivel_ultima_se;
    if (nv == null) return `<li>${rotulo}: sem semana consolidada até o corte</li>`;
    const quando = m.ultima_se ? semanaEmDatas(String(m.ultima_se).split('-')[0], m.ultima_se) : null;
    return `<li>${rotulo}: ${esc(NIVEL[nv] || ('nível ' + nv))}${quando ? ' na semana ' + esc(quando) : ''}</li>`;
  }

  function mostrar(){
    const cod = codigo[sel.value + '|' + (entrada.value || '').trim().toLowerCase()];
    if (!cod) { saida.hidden = true; return; }
    saida.hidden = false;
    saida.innerHTML = `<p class="u-mb-0"><strong>${esc(entrada.value)} (${esc(sel.value)})</strong></p>`
      + `<ul class="u-mb-0">${linha('Dengue', DEN, cod)}${linha('Chikungunya', CHI, cod)}</ul>`;
  }
  entrada.addEventListener('change', mostrar);
  entrada.addEventListener('input', () => { if ((entrada.value || '').length > 2) mostrar(); });
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

  fetch('data/saude_desfechos/dengue_sinan_serie.json').then(r => r.ok ? r.json() : null).then(D => {
    const br = ((D || {}).serie || {}).BR;
    const u = br ? ultimaFechada(Object.fromEntries(Object.entries(br).filter(([k]) => k.startsWith(String(D.ano_corrente))))) : null;
    if (!u) { if (el('nDengueSE')) el('nDengueSE').textContent = 'sem coleta'; return; }
    if (el('nDengueSE')) el('nDengueSE').textContent = n(u.valor);
    if (el('rotuloDengueSE')) {
      el('rotuloDengueSE').textContent = 'notificações de dengue na semana '
        + semanaEmDatas(u.se.split('-')[0], u.se);
    }
    if (el('fonteDengueSE')) el('fonteDengueSE').textContent = 'SINAN (Ministério da Saúde) · '
      + (D.conta === 'notificacoes' ? 'notificações, não casos confirmados' : '') ;
  }).catch(() => {});

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
    if (el('fonteSragSE')) el('fonteSragSE').textContent = 'SIVEP-Gripe (Ministério da Saúde)';
  }).catch(() => {});

  /* Estados com dengue em nível de alerta: a régua é do InfoDengue (níveis 3 e 4) e a agregação por
   * estado é nossa — a nota diz qual é, porque o InfoDengue não publica um nível por estado. */
  fetch('data/saude_desfechos/serie_painel.json').then(r => r.ok ? r.json() : null).then(P => {
    const M = (P || {}).municipios || {};
    if (!Object.keys(M).length) { if (el('nUFsAlerta')) el('nUFsAlerta').textContent = 'sem coleta'; return; }
    const ufs = new Set();
    Object.values(M).forEach(m => { if ((m.nivel_ultima_se || 0) >= 3 && m.uf) ufs.add(m.uf); });
    if (el('nUFsAlerta')) el('nUFsAlerta').textContent = ufs.size + ' de 27';
    if (el('fonteUFsAlerta')) {
      el('fonteUFsAlerta').textContent = 'InfoDengue (Fiocruz/FGV) · o estado entra quando ao menos '
        + 'um município acompanhado está em nível 3 ou 4';
    }
  }).catch(() => {});

  /* O calor vem de `calor_excesso`, que é onde o coletor o escreve: `resumo` com as quatro classes
   * do vocabulário do Ministério da Saúde e `municipios_lidos`. A primeira versão deste cartão
   * procurou o dado em `uf[*].calor_ms`, caminho que o arquivo nunca teve — e dizia "sem coleta"
   * com o dado em disco, que é o pior jeito de errar numa figura de risco. */
  fetch('data/saude_sinais.json').then(r => r.ok ? r.json() : null).then(SS => {
    const C = (SS || {}).calor_excesso || null;
    const r = (C || {}).resumo || null;
    if (!r) { if (el('nCalorMun')) el('nCalorMun').textContent = 'sem coleta'; return; }
    const acima = Number(r.severo || 0) + Number(r.extremo || 0);
    if (el('nCalorMun')) el('nCalorMun').textContent = n(acima);
    if (el('fonteCalorMun')) {
      const lidos = C.municipios_lidos || Object.keys(C.municipios || {}).length;
      el('fonteCalorMun').textContent = 'Painel Nacional de Excesso de Calor (Ministério da Saúde) · '
        + n(lidos) + ' município(s) lido(s)' + (C.data ? ' · consulta de ' + C.data : '');
    }
  }).catch(() => {});

  fetch('data/monitor_saude.json').then(r => r.ok ? r.json() : null).then(MS => {
    const r = ((MS || {}).resposta) || {};
    if (el('nEmergSaude')) el('nEmergSaude').textContent = n(r.emergencias);
    if (el('fonteEmergSaude')) {
      el('fonteEmergSaude').textContent = 'Desde ' + (r.desde || '—')
        + ' · emergência em saúde pública de importância nacional e decretos estaduais';
    }
  }).catch(() => {});
})();

/* ===== Dengue e chikungunya pela fonte primária (bloco A.3) =====
 * Série semanal do país contra a faixa esperada para a época, e mapa por estado em notificações por
 * 100 mil habitantes. Por 100 mil porque o total bruto só ordena os estados por tamanho.
 *
 * A faixa esperada é a mediana e o p90 das semanas equivalentes de 2019 a 2025, calculados aqui a
 * partir da própria série — não há "estimativa de dados recentes": o SINAN publica contagem, e o
 * que falta nas últimas semanas é notificação que ainda vai chegar.
 */
(function arbovirosesPelaPrimaria(){
  const CONFIG = [
    {chave: 'dengue', arquivo: 'data/saude_desfechos/dengue_sinan_serie.json', rotulo: 'dengue',
     canvas: 'cDengueSemana', leg: 'legDengueSemana', box: 'boxDengueSemana',
     linha: 'linhaDengueSemana', mapa: 'mapaDengueUF', legMapa: 'legDengueUF',
     boxMapa: 'boxDengueUF', linhaMapa: 'linhaDengueUF', dl: 'dlDengueUF', frase: 'fraseDengue'},
    {chave: 'chikungunya', arquivo: 'data/saude_desfechos/chik_sinan_serie.json',
     rotulo: 'chikungunya', canvas: 'cChikSemana', leg: 'legChikSemana', box: 'boxChikSemana',
     linha: 'linhaChikSemana', mapa: 'mapaChikUF', legMapa: 'legChikUF', boxMapa: 'boxChikUF',
     linhaMapa: 'linhaChikUF', dl: 'dlChikUF', frase: 'fraseChik'},
  ];
  const el = id => document.getElementById(id);
  const n = v => Number(v || 0).toLocaleString('pt-BR');
  const umaCasa = v => Number(v || 0).toLocaleString('pt-BR', {minimumFractionDigits: 1, maximumFractionDigits: 1});

  const faixa = (serie, anos, se) => {
    const vs = anos.map(a => serie[a + '-' + se]).filter(v => typeof v === 'number').sort((x, y) => x - y);
    if (!vs.length) return null;
    const mediana = vs[Math.floor(vs.length / 2)];
    const p90 = vs[Math.min(vs.length - 1, Math.floor(vs.length * 0.9))];
    return {mediana, p90};
  };

  Promise.all([
    fetch('data/geo_uf.json').then(r => r.ok ? r.json() : null),
    fetch('data/populacao_censo2022.json').then(r => r.ok ? r.json() : null),
    fetch('data/municipios_ibge_referencia.json').then(r => r.ok ? r.json() : null),
  ]).then(([GEO, POP, REF]) => {
    const popUF = {};
    if (POP && REF) {
      const ref = Array.isArray(REF) ? REF : Object.values(REF);
      ref.forEach(m => {
        const cod = String(m.codigo_ibge).padStart(7, '0');
        popUF[m.uf] = (popUF[m.uf] || 0) + Number(POP[cod] || 0);
      });
    }
    CONFIG.forEach(cfg => {
      fetch(cfg.arquivo).then(r => r.ok ? r.json() : null).then(D => {
        const serie = (D || {}).serie;
        const legEl = el(cfg.leg);
        if (!serie || !serie.BR) {
          if (legEl) legEl.innerHTML = '<span class="escala">Série de ' + cfg.rotulo + ' ainda não coletada — lacuna declarada.</span>';
          if (el(cfg.frase)) el(cfg.frase).textContent = 'Série de ' + cfg.rotulo + ' ainda não coletada até o corte.';
          return;
        }
        const ano = String(D.ano_corrente);
        const anos = (D.anos_canal || []).map(String);
        const br = serie.BR;
        const ses = Object.keys(br).filter(k => k.startsWith(ano)).sort();
        const comValor = ses.filter(k => br[k] != null);
        const ultima = comValor[comValor.length - 1];
        const rotulos = ses.map(k => k.split('-')[1]);

        /* A frase do dado: "{n} notificações na semana {SE}, dentro / acima da faixa esperada". A
         * comparação é com a faixa da própria série, e por isso é fato, não juízo. */
        if (ultima && el(cfg.frase)) {
          const f = faixa(br, anos, ultima.split('-')[1]);
          const v = br[ultima];
          const posicao = !f ? 'sem faixa esperada para a época'
            : (v > f.p90 ? 'acima da faixa esperada para a época'
               : (v >= f.mediana ? 'dentro da faixa esperada para a época, acima da mediana'
                  : 'dentro da faixa esperada para a época'));
          el(cfg.frase).textContent = n(v) + ' notificações de ' + cfg.rotulo + ' na semana '
            + semanaEmDatas(ano, ultima) + ', ' + posicao + '. As '
            + 'semanas seguintes ainda recebem notificações e aparecem sem valor.';
        }
        if (el(cfg.linha)) {
          // Era "{n} semana(s) fechada(s) de {ano}": contava semanas, trazia o "(s)" que o item 2
          // proíbe e não dizia ao leitor de quando é o dado. Agora diz o período coberto.
          const ini = primeiraSemanaComValor(ano, comValor);
          el(cfg.linha).textContent = (ini && ultima)
            ? 'de ' + ini + ' a ' + (window.MonitorSemana
                ? MonitorSemana.fimPorExtenso(Number(ano), Number(ultima.split('-')[1])) : '')
            : '';
        }

        const cv = el(cfg.canvas);
        if (cv && typeof Chart !== 'undefined' && window.MonitorMapas) {
          MonitorMapas.padraoGraficos(window.Chart);
          const med = ses.map(k => { const f = faixa(br, anos, k.split('-')[1]); return f ? f.mediana : null; });
          const p90 = ses.map(k => { const f = faixa(br, anos, k.split('-')[1]); return f ? f.p90 : null; });
          // EIXO DE MESES, não de números de semana (item 0). O rótulo aparece só na primeira
          // semana de cada mês; nas outras fica vazio, e assim o eixo se lê como um calendário
          // em vez de uma régua de 1 a 52. Quem precisa da semana exata tem o tooltip, que diz o
          // intervalo de datas — que é como a leitora pensa a data, e não "a semana 33".
          const rotulosMes = rotulosDeMes(ano, ses);
          const titulosData = ses.map(k => semanaEmDatas(ano, k, true));
          new Chart(cv, {data: {labels: rotulosMes, datasets: [
            {type: 'line', label: 'p90 de 2019–2025', data: p90, borderColor: MonitorMapas.PALETA.anos.p90, backgroundColor: MonitorMapas.PALETA.anos.p90, fill: false, pointRadius: 0, borderWidth: 1},
            {type: 'line', label: 'mediana de 2019–2025', data: med, borderColor: MonitorMapas.PALETA.anos.canal, backgroundColor: MonitorMapas.PALETA.anos.canal, fill: false, pointRadius: 0, borderWidth: 1},
            {type: 'bar', label: 'notificações de ' + ano, data: ses.map(k => br[k]), backgroundColor: MonitorMapas.PALETA.anos['2026'] || MonitorMapas.PALETA.serie[0]},
          ]}, options: {animation: false, responsive: true, maintainAspectRatio: false,
            plugins: {legend: {display: false},
              tooltip: {callbacks: {title: itens => (itens && itens[0] ? titulosData[itens[0].dataIndex] : '')}}},
            scales: {y: {beginAtZero: true, title: {display: true, text: 'notificações'}},
                     x: {ticks: {autoSkip: false, maxRotation: 0}}}}});
          // "mediana" e "p90" saem da legenda (item 8): são o nome do cálculo, não o nome do
          // que o leitor vê. O cálculo fica na metodologia; aqui fica o que as duas linhas
          // delimitam, que é uma faixa de valores habituais para aquela época do ano.
          const faixaAnos = anos.length ? ' (' + anos[0] + ' a ' + anos[anos.length - 1] + ')' : '';
          MonitorMapas.legenda(cfg.leg, [
            {cor: MonitorMapas.PALETA.anos['2026'] || MonitorMapas.PALETA.serie[0], rotulo: 'notificações de ' + ano},
            {cor: MonitorMapas.PALETA.anos.canal, rotulo: 'faixa habitual para a época' + faixaAnos + ': menor valor esperado'},
            {cor: MonitorMapas.PALETA.anos.p90, rotulo: 'faixa habitual para a época' + faixaAnos + ': maior valor esperado'}]);
        }


        /* Mapa por estado: acumulado do ano até a última semana fechada, por 100 mil habitantes. */
        const acum = {};
        Object.entries(serie).forEach(([uf, porSE]) => {
          if (uf === 'BR' || !porSE) return;
          acum[uf] = Object.entries(porSE).filter(([k, v]) => k.startsWith(ano) && typeof v === 'number')
            .reduce((a, [, v]) => a + v, 0);
        });
        const taxa = {};
        Object.keys(acum).forEach(uf => { if (popUF[uf]) taxa[uf] = acum[uf] / popUF[uf] * 1e5; });
        if (el(cfg.mapa) && GEO && window.MonitorMapas) {
          const ctx = MonitorMapas.contexto(GEO, 480, 460);
          const rampa = MonitorMapas.PALETA.atmosfera.chuva_claro.rampa;
          const max = Math.max(1, ...Object.values(taxa));
          MonitorMapas.fundo && MonitorMapas.fundo(cfg.mapa, 'chuva_claro');
          MonitorMapas.ufs(ctx, cfg.mapa,
            uf => taxa[uf] == null ? MonitorMapas.NEUTRA : rampa[Math.min(rampa.length - 1, Math.floor(taxa[uf] / max * rampa.length))],
            uf => taxa[uf] == null ? uf + ': sem coleta'
              : uf + ': ' + umaCasa(taxa[uf]) + ' por 100 mil habitantes (' + n(acum[uf]) + ' notificações)');
          MonitorMapas.legenda(cfg.legMapa, [
            ...rampa.map((c, i) => ({cor: c, rotulo: i === 0 ? 'menor' : (i === rampa.length - 1 ? 'maior' : '·')})),
            {cor: MonitorMapas.NEUTRA, rotulo: 'sem coleta'}]);
        }
        // O crédito é da FIGURA, não do desenho: sem ele, uma figura sem malha carregada ficaria
        // sem fonte declarada, e o portão de saúde reprova — com razão.
        /* Os créditos vão com o id LITERAL de propósito: `verificar_saude.py` confere a presença
         * do crédito lendo o fonte do JS, e um id em variável é invisível para ele. Perder a
         * conferência para economizar quatro linhas seria trocar prova por elegância. */
        if (window.MonitorMapas) {
          const fS = {fontes: ['SINAN (Ministério da Saúde)'], data: D.gerado_em};
          const fM = {fontes: ['SINAN (Ministério da Saúde)', 'Censo 2022 (IBGE)'], data: D.gerado_em};
          if (cfg.chave === 'dengue') {
            MonitorMapas.credito('boxDengueSemana', fS);
            MonitorMapas.credito('boxDengueUF', fM);
          } else {
            MonitorMapas.credito('boxChikSemana', fS);
            MonitorMapas.credito('boxChikUF', fM);
          }
        }
        if (el(cfg.linhaMapa)) {
          const ate = ultima && window.MonitorSemana
            ? MonitorSemana.fimPorExtenso(Number(ano), Number(ultima.split('-')[1])) : null;
          // Rótulo vazio em vez de "—" (item 2): sem data, a linha não aparece.
          el(cfg.linhaMapa).textContent = ate ? 'de 1º de janeiro a ' + ate : '';
        }
        if (el(cfg.dl)) {
          const esc = v => String(v == null ? '' : v).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
          el(cfg.dl).innerHTML = Object.keys(taxa).sort((a, b) => taxa[b] - taxa[a]).map(uf =>
            '<dt>' + esc(uf) + '</dt><dd>' + umaCasa(taxa[uf]) + ' por 100 mil habitantes · ' + n(acum[uf]) + ' notificações</dd>').join('');
        }
      }).catch(() => {});
    });
  }).catch(() => {});
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

  /* 1 · O número do MARÉ Saúde no topo. Enquanto não forem 27 verificadas, o rótulo diz de quantas
   * é a média — a diferença entre publicar uma média parcial e publicar um índice nacional. */
  fetch('data/monitor_saude.json').then(r => r.ok ? r.json() : null).then(MS => {
    const res = ((MS || {}).resumo) || {};
    if (res.media_das_verificadas == null) {
      if (el('nIndiceSaude')) el('nIndiceSaude').textContent = 'sem coleta';
      return;
    }
    if (el('nIndiceSaude')) {
      el('nIndiceSaude').textContent = Number(res.media_das_verificadas)
        .toLocaleString('pt-BR', {minimumFractionDigits: 1, maximumFractionDigits: 1});
    }
    if (el('rotuloIndiceSaude')) {
      el('rotuloIndiceSaude').textContent = res.verificadas >= 27
        ? 'de 100, na preparação publicada em saúde'
        : 'de 100, média dos ' + res.verificadas + ' estados verificados';
    }
    if (el('fonteIndiceSaude')) {
      el('fonteIndiceSaude').textContent = 'MARÉ, sobre documentos oficiais lidos · '
        + (res.verificadas || 0) + ' de 27 estados verificados';
    }
  }).catch(() => {});

  /* 2 · O que foi localizado em cada estado: plano, coordenação na saúde e ligação com o governo
   * do estado. Em linguagem de leitor — o leitor não precisa saber que internamente são F1 e F2. */
  Promise.all([
    fetch('data/saude_uf.json').then(r => r.ok ? r.json() : null),
    fetch('data/monitor_saude_v04.json').then(r => r.ok ? r.json() : null),
  ]).then(([SUFd, V04]) => {
    const alvo = el('dlVerificacaoUF');
    if (!alvo || !SUFd) return;
    const uf04 = (V04 || {}).uf || {};
    const doc = o => (o && o.doc) ? esc(o.doc) + (o.data ? ' · ' + esc(o.data) : '') : null;
    alvo.innerHTML = UFS.map(uf => {
      const u = (SUFd.uf || {})[uf] || {};
      const inst = ((u.instrumentos || [])[0]) || {};
      const c = uf04[uf] || {};
      const linhas = [
        ['Plano de saúde', doc(inst)],
        ['Coordenação na saúde', doc((c.coordenacao || {}).f1 || c.coordenacao)],
        ['Ligação com o governo do estado', doc((c.coordenacao || {}).f2)],
      ].map(([rot, v]) => rot + ': ' + (v || 'não localizado até o corte'));
      return '<dt>' + esc(uf) + '</dt><dd>' + linhas.join('<br>') + '</dd>';
    }).join('');
    const linha = el('linhaVerificacaoUF');
    if (linha) {
      const comPlano = UFS.filter(uf => (((SUFd.uf || {})[uf] || {}).instrumentos || [{}])[0].doc).length;
      linha.textContent = comPlano + ' de 27 com plano localizado · atualizado em ' + (SUFd.corte || '—');
    }
    const leg = el('legVerificacaoUF');
    if (leg) leg.innerHTML = '<span class="escala">Documento oficial lido em cada estado; o que não foi localizado aparece como tal.</span>';
    if (window.MonitorMapas) {
      MonitorMapas.credito('boxVerificacaoUF', {fontes: ['MARÉ, sobre diários oficiais e portais das secretarias'], data: SUFd.corte});
    }
  }).catch(() => {});

  /* 3 · Risco previsto por estado — famílias derivadas dos boletins do Painel El Niño. */
  Promise.all([
    fetch('data/geo_uf.json').then(r => r.ok ? r.json() : null),
    fetch('data/saude_uf.json').then(r => r.ok ? r.json() : null),
  ]).then(([GEO, SUFd]) => {
    if (!el('mapaRiscoSan') || !GEO || !SUFd || !window.MonitorMapas) return;
    const FAM = {seca: ['Seca, calor e fogo', MonitorMapas.PALETA.risco.seca],
                 chuvas: ['Chuvas extremas', MonitorMapas.PALETA.risco.chuvas],
                 multi: ['As duas famílias', MonitorMapas.PALETA.risco.multi]};
    const fam = uf => {
      const r = (((SUFd.uf || {})[uf] || {}).risco_sanitario_projetado || []).join(' ').toLowerCase();
      const s = /calor|queimad|arbovir|estiagem|seca/.test(r), c = /leptospir|diarre|hepatite|chuva/.test(r);
      return s && c ? 'multi' : s ? 'seca' : c ? 'chuvas' : null;
    };
    const ctx = MonitorMapas.contexto(GEO, 480, 460);
    MonitorMapas.fundo && MonitorMapas.fundo('mapaRiscoSan', 'chuva_claro');
    MonitorMapas.ufs(ctx, 'mapaRiscoSan',
      uf => fam(uf) ? FAM[fam(uf)][1] : MonitorMapas.NEUTRA,
      uf => { const r = ((SUFd.uf || {})[uf] || {}).risco_sanitario_projetado || [];
              return r.length ? esc(r.join('<br>')) : 'sem risco previsto registrado'; });
    MonitorMapas.legenda('legRiscoSan', Object.values(FAM).map(v => ({cor: v[1], rotulo: v[0]}))
      .concat([{cor: MonitorMapas.NEUTRA, rotulo: 'sem risco previsto registrado'}]));
    const dl = el('dlRiscoSan');
    if (dl) {
      dl.innerHTML = UFS.map(uf => '<dt>' + esc(uf) + '</dt><dd>'
        + esc((((SUFd.uf || {})[uf] || {}).risco_sanitario_projetado || ['sem risco previsto registrado']).join('; '))
        + '</dd>').join('');
    }
    if (el('linhaRiscoSan')) el('linhaRiscoSan').textContent = 'boletins nº 1 a 3 do Painel El Niño';
    MonitorMapas.credito('boxRiscoSan', {fontes: ['Painel El Niño 2026-2027 (CEMADEN/INPE)', 'boletins nº 1 a 3'], data: SUFd.corte});
  }).catch(() => {});

  /* 4 · Síndrome respiratória grave por estado, por 100 mil habitantes. */
  Promise.all([
    fetch('data/geo_uf.json').then(r => r.ok ? r.json() : null),
    fetch('data/saude_desfechos/srag_serie.json').then(r => r.ok ? r.json() : null),
    fetch('data/populacao_censo2022.json').then(r => r.ok ? r.json() : null),
    fetch('data/municipios_ibge_referencia.json').then(r => r.ok ? r.json() : null),
  ]).then(([GEO, S, POP, REF]) => {
    const leg = el('legSragUF');
    if (!S || !S.serie) {
      if (leg) leg.innerHTML = '<span class="escala">Série de síndrome respiratória grave ainda não coletada — lacuna declarada.</span>';
      return;
    }
    const popUF = {};
    if (POP && REF) {
      (Array.isArray(REF) ? REF : Object.values(REF)).forEach(m => {
        popUF[m.uf] = (popUF[m.uf] || 0) + Number(POP[String(m.codigo_ibge).padStart(7, '0')] || 0);
      });
    }
    const ano = String(S.ano_corrente || new Date().getFullYear());
    const acum = {}, taxa = {};
    Object.entries(S.serie).forEach(([uf, porSE]) => {
      if (!porSE || typeof porSE !== 'object' || uf === 'BR') return;
      acum[uf] = Object.entries(porSE).filter(([k, v]) => k.startsWith(ano) && typeof v === 'number')
        .reduce((a, [, v]) => a + v, 0);
      if (popUF[uf]) taxa[uf] = acum[uf] / popUF[uf] * 1e5;
    });
    if (el('mapaSragUF') && GEO && window.MonitorMapas) {
      const ctx = MonitorMapas.contexto(GEO, 480, 460);
      const rampa = MonitorMapas.PALETA.atmosfera.chuva_claro.rampa;
      const max = Math.max(1, ...Object.values(taxa));
      MonitorMapas.fundo && MonitorMapas.fundo('mapaSragUF', 'chuva_claro');
      MonitorMapas.ufs(ctx, 'mapaSragUF',
        uf => taxa[uf] == null ? MonitorMapas.NEUTRA : rampa[Math.min(rampa.length - 1, Math.floor(taxa[uf] / max * rampa.length))],
        uf => taxa[uf] == null ? uf + ': sem coleta'
          : uf + ': ' + umaCasa(taxa[uf]) + ' por 100 mil habitantes (' + n(acum[uf]) + ' internações)');
      MonitorMapas.legenda('legSragUF', [
        ...rampa.map((c, i) => ({cor: c, rotulo: i === 0 ? 'menor' : (i === rampa.length - 1 ? 'maior' : '·')})),
        {cor: MonitorMapas.NEUTRA, rotulo: 'sem coleta'}]);
      MonitorMapas.credito('boxSragUF', {fontes: ['SIVEP-Gripe (Ministério da Saúde)', 'Censo 2022 (IBGE)'], data: S.gerado_em});
    }
    if (el('dlSragUF')) {
      el('dlSragUF').innerHTML = Object.keys(taxa).sort((a, b) => taxa[b] - taxa[a]).map(uf =>
        '<dt>' + esc(uf) + '</dt><dd>' + umaCasa(taxa[uf]) + ' por 100 mil habitantes · ' + n(acum[uf]) + ' internações</dd>').join('');
    }
    if (el('linhaSragUF')) el('linhaSragUF').textContent = 'acumulado de ' + ano + ' · ' + Object.keys(taxa).length + ' estados com dado';
  }).catch(() => {});

  /* 5 · Calor: a distribuição por classe. O Painel do MS publica FOTOGRAFIA por município, não
   * série — e o cartão mostra o que a fonte tem, em vez de fingir uma série semanal. */
  fetch('data/saude_sinais.json').then(r => r.ok ? r.json() : null).then(SS => {
    const C = ((SS || {}).calor_excesso) || null;
    const r = (C || {}).resumo || null;
    const leg = el('legCalorSerie');
    if (!r) {
      if (leg) leg.innerHTML = '<span class="escala">Painel de excesso de calor sem coleta até o corte.</span>';
      return;
    }
    const classes = [['Normal', r.normal || 0], ['Baixo', r.baixo || 0], ['Severo', r.severo || 0],
                     ['Extremo', r.extremo || 0]];
    const cv = el('cCalorSerie');
    if (cv && typeof Chart !== 'undefined' && window.MonitorMapas) {
      MonitorMapas.padraoGraficos(window.Chart);
      new Chart(cv, {type: 'bar', data: {labels: classes.map(c => c[0]),
        datasets: [{label: 'municípios', data: classes.map(c => c[1]),
                    backgroundColor: MonitorMapas.PALETA.ordinal4}]},
        options: {animation: false, responsive: true, maintainAspectRatio: false,
          plugins: {legend: {display: false}},
          scales: {y: {beginAtZero: true, title: {display: true, text: 'municípios'}}}}});
      MonitorMapas.legenda('legCalorSerie', classes.map((c, i) => ({cor: MonitorMapas.PALETA.ordinal4[i], rotulo: c[0].toLowerCase()})));
      MonitorMapas.credito('boxCalorSerie', {fontes: ['Painel Nacional de Excesso de Calor (Ministério da Saúde)'], data: C.data});
    }
    if (el('linhaCalorSerie')) {
      el('linhaCalorSerie').textContent = n(C.municipios_lidos || 0) + ' município(s) lido(s)'
        + (C.data ? ' · consulta de ' + C.data : '');
    }
    if (el('fraseCalor')) {
      el('fraseCalor').textContent = n((r.severo || 0) + (r.extremo || 0))
        + ' município(s) em classe severa ou extrema de excesso de calor na consulta mais recente, '
        + 'de ' + n(C.municipios_lidos || 0) + ' lidos. O vocabulário das classes é o do Ministério '
        + 'da Saúde.';
    }
  }).catch(() => {});

  /* 6 · As três buscas por município. Mesma trava nas três: cidade fora do que a fonte cobre
   * aparece como NÃO ACOMPANHADA, nunca como zero — e a lista oferecida é a do IBGE inteira, para
   * que a busca possa dizer que a cidade existe e não é coberta. */
  function buscaPorMunicipio(sufixo, carregar, responder, contar, fontes) {
    const sel = el('uf' + sufixo), ent = el('nome' + sufixo), lista = el('lista' + sufixo),
          conta = el('conta' + sufixo), saida = el('resultado' + sufixo);
    if (!sel || !ent || !lista || !saida) return;
    Promise.all([
      fetch('data/municipios_ibge_referencia.json').then(r => r.ok ? r.json() : null),
      carregar(),
    ]).then(([REF, base]) => {
      if (!REF) { conta.textContent = 'Lista de municípios sem coleta até o corte.'; return; }
      const ref = Array.isArray(REF) ? REF : Object.values(REF);
      const porUF = {}, codigo = {};
      ref.forEach(m => {
        const c = String(m.codigo_ibge).padStart(7, '0');
        (porUF[m.uf] = porUF[m.uf] || []).push(m.nome);
        codigo[m.uf + '|' + m.nome.toLowerCase()] = c;
      });
      Object.keys(porUF).sort().forEach(uf => sel.insertAdjacentHTML('beforeend', '<option value="' + uf + '">' + uf + '</option>'));
      conta.textContent = contar(base, ref);
      /* O crédito vai com o id LITERAL: o portão de saúde confere a existência do crédito lendo
       * o código-fonte, e id montado por concatenação é invisível para ele — com razão, porque é
       * invisível para quem lê o código também. */
      if (window.MonitorMapas && fontes) {
        const quando = (base && (base.gerado_em || base.data)) || null;
        if (sufixo === 'DengueMunicipios') MonitorMapas.credito('boxDengueMunicipios', {fontes: fontes, data: quando});
        if (sufixo === 'ChikMunicipios') MonitorMapas.credito('boxChikMunicipios', {fontes: fontes, data: quando});
        if (sufixo === 'CalorMunicipios') MonitorMapas.credito('boxCalorMunicipios', {fontes: fontes, data: quando});
      }
      sel.addEventListener('change', () => {
        lista.innerHTML = (porUF[sel.value] || []).slice().sort((a, b) => a.localeCompare(b, 'pt-BR'))
          .map(x => '<option value="' + esc(x) + '"></option>').join('');
        ent.disabled = !sel.value;
        ent.value = '';
        saida.hidden = true;
      });
      const mostrar = () => {
        const cod = codigo[sel.value + '|' + (ent.value || '').trim().toLowerCase()];
        if (!cod) { saida.hidden = true; return; }
        saida.hidden = false;
        saida.innerHTML = '<p class="u-mb-0"><strong>' + esc(ent.value) + ' (' + esc(sel.value) + ')</strong></p>'
          + responder(base, cod);
      };
      ent.addEventListener('change', mostrar);
      ent.addEventListener('input', () => { if ((ent.value || '').length > 2) mostrar(); });
    }).catch(() => {});
  }

  const NIVEL = {1: 'nível 1 (baixa atividade)', 2: 'nível 2 (atenção)', 3: 'nível 3 (alerta)',
                 4: 'nível 4 (emergência)'};
  const respostaAlerta = (base, cod) => {
    const m = base && base.municipios && base.municipios[cod];
    if (!m) return '<p class="u-mb-0">Município não acompanhado nesta série.</p>';
    if (m.nivel_ultima_se == null) return '<p class="u-mb-0">Sem semana consolidada até o corte.</p>';
    return '<p class="u-mb-0">' + esc(NIVEL[m.nivel_ultima_se] || ('nível ' + m.nivel_ultima_se))
      + ' na semana ' + esc(m.ultima_se || '—') + '.</p>';
  };
  const contarAlerta = (base, ref) => ((base && base.municipios)
    ? Object.keys(base.municipios).length.toLocaleString('pt-BR') + ' municípios acompanhados de '
      + ref.length.toLocaleString('pt-BR') + ' no país'
    : 'Série sem coleta até o corte.');

  buscaPorMunicipio('DengueMunicipios',
    () => fetch('data/saude_desfechos/serie_painel.json').then(r => r.ok ? r.json() : null),
    respostaAlerta, contarAlerta, ['InfoDengue (Fiocruz/FGV)']);
  buscaPorMunicipio('ChikMunicipios',
    () => fetch('data/saude_desfechos/chik_serie_painel.json').then(r => r.ok ? r.json() : null),
    respostaAlerta, contarAlerta, ['InfoDengue (Fiocruz/FGV)']);
  buscaPorMunicipio('CalorMunicipios',
    () => fetch('data/saude_sinais.json').then(r => r.ok ? r.json() : null).then(SS => (SS || {}).calor_excesso || null),
    (base, cod) => {
      const m = base && base.municipios && base.municipios[cod];
      if (!m) return '<p class="u-mb-0">Município não lido na consulta mais recente.</p>';
      const classe = m.classe || m.nivel || m;
      return '<p class="u-mb-0">Classe ' + esc(String(classe)) + ' na consulta de ' + esc(base.data || '—') + '.</p>';
    },
    (base, ref) => (base && base.municipios)
      ? Object.keys(base.municipios).length.toLocaleString('pt-BR') + ' municípios lidos na consulta mais recente'
      : 'Painel sem coleta até o corte.',
    ['Painel Nacional de Excesso de Calor (Ministério da Saúde)']);

  /* 7 · A lista do governo federal, sem cartão (o contrato pede lista simples). */
  fetch('data/saude_federal.json').then(r => r.ok ? r.json() : null).then(F => {
    const alvo = el('listaFederalSaude');
    if (!alvo) return;
    const itens = (F && (F.itens || F.documentos)) || [];
    if (!itens.length) {
      alvo.innerHTML = '<li>Nenhum documento federal localizado até o corte.</li>';
      return;
    }
    alvo.innerHTML = itens.map(x => {
      const nome = esc(x.nome || x.titulo || x.documento || 'documento');
      const meta = [x.orgao, x.data].filter(Boolean).map(esc).join(' · ');
      const alvoTxt = x.url ? '<a href="' + esc(x.url) + '" target="_blank" rel="noopener">' + nome + '</a>' : nome;
      return '<li>' + alvoTxt + (meta ? ' <span class="u-muted">(' + meta + ')</span>' : '') + '</li>';
    }).join('');
  }).catch(() => {});
})();
