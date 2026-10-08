// ===== index.html · bloco 1 (extraído em 06/09/2026, CSP sem unsafe-inline) =====
(function(){
  function banner(msg){
    if(document.getElementById('errBanner')) return;
    document.body.insertAdjacentHTML('afterbegin',
      '<div id="errBanner" class="erro-carga">'+msg+'</div>');
  }
  window.addEventListener('error', function(e){
    banner('Erro ao renderizar: ' + (e.message||'desconhecido') + '. Recarregue a página; se persistir, verifique a conexão.');
  });
  window.addEventListener('DOMContentLoaded', function(){
    if (typeof window.jspdf === 'undefined'){
      banner('A biblioteca de geração de PDF (jsPDF) não carregou do CDN. É preciso conexão com a internet para baixar relatórios em PDF — o resto da página funciona normalmente.');
    }
  });
})();

// ===== index.html · bloco 2 (extraído em 06/09/2026, CSP sem unsafe-inline) =====
let VMUN, RESP, RESP_SERIE, RESP_MUN;
// 15/09/2026 (decisão editorial): a RESPOSTA passa a ser um ÍNDICE 0–100 ponderado por população — a parcela da
// população (Censo 2022) que vive em município sob decreto de emergência no ciclo (gerar_resposta.py: campo
// `indice`, = 100 × fracao_populacao). Mesma arte do medidor de antecipação; nunca somado a ele (C17).
const indiceResposta = r => r ? (typeof r.indice === 'number' ? r.indice : +(100 * (r.fracao_populacao || 0)).toFixed(1)) : null;
function respostaTile(uf){
  const r = RESP && RESP.uf && RESP.uf[uf]; if (!r) return '';
  const ir = indiceResposta(r);
  return `<div class="tile-bar tile-bar--resposta" title="Resposta ${String(ir).replace('.', ',')} / 100 · ${r.n_municipios} de ${r.total_municipios} municípios sob decreto"><div class="tile-fill tile-fill--resposta" data-alvo="${ir}" style="--galvo:${Math.max(ir, 0.1)};"></div></div>`;
}
// §5: campos 3–5 da face do cartão — nível de verificação da UF, instrumento estadual, capital (uma linha cada)
function faceTile(uf){
  const d = (DATA.ufs || []).find(u => u.uf === uf) || {};
  const niv = (typeof VRESUMO !== 'undefined' && VRESUMO && VRESUMO.por_uf && VRESUMO.por_uf[uf]) || {};
  const tot = Object.values(niv).reduce((a, b) => a + b, 0);
  const acima = (niv.estadual || 0) + (niv.municipal_completo || 0) + (niv.municipal_parcial || 0);
  const ST = {NOVO:'novo', READ:'readaptado', VIG:'vigente-recorrente', ELAB:'em elaboração', LAC:'não localizado'};
  return `<div class="tile-face">
    <span>diários: ${((VRESUMO && VRESUMO.varredura_diarios && VRESUMO.varredura_diarios.por_uf) || {})[uf] || 0} de ${tot}</span>
    <span>${esc(ST[d.status] || d.status)}${d.data && d.data !== 'Recorrente' ? ' · ' + esc(d.data) : ''}</span>
    <span>${d.capital && d.capital.nome ? esc(d.capital.nome) : 'capital —'}</span></div>`;
  // 08/10/2026 (A3-11): o ladrilho mostra só o NOME da capital. Ele pinta antes de o banco
  // chegar, e qualquer rótulo aqui seria ou o texto à mão que saiu, ou um estado lido de uma
  // tabela que ainda não existe. O estado da capital aparece na ficha do estado, que lê o banco.
}
function barraResposta(uf){
  const r = RESP && RESP.uf && RESP.uf[uf]; if (!r) return '';
  const ir = indiceResposta(r), rec = r.tons.reconhecido, dec = r.tons.decretado_sem_reconhecimento, n = r.n_municipios;
  return `<div class="field"><div class="k">Resposta · o índice</div><div class="v">
    ${typeof window.__miniGauge === 'function' ? window.__miniGauge(ir, 'Resposta · população sob decreto', 'resposta') : ''}
    <strong>${n}</strong> de ${r.total_municipios} municípios · <strong>${Math.round(100 * r.fracao_populacao)}%</strong> da população${r.primeiro_decreto ? ' · primeiro decreto municipal em ' + r.primeiro_decreto : ''}<br>
    <span class="fv u-muted">${rec} reconhecido(s) pela União · ${dec} decretado(s) sem reconhecimento · evento observado: em classificação</span></div></div>`;
}
// AUD-02 revisto (07/10/2026): o escape acontece UMA VEZ, na saida. Escapar na carga e de novo
// na saida dava "Olho d&amp;#39;Agua das Flores" no cartao, e fazia o nome do banco nao casar com o
// da lista de referencia, que nao e escapada.
const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let BR_GEOJSON, PCT_POR_UF, MAP_POINTS, TABELA_MUNICIPIOS, MARE, DATA, TRANSFERENCIAS, MUN_REF, META, POP_CENSO, RECURSOS, FIN, CONSIST, ATOS_RESPOSTA, VRESUMO, MUN_COD = {}, POP_UF = {}, MUN_LATLON = {};
function nivelVerificacao(uf, nome){
  // v2.2.4 (§2.2): padrão é "não verificado"; níveis acima vêm do resumo derivado.
  const cod = MUN_COD[uf + '|' + nome];
  if (!cod || !VRESUMO || !VRESUMO.niveis_acima_do_padrao) return 'nao_verificado';
  return VRESUMO.niveis_acima_do_padrao[String(cod)] || 'nao_verificado';
}
const NIVEL_ROTULO = { nao_verificado: 'ainda não verificado individualmente',
  nacional: 'verificado em fontes nacionais', estadual: 'verificado em fontes nacionais e estaduais',
  municipal_completo: 'verificação completa' };
function renderContadorResposta(){
  const N = RESP && RESP.nacional; const box = document.getElementById('contadorResposta'); if (!box) return;
  const el = id => document.getElementById(id);
  if (!N) { MonitorMapas.credito('respFonte', {fontes: 'MARÉ', data: null}); return; }
  const fm = 100 * N.fracao_municipios, ir = indiceResposta(N);
  el('respNum').textContent = ir.toFixed(1).replace('.', ',');
  el('respNum').setAttribute('data-contar', ir);
  el('respDen').textContent = '/ 100';
  el('respBadge').innerHTML = '<span class="gfaixa-pill">' + esc(N.n_municipios.toLocaleString('pt-BR')) + ' municípios · ' + esc(fm.toFixed(1).replace('.', ',')) + '% dos municípios</span>';
  const fill = el('respFill'); fill.dataset.alvo = Math.max(ir, N.n_municipios ? 0.6 : 0).toFixed(2); fill.style.setProperty('--galvo', String(Math.max(ir, 0.1)));
  fill.style.width = fill.dataset.alvo + '%';
  MonitorMapas.credito('respFonte', {fontes: ['DOU/SEDEC (S2iD)', 'diários oficiais estaduais e municipais'], data: RESP.gerado_em});
}
async function __load(){
  let __ref;
  [BR_GEOJSON, PCT_POR_UF, MAP_POINTS, TABELA_MUNICIPIOS, MARE, DATA, TRANSFERENCIAS, __ref, META, POP_CENSO, RECURSOS, FIN, CONSIST, ATOS_RESPOSTA, VRESUMO] = await Promise.all(
    ['geo_uf','percentual_uf','pontos_mapa','municipios','indice','estados','transferencias','municipios_ibge_referencia','meta','populacao_censo2022','recursos_uf','financiamento_uf','consist','atos_resposta', 'verificacao_resumo']
      .map(f => fetch('data/' + f + '.json').then(r => {
        if(!r.ok) throw new Error('Falha ao carregar data/' + f + '.json');
        return r.json();
      }))
  );
  // AUD-02 (02/09/2026) revisto em 07/10/2026: a carga NAO escapa mais — quem escapa e a saida,
  // uma vez so, por `esc`. A carga continua a derrubar URL que nao seja https://, porque isso e
  // validacao de dado, nao escape de texto.
  (function sanitizar(){
    const walk = (o, chave) => {
      if (Array.isArray(o)) { for (let i = 0; i < o.length; i++) o[i] = walk(o[i], chave); return o; }
      if (o && typeof o === 'object') { for (const k of Object.keys(o)) o[k] = walk(o[k], k); return o; }
      if (typeof o === 'string') {
        if (/^url/i.test(chave || '') || /_url$/i.test(chave || '')) return /^https:\/\//i.test(o.trim()) ? o.trim() : '';
        return o;
      }
      return o;
    };
    [TABELA_MUNICIPIOS, MAP_POINTS, DATA, ATOS_RESPOSTA, TRANSFERENCIAS, RECURSOS, FIN, CONSIST].forEach(x => walk(x, ''));
  })();
  MUN_REF = {};
  __ref.forEach(m => (MUN_REF[m.uf] = MUN_REF[m.uf] || []).push(m.nome));
  __ref.forEach(m => {
    const c = String(m.codigo_ibge).padStart(7, '0');
    MUN_COD[m.uf + '|' + m.nome] = c;
    MUN_LATLON[m.uf + '|' + m.nome] = [m.lon, m.lat];
    POP_UF[m.uf] = (POP_UF[m.uf] || 0) + (POP_CENSO[c] || 0);  // município pós-Censo: 0
  });
  Object.values(MUN_REF).forEach(a => a.sort((x,y) => x.localeCompare(y)));
  // v3.1 §3: contador de resposta (peso zero; arquivos próprios)
  try {
    [RESP, RESP_SERIE, RESP_MUN] = await Promise.all(['data/resposta/por_uf.json','data/resposta/serie_semanal.json','data/resposta/municipios_decretados.json'].map(f => fetch(f).then(r => r.ok ? r.json() : null)));
  } catch(e) { RESP = RESP_SERIE = RESP_MUN = null; }
  __init();
  renderContadorResposta();
  // PR-N0 §1.2: cobertura do diário por município (arquivo pequeno; ausente = rótulo 'ainda não testada')
  fetch('data/cobertura_qd.json').then(r => r.ok ? r.json() : null).then(d => {
    VMUN = {}; Object.entries((d && d.municipios) || {}).forEach(([k, v]) => { VMUN[String(k).padStart(7, '0')] = v.cobertura_qd; });
  }).catch(() => { VMUN = {}; });
}
function __init(){
// 16/09/2026: MEDIA_NACIONAL (média dos 27 estados) foi removida — servia só para comparar
// um estado aberto contra ela (traço no medidor, "X pontos acima/abaixo"); ver miniGauge().
const STATUS_LABEL = {NOVO:"Novo", READ:"Readaptado", ELAB:"Em elaboração", VIG:"Vigente-recorrente", LAC:"Sem plano localizado"};

// 15/09/2026 (pedido da editoria): os três cartões (ONI · R$/hab. · "o que ainda não sabemos") saíram da página inicial;
// os mesmos valores seguem no Monitor de riscos, em Financiamento e em Pesquisadores.
const kpiUFsLAC = Object.entries(MARE).filter(([uf,v]) => v.status_estadual === 'LAC').map(([uf]) => uf);

// ---- Cabeçalho: contadores do herói (auditoria editorial 14/09/2026, §2.1–§2.3).
(function interpretacoes(){
  const el = id => document.getElementById(id); const n = v => Number(v).toLocaleString('pt-BR');
  const total = (VRESUMO && VRESUMO.total_municipios) || 5571;
  if (el('heroVerifFederal')) el('heroVerifFederal').textContent = n(total);
  // 30/09/2026: o texto de abertura passou a ter UMA data só — a da última checagem. O "Dados até"
  // (corte) saiu: ele congelava com o arquivo de transferências e dizia ao leitor que o índice
  // estava parado quando não estava.
})();

// 30/09/2026: o painel "Calendário" da inicial saiu do código, com as outras duas telas de
// calendário (decisão da editoria). O que ele sabia — os marcos do ciclo e os dispositivos da
// Lei 9.504 — passou para a METODOLOGIA, como texto fixo e datado. O motor do defeso, que sabe
// quando o período eleitoral acaba e libera a coleta, é outra coisa e não foi tocado.

// Metadados do cabeçalho e do rodapé: nunca mais texto fixo (achado de Patricia,
// 31/08/2026 — "Fonte: BD_El_Nino_2026_2027_Brasil.xlsx" era um nome de arquivo
// que não existe em lugar nenhum do projeto; corrigido para apontar à seção real
// de fontes verificadas, e os números/data passam a vir de META e MUN_REF.
(function(){
  const totalMun = Object.values(MUN_REF).reduce((s, arr) => s + arr.length, 0);
  const elUfsMun = document.getElementById('metaUfsMun');
  if (elUfsMun) elUfsMun.textContent = Object.keys(MARE).length + ' UFs · ' + totalMun.toLocaleString('pt-BR') + ' municípios cadastrados';
  const dataRef = (META && META.atualizado_em) || (META && META.corte) || '';
  const elVerif = document.getElementById('metaUltimaVerif');
  if (elVerif && dataRef) elVerif.textContent = dataRef;
  const elFooter = document.getElementById('metaAtualizado');
  if (elFooter && dataRef) elFooter.textContent = dataRef;
})();

// 28/09/2026 (item 4 do bloco de frescor). "Última atualização" é a data da PUBLICAÇÃO, e sozinha
// ela não distingue duas coisas diferentes: "nada foi coletado desde então" e "foi coletado e não
// publicado". Foi a segunda que aconteceu entre 25/09 e 28/09 — a coleta seguiu rodando, o
// publicador falhava duas vezes por dia, e nada no site dizia isso. As duas datas, lado a lado,
// dizem. Só descreve o que existe nos arquivos; nenhum juízo, nenhuma instrução de uso.
(function(){
  const el = document.getElementById('metaFrescor');
  if (!el) return;
  const brDeIso = s => {
    const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(s || ''));
    return m ? `${m[3]}/${m[2]}/${m[1]}` : '';
  };
  const publicacao = (META && (META.atualizado_em || META.corte)) || '';
  const doResumo = (typeof VRESUMO !== 'undefined' && VRESUMO && VRESUMO.ultima_rodada_log) || '';
  const mostrar = coleta => {
    if (!coleta || !publicacao) return;   // sem as duas pontas, não se afirma nada
    el.textContent = `Última coleta: ${coleta} · última publicação: ${publicacao}`;
    el.hidden = false;
  };
  fetch('data/saude_pipeline.json')
    .then(r => r.ok ? r.json() : null)
    .then(s => mostrar(brDeIso((s && s.atualizado_em) || doResumo)))
    .catch(() => mostrar(brDeIso(doResumo)));
})();

