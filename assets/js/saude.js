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
let BR_GEOJSON, MSAUDE;
// Lote 6, §2: a frase do dado nasce oculta e só aparece com texto — nunca "—" nem linha vazia.
const mostrarFrase = (alvo, texto) => { alvo.textContent = texto; alvo.hidden = !texto; };
/* Número em texto público com vírgula decimal (A4-16); não-número passa como veio ("—", nulo).
   21/10/2026: uma casa decimal, SALVO quando ela zeraria um valor medido — 0,037 internação por
   100 mil saía "0", e dizer zero onde houve 75 internações é afirmar o que não se mediu. Abaixo de
   0,05 vale um dígito significativo ("0,04", "0,009"), que é curto e não mente. */
const decBR = v => (v == null || v === '' || isNaN(Number(v))) ? v
  : MonitorMapas.numBR(v, Number.isInteger(Number(v)) ? 0 : 1);

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
const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));

async function __load(){
  [BR_GEOJSON, MSAUDE] = await Promise.all(['geo_uf','monitor_saude'].map(f => fetch('data/' + f + '.json').then(r => {
      if(!r.ok) throw new Error('Falha ao carregar data/' + f + '.json'); return r.json(); })));
  if (window.MonitorCatalogo && MonitorCatalogo.pronto) { try { await MonitorCatalogo.pronto; } catch (e) {} }
  tabelaDosPlanos();
  montarDesfechos().catch(_erroSaude("saude:desfechos"));
}

const fonteFigura = MonitorMapas.credito;

/* ===== A situação de cada estado (v0.8, handover VIGIAR 26/10: sai o mapa; fica a tabela) =====
 * Uma tabela por UF com o tipo de plano que cada secretaria estadual de saúde publicou. A UF é o botão
 * que abre a ficha do estado (`#detailSaude`). Os textos de escada vêm de `metodo.escada` do dado. */
const ufsDoMonitor = () => (MSAUDE && MSAUDE.ufs) || {};
const tipoDoEstado = uf => ((ufsDoMonitor()[uf] || {}).instrumento || {}).status || 'NAO_VERIFICADO';
const textoSaude = (id, v) => (window.MonitorCatalogo && MonitorCatalogo.texto(id, v)) || '';

function tabelaDosPlanos() {
  const nome = t => textoSaude('saude.estadual.tipo.' + t);
  const instr = uf => (ufsDoMonitor()[uf] || {}).instrumento || {};
  const escada = ((MSAUDE.metodo || {}).escada) || {};
  mostrarFrase(document.getElementById('escadaPlano'), textoSaude('saude.estadual.escada', escada));
  const coord = o => (o && o.doc) ? esc(ST_COORD[o.status] || o.status || '') + (o.data ? ' · ' + esc(o.data) : '') : esc(textoSaude('saude.estadual.ficha.nao_verificada'));
  document.querySelector('#tblMonitor tbody').innerHTML = UFS.map(uf => { const co = (ufsDoMonitor()[uf] || {}).coordenacao || {};
    return '<tr><td><button type="button" class="chip-risco" data-uf="' + uf + '" aria-label="'
      + esc(textoSaude('saude.estadual.lista.botao', {estado: NOME_UF[uf]})) + '"><strong>' + uf + '</strong></button></td><td>' + esc(nome(tipoDoEstado(uf)))
      + (instr(uf).data ? ' · ' + esc(instr(uf).data) : '') + '</td><td>' + coord(co.f1) + '</td><td>' + coord(co.f2) + '</td></tr>'; }).join('');
  document.querySelector('#tblMonitor tbody').addEventListener('click', ev => { const b = ev.target.closest('button[data-uf]'); if (b) abrirDetalheSaude(b.dataset.uf); });
  fonteFigura('boxMonitor', {fontes: ['MARÉ Saúde'], data: MSAUDE.gerado_em});
}

/* Os degraus das duas funções da coordenação, em linguagem de leitor (METODOLOGIA §91.3). */
const ST_COORD = {
  CRIADO_CICLO: 'criada para o ciclo',
  REATIVADO_CICLO: 'reativada para o ciclo',
  PERMANENTE: 'estrutura permanente',
  ANUNCIADO: 'anunciada, sem ato publicado',
  NOMEADA_COM_ATRIBUICAO: 'secretaria de saúde nomeada, com atribuição',
  LISTADA_SEM_ATRIBUICAO: 'secretaria de saúde listada, sem atribuição',
  LAC: 'não localizada até o corte',
};

