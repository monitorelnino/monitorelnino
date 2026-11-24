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

// 14/09/2026: chikungunya — mesmos quatro arquivos do painel, com prefixo chik_ (coletar_desfechos_saude.py --doenca chikungunya).
// Nulos enquanto o coletor não rodar: o comparador e o mapa declaram lacuna, nunca preenchem.
const UFS = ["AC","AL","AM","AP","BA","CE","DF","ES","GO","MA","MG","MS","MT","PA","PB","PE","PI","PR","RJ","RN","RO","RR","RS","SC","SE","SP","TO"];
const NOME_UF = {AC:'Acre',AL:'Alagoas',AM:'Amazonas',AP:'Amapá',BA:'Bahia',CE:'Ceará',DF:'Distrito Federal',ES:'Espírito Santo',GO:'Goiás',MA:'Maranhão',MG:'Minas Gerais',MS:'Mato Grosso do Sul',MT:'Mato Grosso',PA:'Pará',PB:'Paraíba',PE:'Pernambuco',PI:'Piauí',PR:'Paraná',RJ:'Rio de Janeiro',RN:'Rio Grande do Norte',RO:'Rondônia',RR:'Roraima',RS:'Rio Grande do Sul',SC:'Santa Catarina',SE:'Sergipe',SP:'São Paulo',TO:'Tocantins'};
const NEUTRA = MonitorMapas.cor('sem-dado');
const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));

async function __load(){
  [BR_GEOJSON, MSAUDE] = await Promise.all(['geo_uf','monitor_saude'].map(f => fetch('data/' + f + '.json').then(r => {
      if(!r.ok) throw new Error('Falha ao carregar data/' + f + '.json'); return r.json(); })));
  if (window.MonitorCatalogo && MonitorCatalogo.pronto) { try { await MonitorCatalogo.pronto; } catch (e) {} }
  tabelaDosPlanos();
  montarDesfechos().catch(_erroSaude("saude:desfechos"));
  montarMortalidade().catch(_erroSaude("saude:mortalidade"));
}

const fonteFigura = MonitorMapas.credito;

/* ===== A situação de cada estado (v0.9, editoria 26/10/2026 18:33 BRT) =====
 * Sem mapa. A lista dos tipos de plano traz as siglas dos estados em círculos; passar o mouse, focar ou tocar
 * no círculo mostra tipo, documento, data, órgão e a fonte oficial (o cartão do mapa, que não some ao
 * levar o mouse até o link); o clique abre a ficha. A tabela fica como alternativa. */
const TIPOS_DE_PLANO = ['NOVO', 'READ', 'VIG', 'ELAB', 'VENC', 'LAC', 'NAO_VERIFICADO'];
const ufsDoMonitor = () => (MSAUDE && MSAUDE.ufs) || {};
const tipoDoEstado = uf => ((ufsDoMonitor()[uf] || {}).instrumento || {}).status || 'NAO_VERIFICADO';
const textoSaude = (id, v) => (window.MonitorCatalogo && MonitorCatalogo.texto(id, v)) || '';

/* ===== Quadro de mortalidade (01/11/2026) =====
 * Lê `data/saude_desfechos/mortalidade_comparada.json` (gerador único: gerar_mortalidade_comparada.py);
 * a página só desenha, não calcula. Campo ausente é a lacuna que o arquivo declara, nunca zero. */