// 26/09/2026 (pedido da editoria). Os estados eram agrupados numa COLUNA por região, e o
// desequilíbrio de contagem (9 no Nordeste contra 3 no Sul) deixava um quadrante vazio, porque
// toda coluna herda a altura da mais longa. Enquanto a contagem por região definir a geometria,
// nenhum ajuste de espaçamento resolve. Agora o arranjo é GEOGRÁFICO: cada estado ocupa a
// posição aproximada dele no país, e a contagem desigual deixa de existir como problema.
// A grade é a `br_states_grid1` do pacote geofacet (hafen/grid-designer), publicada e conferida
// contra a fonte — não é posição estimada aqui.
// 02/10/2026 (item 7): a posição geográfica de cada estado passou a viver no componente
// compartilhado, `assets/js/grade-estados.js`, que a inicial e o MARÉ Saúde usam. Duas
// tabelas de posição divergiriam na primeira correção.
const GRADE_BR = (window.GradeEstados && window.GradeEstados.GRADE_BR) || {};
// 27/09/2026 (pedido da editoria): o risco projetado entrou no cartão de cada estado.
// 30/09/2026 (pedido da editoria): sai da frente do cartão — fica só na ficha (janela de
// detalhe), destacado. Carregado à parte para não atrasar o índice: se falhar, a ficha fica
// sem o bloco e nada mais muda. RISCO_UF e RISCO_FONTE são lidos por selectUF() (abaixo).
let RISCO_UF = {}, RISCO_FONTE = null;
fetch('data/sinais_risco.json').then(r => r.ok ? r.json() : null).catch(() => null).then(sr => {
  if (!sr || !sr.uf) return;
  Object.keys(sr.uf).forEach(uf => {
    const r = sr.uf[uf] && sr.uf[uf].risco_projetado;
    if (r && r.texto) RISCO_UF[uf] = r;
  });
  RISCO_FONTE = (sr.fontes || {})['painel_el_nino'] || null;
});

// 30/09/2026 (PR 4 do enquadramento federal de risco): quem consta de qual lista federal, por
// município. Arquivo derivado e enxuto (69 kB) — as bases de origem somam 680 kB e trazem o que a
// transparência pede, não o que o cartão usa. Carregado à parte: se falhar, o cartão fica sem o
// bloco e nada mais muda.
let ENQ_MUN = null, ENQ_FONTES = {};
fetch('data/enquadramento_card.json').then(r => r.ok ? r.json() : null).catch(() => null).then(e => {
  if (!e || !e.municipios) return;
  ENQ_MUN = e.municipios; ENQ_FONTES = e.fontes || {};
});

// Os quatro textos são LITERAIS, aprovados pela editoria em 30/09/2026, e não variam. Só o
// complemento "Risco identificado" da linha de chuva muda, e só entre três valores fechados —
// quando a nota técnica não nomeia o tipo, a frase termina no parêntese.
//
// Nenhuma palavra de dever, obrigação ou recomendação: duas destas listas não criam dever nenhum
// para o município, e a que cria (o cadastro do art. 3º-A da Lei 12.340) não é nenhuma delas.
// `scripts/verificar_textos_enquadramento.py` reprova se estes textos mudarem ou se palavra de
// dever entrar aqui.
// Data em DD/MM/AAAA, como manda a editoria em todo texto publico. ISO sem conversao ja apareceu
// no cartao, e data e dado: ou se mostra no formato do leitor, ou nao se mostra.
const dataBR = s => {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(s || ''));
  return m ? `${m[3]}/${m[2]}/${m[1]}` : String(s || '');
};

// Textos aprovados pela editoria em 07/10/2026 (C3 do handover dos cartoes). Nenhuma palavra de
// dever, obrigacao ou recomendacao: duas destas listas nao criam dever nenhum para o municipio, e a
// que cria (o cadastro do art. 3o-A da Lei 12.340) nao e nenhuma delas.
// `scripts/verificar_textos_enquadramento.py` reprova se estes textos mudarem ou se palavra de
// dever entrar aqui. O ano do MMA vem da portaria em vigor, gravada no dado — nao do codigo.
const ENQ_TEXTO = {
  chuva: 'Consta do cadastro federal de municípios suscetíveis a enxurradas e inundações.',
  geo: 'Consta da lista federal de municípios suscetíveis a risco geo-hidrológico.',
  seca: 'Integra a delimitação oficial do Semiárido brasileiro.',
  fogo: 'Consta da lista federal de municípios prioritários para controle do desmatamento e dos incêndios florestais na Amazônia (MMA, {ano}).',
  nenhuma: 'Não consta das listas federais de risco por município: enxurradas e inundações (Casa Civil), Semiárido (Sudene) e prioritários para desmatamento e incêndios (MMA).',
};
// Os tipos que a nota tecnica nomeia, pelos nomes da fonte, em ordem alfabetica.
const ENQ_TIPO = {d: 'deslizamento', e: 'enxurrada', i: 'inundação'};

// O ano do instrumento, para o texto que o cita. Vem da data gravada na fonte; sem data, o texto
// fica sem o parenteses em vez de inventar ano.
function anoDaFonte(fam){
  const f = (ENQ_FONTES || {})[fam] || {};
  const m = /(\d{4})/.exec(String(f.publicada_em || f.consultado_em || ''));
  return m ? m[1] : '';
}

// Bloco do cartão do município. Vazio quando não se sabe DE QUE município se trata: "não consta de
// nenhuma lista" é afirmação sobre um município identificado, e sem código IBGE não há afirmação a
// fazer. Camada de contexto, peso zero — não entra na nota do MARÉ.
function enquadramentoBox(uf, nome, codigo){
  // 07/10/2026 (A1): o quadro depende do CODIGO IBGE, nao de haver registro no banco de planos.
  // Enquanto ele dependia do registro, 2.916 municipios que constam de lista federal abriam o
  // cartao sem o quadro — o dado existia e nao aparecia.
  if (!ENQ_MUN || !uf) return '';
  const cod = codigo || MUN_COD[uf + '|' + nome];
  if (!cod) return '';
  const marcas = ENQ_MUN[cod] || {};
  const fonte = fam => {
    const f = ENQ_FONTES[fam];
    if (!f || !f.instrumento) return '';
    // Um instrumento pode estar publicado em mais de um documento: as duas notas tecnicas da Casa
    // Civil sao duas, e as duas vao como link.
    const varios = Array.isArray(f.urls) && f.urls.length;
    const links = (varios ? f.urls : (f.url ? [[f.instrumento, f.url]] : []))
      .map(par => `<a href="${esc(par[1])}" target="_blank" rel="noopener">${esc(par[0])}</a>`);
    const quando = f.consultado_em ? ' · consultado em ' + esc(dataBR(f.consultado_em)) : '';
    // Com vários documentos, o nome do órgão vem uma vez e cada documento vira o próprio link —
    // repetir o nome do documento no texto e no link dizia a mesma coisa duas vezes.
    const corpoFonte = varios
      ? esc(f.prefixo || f.instrumento) + ', ' + links.slice(0, -1).join(', ') + (links.length > 1 ? ' e ' : '') + links[links.length - 1]
      : (links.length ? links[0] : esc(f.instrumento));
    return `<p class="fonte">Fonte: ${corpoFonte}${quando}</p>`;
  };
  const tipos = String(marcas.tp || '').split('').map(l => ENQ_TIPO[l]).filter(Boolean).sort((a, b) => a.localeCompare(b, 'pt-BR'));
  const marcasTipo = tipos.length
    ? `<p class="enq-tipos">${tipos.map(x => `<span class="chip-risco">${esc(x)}</span>`).join('')}</p>`
    : '';
  // Ordem fixa chuva → geo-hidrológico → seca → fogo. Interseção mostra todas as linhas.
  const linhas = [];
  if (marcas.ch !== undefined) linhas.push({fam: 'chuva', texto: ENQ_TEXTO.chuva, tipos: marcasTipo});
  if (marcas.geo) linhas.push({fam: 'chuva', texto: ENQ_TEXTO.geo, tipos: ''});
  if (marcas.sa) linhas.push({fam: 'seca', texto: ENQ_TEXTO.seca, tipos: ''});
  if (marcas.mma) linhas.push({fam: 'fogo', texto: ENQ_TEXTO.fogo.replace('{ano}', anoDaFonte('fogo')).replace(' (MMA, )', ' (MMA)'), tipos: ''});
  const corpo = linhas.length
    ? linhas.map(l => `<div class="enq-linha r-${l.fam}"><p class="v">${esc(l.texto)}</p>${l.tipos}${fonte(l.fam)}</div>`).join('')
    : `<div class="enq-linha"><p class="v">${esc(ENQ_TEXTO.nenhuma)}</p>${fonte('chuva')}${fonte('seca')}${fonte('fogo')}</div>`;
  return `<div class="enq-box">
    <p class="k">Este município nas listas federais de risco</p>
    ${corpo}
  </div>`;
}

const regionsEl = document.getElementById('regions');