/* Tempo do ato depois do Boletim nº 1: contexto de peso zero, fora da nota (METODOLOGIA v0.7). */
function tempoDoEstado(t) {
  const d = t && t.dias_apos_boletim_1;
  if (d == null) return esc(textoSaude('saude.estadual.ficha.tempo_sem_dia'));
  return esc(textoSaude(d < 0 ? 'saude.estadual.ficha.tempo_antes' : 'saude.estadual.ficha.tempo_depois', {dias: Math.abs(d)}));
}

/* A ficha do estado, no <dialog>. A coordenação lê `ufs.<UF>.coordenacao` do monitor e se preenche
 * sozinha à medida que a rotina verifica cada estado; sem registro, diz que não foi verificada. */
function abrirDetalheSaude(uf) {
  const m = ufsDoMonitor()[uf] || {}, i = m.instrumento || {}, c = m.cobertura || {}, co = m.coordenacao || {};
  const RS = (MSAUDE && MSAUDE.resposta) || {};
  const tx = id => esc(textoSaude('saude.estadual.ficha.' + id));
  const linha = (k, v) => '<div class="field"><div class="k">' + k + '</div><div class="v">' + v + '</div></div>';
  const doc = o => (o && o.doc) ? '<span class="pill-nivel">' + esc(ST_COORD[o.status] || o.status) + '</span> ' + esc(o.doc)
    + (o.data ? ' (' + esc(o.data) + ')' : '') + (o.url ? ' · <a href="' + esc(o.url) + '" target="_blank" rel="noopener">' + tx('fonte_oficial') + ' →</a>' : '') : tx('nao_verificada');
  document.getElementById('detailSaudeConteudo').innerHTML = '<div class="uf-name">' + esc(NOME_UF[uf] || uf) + ' <span class="sub">(' + uf + ')</span></div>'
    + (m.verificado ? '' : '<p class="placeholder">' + tx('sem_plano') + '</p>')
    + linha(tx('plano'), '<span class="pill-nivel">' + esc(textoSaude('saude.estadual.tipo.' + tipoDoEstado(uf))) + '</span>' + (i.doc ? ' ' + esc(i.doc) : '')
      + (i.data ? ' (' + esc(i.data) + ')' : '') + (i.orgao ? ' · ' + esc(i.orgao) : '')
      + (i.url ? ' · <a href="' + esc(i.url) + '" target="_blank" rel="noopener">' + tx('fonte_oficial') + ' →</a>' : ''))
    + linha(tx('coordenacao'), doc(co.f1)) + linha(tx('governo'), doc(co.f2))
    + linha(tx('tempo'), tempoDoEstado(m.tempo))
    + (m.verificado ? linha(tx('camada'), esc(camadaMunicipalSaude(c)) + '; ' + tx('camada_nota')) : '')
    + linha(tx('resposta'), (RS.ufs || []).includes(uf) ? tx('resposta_sim') : tx('resposta_nao'));
  const dlg = document.getElementById('detailSaude');
  if (!dlg.open) { if (typeof dlg.showModal === 'function') dlg.showModal(); else dlg.open = true; }
}