const MORTALIDADE = fetch('data/saude_desfechos/mortalidade_comparada.json').then(r => (r.ok ? r.json() : null)).catch(() => null);
const _int = v => Number(Math.round(v)).toLocaleString('pt-BR');
const _sinal = v => (v > 0 ? '+' : v < 0 ? '\u2212' : '') + _int(Math.abs(v));
const _mesDe = k => periodoEmPalavras(k, 'mes');
const _meses = T => Object.keys(T || {}).filter(k => /^\d{4}-\d{2}$/.test(k)).sort();
const _mt = (id, v) => textoSaude('saude.mortalidade.' + id, v);
function _linhaDeMes(k, x, lo, hi) {
  const pos = v => (hi > lo ? ((v - lo) / (hi - lo)) * 100 : 50);
  const lac = (texto, id) => '<div class="lacuna lacuna--linha">' + esc(texto || _mt('lacuna.' + id)) + '</div>';
  const f = x.faixa_ref || {};
  const proj = x.projecao_cil == null ? lac(x.lacuna_projecao_cil, 'projecao')
    : '<div class="mort-v">' + _int(x.projecao_cil.valor != null ? x.projecao_cil.valor : x.projecao_cil) + '</div>';
  const reg = '<div class="trilho" role="img" aria-label="' + esc(_mt('reg_aria', {reg: _int(x.registrados), min: _int(f.min), max: _int(f.max)})) + '">'
    + '<span class="faixa" style="left:' + pos(f.min) + '%;width:' + (pos(f.max) - pos(f.min)) + '%"></span>'
    + '<span class="pt' + (x.parcial ? ' parcial' : '') + '" style="left:' + pos(x.registrados) + '%"></span></div>'
    + '<div class="mort-v">' + _int(x.registrados) + (x.parcial ? ' · ' + esc(_mt('parcial')) : '') + '</div>'
    + '<div class="mort-s">' + esc(_mt('faixa', {min: _int(f.min), max: _int(f.max)})) + '</div>';
  const e = x.excesso;
  const exc = e ? '<div class="mort-v">' + _sinal(e.valor) + '</div><div class="mort-s">' + esc(_mt('intervalo', {min: _sinal(e.min), max: _sinal(e.max)}))
    + '</div><div class="mort-s">' + esc(_mt('esperado', {n: _int(x.esperado)})) + '</div>' : lac(x.lacuna_excesso, 'excesso');
  const c = x.obitos_x30;
  const x30 = c ? '<div class="mort-v">' + (c.valor === 0 ? 'zero' : _int(c.valor)) + (c.parcial ? ' · ' + esc(_mt('parcial')) : '') + '</div>' : lac(x.lacuna_x30, 'x30');
  return '<div class="mort-l"><div class="mort-mes">' + esc(_mesDe(k)) + '</div>'
    + [['proj', proj], ['reg', reg], ['exc', exc], ['x30', x30]].map(([id, h]) => '<div data-rot="' + esc(_mt('col.' + id + '.titulo')) + '">' + h + '</div>').join('') + '</div>';
}
function pintarMortalidade(D) {
  const T = (D.territorios || {})[document.getElementById('ufMortalidade').value], alvo = document.getElementById('quadroMortalidade');
  const ks = _meses(T);
  if (!ks.length) { alvo.innerHTML = '<div class="lacuna lacuna--linha">' + esc(_mt('sem_arquivo')) + '</div>'; return; }
  const faixas = ks.map(k => T[k].faixa_ref || {}), regs = ks.map(k => T[k].registrados);
  const lo = Math.min.apply(null, faixas.map(f => f.min).concat(regs)), hi = Math.max.apply(null, faixas.map(f => f.max).concat(regs));
  alvo.innerHTML = '<div class="mort-l mort-h"><div>' + esc(_mt('col.mes')) + '</div>'
    + ['proj', 'reg', 'exc', 'x30'].map(id => '<div><b>' + esc(_mt('col.' + id + '.titulo')) + '</b>' + esc(_mt('col.' + id + '.sub')) + '</div>').join('') + '</div>'
    + ks.map(k => _linhaDeMes(k, T[k], lo, hi)).join('');
  const meses = ks.length === 1 ? _mesDe(ks[0]) : _mesDe(ks[0]).replace(/ de \d{4}$/, '') + ' a ' + _mesDe(ks[ks.length - 1]);
  mostrarFrase(document.getElementById('mesesMortalidade'), _mt('fonte', {meses}));
}
async function montarMortalidade() {
  const D = await MORTALIDADE, bloco = document.getElementById('mortalidade');
  if (!bloco || !D || !D.territorios) return;
  const sel = document.getElementById('ufMortalidade');
  sel.innerHTML = '<option value="BR">' + esc(_mt('brasil')) + '</option>' + UFS.map(u => '<option value="' + u + '">' + esc(NOME_UF[u]) + '</option>').join('');
  sel.addEventListener('change', () => pintarMortalidade(D));
  pintarMortalidade(D);
  fonteFigura('boxMortalidade', {fontes: ['fonte_cil', 'fonte_registro', 'fonte_sim'].map(_mt), consultado: D.consultado_em});
  bloco.hidden = false;
}

function cartaoDoEstado(uf, nome) {
  const i = (ufsDoMonitor()[uf] || {}).instrumento || {};
  return '<strong>' + esc(NOME_UF[uf]) + '</strong><br>' + esc(nome(tipoDoEstado(uf)))
    + (i.doc ? '<br>' + esc(i.doc) : '') + (i.data || i.orgao ? '<br>' + esc([i.data, i.orgao].filter(Boolean).join(' · ')) : '')
    + (i.url ? '<br><a href="' + esc(i.url) + '" target="_blank" rel="noopener">' + esc(textoSaude('saude.estadual.ficha.fonte_oficial')) + ' →</a>' : '');
}