// 26/09/2026: dentro de cada faixa de região, ordem decrescente pelo índice — não alfabética.
// Alinhadas numa série, as barras só são comparáveis se a ordem for a da própria grandeza; em
// ordem alfabética o leitor tem 27 valores e nenhuma leitura. Estado sem índice vai para o fim da
// faixa, sem inventar posição para quem não tem número.
const ufsOrdenadas = DATA.ufs.slice().sort((a, b) => {
  const va = (typeof MARE !== 'undefined' && MARE[a.uf]) ? MARE[a.uf].total : null;
  const vb = (typeof MARE !== 'undefined' && MARE[b.uf]) ? MARE[b.uf].total : null;
  if (va == null && vb == null) return a.uf.localeCompare(b.uf, 'pt-BR');
  if (va == null) return 1;
  if (vb == null) return -1;
  return vb - va;
});
ufsOrdenadas.forEach(item=>{
  const container = regionsEl;
  const tile = document.createElement('div');
  tile.className = `tile st-${item.status}`;
  tile.dataset.uf = item.uf;
  /* 02/10/2026 (item 3.1): a cor do cartão passou a vir do componente, em assets/base.css. Corrigir
   * inline aqui era o que escondia o defeito: a página que esquecesse publicaria texto invisível. */
  const v = (typeof MARE !== 'undefined' && MARE[item.uf]) ? MARE[item.uf].total : null;
  tile.title = `${item.uf} · MARÉ ${v == null ? 'sem dado' : String(v).replace('.', ',')} / 100`;
  const pos = GRADE_BR[item.uf];
  if (pos) { tile.style.gridRow = pos[0]; tile.style.gridColumn = pos[1]; }
  // 26/09/2026 (pedido da editoria): nome por extenso além da sigla. Vem de item.nome, a mesma
  // fonte que a janela de detalhe já usa ("Bahia (BA)") — nenhuma segunda lista de nomes.
  tile.innerHTML = `<span class="tile-uf">${item.uf}</span><span class="tile-nome">${esc(item.nome)}</span>` +
    (v == null
      ? '<span class="tile-score">·</span>'
      : `<span class="tile-score" data-contar="${v}">0,0</span>
         <div class="tile-bar"><div class="tile-fill" data-alvo="${v}" style="--galvo:${Math.max(v, 0.1)};"></div></div>`) +
    respostaTile(item.uf) +
    faceTile(item.uf);
  // 26/09/2026: a linha do estado abre o detalhe e sempre foi uma caixa genérica com ouvinte de clique —
  // sem papel e sem índice de tabulação, quem navega por teclado não alcançava nenhum estado. O
  // defeito é anterior à troca de cartão por linha; a troca só o deixou visível. `role` e `tabindex`
  // tornam o alvo alcançável, Enter e Espaço o acionam como qualquer botão, e o rótulo vem do
  // mesmo texto do title, para o leitor de tela não ouvir a linha inteira campo a campo.
  tile.setAttribute('role', 'button');
  tile.tabIndex = 0;
  tile.setAttribute('aria-label', 'Detalhe de ' + tile.title);
  tile.addEventListener('click', ()=>{ selectUF(item.uf, tile); animarGauges(document.getElementById('detail')); });
  tile.addEventListener('keydown', e=>{ if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); tile.click(); } });
  container.appendChild(tile);
});
animarGauges(document.body); // 31/08/2026: corrigido de getElementById('regions') — o medidor principal do herói
                              // fica FORA de #regions e nunca era animado; document.body cobre os dois.

// ---- Cartão padrão: instrução, sem nota nacional na mesma faixa dos estados ----
// 16/09/2026 (pedido da editoria): mostrar "Brasil (média nacional)" no exato lugar onde o
// detalhe de um estado aparece convidava a comparação; a nota nacional já está no medidor
// do topo da página. Aqui fica só a instrução.
function renderDetalhePadrao(){
  const det = document.getElementById('detail');
  if (!det || det.innerHTML.trim()) return;
  det.innerHTML = `<p class="placeholder">Clique em um estado na grade para abrir o detalhe: componentes verificados, situação da capital e o que cobrar.</p>`;
  det.hidden = false;
}
setTimeout(renderDetalhePadrao, 0);


// 30/09/2026 (pedido da editoria): bloco de risco projetado da ficha do estado, destacado —
// acento de cor pela família dominante (chuva/seca/fogo), componentes em vocabulário fechado
// como chips, frase inteira do boletim e a fonte. Vazio quando não há risco carregado para a UF.
function riscoBox(uf){
  const r = RISCO_UF[uf];
  if (!r) return '';
  const NOME_COMP = {estiagem:'estiagem', incendios:'incêndios', chuvas:'chuvas', sem_sinal:'sem sinal elevado'};
  const FAMILIA = {estiagem:'r-seca', incendios:'r-fogo', chuvas:'r-chuva'};
  const comps = (r.componentes && r.componentes.length ? r.componentes : [r.tipo]);
  const familia = comps.map(c => FAMILIA[c]).find(Boolean) || '';
  const chips = comps.map(c => `<span class="chip-risco">${esc(NOME_COMP[c] || c)}</span>`).join('');
  const fonte = RISCO_FONTE
    ? 'Fonte: ' + (RISCO_FONTE.url_publica
        ? `<a href="${esc(RISCO_FONTE.url_publica)}" target="_blank" rel="noopener">${esc(RISCO_FONTE.documento || RISCO_FONTE.nome)}</a>`
        : esc(RISCO_FONTE.nome))
      + (RISCO_FONTE.consultado_em ? ' · consultado em ' + esc(dataBR(RISCO_FONTE.consultado_em)) : '')
    : '';
  // 07/10/2026 (A3): o horizonte e o que o BOLETIM diz — "no trimestre outubro-novembro-dezembro
  // (OND) de 2026" —, nao "ciclo" nem "trimestre" por conta propria. Sem horizonte gravado, o
  // rotulo fica sem complemento em vez de inventar um.
  const horizonte = (RISCO_FONTE && RISCO_FONTE.horizonte) ? ' ' + RISCO_FONTE.horizonte : '';
  return `<div class="risco-box ${familia}">
    <p class="k">Projeção do Painel El Niño${esc(horizonte)}</p>
    <p class="v">${esc(r.texto)}</p>
    <div class="chips">${chips}</div>
    ${fonte ? `<p class="fonte">${fonte}</p>` : ''}
  </div>`;
}
// 08/10/2026 (A3-11, item 1.10): a capital tinha DUAS fontes — `estados.json.capital.status` e
// `.info`, escritos a mão, e `municipios.json`, que e a fonte da pontuacao. Elas se contradiziam
// em NOVE UFs, e o leitor via no mesmo clique "Novo, base da pontuacao" e "ainda nao verificado"
// (Rio Branco). Agora ha uma fonte: o registro do banco. O texto vem das MESMAS frases do cartao
// do municipio, pela mesma funcao de estado.
// O registro da capital no banco. A ladrilheira dos estados pinta ANTES de `TABELA_MUNICIPIOS`
// chegar do fetch, e `[].find` num objeto vazio derruba a pintura inteira — foi o que apagou o
// seletor de UF e mais onze verificações de runtime na primeira versão deste item.
function regDaCapital(d){
  if (!d || !d.capital || !Array.isArray(TABELA_MUNICIPIOS)) return null;
  return TABELA_MUNICIPIOS.find(m => m.uf === d.uf && m.nome === d.capital.nome) || null;
}
const CAT_ROTULO = {
  plano: 'plano localizado', plano_novo: 'plano do ciclo', plano_readaptado: 'plano readaptado',
  plano_recorrente: 'plano recorrente', plano_antigo: 'plano vigente de ciclo anterior',
  plano_elaboracao: 'plano em elaboração', plano_nomeado: 'plano citado, documento não localizado',
  estrutura: 'estrutura de coordenação', coberto_estadual: 'coberta pelo plano estadual',
  nao_el_nino: 'ato alheio aos riscos do ciclo', nao_localizado: 'não localizado',
  nao_verificado: 'ainda não verificada'
};
function textoDaCapital(reg){
  if (!reg) return 'Ainda não verificamos esta capital com todas as fontes. Isso não é uma afirmação sobre a existência do plano.';
  const st = statusDoPlano(reg.categoria);
  if (st === 'encontrado') return 'Plano de contingência localizado.';
  if (st === 'estadual') return 'Plano de contingência localizado, no âmbito estadual.';
  if (st === 'nomeado'){
    const q = reg.fonte ? esc(reg.fonte) : 'fonte oficial';
    const dd = reg.data ? ', ' + esc(dataBR(reg.data) || reg.data) : '';
    return 'Plano de contingência citado em fonte oficial (' + q + dd + '); documento não localizado até o corte.';
  }
  if (reg.categoria === 'plano_elaboracao') return 'Plano de contingência em elaboração; o documento final não foi localizado até o corte.';
  if (reg.categoria === 'estrutura') return 'Estrutura de coordenação localizada; não é plano de contingência para os riscos deste ciclo.';
  if (reg.categoria === 'nao_localizado') return 'Não localizamos plano de contingência para esta capital até a data de corte.';
  return 'Ainda não verificamos esta capital com todas as fontes. Isso não é uma afirmação sobre a existência do plano.';
}
function rotuloDaCapital(reg){
  return reg && CAT_ROTULO[reg.categoria] ? CAT_ROTULO[reg.categoria] : 'ainda não verificada';
}