__load().catch(err => { const m = document.getElementById('subSaude'); if (m) m.insertAdjacentHTML('afterend', '<p class="note u-rust">Erro ao carregar os dados: '+esc(err.message)+'</p>'); });

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

  /* 4 · Consulta do município (HANDOVER_SAUDE_PAGINA §4): o módulo comum, com a mesma renderização em
   * cartões do Proteja-se. Dengue, chikungunya, calor e plano vêm de `data/saude_municipio/<UF>.json`;
   * respiratória grave e MARÉ Saúde são do estado, e o rótulo diz que são. Município que a fonte não
   * leu diz a sua classe de ausência, nunca zero. Todo texto vive no catálogo. */
  const TC = (id, v) => textoSaude('saude.consulta.' + id, v);
  const semana = v => { const m = /(\d{4})-(\d{1,2})/.exec(String(v || '')); return (m && MonitorSemana.porExtenso(+m[1], +m[2], true)) || ''; };
  const json = f => fetch(f).then(r => r.ok ? r.json() : null).catch(() => null);
  const porUF = {}, extra = Promise.all([json('data/saude_desfechos/srag.json'), json('data/meta.json')]), cartas = () => cartas.p = cartas.p || json('data/municipios_card.json');
  const cartao = (acento, rotulo, valor, nota, classe) => '<div class="cartao cartao--acento-' + acento + '"><p class="cartao-numero-rotulo">' + esc(rotulo) + '</p>'
    + '<p' + (classe ? ' class="' + classe + '"' : '') + '>' + valor + '</p><p class="note u-mb-0">' + nota + '</p></div>';
  /* O plano do município, com o vocabulário da inicial: o documento e a data com link, ou a frase de
     "não localizamos até a data de corte"; a leitura da saúde no plano é a segunda linha descritiva. */
  const cartaoPlanoDoMunicipio = (sp, pl, uf, meta) => {
    const achou = sp.estado === 'encontrado' || sp.estado === 'estadual';
    const valor = sp.estado === 'nao_verificado' ? TC('plano.nao_verificado')
      : achou ? TC(sp.data ? 'plano.com_plano_data' : 'plano.com_plano', {documento: sp.documento || sp.fonte || '', data: sp.data || ''}) : TC('plano.sem_plano', {corte: (meta || {}).corte || ''});
    const camada = achou && pl ? TC(pl.pagina_citada ? 'plano.saude_no_plano' : 'plano.saude_no_plano_sem_pagina', {pagina: pl.pagina_citada}) : '';
    return cartao('musgo', TC('rotulo.plano_municipio'), esc(valor) + (achou && sp.url ? ' · <a href="' + esc(sp.url) + '" target="_blank" rel="noopener">' + esc(TC('plano.abrir')) + '</a>' : ''),
      [camada && esc(camada), achou && sp.fonte && esc(sp.fonte), '<a href="index.html#' + esc(uf) + '">' + esc(TC('plano.ver_inicial')) + '</a>'].filter(Boolean).join(' · '));
  };
  const cartaoArbo = (rotulo, x, d, semanaSemDado) => x
    ? cartao('neutro', rotulo, esc(TC('arbo.nivel_' + x.nivel) || TC('arbo.nivel_outro', {n: x.nivel})), esc(TC('arbo.nota', {semana: semana(x.semana)})))
    : cartao('neutro', rotulo, esc(TC('arbo.nao_lido', {semana: semanaSemDado})), esc(TC('arbo.nota_nao_lido', {data: (d || {}).gerado_em || ''})));
  fetch('data/geo_uf.json').then(r => r.json()).then(GEO => ConsultaMunicipio.montar({uf: 'consultaSaudeUF', municipio: 'consultaSaudeMun', lista: 'consultaSaudeLista', cartao: 'consultaSaudeCard',
    estados: Object.fromEntries(GEO.features.map(f => [f.properties.sigla, f.properties.name])), semLista: TC('sem_lista'),
    municipios: uf => (porUF[uf] = porUF[uf] || Promise.all([json('data/saude_municipio/' + uf + '.json'), extra, cartas()]))
      .then(([D, [S, meta], CARD]) => { porUF[uf].dados = {D, S, meta, CARD}; return D && Object.values(D.municipios).map(x => x.nome); }),
    mostrar: (uf, nome, card) => {
      const {D, S, meta, CARD} = porUF[uf].dados, o = D.origens || {}, [cod, m] = Object.entries(D.municipios).find(([, x]) => x.nome === nome);
      const sp = ConsultaMunicipio.situacaoDoPlano(((CARD || {}).municipios || {})[cod]);
      const sinal = (m.dengue || m.chikungunya || {}).semana, quando = semana(sinal);
      const e = ufsDoMonitor()[uf] || {}, pl = m.saude_no_plano, calor = m.calor && m.calor !== 'Normal';
      const srag = S && S.ultimo && S.ultimo[uf] && S.ultimo[uf].consolidado, pos = srag && posicaoNaFaixa(S, uf);
      card.innerHTML = '<h4>' + esc(nome) + ' · ' + esc(uf) + '</h4><div class="grade-figuras grade-figuras--3">'
        + cartaoArbo(TC('rotulo.dengue'), m.dengue, o.dengue, quando) + cartaoArbo(TC('rotulo.chikungunya'), m.chikungunya, o.chikungunya, quando)
        + cartao('argila', TC('rotulo.calor'), esc(m.calor == null ? TC('calor.sem_coleta') : calor ? TC('calor.com_excesso', {classe: String(m.calor).toLowerCase()}) : TC('calor.sem_excesso')),
            esc(TC('calor.nota', {data: MonitorMapas.dataBR((o.calor || {}).data) || ''})))
        + cartao('neutro', TC('rotulo.srag'), srag ? esc(TC('srag.valor', {n: srag.valor, semana: semana(srag.periodo)})) + (pos ? ' · <span class="posicao posicao--' + pos.posicao + '">' + esc(textoSaude('saude.posicao.' + pos.posicao)) + '</span>' : '') : esc(TC('srag.sem_coleta')),
            esc(TC('srag.nota', {data: (S && MonitorMapas.dataBR(S.coletado_em)) || ''})))
        + cartao('musgo', TC('rotulo.plano_estado'), esc(textoSaude('saude.estadual.tipo.' + tipoDoEstado(uf))) + ' · <a href="#estadual" data-ficha="' + esc(uf) + '">' + esc(TC('plano_estado.ficha')) + '</a>',
            esc(TC('plano_estado.nota', {data: MSAUDE.corte || ''})))
        + cartaoPlanoDoMunicipio(sp, pl, uf, meta) + '</div>';
      card.querySelector('[data-ficha]').addEventListener('click', ev => { ev.preventDefault(); abrirDetalheSaude(ev.target.dataset.ficha); });
    }})).catch(_erroSaude("saude:consulta"));
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
/* A faixa habitual leva a cor da família de risco a que o desfecho pertence, bem clara, para não
   disputar com a linha do valor observado. Só as famílias que a paleta já tem; desfecho sem família
   (óbitos em geral) fica no tom da faixa habitual de sempre. */