function tabelaDosPlanos() {
  const nome = t => textoSaude('saude.estadual.tipo.' + t);
  const cor = t => MonitorMapas.PALETA.status[t] || NEUTRA;
  const instr = uf => (ufsDoMonitor()[uf] || {}).instrumento || {};
  const alvo = document.getElementById('listaTiposPlano'), tip = document.getElementById('mapTooltip');
  alvo.innerHTML = '<h3 class="figura-titulo">' + esc(textoSaude('saude.estadual.lista.titulo')) + '</h3><dl class="faixa-previsto">'
    + TIPOS_DE_PLANO.map(t => UFS.filter(uf => tipoDoEstado(uf) === t)).map((ufs, k) => !ufs.length ? '' :
      '<div><dt><span class="chip-chave" data-tipo="' + TIPOS_DE_PLANO[k] + '">' + esc(nome(TIPOS_DE_PLANO[k])) + '</span></dt><dd class="chips">'
        + ufs.map(uf => '<button type="button" class="chip-risco" data-uf="' + uf + '" aria-label="'
          + esc(textoSaude('saude.estadual.lista.botao', {estado: NOME_UF[uf]})) + '">' + uf + '</button>').join('') + '</dd></div>').join('') + '</dl>';
  alvo.querySelectorAll('[data-tipo]').forEach(e => { e.style.background = cor(e.dataset.tipo); });
  /* O cartão aceita o mouse (classe do componente): some com meio segundo de folga, para dar tempo de chegar ao link. */
  let adeus = 0;
  const mostrar = ev => { const b = ev.target.closest('button[data-uf]'); if (!b) return; clearTimeout(adeus);
    const r = b.getBoundingClientRect(); tip.classList.add('map-tooltip--clicavel');
    MonitorMapas.showTip(cartaoDoEstado(b.dataset.uf, nome), {clientX: r.left, clientY: r.bottom});
    tip.style.left = Math.max(8, Math.min(r.left, window.innerWidth - tip.offsetWidth - 8)) + 'px'; };
  const fechar = () => { MonitorMapas.hideTip(); tip.classList.remove('map-tooltip--clicavel'); };
  const esconder = () => { clearTimeout(adeus); adeus = setTimeout(fechar, 500); };
  ['mouseover', 'focusin'].forEach(e => alvo.addEventListener(e, mostrar));
  ['mouseout', 'focusout'].forEach(e => alvo.addEventListener(e, esconder));
  tip.addEventListener('mouseenter', () => clearTimeout(adeus)); tip.addEventListener('mouseleave', esconder);
  alvo.addEventListener('click', ev => { const b = ev.target.closest('button[data-uf]'); if (b) { fechar(); abrirDetalheSaude(b.dataset.uf); } });
  const escada = ((MSAUDE.metodo || {}).escada) || {};
  mostrarFrase(document.getElementById('escadaPlano'), textoSaude('saude.estadual.escada', escada));
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
          // 17/11/2026: as contagens do estatuto somam o denominador, como os grupos do quadro dos tipos de
          // plano; antes a linha somava 25 de 27 e contava plano vencido como plano localizado.
          com_plano: n(res.ufs_com_plano_localizado), em_elaboracao: res.ufs_em_elaboracao || 0, denominador: n(res.denominador || 27),
          vencido: res.ufs_plano_vencido || 0, nao_localizado: ((res.por_estatuto || {}).plano_nao_localizado) || 0,
          sem_numero: res.nao_verificadas, corte: (MS || {}).corte || ''}));
    }
    if (rp.indice != null) {
      el('respNumSaude').textContent = umaCasa(rp.indice); el('respNumSaude').dataset.contar = rp.indice;
      fixa('respFillSaude', rp.indice, 'decretos de emergência em saúde');
    }
    if (window.MonitorCatalogo) MonitorCatalogo.pronto.then(() => {
      // 15/11/2026 (editoria): ato em vigor localizado tem valor mesmo com leitura parcial; a linha diz o que falta ler.
      const sem = Object.keys(rp.lacunas_estaduais || {}).sort(), total = n(res.denominador || 27);
      const quando = (MS || {}).gerado_em || (MS || {}).corte || '', ufs = (rp.ufs || []).length === 27 ? [] : (rp.ufs || []);
      const parcial = rp.situacao === 'parcial' && sem.length;
      if (parcial) escreve('linhaRespostaSaude', 'saude.topo.resposta.linha_parcial',
        {quando, lidas: total - sem.length, total, siglas: sem.join(', '), n: (rp.eventos || []).filter(e => e.em_vigor).length,
         onde: ufs.length ? ' (' + ufs.join(', ') + ')' : ''});
      if (rp.indice == null) return;   // sem índice: fica a reserva do HTML ("sem coleta até o corte") ou a linha de leitura parcial
      // 10/11/2026: mesma forma do cartão de decretos da página inicial — o número grande é % da população
      // e a pílula só conta os decretos (o percentual repetia o número grande).
      el('respDenSaude').textContent = T('saude.topo.resposta.unidade');
      el('respBadgeSaude').innerHTML = '<span class="gfaixa-pill">' + esc(T('saude.topo.resposta.pilula', {n: rp.emergencias || 0})) + '</span>';
      if (!parcial) escreve('linhaRespostaSaude', 'saude.topo.resposta.linha', {quando});
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
  /* O plano municipal de arboviroses julgado pela régua da saúde (julgar_saude_municipal.py, peso zero).
     Sem plano promovido, a classe de ausência da coleta: citado sem confirmação, não localizado ou não verificado. */
  const arboMun = () => arboMun.p = arboMun.p || json('data/planos_arboviroses_juiz.json');
  const cartaoPlanoSaudeMun = (A, cod, uf) => {
    const x = ((A || {}).municipios || {})[cod], aus = ((A || {}).sem_plano_promovido || {})[cod] || 'nao_verificado';
    const valor = x ? esc(textoSaude('saude.estadual.tipo.' + x.status)) + (x.url ? ' · <a href="' + esc(x.url) + '" target="_blank" rel="noopener">' + esc(TC('plano.abrir')) + '</a>' : '')
      : esc(TC('plano_arbo.' + aus, {corte: (A || {}).atualizado_em ? MonitorMapas.dataBR(A.atualizado_em) : ''}));
    return cartao('musgo', TC('rotulo.plano_arbo_municipio'), valor, x ? esc(TC('plano_arbo.nota', {documento: x.doc || '', data: x.data || ''})) : '',
      {href: 'metodologia.html', pagina: textoSaude('consulta.cartao.pagina.metodologia')});
  };
  const cartao = (acento, rotulo, valor, nota, ver, estado) => ConsultaMunicipio.cartao({acento, rotulo, valor, nota, ver, estado});
  const verObservado = () => ({href: '#observado', pagina: textoSaude('saude.observado.titulo_da_secao')});
  const verMonitor = () => ({href: 'monitor-de-riscos.html#boxTemperatura', pagina: textoSaude('consulta.cartao.pagina.monitor_de_riscos')});
  /* O plano do município, com o vocabulário da inicial: o documento e a data com link, ou a frase de
     "não localizamos até a data de corte"; a leitura da saúde no plano é a segunda linha descritiva. */
  const cartaoPlanoDoMunicipio = (sp, pl, uf, meta) => {
    const achou = sp.estado === 'encontrado' || sp.estado === 'estadual';
    if (sp.estado === 'sem_contar')
      return cartao('musgo', TC('rotulo.plano_municipio'), esc(TC('plano.sem_contar.' + sp.sem_contar.motivo, {fonte: sp.sem_contar.fonte, desde: sp.sem_contar.desde}))
        + (sp.sem_contar.url ? ' · <a href="' + esc(sp.sem_contar.url) + '" target="_blank" rel="noopener">' + esc(TC('plano.abrir')) + '</a>' : ''),
        '', {href: 'index.html#' + uf, pagina: textoSaude('consulta.cartao.pagina.inicial')});
    const valor = sp.estado === 'nao_verificado' ? TC('plano.nao_verificado')
      : achou ? TC(sp.data ? 'plano.com_plano_data' : 'plano.com_plano', {documento: sp.documento || sp.fonte || '', data: sp.data || ''}) : TC('plano.sem_plano', {corte: (meta || {}).corte || ''});
    const camada = achou && pl ? TC(pl.pagina_citada ? 'plano.saude_no_plano' : 'plano.saude_no_plano_sem_pagina', {pagina: pl.pagina_citada}) : '';
    return cartao('musgo', TC('rotulo.plano_municipio'), esc(valor) + (achou && sp.url ? ' · <a href="' + esc(sp.url) + '" target="_blank" rel="noopener">' + esc(TC('plano.abrir')) + '</a>' : ''),
      [achou && sp.plano_da_saude && esc(TC('plano.da_saude', {fonte: sp.plano_da_saude.fonte})), camada && esc(camada), achou && sp.fonte && esc(sp.fonte)].filter(Boolean).join(' · '),
      {href: 'index.html#' + uf, pagina: textoSaude('consulta.cartao.pagina.inicial')});
  };
  /* O estado, nunca o município: a fonte não abre óbitos por município, e o cartão diz isso. */
  const cartaoMortalidade = (M, uf) => {
    const T = M && M.territorios && M.territorios[uf], ks = _meses(T).reverse(), k = ks.find(q => T[q].excesso) || ks[0];
    const x = k && T[k];
    return cartao('neutro', TC('rotulo.mortalidade'), !x ? esc(_mt('sem_arquivo'))
      : esc(x.excesso ? TC('mortalidade.valor', {mes: _mesDe(k), excesso: _sinal(x.excesso.valor)}) : TC('mortalidade.valor_registrados', {mes: _mesDe(k), n: _int(x.registrados)})), '',
      {href: '#mortalidade', pagina: textoSaude('saude.mortalidade.titulo_da_secao')}, NOME_UF[uf]);
  };
  const cartaoArbo = (rotulo, x, d, semanaSemDado) => x
    ? cartao('neutro', rotulo, esc(TC('arbo.nivel_' + x.nivel) || TC('arbo.nivel_outro', {n: x.nivel})), esc(TC('arbo.nota', {semana: semana(x.semana)})), verObservado())
    : cartao('neutro', rotulo, esc(TC('arbo.nao_lido', {semana: semanaSemDado})), esc(TC('arbo.nota_nao_lido', {data: (d || {}).gerado_em || ''})), verObservado());
  fetch('data/geo_uf.json').then(r => r.json()).then(GEO => ConsultaMunicipio.montar({uf: 'consultaSaudeUF', municipio: 'consultaSaudeMun', lista: 'consultaSaudeLista', cartao: 'consultaSaudeCard',
    estados: Object.fromEntries(GEO.features.map(f => [f.properties.sigla, f.properties.name])), semLista: TC('sem_lista'),
    municipios: uf => (porUF[uf] = porUF[uf] || Promise.all([json('data/saude_municipio/' + uf + '.json'), extra, cartas(), MORTALIDADE, arboMun()]))
      .then(([D, [S, meta], CARD, M, A]) => { porUF[uf].dados = {D, S, meta, CARD, M, A}; return D && Object.values(D.municipios).map(x => x.nome); }),
    mostrar: (uf, nome, card) => {
      const {D, S, meta, CARD, M, A} = porUF[uf].dados, o = D.origens || {}, [cod, m] = Object.entries(D.municipios).find(([, x]) => x.nome === nome);
      const sp = ConsultaMunicipio.situacaoDoPlano(((CARD || {}).municipios || {})[cod]);
      const sinal = (m.dengue || m.chikungunya || {}).semana, quando = semana(sinal);
      const e = ufsDoMonitor()[uf] || {}, pl = m.saude_no_plano, calor = m.calor && m.calor !== 'Normal';
      const srag = S && S.ultimo && S.ultimo[uf] && S.ultimo[uf].consolidado, pos = srag && posicaoNaFaixa(S, uf);
      card.innerHTML = '<h4>' + esc(nome) + ' · ' + esc(uf) + '</h4><div class="grade-figuras grade-figuras--3">'
        + cartaoArbo(TC('rotulo.dengue'), m.dengue, o.dengue, quando) + cartaoArbo(TC('rotulo.chikungunya'), m.chikungunya, o.chikungunya, quando)
        + cartao('argila', TC('rotulo.calor'), esc(m.calor == null ? TC('calor.sem_coleta') : calor ? TC('calor.com_excesso', {classe: String(m.calor).toLowerCase()}) : TC('calor.sem_excesso')),
            esc(TC('calor.nota', {data: MonitorMapas.dataBR((o.calor || {}).data) || ''})), verMonitor())
        + cartao('neutro', TC('rotulo.srag'), srag ? esc(TC('srag.valor', {n: srag.valor, semana: semana(srag.periodo)})) + (pos ? ' · <span class="posicao posicao--' + pos.posicao + '">' + esc(textoSaude('saude.posicao.' + pos.posicao)) + '</span>' : '') : esc(TC('srag.sem_coleta')),
            esc(TC('srag.nota', {data: (S && MonitorMapas.dataBR(S.coletado_em)) || ''})), verObservado(), NOME_UF[uf])
        + cartao('musgo', TC('rotulo.plano_estado'), esc(textoSaude('saude.estadual.tipo.' + tipoDoEstado(uf))),
            esc(TC('plano_estado.nota', {data: MSAUDE.corte || ''})), {href: '#estadual', ficha: uf, pagina: textoSaude('saude.estadual.titulo_da_secao')}, NOME_UF[uf])
        + cartaoPlanoDoMunicipio(sp, pl, uf, meta) + cartaoPlanoSaudeMun(A, cod, uf) + cartaoMortalidade(M, uf) + '</div>';
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
function serieEmSvg(valores, faixas, rotulo, estado, corFaixa, marcas) {
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
    /* 17/11/2026 (mapa que anda no tempo): o período escolhido é um traço pontilhado e cada período
       acima da faixa, um traço curto em argila — traço, não ponto, pela mesma razão do último. */
    + (marcas && marcas.cursor != null ? '<line x1="' + x(marcas.cursor) + '" x2="' + x(marcas.cursor) + '" y1="0" y2="' + A
       + '" stroke="' + MonitorMapas.cor('vazio') + '" stroke-width="1" stroke-dasharray="2 2"></line>' : '')
    + (marcas && marcas.acima ? marcas.acima.map((a, i) => !a ? '' : '<line x1="' + x(i) + '" x2="' + x(i) + '" y1="' + (y(valores[i]) - 4)
       + '" y2="' + (y(valores[i]) + 4) + '" stroke="' + FAIXA_COR.acima + '" stroke-width="2"></line>').join('') : '')
    + '</svg>';
}

/* Os períodos do território no ciclo, na ordem do calendário, SEM os que o arquivo declara parciais
   (ainda recebem registro; desenhá-los faria a linha cair no fim). 17/11/2026 (editoria, 16/11: "todo
   dado e gráfico de saúde começa no marco zero do ciclo"): eram as últimas 52 semanas ou 24 meses. */
function recorteRecente(d, uf) {
  const parciais = new Set(d.parcial || []);
  const serie = (d.por_100mil || {})[uf] || {};
  return Object.keys(serie).sort().filter(ch => ch >= inicioDoCiclo(d) && !parciais.has(ch));
}

/* A posição do último valor consolidado do território na faixa habitual da SEMANA DO PRÓPRIO VALOR
   (comparar com a faixa de outra semana é o erro a impedir). Uma função para o cartão, a consulta
   do município e, adiante, o topo e o detalhe. A comparação é nos MESMOS números que o leitor lê:
   a precisão do rótulo varia com o tamanho do valor, e só `decBR` decide por ela. */
function posicaoNaFaixa(d, uf) {
  const c = ((d.ultimo || {})[uf] || {}).consolidado;
  return c ? posicaoNoPeriodo(d, uf, c.periodo, c.por_100mil) : null;
}
/* A mesma conta para qualquer período da série: o mapa que anda no tempo e as linhas por estado. */
function posicaoNoPeriodo(d, uf, periodo, valor) {
  const v0 = valor != null ? valor : (((d.por_100mil || {})[uf]) || {})[periodo];
  const f = ((d.faixa_habitual || {})[uf] || {})[String(periodo).split('-')[1]];
  if (v0 == null || !f || f.p90 == null) return null;
  const uma = x => Number(String(decBR(x)).replace(/\./g, '').replace(',', '.'));
  const v = uma(v0);
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
        d.rotulo + ', desde 29 de junho, sobre a faixa habitual para a época', dentro, corDaFaixa(d))
    + '<p class="cartao-numero-fonte">' + rodape + '</p></div>';
}

function pintarDesfechos() {
  const grade = document.getElementById('gradeDesfechos');
  const seletor = document.getElementById('ufDesfechos');
  if (!grade || !DESFECHOS_LIDOS.length) return;
  const uf = (seletor && seletor.value) || 'BR';
  const comDetalhe = DESFECHOS_LIDOS.filter(EM_EVIDENCIA);
  if (!comDetalhe.some(d => d.desfecho === DESFECHO_ESCOLHIDO)) DESFECHO_ESCOLHIDO = (comDetalhe[0] || {}).desfecho || null;
  grade.innerHTML = DESFECHOS_LIDOS.map(d => cartaoDesfecho(d, uf)).join('');
  pintarDetalhe(comDetalhe.find(d => d.desfecho === DESFECHO_ESCOLHIDO));
}

/* Um ouvinte na grade, não um por cartão: a grade se repinta inteira a cada troca de território. */
function escolherDesfecho(ev) {
  const alvo = ev.target.closest('[data-desfecho]');
  if (!alvo || (ev.type === 'keydown' && ev.key !== 'Enter' && ev.key !== ' ')) return;
  if (ev.type === 'keydown') ev.preventDefault();
  DESFECHO_ESCOLHIDO = alvo.getAttribute('data-desfecho');
  pintarDesfechos();
}

/* 17/11/2026 (editoria, 16/11: "o mapa dos municípios e os estados ao lado"): o detalhe anda no tempo,
   do marco zero do ciclo (Boletim nº 1, 29/06/2026) ao último período fechado. O mapa mostra a posição
   de cada lugar na faixa habitual do período escolhido — os municípios, onde a fonte os traz; os
   estados, onde não — e ao lado cada estado tem a sua linha, com o mesmo período marcado. Nenhuma conta
   nova: a posição é `posicaoNoPeriodo`, a mesma do cartão; a dos municípios vem pronta do gerador. */
const INICIO_DO_CICLO = '2026-06-29';
const TEMPO = {d: null, idx: 0, regua: 'faixa', relogio: 0, mun: {}};

/* Os períodos do ciclo que a série traz fechados: a semana que contém 29/06 em diante, ou de julho em diante. */
function periodosDoCiclo(d) {
  const parciais = new Set(d.parcial || []), chaves = new Set();
  Object.values(d.por_100mil || {}).forEach(s => Object.keys(s || {}).forEach(k => chaves.add(k)));
  const ultimos = Object.values(d.ultimo || {}).map(u => ((u || {}).consolidado || {}).periodo).filter(Boolean).sort();
  const fim = ultimos[ultimos.length - 1];
  return [...chaves].filter(k => k >= inicioDoCiclo(d) && (!fim || k <= fim) && !parciais.has(k)).sort();
}

/* O primeiro período do ciclo na série: a semana que contém 29/06/2026, ou julho. */
const inicioDoCiclo = d => (d.periodo === 'semana'
  ? '2026-' + String(MonitorSemana.semanaDaData(INICIO_DO_CICLO)).padStart(2, '0') : '2026-07');

const domingoDoPeriodo = per => { const r = MonitorSemana.semanaParaDatas(Number(per.split('-')[0]), Number(per.split('-')[1]));
  return r ? r.inicio.toISOString().slice(0, 10) : null; };

async function municipiosNoTempo(d) {
  if (!(d.desfecho in TEMPO.mun)) TEMPO.mun[d.desfecho] = await fetch('data/saude_municipio/tempo_' + d.desfecho + '.json')
    .then(r => (r.ok ? r.json() : null)).catch(() => null);
  return TEMPO.mun[d.desfecho];
}

const NIVEL_COR = () => ({1: MonitorMapas.COR['sem-dado'], 2: MonitorMapas.COR.areia, 3: MonitorMapas.COR.ambar, 4: MonitorMapas.COR.argila});

function pintarTempo() {
  const d = TEMPO.d, pers = d ? periodosDoCiclo(d) : [];
  if (!d || !BR_GEOJSON) return;
  const controles = ['periodoDesfecho', 'tocarDesfecho'].map(id => document.getElementById(id));
  controles.forEach(el => { el.disabled = !pers.length; });
  if (!pers.length) {
    /* Série sem período fechado depois do marco zero: lacuna declarada, com o último período que existe. */
    const ult = ((d.ultimo || {}).BR || {}).consolidado || {};
    d3.select('#mapaDesfecho').selectAll('g.municipios-tempo').remove();
    MonitorMapas.ufs(MonitorMapas.contexto(BR_GEOJSON, 480, 460), 'mapaDesfecho', () => MonitorMapas.NEUTRA,
      () => esc(textoSaude('saude.observado.registram.detalhe.sem_periodo')));
    MonitorMapas.legenda('legMapaDesfecho', []);
    document.getElementById('reguaDesfecho').hidden = true;
    document.getElementById('rotuloPeriodoDesfecho').textContent = '';
    document.getElementById('linhasDesfecho').innerHTML = '';
    document.getElementById('dlDesfechoUF').innerHTML = '';
    mostrarFrase(document.getElementById('leituraDesfecho'), textoSaude('saude.observado.registram.detalhe.sem_ciclo',
      {periodo: ult.periodo ? periodoEmPalavras(ult.periodo, d.periodo) : textoSaude('saude.observado.registram.detalhe.sem_periodo')}));
    return;
  }
  TEMPO.idx = Math.max(0, Math.min(TEMPO.idx, pers.length - 1));
  const per = pers[TEMPO.idx], semanal = d.periodo === 'semana', cor = MonitorMapas.PALETA.posicao;
  const quando = periodoEmPalavras(per, d.periodo);
  const T = (id, v) => textoSaude('saude.observado.registram.detalhe.' + id, v);
  const deslizador = document.getElementById('periodoDesfecho');
  deslizador.max = String(pers.length - 1); deslizador.value = String(TEMPO.idx);
  deslizador.setAttribute('aria-valuetext', quando);
  document.getElementById('rotuloPeriodoDesfecho').textContent = semanal ? T('na_semana', {datas: quando}) : quando;
  const pos = {acima: [], dentro: [], abaixo: [], sem: []};
  UFS.forEach(u => { const p = posicaoNoPeriodo(d, u, per); pos[p ? p.posicao : 'sem'].push(u); });
  const ctx = MonitorMapas.contexto(BR_GEOJSON, 480, 460);
  const M = TEMPO.mun[d.desfecho], k = !M ? -1 : semanal ? (M.semanas || []).indexOf(domingoDoPeriodo(per)) : (M.meses || []).indexOf(per);
  const regua = document.getElementById('reguaDesfecho');
  // A régua do nível só existe onde a fonte publica nível (InfoDengue); SRAG não tem.
  regua.hidden = !(M && k >= 0 && M.municipios.some(m => m.nv.some(v => v != null)));
  if (regua.hidden) TEMPO.regua = 'faixa';
  regua.querySelectorAll('[data-regua]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.regua === TEMPO.regua)));
  const ficha = u => { const p = posicaoNoPeriodo(d, u, per);
    return p ? '<span class="posicao posicao--' + p.posicao + '">' + esc(textoSaude('saude.posicao.' + p.posicao)) + '</span> '
      + esc(T('faixa', {mediana: decBR(p.mediana), p90: decBR(p.p90)})) : esc(T('sem_periodo')); };
  let leitura;
  if (M && k >= 0) {
    /* Municípios: os estados ficam neutros por baixo, para o ponto ser a única cor do mapa. */
    MonitorMapas.ufs(ctx, 'mapaDesfecho', () => MonitorMapas.COR['osso-claro'], ficha);
    const nivel = TEMPO.regua === 'nivel', NC = NIVEL_COR(), P = {a: 'acima', d: 'dentro', b: 'abaixo'};
    const itens = M.municipios.map(m => ({lat: m.lat, lon: m.lon, nome: m.nome, uf: m.uf, p: m.p[k], nv: m.nv[k]}))
      .sort((a, b) => (nivel ? (a.nv || 0) - (b.nv || 0) : (a.p === 'a') - (b.p === 'a')));
    MonitorMapas.pontos(ctx, 'mapaDesfecho', itens, {classe: 'municipios-tempo', opacidade: 1,
      r: x => (nivel ? (x.nv >= 3 ? 5 : 2.5) : (x.p === 'a' ? 5 : 2.5)),
      cor: x => (nivel ? (NC[x.nv] || MonitorMapas.NEUTRA) : (cor[P[x.p]] || MonitorMapas.NEUTRA)),
      rotulo: x => '<strong>' + esc(x.nome) + ' (' + x.uf + ')</strong><br>' + esc(nivel
        ? (x.nv ? T('nivel', {n: x.nv}) : T('sem_periodo')) : (x.p ? textoSaude('saude.posicao.' + P[x.p]) : T('sem_periodo')))});
    const n = c => M.municipios.filter(m => m.p[k] === c).length;
    MonitorMapas.legenda('legMapaDesfecho', nivel
      ? [4, 3, 2, 1].map(v => ({cor: NC[v], rotulo: T('nivel', {n: v})}))
      : [['a', 'acima'], ['d', 'dentro'], ['b', 'abaixo']].map(([c, nome]) => ({cor: cor[nome],
          rotulo: textoSaude('saude.posicao.' + nome) + ' · ' + T('contagem_mun', {n: n(c)})})));
    leitura = T(semanal ? 'frase_municipios' : 'frase_municipios_mes', {quando: quando, acima: n('a'), total: M.municipios.length, estados: pos.acima.length});
  } else {
    d3.select('#mapaDesfecho').selectAll('g.municipios-tempo').remove();
    const lugar = {}; ['acima', 'dentro', 'abaixo'].forEach(c => pos[c].forEach(u => { lugar[u] = c; }));
    MonitorMapas.ufs(ctx, 'mapaDesfecho', u => cor[lugar[u]] || MonitorMapas.NEUTRA, ficha);
    MonitorMapas.legenda('legMapaDesfecho', ['acima', 'dentro', 'abaixo'].map(c => ({cor: cor[c],
      rotulo: textoSaude('saude.posicao.' + c) + ' · ' + T('contagem', {n: pos[c].length})}))
      .concat([{cor: MonitorMapas.NEUTRA, rotulo: T('sem_periodo') + ' · ' + T('contagem', {n: pos.sem.length})}]));
    leitura = T(semanal ? 'frase_estados_semana' : 'frase_estados_mes', {quando: quando, acima: pos.acima.length});
  }
  mostrarFrase(document.getElementById('leituraDesfecho'), leitura);
  /* As linhas: Brasil e os 27 estados em ordem alfabética, cada um na sua escala, o período escolhido marcado. */
  document.getElementById('linhasDesfecho').innerHTML = ['BR'].concat(UFS.slice().sort()).map(u => {
    const serie = (d.por_100mil || {})[u] || {}, faixas = (d.faixa_habitual || {})[u] || {};
    const p = posicaoNoPeriodo(d, u, per), nome = u === 'BR' ? 'Brasil' : NOME_UF[u];
    return '<div class="linha-estado' + (p && p.posicao === 'acima' ? ' linha-estado--acima' : '') + '"><span class="linha-estado-nome">'
      + esc(u === 'BR' ? 'Brasil' : u) + '</span>'
      + serieEmSvg(pers.map(x => serie[x] ?? null), pers.map(x => faixas[String(x).split('-')[1]] || null),
        T('linha_aria', {territorio: nome, quando: quando}), p && p.posicao, corDaFaixa(d),
        {cursor: TEMPO.idx, acima: pers.map(x => (posicaoNoPeriodo(d, u, x) || {}).posicao === 'acima')}) + '</div>';
  }).join('');
  const lista = document.getElementById('dlDesfechoUF');
  if (lista) lista.innerHTML = ['acima', 'dentro', 'abaixo', 'sem'].map(c => pos[c].map(u => {
    const v = ((d.por_100mil || {})[u] || {})[per];
    return '<dt>' + esc(NOME_UF[u] || u) + '</dt><dd>' + (v != null ? esc(decBR(v)) + ' ' + esc(d.unidade) + ' por 100 mil habitantes'
      + (c === 'sem' ? '' : ' · <span class="posicao posicao--' + c + '">' + esc(textoSaude('saude.posicao.' + c)) + '</span>')
      : esc(T('sem_periodo'))) + '</dd>';
  }).join('')).join('');
}

function tocarTempo() {
  const b = document.getElementById('tocarDesfecho'), pers = TEMPO.d ? periodosDoCiclo(TEMPO.d) : [];
  clearInterval(TEMPO.relogio);
  if (b.getAttribute('aria-pressed') === 'true') { b.setAttribute('aria-pressed', 'false'); return; }
  b.setAttribute('aria-pressed', 'true'); TEMPO.idx = 0; pintarTempo();
  TEMPO.relogio = setInterval(() => {
    if (TEMPO.idx >= pers.length - 1) { clearInterval(TEMPO.relogio); b.setAttribute('aria-pressed', 'false'); return; }
    TEMPO.idx++; pintarTempo();
  }, 900);
}

function ligarControlesDoTempo() {
  const fig = document.getElementById('boxDesfecho');
  if (!fig || fig.dataset.ligado) return;
  fig.dataset.ligado = '1';
  document.getElementById('periodoDesfecho').addEventListener('input', ev => { TEMPO.idx = Number(ev.target.value); pintarTempo(); });
  document.getElementById('tocarDesfecho').addEventListener('click', tocarTempo);
  document.getElementById('reguaDesfecho').addEventListener('click', ev => {
    const b = ev.target.closest('[data-regua]'); if (!b) return; TEMPO.regua = b.dataset.regua; pintarTempo(); });
}

/* O detalhe do cartão escolhido, um por vez: escolher outro troca o conteúdo e a página não cresce. */
async function pintarDetalhe(d) {
  const fig = document.getElementById('boxDesfecho');
  if (!fig) return;
  /* Sem desfecho escolhido não há o que detalhar: a figura recolhe, e declara a lacuna na própria
     linha de fonte — sem nomear sistema que não foi lido. Moldura vazia e muda é o pior desfecho. */
  if (!d) {
    fig.hidden = true;
    MonitorMapas.credito('boxDesfecho', {fontes: ['os sistemas de registro declarados em cada desfecho'], data: null});
    return;
  }
  fig.hidden = false;
  ligarControlesDoTempo();
  const T = (id, v) => textoSaude('saude.observado.registram.detalhe.' + id, v);
  const mudou = !TEMPO.d || TEMPO.d.desfecho !== d.desfecho;
  TEMPO.d = d;
  const M = await municipiosNoTempo(d);
  if (mudou) {
    clearInterval(TEMPO.relogio); document.getElementById('tocarDesfecho').setAttribute('aria-pressed', 'false');
    TEMPO.idx = periodosDoCiclo(d).length - 1; TEMPO.regua = 'faixa';
  }
  document.getElementById('tituloDesfecho').textContent = T(M ? 'titulo_municipios' : 'titulo', {desfecho: d.rotulo});
  document.getElementById('legendaDesfecho').textContent = T(M ? (d.periodo === 'semana' ? 'subtitulo_municipios' : 'subtitulo_municipios_mes') : 'subtitulo_estados', {n: M ? M.municipios.length : 0});
  const ultimoBR = ((d.ultimo || {}).BR || {}).consolidado || {};
  document.getElementById('notaDesfecho').textContent = T('legenda', {periodo: periodoCompacto(ultimoBR.periodo, d.periodo),
    parciais: (d.parcial || []).length ? T('parciais', {n: (d.parcial || []).length}) : T('parciais_nenhum')});
  pintarTempo();
  MonitorMapas.credito('boxDesfecho', {fontes: [(d.fonte || {}).sistema].concat(M ? [M.fonte] : []), data: d.coletado_em, url: (d.fonte || {}).url});
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