function selectUF(uf, tileEl){
  // P2 (auditoria 07/09/2026): d.doc, d.orgao, d.estrutura.doc e o nome da capital são texto
  // editorial (resumo humano de documento oficial), não HTML bruto raspado — mas entravam direto
  // em innerHTML sem escape, ao contrário do resto do módulo (ver financiamento.js). Corrigido.
  // 08/10/2026 (A3-11): o texto da capital saiu de `estados.json`; o que ela diz vem do banco.
  document.querySelectorAll('.tile').forEach(t=>t.classList.remove('active'));
  tileEl.classList.add('active');
  const d = DATA.ufs.find(x=>x.uf===uf);
  const badgeClass = 'st-'+d.status;
  // Link do documento da capital: buscado em TABELA_MUNICIPIOS (fonte única), nunca
  // duplicado em DATA — mesma disciplina do resto do banco. Sem link, nomeado como
  // não verificado (regra de ouro: nunca link presumido ou fabricado).
  const capReg = d.capital ? TABELA_MUNICIPIOS.find(m => m.uf === uf && m.nome === d.capital.nome) : null;
  const linkCapital = capReg && capReg.url
    ? `<div class="card-link"><a href="${esc(capReg.url)}" target="_blank" rel="noopener">Ver fonte oficial →</a></div>`
    : capReg && capReg.categoria === 'nao_localizado'
      ? `<div class="card-note">Nenhum documento localizado até o corte dos dados.</div>`
      : capReg && capReg.categoria === 'nao_verificado'
        ? `<div class="card-note">Ainda não verificada individualmente com a bateria completa de fontes.</div>`
        : `<div class="card-note">Documento nomeado; link oficial em verificação.</div>`;
  const capitalBlock = d.capital ? `
    <div class="capital-box">
      <div class="card-kicker">Capital · verificação individual</div>
      <div class="card-title">${esc(d.capital.nome)} <span class="sub">· ${esc(rotuloDaCapital(capReg))}</span></div>
      <div class="card-body">${textoDaCapital(capReg)}</div>
      ${linkCapital}
    </div>` : `<p class="placeholder">Capital sem verificação individual até o corte.</p>`;

  document.getElementById('detailConteudo').innerHTML = `
    <div class="uf-name">${esc(d.nome)} <span class="sub">(${esc(d.uf)})</span></div>
    ${typeof MARE !== 'undefined' && MARE[d.uf] ? miniGauge(MARE[d.uf].total) : ''}
    <div class="uf-region">${esc(d.regiao)}</div>
    <span class="badge ${badgeClass}">${STATUS_LABEL[d.status]}</span>
    ${riscoBox(d.uf)}
    <div class="field"><div class="k">Estrutura de coordenação</div><div class="v">${d.estrutura ? '<span class="pill-nivel">' + (STATUS_LABEL[d.estrutura.status] || d.estrutura.status) + '</span> ' + esc(d.estrutura.doc) + (d.estrutura.data && d.estrutura.data !== '—' ? ' (' + esc(d.estrutura.data) + ')' : '') : '—'}</div></div>
    <div class="field"><div class="k">Instrumento operacional</div><div class="v"><span class="pill-nivel">${STATUS_LABEL[d.status]}</span> ${esc(d.doc)}${d.data ? ' (' + esc(d.data) + ')' : ''}${d.sem_ato_de_aprovacao ? '<br><span class="spec">sem ato de aprovação localizado</span>' : ''}</div></div>
    ${(function(){ // 01/10/2026, texto aprovado pela editoria. A v3.1 dá zero ao instrumento
      // recorrente que NÃO cobre o risco previsto para o ciclo (degrau VIG_NAO_COBRE), e até aqui a
      // interface não dizia isso em lugar nenhum: o cartão mostrava "vigente-recorrente" e o leitor
      // não tinha como saber que o plano trata de outro risco. Os dois riscos vêm do dado
      // (data/consist.json: `instr` e `risco`), nunca escritos à mão, e a frase não diz "não
      // pontua" — a nota é o que a nota é, e a razão dela vive na metodologia.
      const m = (typeof MARE !== 'undefined' && MARE[d.uf]) || null;
      if (!m || m.degrau_instrumento !== 'VIG_NAO_COBRE') return '';
      const c = (typeof CONSIST !== 'undefined' && CONSIST[d.uf]) || null;
      if (!c) return '';
      const familia = t => /chuva|enchent|hidrol|inunda/i.test(t) ? 'chuvas'
                         : /seca|estiagem|h[íi]dric|IIS/i.test(t) ? 'seca'
                         : /inc[êe]ndi|fogo|queimad/i.test(t) ? 'fogo' : null;
      const doInstrumento = familia(String(c.instr || '')), doCiclo = familia(String(c.risco || ''));
      /* Sem conseguir nomear os dois riscos pelo dado, a linha não sai: lacuna declarada é melhor
         do que risco inventado para preencher a frase. */
      if (!doInstrumento || !doCiclo || doInstrumento === doCiclo) return '';
      return `<div class="card-note">O plano estadual em vigor trata de outro risco (${doInstrumento}), não do previsto para este ciclo (${doCiclo}).</div>`;
    })()}
    ${(function(){ /* 03/10/2026: o que o próprio órgão respondeu ao MARÉ por pedido de acesso
      à informação. Não pontua e não deve pontuar: é prova de que o órgão afirma, não de que o
      documento existe e diz o que se espera dele. A frase é literal aprovado pela editoria e vem
      do dado (`nota_lai` em data/estados.json), nunca escrita aqui. */
      return d.nota_lai ? `<div class="card-note">${esc(d.nota_lai)}</div>` : '';
    })()}
    <div class="field"><div class="k">Órgão responsável</div><div class="v">${esc(d.orgao)}</div></div>
    ${(function(){ // 26/09/2026: a face da célula não comporta este campo, e ele NÃO existia no
      // detalhe — sem isto, o alcance da varredura sumiria da interface inteira.
      const niv = (typeof VRESUMO !== 'undefined' && VRESUMO && VRESUMO.por_uf && VRESUMO.por_uf[d.uf]) || {};
      const tot = Object.values(niv).reduce((a, b) => a + b, 0);
      const lidos = ((VRESUMO && VRESUMO.varredura_diarios && VRESUMO.varredura_diarios.por_uf) || {})[d.uf] || 0;
      return tot ? `<div class="field"><div class="k">Diários municipais consultados</div><div class="v">${lidos} de ${tot}</div></div>` : '';
    })()}
    ${d.adpf743 ? '<div class="field"><div class="k">ADPF 743 (STF)</div><div class="v"><span class="pill-nivel">' + ({homologado:'plano homologado', ajustes_exigidos:'ajustes exigidos em 30 dias', ajustes_exigidos_car:'ajustes exigidos (CAR)', apresentado:'plano apresentado'}[d.adpf743.status] || esc(d.adpf743.status)) + '</span> intimado em ' + esc(d.adpf743.intimado_em) + ' · decisão de ' + esc(d.adpf743.decisao) + (d.adpf743.status !== 'homologado' ? ' · resultado após 25/07 não localizado' : '') + '</div></div>' : ''}
    ${barraResposta(d.uf)}
    ${(function(){ // v3.1 (30/09/2026): três componentes com um terço cada, nomeados pelo que são.
      // Na v3.0 estrutura e instrumento eram metades de um componente só; agora cada um vale por si,
      // e a régua temporal saiu da nota. Descrição do que se vê — variável, unidade e valor —, sem
      // juízo: a leitura vive no texto narrativo, não no cartão (portão 19).
      const m = (typeof MARE !== 'undefined' && MARE[d.uf]) || null;
      if (!m || m.instrumento === undefined) return '';
      return `<div class="field"><div class="k">Componentes (um terço cada)</div><div class="v">instrumento operacional ${m.instrumento} · estrutura de coordenação ${m.estrutura} · cobertura populacional ${m.cobertura_pop}</div></div>`;
    })()}
    ${(function(){ // INDICADOR, não componente: não entra na nota. Vazio quando não há data completa
      // do primeiro ato — mês solto e "Recorrente" não viram dia, e lacuna declarada é melhor do
      // que dia inventado.
      const m = (typeof MARE !== 'undefined' && MARE[d.uf]) || null;
      if (!m || m.dias_apos_boletim_1 === null || m.dias_apos_boletim_1 === undefined) return '';
      const n = m.dias_apos_boletim_1;
      const quando = n < 0 ? `${Math.abs(n)} dias antes` : `${n} dias depois`;
      return `<div class="field"><div class="k">Antecedência do primeiro ato datado</div><div class="v">${quando} do Boletim nº 1 (29/06/2026) · ato de ${esc(m.data_primeiro_ato)} · não entra na nota</div></div>`;
    })()}
    ${(function(){ // C12: instrumento publicado dentro da janela do defeso (04/07–25/10/2026) — fato datado, sem juízo
        const m = String(d.data || '').match(/(\d{2})\/(\d{2})\/(\d{4})/); if (!m) return '';
        const dt = new Date(+m[3], +m[2]-1, +m[1]); const ini = new Date(2026,6,4), fim = new Date(2026,9,25);
        return (dt >= ini && dt <= fim) ? `<div class="card-note">Publicado em ${esc(d.data)}, dentro do período eleitoral (04/07–25/10/2026), quando transferências voluntárias e publicidade institucional estão suspensas por lei — a publicação em diário oficial é ato oficial, não publicidade (METODOLOGIA §24).</div>` : '';
      })()}
    ${capitalBlock}
    <p class="note">Acompanhe ${esc(d.nome)} sem visitar o site: <a href="feeds/${d.uf}.xml" type="application/atom+xml">feed de atualizações (Atom)</a> — cada instrumento localizado, cada mudança no índice, com data.</p>
  `;
  const __dialogDetail = document.getElementById('detail');
  if (__dialogDetail) __dialogDetail.setAttribute('aria-label', 'Detalhe do estado');
  // jsdom (suíte de testes) não implementa showModal()/close() do <dialog>, só a propriedade 'open'
  // refletida — no navegador real, showModal() é o caminho certo (bloqueia scroll do fundo, foco).
  if (__dialogDetail && !__dialogDetail.open) {
    if (typeof __dialogDetail.showModal === 'function') __dialogDetail.showModal(); else __dialogDetail.open = true;
  }
}
// 14/09/2026 (pedido de Patricia, 13/09): "Como ler o MARÉ" vira ficha popup no MESMO <dialog> do detalhe do estado,
// aberta pelo link "como ler o MARÉ" logo abaixo da barra do índice; o conteúdo vive oculto em #comoler.
(function(){
  const link = document.getElementById('linkComoLer'), fonte = document.getElementById('comoler'), dlg = document.getElementById('detail');
  if (!link || !fonte || !dlg) return;
  link.addEventListener('click', (e) => {
    e.preventDefault();
    document.getElementById('detailConteudo').innerHTML = fonte.innerHTML;
    dlg.setAttribute('aria-label', 'Como ler o MARÉ Legal');
    if (!dlg.open) { if (typeof dlg.showModal === 'function') dlg.showModal(); else dlg.open = true; }
  });
})();
// 13/09/2026 (pedido de Patricia: quadro dos estados ocupa a página inteira, detalhe vira janela
// popup): fechar pelo botão ×, por clique no fundo (::backdrop) ou por Esc (nativo do <dialog>).
(function(){
  const dlg = document.getElementById('detail');
  if (!dlg) return;
  const fechar = document.getElementById('detailFechar');
  const fecharDialog = () => { if (typeof dlg.close === 'function') dlg.close(); else dlg.open = false; };
  if (fechar) fechar.addEventListener('click', fecharDialog);
  dlg.addEventListener('click', (evt) => { if (evt.target === dlg) fecharDialog(); });   // clique fora do conteúdo (::backdrop não recebe click em todo navegador)
})();

// ---- Infraestrutura compartilhada com a página Defesa civil (ex-mapas e gráficos): tooltip
// (usado pela linha do tempo do herói) e HAB_SET (usado no cartão de cidade,
// indicador de habilitação a recurso federal) — pequenas o bastante para
// recalcular aqui em vez de depender da página que tem os mapas completos.
const showTip = MonitorMapas.showTip, hideTip = MonitorMapas.hideTip;
const habilitados = MAP_POINTS.filter(p => p.categoria === 'decreto');
const HAB_SET = new Set(habilitados.map(p => (p.nome || '').toLowerCase() + '|' + p.uf));

// =========================================================
// Tabela pesquisável de municípios
// =========================================================
const CANAL_LABEL = {DOM:'Diário Oficial dos Municípios', DOU:'Diário Oficial da União',
  repositorio_estadual:'repositório estadual de planos', orgao_estadual:'órgão estadual',
  // 28/09/2026 (§281): "imprensa" é canal de DESCOBERTA, não de registro, e o rótulo tinha de
  // dizer isso. Treze registros traziam "via imprensa" ao lado de uma fonte descrita como
  // oficial, e o leitor não tinha como saber que a matéria serviu para achar o documento, não
  // para provar o ato. Nenhum dos treze pontua — o rótulo era o problema inteiro.
  site_municipal:'site oficial do município', imprensa:'imprensa (descoberta)', '—':''};
const CAT_LABEL_TBL = {
  plano:['Plano preventivo',MonitorMapas.PALETA.categorias.plano], plano_antigo:['Plano vigente, de ciclo anterior',MonitorMapas.PALETA.categorias.plano_antigo],
  plano_elaboracao:['Em elaboração',MonitorMapas.PALETA.categorias.plano_elaboracao], plano_novo:['Plano novo, dedicado ao ciclo',MonitorMapas.PALETA.categorias.plano_novo], plano_readaptado:['Plano readaptado para o ciclo',MonitorMapas.PALETA.categorias.plano_readaptado], plano_recorrente:['Plano recorrente, sazonal',MonitorMapas.PALETA.categorias.plano_recorrente], estrutura:['Estrutura de coordenação',MonitorMapas.PALETA.categorias.estrutura], decreto:['Decreto reativo',MonitorMapas.PALETA.categorias.decreto],
  coberto_estadual:['Coberto pelo estado',MonitorMapas.PALETA.categorias.coberto_estadual], nao_el_nino:['Não é El Niño',MonitorMapas.PALETA.categorias.nao_el_nino],
  nao_localizado:['Nada localizado',MonitorMapas.PALETA.categorias.nao_localizado],
  nao_verificado:['Ainda não verificado',MonitorMapas.PALETA.categorias.nao_verificado],
};
// 15/09/2026: os relógios de prazo (renderPrazos) e a nota do período eleitoral saíram da página inicial; os prazos
// vivem na METODOLOGIA desde 30/09/2026, quando as três telas de calendário saíram do código.
MonitorMapas.credito('prazosFonte', {fontes: ['registro de marcos do Monitor (Lei 12.608, ADPF 743, MPs 1.367 e 1.384, calendário do TSE, boletins do Painel El Niño)'], data: (typeof META !== 'undefined' && META && (META.atualizado_em || META.corte)) || null});
(function(){ const c = document.getElementById('citacaoCorte'); if (c && META && META.corte) c.textContent = META.corte; })();
// Link direto para um estado (#SC): usado pelos selos embutidos em outros sites (31/08/2026).
(function(){
  const h = (location.hash || '').replace('#', '').toUpperCase();
  if (/^[A-Z]{2}$/.test(h) && MARE[h]) {
    const tile = document.querySelector('#regions .tile[data-uf="' + h + '"]');
    if (tile) selectUF(h, tile);
  }
})();
(document.getElementById('munCount')||{}).textContent = TABELA_MUNICIPIOS.length;

// ---- Seção de fontes: derivada dos próprios dados (nenhum link não verificado) ----

// Um item por FONTE (domínio), com contagem de registros — os links de cada
// documento individual permanecem, linha a linha, na tabela de auditoria acima.