const FAMILIA_DO_DESFECHO = {dengue: 'calor', chikungunya: 'calor', internacoes_cardio: 'calor', internacoes_renal: 'calor',
  internacoes_calor: 'calor', srag: 'fogo', internacoes_respiratorias: 'fogo', internacoes_fumaca: 'fogo',
  diarreias: 'chuva', leptospirose: 'chuva', hepatite_a: 'chuva', internacoes_desidratacao: 'chuva'};
const corDaFaixa = d => MonitorMapas.PALETA.familia[FAMILIA_DO_DESFECHO[d.desfecho]] || MonitorMapas.PALETA.serie_habitual.faixa;
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

/* A linha dos períodos recentes sobre a faixa habitual, em SVG: polígono da faixa na cor da família,
   linha em tinta, último ponto em argila. Sem eixo e sem número: quem mede é o cartão. */
function serieEmSvg(valores, faixas, rotulo, estado, corFaixa) {
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
    + (temFaixa ? '<polygon points="' + faixaCima + ' ' + faixaBaixo + '" fill="' + corFaixa + '" fill-opacity="0.22"></polygon>' : '')
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

/* A posição do último valor consolidado do território na faixa habitual da SEMANA DO PRÓPRIO VALOR
   (comparar com a faixa de outra semana é o erro a impedir). Uma função para o cartão, a consulta
   do município e, adiante, o topo e o detalhe. A comparação é nos MESMOS números que o leitor lê:
   a precisão do rótulo varia com o tamanho do valor, e só `decBR` decide por ela. */
function posicaoNaFaixa(d, uf) {
  const c = ((d.ultimo || {})[uf] || {}).consolidado;
  const f = c && ((d.faixa_habitual || {})[uf] || {})[String(c.periodo).split('-')[1]];
  if (!f || f.p90 == null) return null;
  const uma = x => Number(String(decBR(x)).replace(/\./g, '').replace(',', '.'));
  const v = uma(c.por_100mil);
  return {posicao: v > uma(f.p90) ? 'acima' : (v < uma(f.mediana) ? 'abaixo' : 'dentro'), mediana: f.mediana, p90: f.p90};
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
  const p = posicaoNaFaixa(d, uf), dentro = p && p.posicao;
  const texto = !p ? textoSaude('saude.posicao.sem_faixa')
    : textoSaude('saude.posicao.' + p.posicao) + ' (' + decBR(p.mediana) + ' a ' + decBR(p.p90) + ')';
  /* Só o desfecho em evidência abre detalhe (§2): o cartão da segunda camada não é botão, não entra
     na ordem de tabulação e não promete um mapa que a seção não desenha para ele. */
  return '<div class="cartao-numero cartao-numero--saude"'
    + (EM_EVIDENCIA(d) ? ' role="button" tabindex="0" data-desfecho="' + esc(d.desfecho)
        + '" aria-pressed="' + (d.desfecho === DESFECHO_ESCOLHIDO) + '"' : '') + '>'
    + '<p class="cartao-numero-familia">' + esc(d.rotulo) + '</p>'
    + '<p class="cartao-numero-valor">' + esc(_qtdCartao(c.por_100mil)) + '</p>'
    + '<p class="cartao-numero-rotulo">' + esc(d.unidade) + ' por 100 mil' + cadencia
    + esc(periodoEmPalavras(c.periodo, d.periodo)) + '</p>'
    + '<p class="cartao-numero-variacao' + (p ? ' posicao posicao--' + dentro : '') + '">' + esc(texto) + '</p>'
    + serieEmSvg(chaves.map(ch => serie[ch]), chaves.map(doAno),
        d.rotulo + ', ' + (d.periodo === 'semana' ? 'últimas 52 semanas' : 'últimos 24 meses')
        + ', sobre a faixa habitual para a época', dentro, corDaFaixa(d))
    + '<p class="cartao-numero-fonte">' + rodape + '</p></div>';
}

/* A posição de cada UF na faixa habitual da semana do PRÓPRIO valor. O mapa, a frase de leitura e a
   lista leem estas mesmas contas (`posicaoNaFaixa`, a mesma do cartão e da consulta), e o "acima" do
   mapa é o `ufs_acima_faixa` do topo: nenhum número é recalculado em dois lugares. */
function posicoesDasUFs(d) {
  const r = {acima: [], dentro: [], abaixo: [], sem: []};
  UFS.forEach(u => { const p = posicaoNaFaixa(d, u); r[p ? p.posicao : 'sem'].push(u); });
  return r;
}

/* O mapa do detalhe pinta a posição de cada estado na sua faixa (acima, dentro ou abaixo), nas três
   cores da posição; a taxa bruta fica na ficha. Estado sem período fechado ou sem faixa fica em
   sem-dado, e a legenda nomeia a classe — nunca zero. */
function pintarMapaDoDesfecho(d, pos) {
  const svgId = 'mapaDesfecho';
  if (!document.getElementById(svgId) || !BR_GEOJSON) return;
  const cor = MonitorMapas.PALETA.posicao;
  const lugar = {};
  ['acima', 'dentro', 'abaixo'].forEach(k => pos[k].forEach(u => { lugar[u] = k; }));
  const ctx = MonitorMapas.contexto(BR_GEOJSON, 480, 460);
  MonitorMapas.ufs(ctx, svgId, u => cor[lugar[u]] || MonitorMapas.NEUTRA, u => {
    const c = ((d.ultimo || {})[u] || {}).consolidado;
    if (!lugar[u] || !c) return esc(textoSaude('saude.observado.registram.detalhe.sem_periodo'));
    const f = posicaoNaFaixa(d, u);
    return esc(textoSaude('saude.observado.registram.detalhe.ficha', {n: _qtdCartao(c.valor), unidade: d.unidade, taxa: decBR(c.por_100mil)}))
      + '<br><span class="posicao posicao--' + f.posicao + '">' + esc(textoSaude('saude.posicao.' + f.posicao)) + '</span> '
      + esc(textoSaude('saude.observado.registram.detalhe.faixa', {mediana: decBR(f.mediana), p90: decBR(f.p90)}))
      + '<br>' + esc(textoSaude('saude.observado.registram.detalhe.periodo_' + (d.periodo === 'semana' ? 'semana' : 'mes'),
          {datas: periodoEmPalavras(c.periodo, d.periodo), mes: periodoEmPalavras(c.periodo, d.periodo)}));
  });
  MonitorMapas.legenda('legMapaDesfecho', ['acima', 'dentro', 'abaixo'].map(k => ({cor: cor[k],
      rotulo: textoSaude('saude.posicao.' + k) + ' · ' + textoSaude('saude.estadual.lista.contagem', {n: pos[k].length})}))
    .concat([{cor: MonitorMapas.NEUTRA, rotulo: textoSaude('saude.observado.registram.detalhe.sem_periodo') + ' · '
      + textoSaude('saude.estadual.lista.contagem', {n: pos.sem.length})}]));
  /* A lista recolhida é a alternativa acessível do mapa: os estados acima primeiro. */
  const lista = document.getElementById('dlDesfechoUF');
  if (lista) lista.innerHTML = ['acima', 'dentro', 'abaixo', 'sem'].map(k => pos[k].map(u => {
    const c = ((d.ultimo || {})[u] || {}).consolidado;
    return '<dt>' + esc(NOME_UF[u] || u) + '</dt><dd>' + (c ? esc(decBR(c.por_100mil)) + ' ' + esc(d.unidade) + ' por 100 mil habitantes'
      + (k === 'sem' ? '' : ' · <span class="posicao posicao--' + k + '">' + esc(textoSaude('saude.posicao.' + k)) + '</span>')
      : esc(textoSaude('saude.observado.registram.detalhe.sem_periodo'))) + '</dd>';
  }).join('')).join('');
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

/* O ano do canal endêmico: o ano do último valor fechado, mês a mês, sobre a faixa habitual da
   época (mediana a p90 de 2019 a 2025), com o ano anterior em linha fina e os períodos que ainda
   recebem registro tracejados. O eixo é do ano mostrado, não do pico de anos passados. */
function dadosDoAno(d, uf) {
  const serie = (d.por_100mil || {})[uf] || {}, faixas = (d.faixa_habitual || {})[uf] || {};
  const parciais = new Set(d.parcial || []);
  const c = ((((d.ultimo || {})[uf] || {}).consolidado) || {}).periodo || Object.keys(serie).sort().filter(k => !parciais.has(k)).pop() || '';
  const ano = Number(String(c).split('-')[0]) || null;
  const posicoes = Object.keys(faixas).sort();
  const de = (a, p) => a == null ? null : (serie[a + '-' + p] ?? null);
  const fechado = p => parciais.has(ano + '-' + p) ? null : de(ano, p);
  const ultimoFechado = posicoes.filter(p => fechado(p) != null).pop();
  return {ano, posicoes, faixas, parciais,
    faixaAlta: posicoes.map(p => faixas[p].p90 ?? null), faixaBaixa: posicoes.map(p => faixas[p].mediana ?? null),
    atual: posicoes.map(fechado), anterior: posicoes.map(p => de(ano && ano - 1, p)),
    incompleto: posicoes.map(p => (parciais.has(ano + '-' + p) || p === ultimoFechado) ? de(ano, p) : null)};
}

/* O detalhe do cartão escolhido, um por vez: escolher outro troca o conteúdo e a página não cresce. */
function pintarDetalhe(d, uf) {
  const fig = document.getElementById('boxDesfecho'), cv = document.getElementById('cDesfecho');
  if (!fig || !cv || !window.Chart) return;
  /* Sem desfecho escolhido não há o que detalhar: a figura recolhe, e declara a lacuna na própria
     linha de fonte — sem nomear sistema que não foi lido. Moldura vazia e muda é o pior desfecho. */
  if (!d) {
    fig.hidden = true;
    MonitorMapas.credito('boxDesfecho', {fontes: ['os sistemas de registro declarados em cada desfecho'], data: null});
    return;
  }
  fig.hidden = false;
  const semanal = d.periodo === 'semana';
  const A = dadosDoAno(d, uf);
  const C = window.MonitorCatalogo;
  const molde = (chave, vals) => (C && C.texto('saude.observado.registram.detalhe.' + chave, vals)) || '';
  const campo = (id, texto) => { const el = document.getElementById(id); if (el) el.textContent = texto; };
  const territorio = uf === 'BR' ? 'Brasil' : NOME_UF[uf];
  const c = ((((d.ultimo || {})[uf] || {}).consolidado) || {});
  campo('tituloDesfecho', molde('titulo', {desfecho: d.rotulo}));
  const sub = document.getElementById('legendaDesfecho');
  if (sub) sub.textContent = c.periodo ? molde(semanal ? 'subtitulo_semana' : 'subtitulo_mes',
    {territorio: territorio, datas: periodoEmPalavras(c.periodo, d.periodo), mes: periodoEmPalavras(c.periodo, d.periodo)}) : territorio;
  /* A frase de leitura: o país (ou o estado escolhido) e a contagem dos 27, cada posição na sua cor.
     Os pedaços entram por marcadores e são trocados depois de escapados, para o catálogo escrever a frase inteira. */
  const pos = posicoesDasUFs(d);
  const p = posicaoNaFaixa(d, uf);
  const span = (k, texto) => '<span class="posicao posicao--' + k + '">' + esc(texto) + '</span>';
  const parte = k => molde('n_' + k, {k: pos[k].length});
  const frase = esc(molde('frase', {territorio: territorio, posicao: '\u0001p', acima: '\u0001a', dentro: '\u0001d', abaixo: '\u0001b'}))
    .replace('\u0001p', p ? span(p.posicao, textoSaude('saude.posicao.' + p.posicao)) : esc(textoSaude('saude.posicao.sem_faixa')))
    .replace('\u0001a', span('acima', parte('acima'))).replace('\u0001d', span('dentro', parte('dentro')))
    .replace('\u0001b', span('abaixo', parte('abaixo')));
  const leitura = document.getElementById('leituraDesfecho');
  if (leitura) { leitura.innerHTML = frase; leitura.hidden = !A.ano; }
  const ultimoBR = ((d.ultimo || {}).BR || {}).consolidado || {};
  campo('notaDesfecho', molde('legenda', {periodo: periodoCompacto(ultimoBR.periodo, d.periodo),
    parciais: (d.parcial || []).length ? molde('parciais', {n: (d.parcial || []).length}) : molde('parciais_nenhum')}));
  /* Eixo: meses, como manda a régua do site; o tooltip traz o período por extenso. */
  const MES = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro'];
  const rotulos = !A.ano ? [] : semanal ? rotulosDeMes(A.ano, A.posicoes.map(x => A.ano + '-' + x)) : A.posicoes.map(x => MES[Number(x) - 1].slice(0, 3));
  const titulo = it => { const x = A.posicoes[it[0].dataIndex]; return semanal ? semanaEmDatas(A.ano, A.ano + '-' + x, false) : MES[Number(x) - 1] + ' de ' + A.ano; };
  const fam = corDaFaixa(d), ink = MonitorMapas.cor('vazio');
  const linha = (label, data, extra) => Object.assign({type: 'line', label: label, data: data, pointRadius: 0, order: 1}, extra);
  MonitorMapas.padraoGraficos(window.Chart);
  if (__graficoDesfecho.g && typeof __graficoDesfecho.g.destroy === 'function') __graficoDesfecho.g.destroy();
  __graficoDesfecho.g = new Chart(cv, {data: {labels: rotulos, datasets: [
      linha(molde('leg_ano', {ano: String(A.ano)}), A.atual, {borderColor: ink, borderWidth: 2}),
      linha(molde('leg_ano', {ano: String((A.ano || 0) - 1)}), A.anterior, {borderColor: MonitorMapas.COR.muted, borderWidth: 1, order: 2}),
      linha(molde(semanal ? 'leg_incompleto_semana' : 'leg_incompleto_mes'), A.incompleto, {borderColor: ink, borderWidth: 2, borderDash: [4, 3]}),
      /* A faixa é uma FAIXA, não duas linhas: o traço de cima preenche até o de baixo. */
      linha(molde('leg_faixa'), A.faixaAlta, {fill: '+1', borderColor: fam + '66', backgroundColor: fam + '38', borderWidth: 1, order: 3}),
      linha(molde('leg_faixa'), A.faixaBaixa, {borderColor: fam + '66', borderWidth: 1, order: 3})]},
    options: {animation: false, responsive: true, maintainAspectRatio: false,
      plugins: {legend: {display: false}, tooltip: {callbacks: {title: titulo}}},
      scales: {x: {grid: {display: false}, ticks: {autoSkip: false, maxRotation: 0}},
               y: {beginAtZero: true, title: {display: true, text: d.unidade + ' por 100 mil'}}}}});
  MonitorMapas.legenda('legDesfecho', [
    {cor: ink, rotulo: molde('leg_ano', {ano: String(A.ano)})},
    {cor: MonitorMapas.COR.muted, rotulo: molde('leg_ano', {ano: String((A.ano || 0) - 1)})},
    {cor: fam, rotulo: molde('leg_faixa')},
    {cor: ink, rotulo: molde(semanal ? 'leg_incompleto_semana' : 'leg_incompleto_mes')}]);
  pintarMapaDoDesfecho(d, pos);
  /* O gráfico nasce antes de o mapa ocupar a segunda coluna da figura dupla: sem este ajuste, a
     tela do Chart.js guarda a largura da figura inteira e passa por cima do mapa. */
  if (__graficoDesfecho.g && typeof __graficoDesfecho.g.resize === 'function') __graficoDesfecho.g.resize();
  MonitorMapas.credito('boxDesfecho', {fontes: [(d.fonte || {}).sistema], data: d.coletado_em, url: (d.fonte || {}).url});
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