// =========================================================
// ENCONTRE SUA CIDADE — lente pessoal e comparação social
// =========================================================
const UF_NOME = {}; BR_GEOJSON.features.forEach(f => UF_NOME[f.properties.sigla] = f.properties.name);
const __estArr = Array.isArray(DATA) ? DATA : Object.values(DATA).flat();
const EST = Object.fromEntries(__estArr.map(e => [e.uf, e]));
const DOM_LINKS = {PB:'https://www.diariomunicipal.com.br/famup', AL:'https://www.diariomunicipal.com.br/ama', RN:'https://www.diariomunicipal.com.br/femurn', PA:'https://www.diariomunicipal.com.br/famep', SE:'https://www.diariomunicipal.com.br/sergipe'};
const EMAILS = {AC:'defesacivil.acre.cepdec@gmail.com', AL:'defesacivil@bombeiros.al.gov.br', AP:'secretaria@defesacivil.ap.gov.br', AM:'comadec@comadec.am.gov.br', BA:'defesa.civil@sudec.ba.gov.br', CE:'defesacivil@cb.ce.gov.br', DF:'defesa.civil@ssp.df.gov.br', ES:'defesacivil@bombeiros.es.gov.br', GO:'cbmgo.codec@gmail.com', MA:'cbmma@cbm.ma.gov.br', MT:'gabinete@defesacivil.mt.gov.br', MS:'cedec@defesacivil.ms.gov.br', MG:'defesacivil@defesacivil.mg.gov.br', PA:'chefiagabinete@bombeiros.pa.gov.br', PB:'defesacivil.pb@gmail.com', PR:'defesacivil@defesacivil.pr.gov.br', PE:'codecipe@camil.pe.gov.br', PI:'defesacivilpiaui@gmail.com', RJ:'suop@defesacivil.rj.gov.br', RN:'defesacivil@rn.gov.br', RS:'defesa-civil@casamilitar.rs.gov.br', RO:'gabcmd@cbm.ro.gov.br', RR:'comandocbmrr@hotmail.com', SC:'gabinete@defesacivil.sc.gov.br', SP:'defesacivil@sp.gov.br', SE:'defesacivil@defesacivil.se.gov.br', TO:'defesacivil@bombeiros.to.gov.br'};
const PORTAIS_UF = {AC:["https://defesacivil.ac.gov.br","defesacivil.ac.gov.br"], AL:["https://defesacivil.al.gov.br","defesacivil.al.gov.br"], AM:["https://www.defesacivil.am.gov.br","www.defesacivil.am.gov.br"], AP:["https://defesacivil.ap.gov.br","defesacivil.ap.gov.br"], BA:["https://defesacivil.ba.gov.br","defesacivil.ba.gov.br"], CE:["https://defesacivil.ce.gov.br","defesacivil.ce.gov.br"], DF:["https://defesacivil.df.gov.br","defesacivil.df.gov.br"], ES:["https://defesacivil.es.gov.br","defesacivil.es.gov.br"], GO:["https://bombeiros.go.gov.br","bombeiros.go.gov.br"], MA:["https://defesacivil.ma.gov.br","defesacivil.ma.gov.br"], MG:["https://defesacivil.mg.gov.br","defesacivil.mg.gov.br"], MS:["https://www.defesacivil.ms.gov.br/","www.defesacivil.ms.gov.br"], MT:["https://defesacivil.mt.gov.br","defesacivil.mt.gov.br"], PA:["https://www.bombeiros.pa.gov.br/defesacivil/","www.bombeiros.pa.gov.br/defesacivil"], PB:["https://paraiba.pb.gov.br/diretas/defesa-civil","paraiba.pb.gov.br/diretas/defesa-civil"], PE:["https://www.defesacivil.pe.gov.br/","www.defesacivil.pe.gov.br"], PI:["https://portal.pi.gov.br/defesacivil","portal.pi.gov.br/defesacivil"], PR:["https://www.defesacivil.pr.gov.br","www.defesacivil.pr.gov.br"], RJ:["https://www.defesacivil.rj.gov.br/","www.defesacivil.rj.gov.br"], RN:["tel:+558432325153","(84) 3232-5153 (sem portal)"], RO:["https://cbm.ro.gov.br","cbm.ro.gov.br"], RR:["https://www.cbm.rr.gov.br/","www.cbm.rr.gov.br"], RS:["https://defesacivil.rs.gov.br","defesacivil.rs.gov.br"], SC:["https://defesacivil.sc.gov.br","defesacivil.sc.gov.br"], SE:["https://defesacivil.se.gov.br","defesacivil.se.gov.br"], SP:["https://www.defesacivil.sp.gov.br","www.defesacivil.sp.gov.br"], TO:["https://defesacivil.to.gov.br","defesacivil.to.gov.br"]};   // 15/09/2026: espelho de data/contatos_uf.json (diretório oficial do MIDR; portais verificados e corrigidos por busca independente)   // 15/09/2026: espelho de data/contatos_uf.json (diretório oficial do MIDR; portais verificados e corrigidos por busca independente)   // 15/09/2026: espelho de data/contatos_uf.json (diretório oficial do MIDR; portais verificados)

// ---- Conteúdo oficial reproduzido: guias de proteção por risco (fontes nomeadas) ----
const GUIAS = {
 chuvas: { t:'Chuvas intensas, enchentes e deslizamentos',
  fonte:'Defesa Civil e Ministério da Saúde (cartilha oficial)',
  urls:[['Guia da Defesa Civil (PR)','https://www.defesacivil.pr.gov.br/Noticia/O-que-fazer-em-desastres-Defesa-Civil-orienta-populacao-sobre-antes-durante-e-depois'],
        ['Cartilha do Ministério da Saúde (PDF)','https://bvsms.saude.gov.br/bvs/publicacoes/cartilha_orientacao_populacao_chuvas_intensas.pdf']],
  blocos:[
   {h:'Antes', itens:['Guarde documentos e itens de valor em saco plástico fechado, em local alto',
    'Combine com a família um ponto de encontro e uma rota de saída',
    'Limpe calhas e não jogue lixo em córregos nem em encostas',
    'Cadastre-se nos alertas por SMS: envie seu CEP para 40199']},
   {h:'Durante', itens:['Nunca atravesse áreas alagadas: 15 cm de correnteza derrubam um adulto',
    'Se a água entrar em casa, desligue a energia e o gás',
    'Rachaduras, estalos, portas emperradas ou postes inclinados: saia imediatamente do local',
    'Vá para um ponto alto e siga as orientações da Defesa Civil (199)']},
   {h:'Depois', itens:['Beba apenas água filtrada ou fervida; não consuma alimentos que tocaram a água da enchente',
    'Evite contato com água e lama; febre ou dores no corpo dias depois: procure a saúde',
    'Não use equipamentos elétricos que foram molhados',
    'Só retorne a área de deslizamento com liberação da Defesa Civil']}]},
 fogo: { t:'Incêndios florestais e fumaça',
  fonte:'Ministério da Saúde (orientações de julho/2026, ciclo El Niño)',
  urls:[['Orientações do Ministério da Saúde','https://www.gov.br/saude/pt-br/assuntos/noticias-ms/2026/julho/ministerio-da-saude-monitora-impactos-dos-incendios-florestais-na-saude-e-orienta-populacao-sobre-exposicao-a-fumaca']],
  blocos:[
   {h:'Prevenção', itens:['Não queime lixo nem use fogo para limpar terrenos e pastagens',
    'Não descarte bitucas de cigarro em vias e vegetação; mantenha terrenos limpos',
    'Acompanhe boletins e alertas oficiais de queimadas e qualidade do ar']},
   {h:'Durante a fumaça', itens:['Aumente a ingestão de água para proteger as vias respiratórias',
    'Evite exercícios ao ar livre e mantenha portas e janelas fechadas nos horários de pico',
    'Máscaras PFF2/N95 reduzem a inalação das partículas finas',
    'Atenção redobrada: crianças menores de 5 anos, maiores de 60, gestantes e pessoas com doença cardíaca ou respiratória']},
   {h:'Sinais de alerta', itens:['Falta de ar, tontura, dor no peito, confusão mental ou dor de cabeça intensa: procure atendimento imediato',
    'Quem tem doença respiratória: mantenha os medicamentos de crise à mão']}]},
 seca: { t:'Estiagem e calor',
  fonte:'Ministério da Saúde e vigilâncias em saúde (ciclo El Niño 2026)',
  urls:[['Recomendações oficiais (Agência Gov)','https://agenciagov.ebc.com.br/noticias/202607/15-estados-na-lista-de-focos-de-calor-veja-como-se-cuidar']],
  blocos:[
   {h:'Como se preparar', itens:['Reserve água tratada e acompanhe os comunicados e rodízios da sua cidade',
    'Guarde à mão os contatos de emergência e acompanhe os boletins oficiais']},
   {h:'Como se cuidar', itens:['Aumente a ingestão de água e procure locais frescos',
    'Evite atividade física ao ar livre nas horas mais quentes',
    'Atenção redobrada com crianças, idosos e gestantes: risco de desidratação']},
   {h:'Sinais de alerta', itens:['Náusea, vômito, febre, tontura ou confusão: procure atendimento de saúde']}]}
};
function guiasDoEstado(uf){
  const r = (typeof CONSIST !== 'undefined' && CONSIST[uf]) ? CONSIST[uf].risco : '';
  const g = [];
  if (/chuva|enchent/i.test(r)) g.push('chuvas');
  if (/estiagem|seca|reservat|h[íi]dric|IIS/i.test(r)) g.push('seca');
  if (/inc[êe]ndi|fogo/i.test(r)) g.push('fogo');
  return g.length ? g : ['chuvas', 'seca', 'fogo'];
}
function htmlGuia(chave, compacto){
  const g = GUIAS[chave];
  const blocos = g.blocos.map(b => `<p class="u-mb-0"><strong>${b.h}:</strong></p><ul>${b.itens.map(i => `<li>${i}</li>`).join('')}</ul>`).join('');
  const fontes = g.urls.map(u => `<a href="${u[1]}" target="_blank" rel="noopener">${u[0]}</a>`).join(' · ');
  return `<details class="pedido-lai"><summary>${g.t}</summary>
    <div class="u-mt-2">${blocos}<p class="note">Fonte: ${g.fonte} · ${fontes}</p></div></details>`;
}

const selUF = document.getElementById('ufSelect');
Object.entries(UF_NOME).sort((a,b)=>a[1].localeCompare(b[1]))
  .forEach(([sig,nome]) => selUF.insertAdjacentHTML('beforeend', `<option value="${sig}">${nome}</option>`));
// 16/09/2026 (pedido da editoria): o site não ranqueia nem compara municípios/estados entre
// si nem contra a média nacional — ORDEM_MARE (posição no ranking) e a comparação com
// MEDIA_NACIONAL foram removidas. Cada estado mostra só a própria nota, no medidor.
function miniGauge(valor, rotulo, variante){
  // 15/09/2026: uma só arte para toda barra do site; `variante` = 'resposta' usa o preenchimento frio→quente
  // 16/09/2026 (pedido da editoria): o traço e o rótulo que marcavam a média nacional no trilho — uma
  // comparação visual entre o estado aberto e os demais — foram removidos; a barra mostra só a nota do estado.
  const resposta = variante === 'resposta';
  return `<div class="gauge-mini gauge-zone${resposta ? ' gauge-zone--resposta' : ''}">
    <div class="gauge-head">
      <span class="gnum" data-contar="${valor}">0,0</span><span class="gden">/ 100</span>
      <span class="glabel">${rotulo || 'MARÉ do estado'}</span>
    </div>
    <div class="gauge-track">
      <div class="gauge-fill${resposta ? ' gauge-fill--resposta' : ''}" data-alvo="${valor}" style="--galvo:${Math.max(valor, 0.1)};"></div>
    </div>
    <div class="gauge-ends">
      <span>0</span>
      <span>100</span>
    </div>
  </div>`;
}
window.__miniGauge = miniGauge;   // barraResposta (escopo de módulo) reutiliza o mesmo medidor do detalhe do estado
function animarGauges(root){
  const reduz = (typeof matchMedia === 'function') && matchMedia('(prefers-reduced-motion: reduce)').matches;
  const temRAF = (typeof requestAnimationFrame === 'function');
  root.querySelectorAll('.gauge-fill[data-alvo], .tile-fill[data-alvo]').forEach(f => {
    const set = () => { f.style.width = f.dataset.alvo + '%'; };
    (!temRAF || reduz) ? set() : requestAnimationFrame(() => requestAnimationFrame(set));
  });
  root.querySelectorAll('[data-contar]').forEach(el => {
    const alvo = parseFloat(el.dataset.contar);
    const fmt = (x) => x.toFixed(1).replace('.', ',');
    if (!temRAF || reduz){ el.textContent = fmt(alvo); return; }
    const dur = 1200, t0 = performance.now();
    const passo = (t) => {
      const k = Math.min(1, (t - t0) / dur);
      const e = 1 - Math.pow(1 - k, 3);
      el.textContent = fmt(alvo * e);
      if (k < 1) requestAnimationFrame(passo);
    };
    requestAnimationFrame(passo);
  });
}
const STATUS_HUMANO = {NOVO:'plano estadual novo, específico para o El Niño', READ:'plano recorrente readaptado para o ciclo',
  VIG:'instrumento recorrente, sem menção nominal ao El Niño', ELAB:'plano estadual ainda em elaboração', LAC:'sem plano estadual nominal para o El Niño'};
const nrm = s => s.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().trim();

// Decretos de emergência do município (data/atos_resposta.json — registro, nunca
// pontua). 31/08/2026: cartão e PDF diziam "nenhum decreto localizado" para Biguaçu
// enquanto o mapa 6 mostrava o decreto de 30/08 — o cartão não lia esse arquivo.
// 13/09/2026 (pedido de Patricia): o gerador de pedido de LAI pronto para o cidadão
// copiar e enviar (textoPedidoAcesso/htmlPedidoAcesso, ativo desde 31/08/2026) foi
// retirado da parte visível do site — pedidos de LAI passam a ser feitos por e-mail,
// de forma privada e centralizada pela equipe (ver gerar_lai.py e o fluxo já existente
// via monitorelnino@gmail.com), não mais pelo visitante a partir do site.
function emergenciasDoMunicipio(nome, uf){
  if (typeof ATOS_RESPOSTA === 'undefined' || !ATOS_RESPOSTA || !ATOS_RESPOSTA.eventos) return [];
  return ATOS_RESPOSTA.eventos.filter(e => e.uf === uf && nrm(e.nome) === nrm(nome))
    .sort((a,b) => (b.data||'').split('/').reverse().join('').localeCompare((a.data||'').split('/').reverse().join('')));
}
function popLinha(nome, uf){
  const c = MUN_COD[uf + '|' + nome];
  const p = c ? POP_CENSO[c] : null;
  if (!p) return '';
  const pct = POP_UF[uf] ? (100 * p / POP_UF[uf]) : 0;
  return `<p class="fk">População (Censo 2022)</p>
      <p class="fv">${p.toLocaleString('pt-BR')} habitantes <span class="u-muted">· ${pct.toFixed(1).replace('.', ',')}% do estado</span></p>`;
}
// 30/09/2026 (decisão de design da editoria): o cartão do município é MÍNIMO. Quatro coisas, nada
// mais — se o plano foi encontrado, o risco do estado no mesmo componente da ficha (`riscoBox`), o
// link do documento quando há, e o convite ao formulário quando não há. Tudo o que havia antes
// (PDF, contatos, SMS, decreto de emergência, nível de verificação, população, vigência, guias por
// risco, FGTS, "o que fazer e o que cobrar") saiu por decisão explícita: o cartão respondia a
// perguntas que ninguém fez ali, e a que importa — "minha cidade tem plano?" — se perdia no meio.
//
// O MAPEAMENTO de categoria para "encontrado / não encontrado" é da editoria, confirmado em
// 30/09/2026, e está declarado aqui em vez de espalhado por condições: quem revisar a regra lê uma
// tabela, não um emaranhado de `if`.
const PLANO_ENCONTRADO = ['plano', 'plano_novo', 'plano_readaptado', 'plano_recorrente', 'plano_antigo'];
// `coberto_estadual` conta como encontrado, com uma palavra a mais: o plano existe e é do estado.
const PLANO_ESTADUAL = ['coberto_estadual'];
// `decreto` NÃO é plano: decreto de emergência é resposta, não preparação, e a metodologia nunca os
// confundiu. `plano_elaboracao` é "ainda não", e `nao_el_nino` é ato de outro risco. Os três, mais
// `nao_localizado` e `nao_verificado`, levam ao convite para enviar o documento.
function statusDoPlano(categoria){
  if (PLANO_ENCONTRADO.includes(categoria)) return 'encontrado';
  if (PLANO_ESTADUAL.includes(categoria)) return 'estadual';
  return 'nao_encontrado';
}

// O nome como a lista de referencia do IBGE o escreve, a partir do que o visitante digitou. E por
// ele que se chega ao codigo: comparar texto normalizado e o unico casamento possivel entre o que
// se digita e a lista oficial.
function nomeOficialDe(uf, digitadoNormalizado){
  if (!uf || !digitadoNormalizado) return '';
  return (MUN_REF[uf] || []).find(n => nrm(n) === digitadoNormalizado) || '';
}

function renderMinha(){
  const card = document.getElementById('meuCard');
  const q = nrm(document.getElementById('cidadeInput').value);
  const uf = selUF.value;
  // Sem município não há cartão, com ou sem estado: o painel é do MUNICÍPIO, e o retrato do estado
  // vive na ficha do estado, logo abaixo nesta mesma página.
  if (!q){ card.hidden = true; card.innerHTML = ''; return; }

  // 07/10/2026 (A1): o municipio se resolve pelo CODIGO IBGE, que vem da lista de referencia dos
  // 5.571 — e nao do banco de planos, que cobre uma parte. O registro do banco, quando existe,
  // tambem se procura pelo codigo. Quem nao tem registro continua tendo cartao.
  const codigoDigitado = uf ? MUN_COD[uf + '|' + nomeOficialDe(uf, q)] : '';
  let matches = TABELA_MUNICIPIOS.filter(m => nrm(m.nome) === q);
  if (uf) matches = matches.filter(m => m.uf === uf);
  const porCodigo = codigoDigitado
    ? TABELA_MUNICIPIOS.filter(m => MUN_COD[m.uf + '|' + m.nome] === codigoDigitado)
    : [];
  if (porCodigo.length === 1) matches = porCodigo;
  const m = matches.length === 1 ? matches[0] : null;
  const ufFinal = uf || (m ? m.uf : '');
  card.dataset.uf = ufFinal || '';
  const nomeDigitado = document.getElementById('cidadeInput').value.trim();
  const linkFormulario = `prefeituras.html?uf=${encodeURIComponent(ufFinal)}&tipo=plano&mun=${encodeURIComponent(nomeDigitado)}`;

  let html = `<p class="note"><a href="#" id="trocarMun">← consultar outro município</a></p>
    <h4>${esc(nomeDigitado)}${ufFinal ? ' · ' + esc(ufFinal) : ''}</h4>`;

  if (matches.length > 1){
    // Com o campo de município liberado só depois do estado e a lista já filtrada por UF, este
    // ramo praticamente não ocorre — mas ocorre se alguém digitar o nome sem usar a lista. Fica
    // uma frase mínima, sem o resto do cartão.
    html += `<p>Há municípios com esse nome em mais de um estado (${esc([...new Set(matches.map(x => x.uf))].join(', '))}); selecione o seu ao lado.</p>`;
    card.innerHTML = html; card.hidden = false; return;
  }

  const status = m ? statusDoPlano(m.categoria) : 'nao_encontrado';
  if (status === 'encontrado' || status === 'estadual'){
    html += `<p class="fv"><strong>Plano de contingência localizado${status === 'estadual' ? ', no âmbito estadual' : ''}.</strong></p>`;
    /* DECISÃO DA EDITORIA, 03/10/2026: plano publicado em domínio oficial do ente conta no degrau
       que a leitura indicar, mesmo sem o ato de aprovação — e a ficha DIZ que o ato não foi
       localizado. A frase descreve o que se tem e o que não se tem, sem juízo: o índice mede
       preparação publicada, e o ato de aprovação é atributo de formalização. */
    if (m && m.sem_ato_de_aprovacao){
      html += `<p class="note">Sem ato de aprovação localizado: o plano está publicado em domínio oficial do município; o decreto ou portaria que o aprova não foi localizado até a data de corte.</p>`;
    }
  } else if (m && m.categoria === 'nao_localizado'){
    // "Não localizamos" só onde a busca DE FATO ocorreu e não achou. É o teto público de ausência
    // do projeto: nunca "não existe", e nunca sobre município que ninguém procurou.
    html += `<p class="fv"><strong>Não localizamos plano de contingência para este município até a data de corte.</strong></p>`;
  } else {
    // §6 (v2.2.4), trava de prova: município que ainda não passou pela bateria completa de fontes
    // — inclusive o que sequer tem registro no banco, que é a maioria dos 5.571 — NÃO pode receber
    // "não localizamos": isso afirmaria uma busca que não houve. O padrão é o que o dado sustenta.
    html += `<p class="fv"><strong>Ainda não verificamos este município com todas as fontes.</strong> Isso não é uma afirmação sobre a existência do plano.</p>`;
  }

  html += riscoBox(ufFinal);
  html += enquadramentoBox(ufFinal, m ? m.nome : nomeOficialDe(ufFinal, q), codigoDigitado);

  if (status === 'encontrado' || status === 'estadual'){
    const fonte = m.url
      ? `<a href="${esc(m.url)}" target="_blank" rel="noopener">${esc(m.fonte)}</a>`
      : esc(m.fonte);
    html += `<p class="fk">Onde o documento foi localizado</p><p class="fv">${fonte}</p>`;
  } else {
    html += `<p class="note">Tem o documento da sua prefeitura? <a href="${linkFormulario}">Envie pelo formulário</a> — toda entrada passa pela conferência da plataforma.</p>`;
  }

  card.innerHTML = html;
  animarGauges(card);
  card.hidden = false;
}
function popularLista(){
  const dl = document.getElementById('listaMun');
  const uf = selUF.value;
  dl.innerHTML = (uf && MUN_REF[uf] ? MUN_REF[uf] : []).map(n => `<option value="${esc(n)}">`).join('');
}
document.getElementById('cidadeInput').addEventListener('input', renderMinha);
selUF.addEventListener('change', () => {
  const campo = document.getElementById('cidadeInput');
  campo.value = '';
  // 30/09/2026: o campo de município nasce desabilitado e só abre quando há estado — mesmo padrão
  // de `prefeituras.html`. Sem isso, dava para digitar um município antes de escolher o estado e
  // cair no ramo de nome ambíguo, que o cartão mínimo não quer ter.
  campo.disabled = !selUF.value;
  popularLista();
  renderMinha();
});
document.getElementById('cidadeInput').addEventListener('focus', (e) => e.target.select());
document.getElementById('limparCidade').addEventListener('click', () => {
  const inp = document.getElementById('cidadeInput');
  inp.value = ''; renderMinha(); inp.focus();
});
document.getElementById('meuCard').addEventListener('click', (e) => {
  if (e.target && e.target.id === 'trocarMun'){
    e.preventDefault();
    const inp = document.getElementById('cidadeInput');
    inp.value = ''; renderMinha(); inp.focus(); inp.scrollIntoView({behavior:'smooth', block:'center'});
  }
});

if (typeof META !== 'undefined' && META && META.corte) {
  const el = document.getElementById('corteDados');
  if (el) el.textContent = META.corte;
}

// ---- Relatório em PDF (logo, marca d'água e rodapé institucionais) ----
const LOGO_PDF = 'data:image/png;base64,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';
// =========================================================
// RELATÓRIO PARA O CIDADÃO — um único template para estado e município
// (31/08/2026, pedido de Patricia: "esses PDFs são para usuários, não para
// auditores"). Ordem do que importa para quem mora lá: contatos de
// emergência → risco projetado → o que já existe → o que ainda falta →
// como se proteger → links úteis. Metodologia, componentes e camada
// declarada ficam fora — estão em METODOLOGIA.pdf.
// =========================================================
function gerarRelatorioCidadao(uf, municipio){
  if (!window.jspdf || !window.jspdf.jsPDF){ alert('A geração de PDF requer conexão com a internet nesta versão.'); return; }
  const v = MARE[uf], d = EST[uf], i = PCT_POR_UF[uf];
  if (!v || !d || !i) return;
  const reg = municipio ? TABELA_MUNICIPIOS.find(m => m.uf === uf && nrm(m.nome) === nrm(municipio)) : null;
  const ehCapital = municipio && d.capital && nrm(d.capital.nome) === nrm(municipio);
  const emergs = municipio ? emergenciasDoMunicipio(municipio, uf) : [];
  const doc = new window.jspdf.jsPDF({unit:'pt', format:'a4'});
  const W = doc.internal.pageSize.getWidth(), H = doc.internal.pageSize.getHeight(), M = 52;
  let y = 0;
  const INK=[21,32,26], MUTED=[85,100,91], TERRA=[124,74,52], AZUL=[53,86,107];
  const marca = () => { doc.saveGraphicsState(); doc.setGState(new doc.GState({opacity:0.07}));
    doc.setFont('helvetica','bold'); doc.setFontSize(52); doc.setTextColor(60,60,60);
    doc.text('FUTURA · EVIDENCE LAB', W/2, H/2, {angle:45, align:'center'}); doc.restoreGraphicsState(); };
  const rod = () => { doc.setFont('helvetica','normal'); doc.setFontSize(8.5); doc.setTextColor(120,110,95);
    doc.text('MARÉ · Monitor de Antecipação e Resposta ao El Niño · monitorelnino.com.br · Não substitui as orientações da Defesa Civil da sua cidade.', M, H-30);
    doc.text('© 2026 Futura Evidence Lab. Dados verificados em fontes oficiais.', M, H-18);
    doc.text('Página ' + doc.internal.getNumberOfPages(), W-M, H-18, {align:'right'}); };
  const nova = () => { rod(); doc.addPage(); marca(); y = M; };
  const par = (txt, o) => {
    o = Object.assign({tam:10.5, negrito:false, cor:INK, espaco:3, bullet:false, recuo:0}, o || {});
    doc.setFont('helvetica', o.negrito ? 'bold' : 'normal'); doc.setFontSize(o.tam); doc.setTextColor(...o.cor);
    const linhas = doc.splitTextToSize((o.bullet ? '•  ' : '') + txt, W - 2*M - o.recuo);
    const alt = linhas.length * (o.tam * 1.38) + o.espaco;
    if (y + alt > H - 60) nova();
    doc.text(linhas, M + o.recuo, y); y += alt;
  };
  const secao = (t) => { y += 10; if (y > H - 110) nova(); par(t, {tam:12.5, negrito:true, cor:TERRA, espaco:6}); };
  const item = (t) => par(t, {bullet:true, espaco:2});
  const link = (rotulo, url) => { if (!url) { item(rotulo); return; }
    const tx = rotulo + ': ' + url;
    par(tx, {bullet:true, espaco:2, cor:AZUL});
    // link clicável sobre a última linha renderizada
    doc.link(M, y - 10.5*1.38 - 2, W - 2*M, 10.5*1.38, {url}); };
  const fmt = n => String(n).replace('.', ',');

  // ---- cabeçalho ----
  marca();
  doc.addImage(LOGO_PDF, 'PNG', M, 42, 150, 56);
  doc.setFont('helvetica','bold'); doc.setFontSize(16); doc.setTextColor(...INK);
  doc.text('MARÉ · Monitor de Antecipação e Resposta ao El Niño', M, 128);
  doc.setFont('helvetica','normal'); doc.setFontSize(10); doc.setTextColor(...MUTED);
  const corte = (typeof META !== 'undefined' && META && META.corte) ? META.corte : '';
  doc.text('El Niño 2026/2027 · Corte dos dados: ' + corte + ' · Gerado em ' + new Date().toLocaleDateString('pt-BR'), M, 143);
  doc.setDrawColor(198,180,150); doc.line(M, 152, W-M, 152);
  y = 180;
  doc.setFont('helvetica','bold'); doc.setFontSize(22); doc.setTextColor(...AZUL);
  doc.text(municipio ? (municipio + ' · ' + uf) : d.nome + ' (' + uf + ')', M, y); y += 30;

  // ---- 1. Em emergência ----
  secao('Em emergência, ligue');
  par('199 — Defesa Civil     ·     193 — Corpo de Bombeiros     ·     192 — SAMU', {negrito:true, tam:12});
  item('Alertas oficiais no celular: envie seu CEP por SMS para 40199 (gratuito). O Defesa Civil Alerta avisa automaticamente, sem cadastro, em aparelhos 4G/5G.');
  const p = PORTAIS_UF[uf];
  const orgao = d.orgao || 'Defesa Civil estadual';
  item(orgao + (p ? ' — ' + p[1] : '') + (EMAILS[uf] ? ' — ' + EMAILS[uf] : ''));

  // ---- 2. Risco projetado ----
  secao('Risco projetado para ' + d.nome + ' neste ciclo');
  const risco = (typeof CONSIST !== 'undefined' && CONSIST[uf]) ? CONSIST[uf].risco : '';
  par((risco || 'Sem sinal elevado projetado para o trimestre') + '.');
  par('Fonte: Boletins nº 1 e 2 do Painel El Niño 2026/2027 (Governo Federal). Os boletins são mensais; consulte o mais recente.', {tam:9.5, cor:MUTED});

  // ---- 3. O que já existe ----
  secao('O que já existe');
  item('Estado: ' + STATUS_HUMANO[v.status_estadual] + (v.status_estadual !== 'LAC' && d.doc ? ' — ' + d.doc + (d.data ? ' (' + d.data + ')' : '') : '') + '.');
  if (FIN && FIN[uf] && FIN[uf].status === 'localizado')
    item('Recurso preventivo estadual: ' + FIN[uf].instrumento + ' (' + FIN[uf].norma + '), repassado antes do dano, condicionado a ' + FIN[uf].condicionalidade + '.');
  if (municipio) {
    if (reg && reg.categoria !== 'nao_localizado') {
      const lbl = CAT_LABEL_TBL[reg.categoria][0];
      const doc_ = (reg.documento && reg.documento !== '—') ? ' — ' + reg.documento : '';
      const dat_ = (reg.data && reg.data !== '—') ? ' (' + reg.data + ')' : '';
      const fon_ = (reg.fonte && reg.fonte !== '—') ? '. Fonte: ' + reg.fonte : '';
      item(municipio + ': ' + lbl + doc_ + dat_ + fon_ + '.');
    } else if (reg) {
      item(municipio + ': verificado individualmente — nenhum ' + (emergs.length ? 'plano preventivo' : 'plano ou decreto') + ' publicado em fonte pública até o corte.');
    } else {
      item(municipio + ': nenhum ' + (emergs.length ? 'plano preventivo' : 'plano ou decreto') + ' publicado em fonte pública até o corte.');
    }
    if (typeof HAB_SET !== 'undefined' && HAB_SET.has(nrm(municipio) + '|' + uf))
      item('Reconhecimento federal vigente: o município pode solicitar recursos de resposta pelo S2iD.');
    // 08/10/2026 (A3-07): `e.data` nos eventos do DOU é a data do RECONHECIMENTO, não a do
    // decreto — a frase dizia "decretou em 02/09" sobre um decreto de 17/08. As duas datas são
    // coisas diferentes e agora aparecem as duas, cada uma com o seu nome.
    emergs.forEach(e => {
      const dDec = e.data_decreto_municipal || e.data;
      const dRec = e.data_reconhecimento || (String(e.causa || '').indexOf('reconhecimento') >= 0 ? e.data : '');
      const quando = (dRec && dRec !== dDec)
        ? 'decreto municipal em ' + dDec + '; reconhecimento federal em ' + dRec
        : 'decreto municipal em ' + dDec;
      item(municipio + ': ' + quando + ' (' + e.causa + '). Ato de resposta a dano já ocorrido — não conta para o índice. Fonte: ' + e.fonte + '.');
    });
  } else if (d.capital) {
    const regCap = regDaCapital(d);
    item('Capital (' + d.capital.nome + '): ' + textoDaCapital(regCap).replace(/<[^>]*>/g, ''));
  }
  if (uf !== 'DF') item('Municípios do estado com algum ato localizado: ' + i.com_ato + ' de ' + i.total + ' (' + fmt(i.pct) + '%) — ' + i.n_plano + ' com plano preventivo, ' + i.n_decreto + ' com decreto de emergência.');  // DF: o único município é Brasília, já descrita como capital
  const fx = v.total < 25 ? 'estágio inicial' : v.total < 50 ? 'em construção' : v.total < 70 ? 'consolidado' : 'avançado';
  item('No índice MARÉ, ' + d.nome + ' está em ' + fmt(v.total) + '/100 (' + fx + ').');
  // 24/09/2026: o PDF é gerado pelo cartão e tinha de dizer a mesma coisa que ele — o cartão passou a
  // mostrar a barra de resposta, e aqui a mesma grandeza entra em texto. Os dois índices não se somam (C17).
  { const _r = RESP && RESP.uf && RESP.uf[uf];
    if (_r) item('Índice de resposta (população em município sob decreto de emergência no ciclo): ' + fmt(indiceResposta(_r)) + '/100 — ' + _r.n_municipios + ' de ' + _r.total_municipios + ' municípios. Mede reação a dano ocorrido; não se soma ao MARÉ, que mede antecipação.'); }

  // ---- 4. O que ainda falta ----
  secao('O que ainda falta — e o que cobrar');
  const faltas = [];
  if (v.status_estadual === 'LAC') faltas.push('O estado ainda não publicou plano estadual nominal para o El Niño. É o primeiro item a cobrar da Defesa Civil estadual.');
  if (v.status_estadual === 'ELAB') faltas.push('O plano estadual está em elaboração e ainda não foi publicado. Pergunte a data prevista de publicação.');
  if (v.status_estadual === 'VIG') faltas.push('O instrumento estadual é recorrente e não menciona o El Niño 2026/2027. Pergunte se haverá atualização específica para o ciclo.');
  if (municipio) {
    const cat = reg ? reg.categoria : null;
    const _nivF = nivelVerificacao(uf, municipio);
    if (cat === 'nao_localizado' && _nivF === 'municipal_completo') faltas.push('Após verificação individual completa, não localizamos plano de contingência da sua cidade. Peça à prefeitura pela ouvidoria ou e-SIC (Lei 12.527/2011): resposta obrigatória em 20 dias.');
    else if (!cat || cat === 'nao_localizado' || cat === 'nao_verificado') faltas.push('Ainda não verificamos sua cidade com a bateria completa de fontes. Peça o documento à prefeitura pela ouvidoria ou e-SIC (Lei 12.527/2011, resposta em até 20 dias) e envie pelo formulário no fim desta página.');
    else if (cat === 'plano_antigo') faltas.push('O plano da sua cidade é de edição anterior. Pergunte à prefeitura se há atualização para 2026/2027.');
    else if (cat === 'decreto') faltas.push('Sua cidade tem decreto de emergência (resposta a dano ocorrido), mas não localizamos plano preventivo. Pergunte à prefeitura se existe e onde está publicado.');
    else if (cat === 'plano_elaboracao') faltas.push('O plano da sua cidade está em elaboração. Pergunte a data prevista.');
    else if (cat === 'nao_el_nino') faltas.push('O ato localizado na sua cidade não trata do El Niño. Pergunte se há plano específico para o ciclo.');
    else if (cat === 'coberto_estadual') faltas.push('Sua cidade está coberta pelo plano estadual, sem plano próprio. Cobertura estadual é operacional: o dever de ter plano municipal continua (Lei 12.608, art. 8º).');
    if (emergs.length && cat !== 'plano') faltas.push('Sua cidade já precisou decretar emergência neste ciclo. Um plano preventivo publicado reduz o improviso da próxima vez.');
  } else if (d.capital) {
    // A lacuna da capital sai da MESMA fonte do resto: a categoria do banco, nunca o texto
    // escrito à mão em `estados.json` (A3-11).
    const regCap = regDaCapital(d);
    const catCap = regCap ? regCap.categoria : '';
    if (!catCap || catCap === 'nao_verificado') faltas.push('Ainda não verificamos a capital com a bateria completa de fontes.');
    else if (catCap === 'nao_localizado') faltas.push('Não localizamos plano de contingência da capital até o corte.');
    else if (catCap === 'plano_elaboracao') faltas.push('O plano da capital está em elaboração; o documento final não foi localizado até o corte.');
    else if (catCap === 'plano_nomeado') faltas.push('O plano da capital é citado em fonte oficial, e o documento não foi localizado até o corte.');
    else if (catCap === 'estrutura') faltas.push('Na capital localizamos estrutura de coordenação, não plano de contingência para os riscos do ciclo.');
  }
  if (i.com_ato === 0) faltas.push('Nenhum ato municipal localizado no estado até o corte.');
  else if (i.n_decreto > i.n_plano) faltas.push('No estado, predominam decretos de emergência sobre planos preventivos: a resposta vem depois do dano.');
  if (!faltas.length) faltas.push('Nenhuma lacuna crítica localizada até o corte. Confirme se o plano está atualizado para 2026/2027 e conheça a rota de saída do seu bairro.');
  par('Nível de verificação desta cidade: ' + NIVEL_ROTULO[nivelVerificacao(uf, municipio)] + '.', {tam:9.5, cor:MUTED, espaco:4});
  faltas.forEach(item);
  par('O planejamento federal de 29/07/2026 (Sala de Situação do El Niño, 24 ministérios) prevê a atualização dos planos de contingência, com identificação de áreas de risco e fortalecimento das estruturas locais de resposta — é um compromisso público, e vale como argumento ao cobrar o estado e a prefeitura.', {tam:9.5, cor:MUTED, espaco:4});

  // 13/09/2026 (pedido de Patricia): seção 'Pedido de informação pronto' (Lei de Acesso à
  // Informação) retirada do PDF do cidadão — pedidos de LAI passam a ser feitos por e-mail,
  // de forma privada, não mais gerados para o visitante copiar e enviar.

  // ---- 5. Como se proteger ----
  const chaves = guiasDoEstado(uf);
  secao('Como se proteger' + (chaves.length < 3 ? ' — riscos projetados para o estado' : ''));
  chaves.forEach(ch => {
    const g = GUIAS[ch];
    par(g.t, {negrito:true, tam:11, espaco:4});
    g.blocos.forEach(b => { par(b.h + ':', {negrito:true, tam:10, cor:MUTED, espaco:1, recuo:8}); b.itens.forEach(it => par(it, {bullet:true, espaco:1, recuo:8})); });
    par('Fonte: ' + g.fonte + '.', {tam:9, cor:MUTED, espaco:6, recuo:8});
  });

  // ---- 6. Links úteis ----
  secao('Links úteis');
  if (p && !/^tel:/.test(p[0])) link('Defesa Civil estadual', p[0]);
  if (reg && reg.url) link('Documento localizado (' + reg.fonte + ')', reg.url);
  if (DOM_LINKS[uf]) link('Diário Oficial dos Municípios', DOM_LINKS[uf]);
  link('Defesa Civil Alerta (cadastro e informações)', 'https://www.gov.br/mdr/pt-br/assuntos/protecao-e-defesa-civil/defesa-civil-alerta');
  link('Painel El Niño 2026/2027 — Boletim nº 3, 01/09/2026 (INPE/Cemaden, PDF)', 'https://www.gov.br/cemaden/pt-br/assuntos/monitoramento/el-nino/boletim-do-painel-el-nino-ndeg-03-agosto-de-2026-potenciais-impactos-e-orientacoes/painel-el-nino-3-edicao.pdf');
  link('Painel El Niño 2026/2027 — Boletim nº 1, 29/06/2026 (CEMADEN)', 'https://www.gov.br/cemaden/pt-br/lancado-o-primeiro-boletim-do-painel-do-el-nino-2026-2027-apresentando-potenciais-impactos-e-orientacoes');
  link('Este relatório atualizado, e os demais estados e cidades', 'https://monitorelnino.com.br');

  rod();
  doc.save(municipio ? 'relatorio-el-nino-' + uf + '-' + nrm(municipio).replace(/\s+/g,'-') + '.pdf' : 'relatorio-el-nino-' + uf + '.pdf');
}
function gerarPDF(){
  const uf = selUF.value || (document.getElementById('meuCard').dataset.uf || '');
  const cid = document.getElementById('cidadeInput').value.trim();
  if (!uf) { alert('Selecione o estado.'); return; }
  gerarRelatorioCidadao(uf, cid || null);
}
document.getElementById('meuCard').addEventListener('click', (e) => {
  if (e.target && e.target.id === 'btnPDF') gerarPDF();
});
// Copiar o pedido de informação (cartão da cidade e detalhe do estado).
function copiarPedido(botao){
  const ta = botao.parentElement.querySelector('.pedido-texto');
  const feito = () => { const t0 = botao.textContent; botao.textContent = 'Copiado'; setTimeout(() => { botao.textContent = t0; }, 2000); };
  if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(ta.value).then(feito, () => { ta.select(); document.execCommand('copy'); feito(); });
  else { ta.select(); document.execCommand('copy'); feito(); }
}
['meuCard', 'detail'].forEach(id => document.getElementById(id).addEventListener('click', (e) => {
  const b = e.target && e.target.closest && e.target.closest('.btn-copiar-pedido');
  if (b) copiarPedido(b);
}));

// ---- Relatório de ESTADO em PDF (conteúdo próprio: veredito, componentes, capital, cobertura, cobranças) ----


// ---- Herói: barra do MARÉ + faixa temporal ----
(function(){
  const fill = document.getElementById('gaugeFill');
  // 03/09/2026: o alvo da barra e do contador vem do ÍNDICE calculado (data/indice.json), não do
  // HTML — o valor gravado (data-alvo) é só fallback e é regravado por recalcular_mare.py --write.
  try {
    if (typeof MARE === 'object' && MARE) {
      const tot = Object.keys(MARE).filter(k => k.length === 2 && MARE[k] && typeof MARE[k].total === 'number').map(k => MARE[k].total);
      if (tot.length === 27) {
        const media = Math.round((tot.reduce((a, b) => a + b, 0) / 27) * 10) / 10;
        fill.dataset.alvo = String(media); fill.style.setProperty('--galvo', String(media));
        const tr = fill.closest('.gauge-track'); if (tr) tr.setAttribute('aria-label', 'Barra de progresso: MARÉ nacional em ' + media.toLocaleString('pt-BR', {minimumFractionDigits: 1}) + ' de 100');
        const nEl = document.getElementById('gaugeNum'); if (nEl) nEl.textContent = media.toLocaleString('pt-BR', {minimumFractionDigits: 1});
      }
    }
  } catch (e) {}
  // 30/09/2026 (item 4 da fila viva): a frase-resumo "N estados com plano para o ciclo..."
  // saiu da inicial. Ela já tinha migrado de defesa-civil.html em 18/09; não se recria em
  // nenhum outro lugar sem novo pedido.
  const temRAF = (typeof requestAnimationFrame === 'function');
  const raf = temRAF
    ? (f) => requestAnimationFrame(() => requestAnimationFrame(f))
    : (f) => setTimeout(f, 60);
  raf(() => { fill.style.width = fill.dataset.alvo + '%'; });
  // contador subindo em sincronia com a barra
  const numEl = document.getElementById('gaugeNum');
  const alvo = parseFloat(fill.dataset.alvo);
  const reduz = (typeof matchMedia === 'function') && matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (!temRAF || reduz){
    numEl.textContent = alvo.toFixed(1).replace('.', ',');
  } else {
    const dur = 1400, t0 = performance.now();
    const passo = (t) => {
      const k = Math.min(1, (t - t0) / dur);
      const e = 1 - Math.pow(1 - k, 3);
      numEl.textContent = (alvo * e).toFixed(1).replace('.', ',');
      if (k < 1) requestAnimationFrame(passo);
    };
    requestAnimationFrame(passo);
  }
  const strip = document.getElementById('heroStrip');
  if (!strip) return;   // 15/09/2026: a linha do tempo saiu da inicial (pedido da editoria); código guardado para reuso
  const d0 = -89;   // 01/04/2026, em dias relativos ao Boletim nº 1
  const __corteParts = ((typeof META !== 'undefined' && META && META.corte) || '25/08/2026').split('/').map(Number);
  const d1 = Math.round((new Date(__corteParts[2], __corteParts[1]-1, __corteParts[0]) - new Date(2026, 5, 29)) / 86400000);   // corte lido de meta.json
  { const sc = document.getElementById('stripCorte'); if (sc && typeof META !== 'undefined' && META && META.corte) sc.textContent = META.corte; }
  // faixa derivada dos dados vivos (27/08): Boletim nº 1 + datas reais dos instrumentos estaduais
  const __MARCO = new Date(2026, 5, 29);
  const timelineData = [{days: 0, label: 'Boletim nº 1 · Painel El Niño', quando: '29/06/2026', doc: ''}];
  DATA.ufs.forEach(u => {
    const m = /^(\d{2})\/(\d{2})\/(\d{4})$/.exec(u.data || '');
    if (!m || u.status === 'LAC') return;
    const dias = Math.round((new Date(+m[3], +m[2] - 1, +m[1]) - __MARCO) / 86400000);
    if (dias >= d0 && dias <= d1) timelineData.push({days: dias, label: u.uf + ': instrumento estadual', quando: u.data, doc: u.doc || ''});
  });
  timelineData.forEach(ev => {
    const t = document.createElement('span');
    t.className = 'strip-tick' + (ev.days === 0 ? ' boletim' : '');
    t.setAttribute('role', 'img');
    t.style.left = (100 * (ev.days - d0) / (d1 - d0)).toFixed(2) + '%';
    t.setAttribute('tabindex', '0');
    t.setAttribute('aria-label', ev.label + (ev.quando ? ' · ' + ev.quando : ''));
    const mostrar = (evt) => {
      const b = t.getBoundingClientRect();
      showTip(`<strong>${esc(ev.label)}</strong>${ev.quando ? '<br>' + esc(ev.quando) : ''}${ev.doc ? '<br>' + esc(ev.doc) : ''}`,
        evt.clientX ? evt : {clientX: b.x + b.width/2, clientY: b.y});
    };
    t.addEventListener('mouseenter', mostrar);
    t.addEventListener('focus', mostrar);
    t.addEventListener('mouseleave', hideTip);
    t.addEventListener('blur', hideTip);
    strip.appendChild(t);
  });
})();


}
__load().catch(err => {
  document.body.insertAdjacentHTML('afterbegin',
    '<div class="erro-carga">' +
    'Erro ao carregar os dados: ' + err.message +
    '. Sirva a pasta via HTTP (ex.: <code>npx serve</code>) — abrir o arquivo diretamente bloqueia o fetch.</div>');
});

// Faixa interpretativa do MARÉ (cortes normativos declarados na Metodologia §5.6)
// Selo visual (não mais palavra colorida solta em frase corrida) — os nomes e
// limites de cada faixa já ficam explícitos nos marcos da barra logo abaixo,
// então aqui só se declara em qual faixa o país está agora (31/08/2026).
(function(){
  var g = document.getElementById('gaugeNum'), el = document.getElementById('faixaMare');
  if (!g || !el) return;
  var v = parseFloat(g.textContent.replace(',', '.'));
  // [rótulo, fundo, texto] — pares conferidos contra WCAG AA (4,5:1) em 31/08/2026:
  // ferrugem/claro 6,45 · tan/escuro 6,65 · oliva escurecido/claro ≥4,5 · azul/claro 6,91
  var fx = MonitorMapas.PALETA.faixaDe(v); var f = [MonitorMapas.PALETA.faixaRotulo[fx], MonitorMapas.PALETA.faixas[fx], MonitorMapas.PALETA.faixasTexto[fx]];
  el.innerHTML = 'Preparação demonstrada<span class="gfaixa-pill" style="background:' + f[1] + '; color:' + f[2] + '">' + f[0] + '</span>';
})();

// ===== index.html · bloco 3 (extraído em 06/09/2026, CSP sem unsafe-inline) =====
window.addEventListener('load', function(){ if (window.VLibras && window.VLibras.Widget) { try { new window.VLibras.Widget('https://vlibras.gov.br/app'); } catch (e) {} } });

// ===== formulário "Indique um documento publicado" (migrou de pesquisadores.html para o fim do MARÉ Legal em 16/09/2026) =====
(function(){
  const p = new URLSearchParams(location.search); if (!document.getElementById('cUF')) return;
  const set = (id, v) => { const el = document.getElementById(id); if (el && v) el.value = v; };
  set('cUF', (p.get('uf') || '').toUpperCase());
  // Lista de municípios por UF (malha IBGE): carga preguiçosa, com degradação graciosa
  let __refMun = null;
  async function preencherMunicipios(){
    const uf = document.getElementById('cUF').value;
    const dl = document.getElementById('listaMunEnvio');
    // 30/09/2026 (§311): o campo de município nasce desabilitado e abre com o estado — mesmo
    // padrão do cartão da cidade e de `prefeituras.html`. Digitar município sem estado enviava
    // um nome que a lista não podia validar.
    const campo = document.getElementById('cMunicipio');
    if (campo) campo.disabled = !uf;
    if (!uf){ dl.innerHTML = ''; return; }
    try {
      if (!__refMun){
        __refMun = window.__MUN_REF__ || await fetch('data/municipios_ibge_referencia.json').then(r => r.json());
      }
          dl.innerHTML = __refMun.filter(m => m.uf === uf)
        .map(m => esc(m.nome)).sort((a, b) => a.localeCompare(b))
        .map(n => `<option value="${n}">`).join('');
    } catch (e) { dl.innerHTML = ''; /* offline/prévia sem dados: campo segue como texto livre */ }
  }
  document.getElementById('cUF').addEventListener('change', preencherMunicipios);
  preencherMunicipios();
  // Quando a URL traz `?uf=...&mun=...` (o convite do cartão do município), o campo precisa estar
  // aberto antes de receber o valor.
  if (p.get('uf')) { const c = document.getElementById('cMunicipio'); if (c) c.disabled = false; }
  set('cMunicipio', p.get('mun') || '');
  set('cTipo', p.get('tipo') || '');
  // Produção = domínio final OU o subdomínio temporário *.netlify.app (útil para testar
  //   nas Partes 2-3 do guia de publicação, antes do DNS do domínio próprio propagar).
  // Qualquer outro host (prévia local, file://, artefato de visualização) mantém o
  //   formulário desativado — Netlify Forms só funciona quando hospedado de fato.
  const ehProducao = /\.netlify\.app$/.test(location.hostname) || /(^|\.)monitorelnino\.com\.br$/.test(location.hostname);
  if (!ehProducao){
    const off = document.getElementById('contribOffline'); if (off) off.textContent = 'Nesta prévia local o envio fica desativado; na versão publicada, funciona.';
    document.getElementById('formContrib').addEventListener('submit', (e) => { e.preventDefault();
      alert('Prévia local: o envio do formulário funciona apenas na versão publicada do site.'); });
  }
})();
